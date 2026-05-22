"""Lecture Transcriber — FastAPI Backend"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    result: Optional[dict] = None

def validate_audio_file(file: UploadFile) -> bool:
    """Simple magic-bytes check (no external dependency)"""
    allowed_signatures = [
        b'\xff\xfb',      # MP3
        b'ID3',           # MP3
        b'RIFF',          # WAV
        b'OggS',          # OGG
        b'\x00\x00\x00\x18ftypmp4',  # MP4/M4A
    ]
    file.file.seek(0)
    header = file.file.read(16)
    file.file.seek(0)
    return any(header.startswith(sig) for sig in allowed_signatures)

@app.post("/transcribe", response_model=JobResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    if not validate_audio_file(file):
        raise HTTPException(status_code=400, detail="Invalid audio file format")
    
    job_id = str(uuid.uuid4())
    redis_store.set_job(job_id, {"status": "processing", "progress": 0})
    
    # Start background task
    asyncio.create_task(process_transcription(job_id, file))
    return JobResponse(job_id=job_id, status="processing")

async def process_transcription(job_id: str, file: UploadFile):
    try:
        content = await file.read()
        file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        file_path.write_bytes(content)
        
        # TODO: Call your actual transcription logic here
        redis_store.set_job(job_id, {"status": "completed", "progress": 100, "result": {"transcript": "..."}})
    except Exception as e:
        redis_store.set_job(job_id, {"status": "error", "error": str(e)})

@app.get("/status/{job_id}", response_model=JobResponse)
async def get_status(job_id: str):
    job = redis_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job)

@app.get("/health")
async def health_check():
    return {"status": "ok", "redis": redis_store.health_check()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
