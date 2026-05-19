"""
transcribe.py
Whisper-based audio transcription with Hindi/English support.
"""

import os
import re
from pathlib import Path
from typing import Optional

import openai
from pydub import AudioSegment

from language_detect import tag_segment_language
from transliterate import devanagari_to_roman


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe_audio(
    audio_path: str,
    language_hint: str = "auto",
    script: str = "devanagari",
) -> dict:
    """
    Transcribe an audio file using OpenAI Whisper.

    Args:
        audio_path: Path to the audio file.
        language_hint: "auto", "hi" (Hindi), or "en" (English).
        script: "devanagari" (keep Hindi in Devanagari) or "roman" (transliterate).

    Returns:
        dict with keys: detected_language, segments, full_text
    """
    audio_path = str(audio_path)

    # Convert to 16kHz mono WAV if needed (Whisper prefers this)
    processed_path = _preprocess_audio(audio_path)

    # Build Whisper request params
    whisper_kwargs = {
        "model": WHISPER_MODEL,
        "response_format": "verbose_json",   # gives us segments + timestamps
        "timestamp_granularities": ["segment"],
    }

    if language_hint != "auto":
        whisper_kwargs["language"] = language_hint  # "hi" or "en"

    # Call Whisper API
    with open(processed_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            **whisper_kwargs,
        )

    detected_language = getattr(transcript, "language", "en")

    # Process segments
    segments = []
    for seg in transcript.segments:
        text = seg.text.strip()
        lang_tag = tag_segment_language(text, detected_language)

        # Transliterate Hindi → Roman if requested
        if script == "roman" and lang_tag in ("hi", "hi+en"):
            text = devanagari_to_roman(text)

        segments.append({
            "id": seg.id,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": text,
            "language": lang_tag,
        })

    full_text = " ".join(s["text"] for s in segments)

    # Clean up temp file if we created one
    if processed_path != audio_path:
        Path(processed_path).unlink(missing_ok=True)

    return {
        "detected_language": detected_language,
        "segments": segments,
        "full_text": full_text,
    }


def _preprocess_audio(audio_path: str) -> str:
    """
    Convert audio to 16kHz mono WAV for optimal Whisper performance.
    Returns path to processed file (may be original if already compatible).
    """
    path = Path(audio_path)
    suffix = path.suffix.lower()

    # Whisper API handles most formats natively; only convert if > 25 MB
    if path.stat().st_size < 25 * 1024 * 1024:
        return audio_path

    # Chunk large files (Whisper has a 25 MB limit per request)
    out_path = str(path.with_suffix(".wav"))
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(out_path, format="wav")
    return out_path
