"""
Lecture Transcriber — FastAPI Backend
Handles audio upload, transcription via Whisper, language detection, and export.
"""

import os
import uuid
import asyncio
import magic                          # python-magic: validates real file type
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from transcribe import transcribe_audio
from language_detect import detect_language_mix
from export import export_transcript, cleanup_export   # FIX: import cleanup helper

# ── App Setup ──────────────────────────────────────────────────────────────────

# FIX: rate limiter — prevents upload abuse
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Lecture Transcriber API",
    description="Hindi & English lecture transcription with automatic language detection",
    version="1.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

RESULTS: dict = {}   # In-memory store; swap for Redis in production

MAX_FILE_SIZE   = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
ALLOWED_TYPES   = {
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/webm",
    "video/mp4",  "audio/mp4", "audio/x-wav",
}
# FIX: magic-byte signatures for the same formats (used for real validation)
ALLOWED_MAGIC   = {
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/webm",
    "video/mp4",  "audio/mp4", "audio/x-m4a",
}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Lecture Transcriber API is running 🎙️"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/transcribe", status_code=202)
@limiter.limit("10/minute")           # FIX: rate limit uploads per IP
async def start_transcription(
    request: Request,                 # required by slowapi
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language_hint: str = Form("auto"),
    script: str = Form("devanagari"),
):
    """
    Upload an audio file and start async transcription.
    Returns a job_id to poll for results.
    """
    # FIX: validate language_hint and script values explicitly
    if language_hint not in ("auto", "hi", "en"):
        raise HTTPException(status_code=400, detail="language_hint must be 'auto', 'hi', or 'en'")
    if script not in ("devanagari", "roman"):
        raise HTTPException(status_code=400, detail="script must be 'devanagari' or 'roman'")

    # FIX: validate content-type header (first line of defence)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: mp3, wav, ogg, webm, mp4",
        )

    # Read and size-check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # FIX: validate real MIME type via magic bytes — can't be spoofed by the client
    real_mime = magic.from_buffer(content, mime=True)
    if real_mime not in ALLOWED_MAGIC:
        raise HTTPException(
            status_code=415,
            detail=f"File content does not match an allowed audio/video type (detected: {real_mime})",
        )

    # FIX: guard against None filename
    safe_filename = file.filename or "upload"
    suffix        = Path(safe_filename).suffix or ".mp3"

    job_id     = str(uuid.uuid4())
    audio_path = UPLOAD_DIR / f"{job_id}{suffix}"
    audio_path.write_bytes(content)

    RESULTS[job_id] = {"status": "processing", "job_id": job_id}

    background_tasks.add_task(
        run_transcription,
        job_id=job_id,
        audio_path=str(audio_path),
        language_hint=language_hint,
        script=script,
    )

    return {"job_id": job_id, "status": "processing"}


@app.get("/api/transcribe/{job_id}")
async def get_transcription(job_id: str):
    """Poll for transcription result."""
    if job_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Job not found")
    return RESULTS[job_id]


@app.get("/api/export/{job_id}")
async def export(job_id: str, format: str = "txt"):
    """Download transcript as TXT, PDF, or SRT."""
    if job_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = RESULTS[job_id]
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail="Transcription not complete yet")

    if format not in ("txt", "pdf", "srt"):
        raise HTTPException(status_code=400, detail="Format must be txt, pdf, or srt")

    out_path = export_transcript(job_id, job, format)

    # FIX: track export paths so delete_job can clean them up
    RESULTS[job_id].setdefault("export_paths", []).append(out_path)

    media_types = {"txt": "text/plain", "pdf": "application/pdf", "srt": "text/plain"}
    return FileResponse(
        out_path,
        media_type=media_types[format],
        filename=f"transcript_{job_id[:8]}.{format}",
    )


@app.delete("/api/transcribe/{job_id}")
async def delete_job(job_id: str):
    """Clean up a job, its audio file, and any exported files."""
    if job_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove uploaded audio
    for f in UPLOAD_DIR.glob(f"{job_id}*"):
        f.unlink(missing_ok=True)

    # FIX: remove all export files for this job
    cleanup_export(job_id)

    del RESULTS[job_id]
    return {"message": "Job deleted"}


# ── Background Task ────────────────────────────────────────────────────────────

async def run_transcription(
    job_id: str,
    audio_path: str,
    language_hint: str,
    script: str,
):
    """Background task: transcribe audio and store result."""
    try:
        result = await asyncio.to_thread(
            transcribe_audio,
            audio_path=audio_path,
            language_hint=language_hint,
            script=script,
        )

        language_mix      = detect_language_mix(result["segments"])
        result["language_mix"] = language_mix
        result["job_id"]  = job_id
        result["status"]  = "done"

        RESULTS[job_id] = result

    except Exception as exc:
        RESULTS[job_id] = {
            "job_id": job_id,
            "status": "error",
            "error":  str(exc),
        }
    finally:
        # FIX: always remove the uploaded audio once transcription finishes
        for f in UPLOAD_DIR.glob(f"{job_id}*"):
            f.unlink(missing_ok=True)


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
