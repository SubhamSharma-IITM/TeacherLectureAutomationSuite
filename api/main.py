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
    error: Optional[str] = None
    result: Optional[dict] = None

# 1. FIXED: Validates clean raw bytes instead of a fragile file stream wrapper
def validate_audio_bytes(header: bytes) -> bool:
    """Simple magic-bytes check on raw binary header data"""
    allowed_signatures = [
        b'\xff\xfb',      # MP3
        b'ID3',           # MP3
        b'RIFF',          # WAV
        b'OggS',          # OGG
        b'\x00\x00\x00\x18ftypmp4',  # MP4/M4A
    ]
    return any(header.startswith(sig) for sig in allowed_signatures)

@app.post("/transcribe", response_model=JobResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    
    # FIX 2: Consume the file stream completely right here at the entrance.
    try:
        content = await file.read()
    except Exception as e:
        # If the file reading fails, fail gracefully before touching Redis
        raise HTTPException(status_code=500, detail=f"Failed to read upload stream: {str(e)}")
    
    # Pass the first 16 bytes of our safe memory content array to validation
    if not validate_audio_bytes(content[:16]):
        raise HTTPException(status_code=400, detail="Invalid audio file format")
    
    # Save standard initial state to Redis securely
    initial_job = {"job_id": job_id, "status": "processing", "progress": 0}
    redis_store.set_job(job_id, initial_job)
    
    # Offload the fully stable byte contents to background task
    asyncio.create_task(process_transcription(job_id, file.filename, content))
    return JobResponse(job_id=job_id, status="processing")

async def process_transcription(job_id: str, filename: str, content: bytes):
    try:
        file_path = UPLOAD_DIR / f"{job_id}_{filename}"
        file_path.write_bytes(content)
        
        # TODO: Insert your actual transcription or Whisper execution logic here
        
        success_payload = {
            "job_id": job_id,
            "status": "completed", 
            "progress": 100, 
            "result": {"transcript": "Your processed transcription text goes here."}
        }
        redis_store.set_job(job_id, success_payload)
        
    except Exception as e:
        error_payload = {
            "job_id": job_id,
            "status": "error", 
            "progress": 0,
            "error": str(e)
        }
        redis_store.set_job(job_id, error_payload)

@app.get("/status/{job_id}", response_model=JobResponse)
async def get_status(job_id: str):
    job = redis_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if isinstance(job, str):
        try:
            job = json.loads(job)
        except:
            pass
            
    # Absolute safety fallback: Always explicitly enforce the job_id back into the validated dict
    if isinstance(job, dict):
        job["job_id"] = job_id
        if "result" in job and isinstance(job["result"], str):
            try:
                job["result"] = json.loads(job["result"])
            except:
                pass
                
    return JobResponse(**job)

@app.get("/health")
async def health_check():
    return {"status": "ok", "redis": redis_store.health_check()}
