"""
transcribe.py
Whisper-based audio transcription with Hindi/English support.
Handles large files via chunking and cleans up temp files safely.
"""
import os
import tempfile
import asyncio
from pathlib import Path
from typing import Optional

import openai
from pydub import AudioSegment

from language_detect import tag_segment_language

# ── Config ─────────────────────────────────────────────────────────────────────

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
WHISPER_MAX_BYTES = 24 * 1024 * 1024          # 24 MB — stay under the 25 MB API limit
CHUNK_DURATION_MS = 10 * 60 * 1000            # 10-minute chunks
CHUNK_OVERLAP_MS  = 2 * 1000                  # 2-second overlap to avoid cutting words

# FIX: validate API key at import time, not silently at first request
_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set")

client = openai.OpenAI(api_key=_api_key)


# ── Public API ─────────────────────────────────────────────────────────────────

def transcribe_audio(
    audio_path: str,
    language_hint: str = "auto",
    script: str = "devanagari",
    model: str = WHISPER_MODEL,           # FIX: per-call override, not baked-in constant
) -> dict:
    """
    Transcribe an audio file using OpenAI Whisper.

    Args:
        audio_path:    Path to the audio file.
        language_hint: "auto", "hi" (Hindi), or "en" (English).
        script:        "devanagari" or "roman" (transliterates Hindi → Roman).
        model:         Whisper model name (default from env).

    Returns:
        dict with keys: detected_language, segments, full_text
    """
    audio_path = str(audio_path)
    file_size  = Path(audio_path).stat().st_size

    if file_size <= WHISPER_MAX_BYTES:
        # Small file — transcribe directly
        segments, detected_language = _transcribe_file(
            audio_path, language_hint, model
        )
    else:
        # FIX: large file — actually chunk and merge instead of just converting
        segments, detected_language = _transcribe_chunked(
            audio_path, language_hint, model
        )

    # Tag language per segment and optionally transliterate
    processed = []
    for seg in segments:
        text     = seg["text"].strip()
        lang_tag = tag_segment_language(text, detected_language)

        if script == "roman" and lang_tag in ("hi", "hi+en"):
            from transliterate import devanagari_to_roman   # FIX: lazy import; won't crash English-only use
            text = devanagari_to_roman(text)

        processed.append({
            "id":       seg["id"],
            "start":    round(seg["start"], 2),
            "end":      round(seg["end"], 2),
            "text":     text,
            "language": lang_tag,
        })

    full_text = " ".join(s["text"] for s in processed)

    return {
        "detected_language": detected_language,
        "segments":          processed,
        "full_text":         full_text,
    }


# ── Internal helpers ───────────────────────────────────────────────────────────

def _whisper_kwargs(language_hint: str, model: str) -> dict:
    kwargs = {
        "model":                    model,
        "response_format":          "verbose_json",
        "timestamp_granularities":  ["segment"],
    }
    if language_hint != "auto":
        kwargs["language"] = language_hint
    return kwargs


def _transcribe_file(audio_path: str, language_hint: str, model: str):
    """Transcribe a single file that fits within the Whisper size limit."""
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            file=f, **_whisper_kwargs(language_hint, model)
        )
    detected = getattr(transcript, "language", "en")
    segments = [
        {"id": s.id, "start": s.start, "end": s.end, "text": s.text}
        for s in transcript.segments
    ]
    return segments, detected


def _transcribe_chunked(audio_path: str, language_hint: str, model: str):
    """
    FIX: Split audio into overlapping chunks, transcribe each, and stitch results.
    Timestamps are offset so the final segment list is continuous.
    """
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(16000)   # normalise for Whisper

    duration_ms = len(audio)
    all_segments = []
    detected_language = "en"
    segment_id_offset = 0

    start_ms = 0
    while start_ms < duration_ms:
        end_ms  = min(start_ms + CHUNK_DURATION_MS, duration_ms)
        chunk   = audio[start_ms:end_ms]
        offset_s = start_ms / 1000.0

        # Write chunk to a temp file
        # FIX: use tempfile so we never overwrite the original
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            chunk.export(tmp_path, format="wav")
            segs, lang = _transcribe_file(tmp_path, language_hint, model)
        finally:
            Path(tmp_path).unlink(missing_ok=True)   # FIX: always clean up temp file

        if not all_segments:
            detected_language = lang

        for seg in segs:
            all_segments.append({
                "id":    segment_id_offset + seg["id"],
                "start": seg["start"] + offset_s,
                "end":   seg["end"]   + offset_s,
                "text":  seg["text"],
            })
        segment_id_offset += len(segs)

        # Advance by chunk size minus overlap so words at boundaries aren't cut
        start_ms += CHUNK_DURATION_MS - CHUNK_OVERLAP_MS

    # De-duplicate segments that appear in the overlap window
    all_segments = _dedupe_overlap(all_segments)
    return all_segments, detected_language


def _dedupe_overlap(segments: list) -> list:
    """
    Remove duplicate or near-duplicate segments introduced by chunk overlap.
    Two segments are duplicates if their start times are within 1.5 seconds.
    """
    if not segments:
        return segments
    deduped = [segments[0]]
    for seg in segments[1:]:
        if seg["start"] - deduped[-1]["start"] > 1.5:
            deduped.append(seg)
    return deduped
