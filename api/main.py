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

# UPDATED: Added an optional error field so Pydantic knows how to parse error states
class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    error: Optional[str] = None
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
    
    # FIX 1: Read the file bytes completely right here while the request context is alive!
    # This prevents the "I/O operation on closed file" error.
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read upload stream: {str(e)}")
    
    redis_store.set_job(job_id, {"status": "processing", "progress": 0})
    
    # Pass the raw binary content down to the background task instead of the ephemeral file object
    asyncio.create_task(process_transcription(job_id, file.filename, content))
    return JobResponse(job_id=job_id, status="processing")

# UPDATED: Expects raw bytes and filename string now
async def process_transcription(job_id: str, filename: str, content: bytes):
    try:
        file_path = UPLOAD_DIR / f"{job_id}_{filename}"
        file_path.write_bytes(content)
        
        # TODO: Call your actual transcription logic here
        
        # FIX 2: Ensure job_id is saved alongside the payload on completion
        redis_store.set_job(job_id, {
            "job_id": job_id,
            "status": "completed", 
            "progress": 100, 
            "result": {"transcript": "..."}
        })
    except Exception as e:
        # FIX 3: Ensure job_id is explicitly saved alongside the error description
        redis_store.set_job(job_id, {
            "job_id": job_id,
            "status": "error", 
            "error": str(e)
        })

@app.get("/status/{job_id}", response_model=JobResponse)
async def get_status(job_id: str):
    job = redis_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # FIX 4: Safety double-check—if Redis lost the job_id, patch it dynamically
    if isinstance(job, dict) and "job_id" not in job:
        job["job_id"] = job_id
        
    return JobResponse(**job)

@app.get("/health")
async def health_check():
    return {"status": "ok", "redis": redis_store.health_check()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
