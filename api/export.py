"""
export.py
Export transcripts as TXT, SRT subtitles, or PDF.
"""
import os
from pathlib import Path
from typing import List

EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

# FIX: plain text labels instead of emoji flags — avoids encoding issues in
#      downstream tools, terminals, and some PDF renderers
LANG_LABELS = {"hi": "[HI]", "en": "[EN]", "hi+en": "[HI+EN]"}


def export_transcript(job_id: str, job: dict, format: str) -> str:
    """
    Export a completed transcript job to the requested format.

    Args:
        job_id: The job identifier (must be a uuid4 string).
        job:    The full job result dict (status=done).
        format: "txt", "srt", or "pdf"

    Returns:
        Absolute path to the exported file.
    """
    # FIX: sanitise job_id to prevent path traversal
    if not job_id or "/" in job_id or ".." in job_id:
        raise ValueError(f"Invalid job_id: {job_id!r}")

    handlers = {
        "txt": _export_txt,
        "srt": _export_srt,
        "pdf": _export_pdf,
    }
    return handlers[format](job_id, job)


def cleanup_export(job_id: str) -> None:
    """
    FIX: Delete all export files for a job (call this from main.py's delete_job).
    """
    for path in EXPORT_DIR.glob(f"{job_id}.*"):
        path.unlink(missing_ok=True)


# ── TXT ─────────────────────────────────────────────────────────────────────────

def _export_txt(job_id: str, job: dict) -> str:
    out_path = EXPORT_DIR / f"{job_id}.txt"
    segments: List[dict] = job.get("segments", [])
    mix = job.get("language_mix", {})

    lines = [
        "=== Lecture Transcript ===",
        f"Detected Language : {job.get('detected_language', 'unknown').upper()}",
        f"Language Mix      : Hindi {mix.get('hindi', 0)}%  |  English {mix.get('english', 0)}%  |  Mixed {mix.get('mixed', 0)}%",
        "",
        "── Transcript ──",
        "",
    ]

    for seg in segments:
        timestamp  = f"[{_fmt_time(seg['start'])} --> {_fmt_time(seg['end'])}]"
        lang_label = LANG_LABELS.get(seg["language"], "")
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
    Generate a PDF using reportlab with proper Devanagari font support.
    FIX: raises ImportError clearly instead of silently producing a fake PDF.
    FIX: registers a Devanagari-capable font so Hindi text renders correctly.
    """
    out_path = EXPORT_DIR / f"{job_id}.pdf"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as e:
        raise RuntimeError(
            "reportlab is required for PDF export. Install it with: pip install reportlab"
        ) from e

    # FIX: register a Devanagari-capable font so Hindi doesn't render as boxes.
    # Expects NotoSansDevanagari-Regular.ttf in the same directory or on FONT_PATH.
    FONT_NAME = "NotoSans"
    FONT_PATH = os.getenv("DEVANAGARI_FONT_PATH", "NotoSansDevanagari-Regular.ttf")
    _register_font(pdfmetrics, TTFont, FONT_NAME, FONT_PATH)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    story  = []
    mix    = job.get("language_mix", {})

    # Title
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=18, spaceAfter=12, fontName=FONT_NAME,
    )
    story.append(Paragraph("Lecture Transcript", title_style))

    # Meta
    normal_style = ParagraphStyle(
        "CustomNormal", parent=styles["Normal"], fontName=FONT_NAME
    )
    meta = (
        f"Detected Language: <b>{job.get('detected_language', '').upper()}</b><br/>"
        f"Hindi: {mix.get('hindi', 0)}%  |  English: {mix.get('english', 0)}%  |  Mixed: {mix.get('mixed', 0)}%"
    )
    story.append(Paragraph(meta, normal_style))
    story.append(Spacer(1, 0.5 * cm))

    # Segments
    lang_colors = {"hi": "#E87722", "en": "#1A56DB", "hi+en": "#7C3AED"}
    for seg in job.get("segments", []):
        ts    = f"[{_fmt_time(seg['start'])} --> {_fmt_time(seg['end'])}]"
        color = lang_colors.get(seg["language"], "#333333")
        label = LANG_LABELS.get(seg["language"], "")

        header = Paragraph(
            f'<font color="{color}"><b>{ts} {label}</b></font>',
            normal_style,
        )
        body = Paragraph(seg["text"], normal_style)
        story.extend([header, body, Spacer(1, 0.3 * cm)])

    doc.build(story)
    return str(out_path)


def _register_font(pdfmetrics, TTFont, font_name: str, font_path: str) -> None:
    """Register the Devanagari font; log a warning if the file is missing."""
    try:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    except Exception:
        import warnings
        warnings.warn(
            f"Devanagari font not found at '{font_path}'. "
            "Hindi text may not render correctly in PDFs. "
            "Set DEVANAGARI_FONT_PATH to point to NotoSansDevanagari-Regular.ttf.",
            stacklevel=3,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _fmt_srt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm for SRT."""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"def _export_txt(job_id: str, job: dict) -> str:
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
