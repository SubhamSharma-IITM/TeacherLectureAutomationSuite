# 🎙️ Lecture Transcriber — Hindi & English AI Transcription Tool

A full-featured web application that automatically **detects** whether a lecture is in **Hindi**, **English**, or **Hinglish** (code-mixed), and transcribes it accordingly using OpenAI Whisper + custom post-processing.

---

## ✨ Features

- 🔍 **Automatic Language Detection** — Hindi, English, or mixed (Hinglish)
- 🎙️ **Live Recording** — Capture audio directly from the browser
- 📁 **File Upload** — MP3, MP4, WAV, OGG, WEBM support
- 📝 **Real-time Transcription** — Streamed word-by-word output
- 🌐 **Script Toggle** — View Hindi in Devanagari or Roman (transliteration)
- 📤 **Export** — Download as TXT, PDF, or SRT (subtitle format)
- 📊 **Language Stats** — Percentage breakdown of Hindi vs English segments
- 🕑 **Timestamped Segments** — Click a timestamp to replay that segment
- 🌙 **Dark / Light Mode**

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite |
| Styling | Tailwind CSS + custom CSS |
| Transcription API | OpenAI Whisper API (`whisper-1`) |
| Language Detection | `langdetect` + custom Devanagari heuristic |
| Transliteration | `indic-transliteration` (Python) |
| Backend | FastAPI (Python 3.11) |
| Audio Processing | `pydub` + `ffmpeg` |
| Storage | Local filesystem (pluggable to S3) |

---

## 📁 Project Structure

```
lecture-transcriber/
├── api/                         # FastAPI backend
│   ├── main.py                  # App entry point, routes
│   ├── transcribe.py            # Whisper integration
│   ├── language_detect.py       # Lang detection logic
│   ├── transliterate.py         # Devanagari ↔ Roman
│   ├── export.py                # TXT / PDF / SRT export
│   └── requirements.txt
│
├── src/                         # React frontend
│   ├── components/
│   │   ├── Recorder.jsx         # Live mic recording
│   │   ├── Uploader.jsx         # Drag-and-drop file upload
│   │   ├── TranscriptViewer.jsx # Timestamped transcript display
│   │   ├── LanguageBadge.jsx    # Detected language indicator
│   │   ├── ExportPanel.jsx      # Export controls
│   │   └── SettingsPanel.jsx    # Language / script preferences
│   ├── hooks/
│   │   ├── useRecorder.js       # MediaRecorder hook
│   │   └── useTranscription.js  # API polling / SSE hook
│   ├── utils/
│   │   ├── api.js               # Axios API client
│   │   └── formatTime.js        # Seconds → MM:SS
│   ├── styles/
│   │   └── globals.css
│   ├── App.jsx
│   └── main.jsx
│
├── tests/
│   ├── test_transcribe.py
│   ├── test_language_detect.py
│   └── test_export.py
│
├── docs/
│   ├── architecture.md
│   └── api-reference.md
│
├── public/
│   └── sample_lecture.mp3       # Demo audio file
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.frontend
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- ffmpeg installed (`brew install ffmpeg` / `apt install ffmpeg`)
- OpenAI API Key

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/lecture-transcriber.git
cd lecture-transcriber
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Start the backend
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Start the frontend
```bash
# From project root
npm install
npm run dev
# Opens at http://localhost:5173
```

### 5. (Optional) Docker Compose
```bash
docker-compose up --build
# Frontend: http://localhost:3000
# API:      http://localhost:8000
```

---

## 🔧 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ |
| `WHISPER_MODEL` | `whisper-1` (default) | ❌ |
| `MAX_FILE_SIZE_MB` | Upload limit in MB (default: 100) | ❌ |
| `LANGUAGE_HINT` | Force language: `hi`, `en`, or `auto` | ❌ |

---

## 🌐 API Reference

### `POST /api/transcribe`
Upload an audio file for transcription.

**Request:** `multipart/form-data`
| Field | Type | Description |
|---|---|---|
| `file` | File | Audio file (mp3, wav, mp4, ogg, webm) |
| `language_hint` | string | `"auto"`, `"hi"`, or `"en"` |
| `script` | string | `"devanagari"` or `"roman"` |

**Response:**
```json
{
  "job_id": "abc123",
  "status": "processing"
}
```

---

### `GET /api/transcribe/{job_id}`
Poll for transcription result.

**Response:**
```json
{
  "job_id": "abc123",
  "status": "done",
  "detected_language": "hi",
  "language_mix": { "hindi": 72, "english": 28 },
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 4.2,
      "text": "नमस्ते, आज हम machine learning के बारे में बात करेंगे।",
      "language": "hi"
    }
  ],
  "full_text": "..."
}
```

---

### `GET /api/export/{job_id}?format=txt|pdf|srt`
Download the transcript in the specified format.

---

## 🧠 Language Detection Logic

```
1. Run Whisper with language=None (auto-detect)
2. Whisper returns detected_language ("hi" or "en")
3. For each segment, apply custom heuristic:
   a. Count Devanagari characters → if > 20% → tag as Hindi
   b. Run langdetect on segment text → secondary signal
   c. Code-mixed segments tagged as "hi+en"
4. Compute overall language_mix percentages
```

The tool handles **Hinglish** gracefully — segments are individually tagged so you get an accurate mix breakdown rather than forcing everything into one language.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push and open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/).

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
