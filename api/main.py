"""Lecture Transcriber — FastAPI Backend"""
import os
import uuid
import asyncio
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
import redis_store

app = FastAPI(title="Teacher Lecture Automation Suite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHISPER_MODEL  = os.getenv("WHISPER_MODEL", "whisper-1")
LANGUAGE_HINT  = os.getenv("LANGUAGE_HINT", "auto")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    error: Optional[str] = None
    result: Optional[dict] = None

def validate_audio_bytes(header: bytes) -> bool:
    allowed_signatures = [
        b'\xff\xfb', b'ID3', b'RIFF', b'OggS',
        b'\x00\x00\x00\x18ftypmp4',
    ]
    return any(header.startswith(sig) for sig in allowed_signatures)

@app.post("/transcribe", response_model=JobResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

    if not validate_audio_bytes(content[:16]):
        raise HTTPException(status_code=400, detail="Invalid audio file format")

    job_id = str(uuid.uuid4())
    redis_store.set_job(job_id, {"job_id": job_id, "status": "processing", "progress": 0})
    asyncio.create_task(process_transcription(job_id, file.filename, content))
    return JobResponse(job_id=job_id, status="processing")

async def process_transcription(job_id: str, filename: str, content: bytes):
    file_path = UPLOAD_DIR / f"{job_id}_{filename}"
    try:
        # Save to disk
        file_path.write_bytes(content)

        # Call OpenAI Whisper API
        kwargs = {"model": WHISPER_MODEL}
        if LANGUAGE_HINT != "auto":
            kwargs["language"] = LANGUAGE_HINT

        with open(file_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                file=(filename, audio_file),
                **kwargs
            )

        transcript = response.text

        redis_store.set_job(job_id, {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "result": {"transcript": transcript}
        })

    except Exception as e:
        redis_store.set_job(job_id, {
            "job_id": job_id,
            "status": "error",
            "progress": 0,
            "error": str(e)
        })
    finally:
        if file_path.exists():
            file_path.unlink()

@app.get("/status/{job_id}", response_model=JobResponse)
async def get_status(job_id: str):
    job = redis_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if isinstance(job, dict):
        job["job_id"] = job_id
    return JobResponse(**job)

@app.get("/health")
async def health_check():
    return {"status": "ok", "redis": redis_store.health_check()}
