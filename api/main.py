"""
Lecture Transcriber — FastAPI Backend
Handles audio upload, transcription via Whisper or Grok, language detection,
export, and AI-powered assignment generation.
"""

import os
import uuid
import asyncio
import magic
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from transcribe import transcribe_audio
from transcribe_grok import transcribe_audio_grok
from language_detect import detect_language_mix
from export import export_transcript, cleanup_export
from assignment import generate_assignment
from redis_store import (
    set_job,
    get_job,
    delete_job as redis_delete_job,
    job_exists,
    update_job_status,
    health_check as redis_health_check,
)

# ── App Setup ──────────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Lecture Transcriber API",
    description="Hindi & English lecture transcription with Whisper and Grok support, plus AI assignment generation",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
ALLOWED_TYPES = {
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/webm",
    "video/mp4",  "audio/mp4", "audio/x-wav",
}
ALLOWED_MAGIC = {
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/webm",
    "video/mp4",  "audio/mp4", "audio/x-m4a",
}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Lecture Transcriber API is running 🎙️"}


@app.get("/health")
async def health():
    redis_status = redis_health_check()
    return {
        "status": "ok" if redis_status["status"] == "ok" else "degraded",
        "redis":  redis_status,
    }


@app.post("/api/transcribe", status_code=202)
@limiter.limit("10/minute")
async def start_transcription(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language_hint: str = Form("auto"),
    script: str = Form("devanagari"),
    provider: str = Form("whisper"),
):
    """
    Upload an audio/video file and start async transcription.
    Returns a job_id to poll for results.
    Provider 'grok' supports larger files and longer videos.
    """
    if language_hint not in ("auto", "hi", "en"):
        raise HTTPException(status_code=400, detail="language_hint must be 'auto', 'hi', or 'en'")
    if script not in ("devanagari", "roman"):
        raise HTTPException(status_code=400, detail="script must be 'devanagari' or 'roman'")
    if provider not in ("whisper", "grok"):
        raise HTTPException(status_code=400, detail="provider must be 'whisper' or 'grok'")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: mp3, wav, ogg, webm, mp4",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    real_mime = magic.from_buffer(content, mime=True)
    if real_mime not in ALLOWED_MAGIC:
        raise HTTPException(
            status_code=415,
            detail=f"File content does not match an allowed audio/video type (detected: {real_mime})",
        )

    safe_filename = file.filename or "upload"
    suffix        = Path(safe_filename).suffix or ".mp3"
    job_id        = str(uuid.uuid4())
    audio_path    = UPLOAD_DIR / f"{job_id}{suffix}"
    audio_path.write_bytes(content)

    set_job(job_id, {"status": "processing", "job_id": job_id, "provider": provider})

    background_tasks.add_task(
        run_transcription,
        job_id=job_id,
        audio_path=str(audio_path),
        language_hint=language_hint,
        script=script,
        provider=provider,
    )

    return {"job_id": job_id, "status": "processing", "provider": provider}


@app.get("/api/transcribe/{job_id}")
async def get_transcription(job_id: str):
    """Poll for transcription result."""
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return get_job(job_id)


@app.get("/api/export/{job_id}")
async def export(job_id: str, format: str = "txt"):
    """Download transcript as TXT, PDF, or SRT."""
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    job = get_job(job_id)
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail="Transcription not complete yet")
    if format not in ("txt", "pdf", "srt"):
        raise HTTPException(status_code=400, detail="Format must be txt, pdf, or srt")

    out_path     = export_transcript(job_id, job, format)
    export_paths = job.get("export_paths", [])
    export_paths.append(out_path)
    job["export_paths"] = export_paths
    set_job(job_id, job)

    media_types = {"txt": "text/plain", "pdf": "application/pdf", "srt": "text/plain"}
    return FileResponse(
        out_path,
        media_type=media_types[format],
        filename=f"transcript_{job_id[:8]}.{format}",
    )


@app.post("/api/assignment/{job_id}", status_code=200)
@limiter.limit("5/minute")
async def create_assignment(
    request: Request,
    job_id: str,
    question_types: List[str] = Form(["mcq", "short_answer", "true_false"]),
    difficulty: str           = Form("medium"),
    num_questions: int        = Form(10),
):
    """
    Generate a practice assignment from a completed transcript.
    Powered by Claude (Anthropic).
    """
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    job = get_job(job_id)
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail="Transcription not complete yet")

    if difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="difficulty must be easy, medium, or hard")
    if not 1 <= num_questions <= 50:
        raise HTTPException(status_code=400, detail="num_questions must be between 1 and 50")

    valid_types = {"mcq", "short_answer", "true_false"}
    invalid     = set(question_types) - valid_types
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid question types: {invalid}")

    full_text = job.get("full_text", "")
    if not full_text:
        raise HTTPException(status_code=422, detail="Transcript has no text content")

    try:
        assignment = await asyncio.to_thread(
            generate_assignment,
            full_text=full_text,
            question_types=question_types,
            difficulty=difficulty,
            num_questions=num_questions,
            language=job.get("detected_language", "en"),
        )
        return assignment
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Assignment generation failed: {str(exc)}")


@app.delete("/api/transcribe/{job_id}")
async def delete_job_route(job_id: str):
    """Clean up a job, its audio file, and any exported files."""
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    for f in UPLOAD_DIR.glob(f"{job_id}*"):
        f.unlink(missing_ok=True)

    cleanup_export(job_id)
    redis_delete_job(job_id)
    return {"message": "Job deleted"}


# ── Background Task ────────────────────────────────────────────────────────────

async def run_transcription(
    job_id: str,
    audio_path: str,
    language_hint: str,
    script: str,
    provider: str = "whisper",
):
    """Background task: transcribe audio using selected provider and store result."""
    try:
        if provider == "grok":
            result = await asyncio.to_thread(
                transcribe_audio_grok,
                audio_path=audio_path,
                language_hint=language_hint,
                script=script,
            )
        else:
            result = await asyncio.to_thread(
                transcribe_audio,
                audio_path=audio_path,
                language_hint=language_hint,
                script=script,
            )

        language_mix           = detect_language_mix(result["segments"])
        result["language_mix"] = language_mix
        result["job_id"]       = job_id
        result["status"]       = "done"

        set_job(job_id, result)

    except Exception as exc:
        set_job(job_id, {
            "job_id":   job_id,
            "status":   "error",
            "error":    str(exc),
            "provider": provider,
        })
    finally:
        for f in UPLOAD_DIR.glob(f"{job_id}*"):
            f.unlink(missing_ok=True)


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
