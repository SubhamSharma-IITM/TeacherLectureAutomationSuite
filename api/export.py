"""
export.py
Export transcripts as TXT, SRT subtitles, or PDF.
"""

import os
from pathlib import Path
from typing import List


EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)


def export_transcript(job_id: str, job: dict, format: str) -> str:
    """
    Export a completed transcript job to the requested format.

    Args:
        job_id: The job identifier.
        job:    The full job result dict (status=done).
        format: "txt", "srt", or "pdf"

    Returns:
        Absolute path to the exported file.
    """
    handlers = {
        "txt": _export_txt,
        "srt": _export_srt,
        "pdf": _export_pdf,
    }
    return handlers[format](job_id, job)


# ── TXT ─────────────────────────────────────────────────────────────────────────

def _export_txt(job_id: str, job: dict) -> str:
    out_path = EXPORT_DIR / f"{job_id}.txt"
    segments: List[dict] = job.get("segments", [])
    mix = job.get("language_mix", {})

    lines = [
        "=== Lecture Transcript ===",
        f"Detected Language: {job.get('detected_language', 'unknown').upper()}",
        f"Language Mix  → Hindi: {mix.get('hindi', 0)}%  |  English: {mix.get('english', 0)}%  |  Mixed: {mix.get('mixed', 0)}%",
        "",
        "── Transcript ──",
        "",
    ]

    for seg in segments:
        timestamp = f"[{_fmt_time(seg['start'])} → {_fmt_time(seg['end'])}]"
        lang_label = {"hi": "🇮🇳 HI", "en": "🇬🇧 EN", "hi+en": "🌐 HI+EN"}.get(seg["language"], "")
        lines.append(f"{timestamp} {lang_label}")
        lines.append(seg["text"])
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


# ── SRT ─────────────────────────────────────────────────────────────────────────

def _export_srt(job_id: str, job: dict) -> str:
    out_path = EXPORT_DIR / f"{job_id}.srt"
    segments: List[dict] = job.get("segments", [])

    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_fmt_srt_time(seg['start'])} --> {_fmt_srt_time(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


# ── PDF ─────────────────────────────────────────────────────────────────────────

def _export_pdf(job_id: str, job: dict) -> str:
    """
    Generate a PDF using reportlab.
    Falls back to a plain-text file with .pdf extension if reportlab is unavailable.
    """
    out_path = EXPORT_DIR / f"{job_id}.pdf"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        mix = job.get("language_mix", {})

        # Title
        title_style = ParagraphStyle("Title", parent=styles["Title"],
                                     fontSize=18, spaceAfter=12)
        story.append(Paragraph("Lecture Transcript", title_style))

        # Meta
        meta = (
            f"Detected Language: <b>{job.get('detected_language', '').upper()}</b><br/>"
            f"Hindi: {mix.get('hindi', 0)}% | English: {mix.get('english', 0)}% | Mixed: {mix.get('mixed', 0)}%"
        )
        story.append(Paragraph(meta, styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        # Segments
        for seg in job.get("segments", []):
            ts = f"[{_fmt_time(seg['start'])} → {_fmt_time(seg['end'])}]"
            lang_colors = {"hi": "#E87722", "en": "#1A56DB", "hi+en": "#7C3AED"}
            color = lang_colors.get(seg["language"], "#333")

            header = Paragraph(
                f'<font color="{color}"><b>{ts} {seg["language"].upper()}</b></font>',
                styles["Normal"]
            )
            body = Paragraph(seg["text"], styles["Normal"])
            story.extend([header, body, Spacer(1, 0.3*cm)])

        doc.build(story)

    except ImportError:
        # Fallback: write plain text with PDF extension
        txt_content = _export_txt(job_id, job)
        out_path.write_text(Path(txt_content).read_text(encoding="utf-8"), encoding="utf-8")

    return str(out_path)


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _fmt_srt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm for SRT."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
