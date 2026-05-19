# Architecture Overview

## System Diagram

```
Browser
  │
  ├── Upload audio file  ──────────────────────────────┐
  │   (Uploader.jsx)                                    │
  │                                                     ▼
  ├── Record live audio                        FastAPI Backend
  │   (Recorder.jsx + useRecorder.js)          (api/main.py)
  │                                                     │
  └── Poll for results ◄────────────── Job Queue ───────┤
      (useTranscription.js)             (in-memory)      │
                                                         ▼
                                              transcribe.py
                                              (Whisper API)
                                                         │
                                              ┌──────────┴──────────┐
                                              ▼                     ▼
                                     language_detect.py    transliterate.py
                                     (per-segment tagging)  (Devanagari→Roman)
                                              │
                                              ▼
                                          export.py
                                       (TXT / SRT / PDF)
```

## Request Flow

### 1. Upload + Start Job
```
POST /api/transcribe
  → Validate file (type, size)
  → Save to disk (uploads/{job_id}.ext)
  → Register job as "processing"
  → Spawn background task
  → Return {job_id}
```

### 2. Background Transcription
```
run_transcription(job_id)
  → transcribe_audio(path, language_hint, script)
      → Preprocess audio (convert if > 25MB)
      → Call Whisper API (verbose_json)
      → For each segment:
          tag_segment_language(text, whisper_lang)
          [optional] devanagari_to_roman(text)
  → detect_language_mix(segments)
  → Store result in RESULTS[job_id]
```

### 3. Polling
```
GET /api/transcribe/{job_id}
  → Return RESULTS[job_id]
  → Frontend polls every 2s until status = "done" | "error"
```

### 4. Export
```
GET /api/export/{job_id}?format=txt|srt|pdf
  → export_transcript(job_id, job, format)
  → Stream file as download
```

## Language Detection Algorithm

```python
def tag_segment_language(text, whisper_detected):
    devanagari_ratio = count_devanagari(text) / len(text)
    english_ratio = common_english_words(text) / len(words)

    if devanagari_ratio >= 0.15 and english_ratio >= 0.15:
        return "hi+en"   # Hinglish
    elif devanagari_ratio >= 0.15:
        return "hi"
    else:
        return "en"
```

## Scaling Considerations

- **Job storage**: Replace in-memory `RESULTS` dict with Redis for multi-worker deployments
- **File storage**: Replace local `uploads/` with AWS S3 or GCS
- **Large files**: Chunk audio > 25 MB before sending to Whisper (pydub splitting)
- **Rate limits**: Add a job queue (Celery + Redis) to throttle concurrent Whisper calls
- **Auth**: Add JWT authentication for multi-user deployments
