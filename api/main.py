"""
Lecture Transcriber — FastAPI Backend
Handles audio upload, transcription via Whisper, language detection, and export.
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from transcribe import transcribe_audio
from language_detect import detect_language_mix
from export import export_transcript

# ── App Setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Lecture Transcriber API",
    description="Hindi & English lecture transcription with automatic language detection",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

RESULTS: dict = {}  # In-memory store; swap for Redis in production

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
ALLOWED_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/webm",
                 "video/mp4", "audio/mp4", "audio/x-wav"}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Lecture Transcriber API is running 🎙️"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/transcribe", status_code=202)
async def start_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language_hint: str = Form("auto"),   # "auto" | "hi" | "en"
    script: str = Form("devanagari"),    # "devanagari" | "roman"
):
    """
    Upload an audio file and start async transcription.
    Returns a job_id to poll for results.
    """
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. "
                   f"Allowed: mp3, wav, ogg, webm, mp4"
        )

    # Read and size-check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed: {MAX_FILE_SIZE // (1024*1024)} MB"
        )

    # Save to disk
    job_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix or ".mp3"
    audio_path = UPLOAD_DIR / f"{job_id}{suffix}"
    audio_path.write_bytes(content)

    # Register job
    RESULTS[job_id] = {"status": "processing", "job_id": job_id}

    # Start background transcription
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
    media_types = {"txt": "text/plain", "pdf": "application/pdf", "srt": "text/plain"}

    return FileResponse(
        out_path,
        media_type=media_types[format],
        filename=f"transcript_{job_id[:8]}.{format}",
    )


@app.delete("/api/transcribe/{job_id}")
async def delete_job(job_id: str):
    """Clean up a job and its audio file."""
    if job_id not in RESULTS:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove audio files
    for f in UPLOAD_DIR.glob(f"{job_id}*"):
        f.unlink(missing_ok=True)

    del RESULTS[job_id]
    return {"message": "Job deleted"}


# ── Background Task ─────────────────────────────────────────────────────────────

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

        # Enrich with language mix stats
        language_mix = detect_language_mix(result["segments"])
        result["language_mix"] = language_mix
        result["job_id"] = job_id
        result["status"] = "done"

        RESULTS[job_id] = result

    except Exception as exc:
        RESULTS[job_id] = {
            "job_id": job_id,
            "status": "error",
            "error": str(exc),
        }


# ── Entry Point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
