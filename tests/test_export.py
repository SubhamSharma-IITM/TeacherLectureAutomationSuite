"""
tests/test_export.py
Unit tests for export functionality.
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
from pathlib import Path
from export import export_transcript, _fmt_time, _fmt_srt_time


SAMPLE_JOB = {
    "status": "done",
    "detected_language": "hi",
    "language_mix": {"hindi": 65, "english": 28, "mixed": 7, "primary": "hi"},
    "segments": [
        {"id": 0, "start": 0.0, "end": 4.2, "text": "नमस्ते, आज हम machine learning के बारे में बात करेंगे।", "language": "hi+en"},
        {"id": 1, "start": 4.2, "end": 8.5, "text": "First, let us understand what a neural network is.", "language": "en"},
        {"id": 2, "start": 8.5, "end": 13.0, "text": "यह एक बहुत महत्वपूर्ण concept है।", "language": "hi"},
    ],
    "full_text": "नमस्ते, आज हम machine learning के बारे में बात करेंगे। First, let us understand what a neural network is। यह एक बहुत महत्वपूर्ण concept है।",
}


class TestFormatHelpers:

    def test_fmt_time_basic(self):
        assert _fmt_time(0) == "00:00"
        assert _fmt_time(61) == "01:01"
        assert _fmt_time(3600) == "60:00"

    def test_fmt_srt_time(self):
        assert _fmt_srt_time(0.0) == "00:00:00,000"
        assert _fmt_srt_time(61.5) == "00:01:01,500"
        assert _fmt_srt_time(3661.123) == "01:01:01,123"


class TestExportTxt:

    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "exports").mkdir()
        out = export_transcript("test-job-001", SAMPLE_JOB, "txt")
        assert Path(out).exists()

    def test_txt_content(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "exports").mkdir()
        out = export_transcript("test-job-002", SAMPLE_JOB, "txt")
        content = Path(out).read_text(encoding="utf-8")
        assert "Lecture Transcript" in content
        assert "Hindi" in content or "HI" in content
        assert "नमस्ते" in content
        assert "neural network" in content


class TestExportSrt:

    def test_srt_format(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "exports").mkdir()
        out = export_transcript("test-job-003", SAMPLE_JOB, "srt")
        content = Path(out).read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:04,200" in content
        assert "नमस्ते" in content

    def test_srt_numbering(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "exports").mkdir()
        out = export_transcript("test-job-004", SAMPLE_JOB, "srt")
        lines = Path(out).read_text(encoding="utf-8").splitlines()
        # First line should be "1"
        assert lines[0].strip() == "1"
