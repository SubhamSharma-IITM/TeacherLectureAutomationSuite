# TeacherLectureAutomationSuite

A full-stack tool for transcribing Hindi/English/Hinglish lectures, generating subtitle files, and creating AI-powered practice assignments from lecture content.

---

## Features

- **Audio transcription** via OpenAI Whisper (short files) or Grok/xAI (long videos)
- **Language detection** — automatically identifies Hindi, English, and Hinglish (code-mixed) segments
- **Devanagari / Roman script** toggle for Hindi output
- **Export** to TXT, SRT subtitles, or PDF with correct Devanagari font rendering
- **Assignment generator** — Claude (Anthropic) generates MCQ, Short Answer, and True/False questions from the transcript
- **Record in-browser** or upload existing audio files (MP3, WAV, OGG, WEBM, MP4)

---

## Project Structure

```
TeacherLectureAutomationSuite/
├── api/                        # FastAPI backend
│   ├── main.py                 # API routes and job management
│   ├── transcribe.py           # Whisper transcription + chunking
│   ├── transcribe_grok.py      # Grok transcription for long videos
│   ├── language_detect.py      # Hindi/English/Hinglish detection
│   ├── transliterate.py        # Devanagari ↔ Roman transliteration
│   ├── export.py               # TXT / SRT / PDF export
│   ├── assignment.py           # Claude-powered assignment generation
│   ├── redis_store.py          # Redis job store
│   └── requirements.txt
├── src/                        # React frontend (Vite + Tailwind)
│   ├── App.jsx
│   ├── hooks/
│   │   ├── useTranscription.js
│   │   └── useRecorder.js
│   ├── components/
│   │   ├── Uploader.jsx
│   │   ├── Recorder.jsx
│   │   ├── TranscriptViewer.jsx
│   │   ├── LanguageBadge.jsx
│   │   ├── ExportPanel.jsx
│   │   ├── SettingsPanel.jsx
│   │   └── AssignmentPanel.jsx
│   ├── utils/
│   │   ├── api.js
│   │   └── formatTime.js
│   └── styles/
│       └── globals.css
├── tests/                      # pytest test suite
├── docs/
├── drive_to_vimeo/
├── Dockerfile.api
├── Dockerfile.frontend
├── docker-compose.yml
├── nginx.conf
├── .env.example
└── .dockerignore
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| Docker + Docker Compose | any recent |
| Redis | 7+ (handled by Docker) |

**System libraries required on the host (if not using Docker):**
```bash
# Ubuntu / Debian
sudo apt-get install ffmpeg libmagic1

# macOS
brew install ffmpeg libmagic
```

---

## Quick Start (Docker — recommended)

```bash
# 1. Clone the repo
git clone https://github.com/SubhamSharma-IITM/TeacherLectureAutomationSuite.git
cd TeacherLectureAutomationSuite

# 2. Set up environment variables
cp .env.example .env
# Edit .env and fill in your API keys (see below)

# 3. Start everything
docker-compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for Whisper |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for assignment generation |
| `XAI_API_KEY` | For Grok | xAI API key for long-video transcription |
| `REDIS_URL` | Yes | Redis connection string (default: `redis://localhost:6379/0`) |
| `WHISPER_MODEL` | No | Whisper model (default: `whisper-1`) |
| `CLAUDE_MODEL` | No | Claude model (default: `claude-sonnet-4-20250514`) |
| `MAX_FILE_SIZE_MB` | No | Upload limit in MB (default: `100`) |
| `DEVANAGARI_FONT_PATH` | For PDF | Path to `NotoSansDevanagari-Regular.ttf` |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
| `LANGUAGE_HINT` | No | Server-side default: `auto`, `hi`, or `en` |

---

## Local Development (without Docker)

### Backend

```bash
cd api
pip install -r requirements.txt --break-system-packages

# Redis must be running
redis-server &

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
# From repo root
npm install
npm run dev
```

### Tests

```bash
cd tests
pip install pytest --break-system-packages
pytest -v
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/transcribe` | Upload audio and start transcription job |
| `GET` | `/api/transcribe/{job_id}` | Poll job status / get result |
| `DELETE` | `/api/transcribe/{job_id}` | Delete job and clean up files |
| `GET` | `/api/export/{job_id}` | Download transcript (`?format=txt\|srt\|pdf`) |
| `POST` | `/api/assignment/{job_id}` | Generate practice assignment from transcript |
| `GET` | `/health` | Service health check |

### Upload parameters (`POST /api/transcribe`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | File | — | Audio file (MP3, WAV, OGG, WEBM, MP4) |
| `language_hint` | string | `auto` | `auto`, `hi`, or `en` |
| `script` | string | `devanagari` | `devanagari` or `roman` |
| `provider` | string | `whisper` | `whisper` or `grok` |

---

## Devanagari Font for PDF Export

The PDF exporter requires `NotoSansDevanagari-Regular.ttf`. The Dockerfile downloads it automatically. For local dev:

```bash
curl -L -o api/NotoSansDevanagari-Regular.ttf \
  "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
```

Then set `DEVANAGARI_FONT_PATH=NotoSansDevanagari-Regular.ttf` in your `.env`.

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Run tests: `pytest tests/ -v`
4. Push and open a PR

---

## License

MIT
