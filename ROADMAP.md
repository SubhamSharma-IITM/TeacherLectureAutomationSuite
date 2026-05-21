TeacherLectureAutomationSuite/
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.frontend
├── nginx.conf
├── .env.example
├── .dockerignore
├── .gitignore
├── package.json
├── index.html
├── vite.config.js
├── tailwind.config.js
├── ROADMAP.md
├── README.md
├── api/
│   ├── main.py
│   ├── transcribe.py
│   ├── language_detect.py
│   ├── transliterate.py
│   ├── export.py
│   └── requirements.txt
└── src/
    ├── App.jsx
    ├── main.jsx
    ├── components/
    │   ├── Recorder.jsx
    │   ├── Uploader.jsx
    │   ├── TranscriptViewer.jsx
    │   ├── LanguageBadge.jsx
    │   ├── ExportPanel.jsx
    │   └── SettingsPanel.jsx
    ├── hooks/
    │   ├── useTranscription.js
    │   └── useRecorder.js
    ├── utils/
    │   ├── api.js
    │   └── formatTime.js
    └── styles/
        └── globals.css
