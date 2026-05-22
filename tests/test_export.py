"""
tests/test_export.py
Unit tests for export functionality.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
from pathlib import Path
import export as export_module
from export import export_transcript, cleanup_export, _fmt_time, _fmt_srt_time

SAMPLE_JOB = {
    "status": "done",
    "detected_language": "hi",
    "language_mix": {"hindi": 65, "english": 28, "mixed": 7, "primary": "hi"},
    "segments": [
        {"id": 0, "start": 0.0,  "end": 4.2,  "text": "नमस्ते, आज हम machine learning के बारे में बात करेंगे।", "language": "hi+en"},
        {"id": 1, "start": 4.2,  "end": 8.5,  "text": "First, let us understand what a neural network is.",    "language": "en"},
        {"id": 2, "start": 8.5,  "end": 13.0, "text": "यह एक बहुत महत्वपूर्ण concept है।",                    "language": "hi"},
    ],
    "full_text": "नमस्ते, आज हम machine learning के बारे में बात करेंगे। First, let us understand what a neural network is। यह एक बहुत महत्वपूर्ण concept है।",
}


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_export_dir(tmp_path, monkeypatch):
    """
    FIX: patch EXPORT_DIR at the module level so all export functions write
    to tmp_path instead of the real exports/ directory.
    monkeypatch.chdir alone doesn't work because EXPORT_DIR is set at import time.
    """
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    monkeypatch.setattr(export_module, "EXPORT_DIR", export_dir)


def make_job_id(suffix: str) -> str:
    """Generate a safe test job ID."""
    return f"test-job-{suffix}"


# ── Format helpers ─────────────────────────────────────────────────────────────

class TestFormatHelpers:
    def test_fmt_time_zero(self):
        assert _fmt_time(0) == "00:00"

    def test_fmt_time_one_minute(self):
        assert _fmt_time(61) == "01:01"

    def test_fmt_time_large(self):
        # _fmt_time uses MM:SS — 3600s = 60 minutes, not hours
        assert _fmt_time(3600) == "60:00"

    def test_fmt_srt_zero(self):
        assert _fmt_srt_time(0.0) == "00:00:00,000"

    def test_fmt_srt_one_minute(self):
        assert _fmt_srt_time(61.5) == "00:01:01,500"

    def test_fmt_srt_one_hour(self):
        assert _fmt_srt_time(3661.123) == "01:01:01,123"

    def test_fmt_srt_millisecond_precision(self):
        assert _fmt_srt_time(1.001) == "00:00:01,001"


# ── TXT export ─────────────────────────────────────────────────────────────────

class TestExportTxt:
    def test_creates_file(self):
        out = export_transcript(make_job_id("txt-001"), SAMPLE_JOB, "txt")
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_contains_header(self):
        out = export_transcript(make_job_id("txt-002"), SAMPLE_JOB, "txt")
        content = Path(out).read_text(encoding="utf-8")
        assert "Lecture Transcript" in content

    def test_contains_language_info(self):
        out = export_transcript(make_job_id("txt-003"), SAMPLE_JOB, "txt")
        content = Path(out).read_text(encoding="utf-8")
        assert "HI" in content or "Hindi" in content

    def test_contains_devanagari_text(self):
        out = export_transcript(make_job_id("txt-004"), SAMPLE_JOB, "txt")
        content = Path(out).read_text(encoding="utf-8")
        assert "नमस्ते" in content

    def test_contains_english_text(self):
        out = export_transcript(make_job_id("txt-005"), SAMPLE_JOB, "txt")
        content = Path(out).read_text(encoding="utf-8")
        assert "neural network" in content

    def test_utf8_encoding(self):
        out = export_transcript(make_job_id("txt-006"), SAMPLE_JOB, "txt")
        # Should not raise — file must be valid UTF-8
        Path(out).read_text(encoding="utf-8")


# ── SRT export ─────────────────────────────────────────────────────────────────

class TestExportSrt:
    def test_creates_file(self):
        out = export_transcript(make_job_id("srt-001"), SAMPLE_JOB, "srt")
        assert Path(out).exists()

    def test_srt_timestamps(self):
        out = export_transcript(make_job_id("srt-002"), SAMPLE_JOB, "srt")
        content = Path(out).read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:04,200" in content

    def test_srt_numbering_starts_at_one(self):
        out = export_transcript(make_job_id("srt-003"), SAMPLE_JOB, "srt")
        lines = Path(out).read_text(encoding="utf-8").splitlines()
        assert lines[0].strip() == "1"

    def test_srt_contains_text(self):
        out = export_transcript(make_job_id("srt-004"), SAMPLE_JOB, "srt")
        content = Path(out).read_text(encoding="utf-8")
        assert "नमस्ते" in content
        assert "neural network" in content

    def test_srt_segment_count(self):
        out = export_transcript(make_job_id("srt-005"), SAMPLE_JOB, "srt")
        content = Path(out).read_text(encoding="utf-8")
        # Each segment starts with its index number on its own line
        segment_numbers = [
            line.strip() for line in content.splitlines()
            if line.strip().isdigit()
        ]
        assert len(segment_numbers) == len(SAMPLE_JOB["segments"])


# ── PDF export ─────────────────────────────────────────────────────────────────

class TestExportPdf:
    def test_creates_file(self):
        pytest.importorskip("reportlab")  # skip if reportlab not installed
        out = export_transcript(make_job_id("pdf-001"), SAMPLE_JOB, "pdf")
        assert Path(out).exists()

    def test_pdf_non_empty(self):
        pytest.importorskip("reportlab")
        out = export_transcript(make_job_id("pdf-002"), SAMPLE_JOB, "pdf")
        assert Path(out).stat().st_size > 1024  # at least 1KB

    def test_pdf_magic_bytes(self):
        pytest.importorskip("reportlab")
        out = export_transcript(make_job_id("pdf-003"), SAMPLE_JOB, "pdf")
        header = Path(out).read_bytes()[:4]
        assert header == b"%PDF"  # valid PDF magic bytes


# ── Validation ─────────────────────────────────────────────────────────────────

class TestValidation:
    def test_invalid_job_id_slash(self):
        # FIX: path traversal guard
        with pytest.raises(ValueError, match="Invalid job_id"):
            export_transcript("../evil", SAMPLE_JOB, "txt")

    def test_invalid_job_id_dotdot(self):
        with pytest.raises(ValueError, match="Invalid job_id"):
            export_transcript("..\\evil", SAMPLE_JOB, "txt")

    def test_invalid_format(self):
        with pytest.raises(KeyError):
            export_transcript(make_job_id("val-001"), SAMPLE_JOB, "docx")


# ── Cleanup ────────────────────────────────────────────────────────────────────

class TestCleanup:
    def test_cleanup_removes_files(self):
        job_id = make_job_id("cleanup-001")
        export_transcript(job_id, SAMPLE_JOB, "txt")
        export_transcript(job_id, SAMPLE_JOB, "srt")
        cleanup_export(job_id)
        remaining = list(export_module.EXPORT_DIR.glob(f"{job_id}.*"))
        assert remaining == []

    def test_cleanup_nonexistent_job(self):
        # Should not raise even if no files exist
        cleanup_export("nonexistent-job-id")
