"""
transcribe_grok.py
Grok (xAI) based transcription for long videos.
Uses the xAI API which supports larger files and longer context.
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

from openai import OpenAI          # xAI API is OpenAI-compatible
from pydub import AudioSegment

from language_detect import tag_segment_language

# ── Config ─────────────────────────────────────────────────────────────────────

XAI_API_KEY   = os.getenv("XAI_API_KEY")
XAI_BASE_URL  = "https://api.x.ai/v1"
GROK_MODEL    = os.getenv("GROK_MODEL", "grok-2-vision-1212")

# Grok supports up to 100MB per request — much larger than Whisper's 25MB
GROK_MAX_BYTES     = 90 * 1024 * 1024       # 90MB — stay under the limit
CHUNK_DURATION_MS  = 20 * 60 * 1000         # 20-minute chunks for very long videos
CHUNK_OVERLAP_MS   = 3 * 1000               # 3-second overlap

if not XAI_API_KEY:
    raise RuntimeError("XAI_API_KEY environment variable is not set")

client = OpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL)


# ── Public API ─────────────────────────────────────────────────────────────────

def transcribe_audio_grok(
    audio_path: str,
    language_hint: str = "auto",
    script: str = "devanagari",
) -> dict:
    """
    Transcribe an audio/video file using Grok (xAI).
    Handles large files by chunking into 20-minute segments.

    Args:
        audio_path:    Path to the audio/video file.
        language_hint: "auto", "hi", or "en".
        script:        "devanagari" or "roman".

    Returns:
        dict with keys: detected_language, segments, full_text
    """
    audio_path = str(audio_path)
    file_size  = Path(audio_path).stat().st_size

    if file_size <= GROK_MAX_BYTES:
        segments, detected_language = _transcribe_file_grok(audio_path, language_hint)
    else:
        segments, detected_language = _transcribe_chunked_grok(audio_path, language_hint)

    # Tag language per segment and optionally transliterate
    processed = []
    for seg in segments:
        text     = seg["text"].strip()
        lang_tag = tag_segment_language(text, detected_language)

        if script == "roman" and lang_tag in ("hi", "hi+en"):
            from transliterate import devanagari_to_roman
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
        "provider":          "grok",
    }


# ── Internal helpers ───────────────────────────────────────────────────────────

def _build_prompt(language_hint: str) -> str:
    """Build a system prompt for Grok to guide transcription."""
    lang_instruction = {
        "hi":   "The audio is in Hindi. Transcribe in Devanagari script.",
        "en":   "The audio is in English.",
        "auto": "The audio may contain Hindi, English, or a mix of both (Hinglish). Transcribe accurately preserving the original language.",
    }.get(language_hint, "")
    return (
        f"You are a professional lecture transcription assistant. "
        f"Transcribe the audio accurately with timestamps for each segment. "
        f"{lang_instruction} "
        f"Return a JSON array of segments with keys: id, start (seconds), end (seconds), text."
    )


def _transcribe_file_grok(audio_path: str, language_hint: str):
    """Transcribe a single file using Grok."""
    import json

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    import base64
    audio_b64 = base64.b64encode(audio_data).decode("utf-8")
    suffix     = Path(audio_path).suffix.lower().lstrip(".")
    mime_map   = {
        "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg",
        "webm": "audio/webm", "mp4": "audio/mp4", "m4a": "audio/mp4",
    }
    mime_type = mime_map.get(suffix, "audio/mpeg")

    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[
            {
                "role": "system",
                "content": _build_prompt(language_hint),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "audio_url",
                        "audio_url": {
                            "url": f"data:{mime_type};base64,{audio_b64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": "Please transcribe this lecture audio with timestamps.",
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    # Normalise: Grok may return {"segments": [...]} or just [...]
    raw_segments = data if isinstance(data, list) else data.get("segments", [])

    segments = [
        {
            "id":    i,
            "start": float(seg.get("start", 0)),
            "end":   float(seg.get("end",   0)),
            "text":  seg.get("text", "").strip(),
        }
        for i, seg in enumerate(raw_segments)
    ]

    # Detect language from first non-empty segment
    detected = language_hint if language_hint != "auto" else "en"
    return segments, detected


def _transcribe_chunked_grok(audio_path: str, language_hint: str):
    """Split very large files into 20-minute chunks and merge results."""
    audio    = AudioSegment.from_file(audio_path)
    audio    = audio.set_channels(1).set_frame_rate(16000)
    duration = len(audio)

    all_segments      = []
    detected_language = "en"
    segment_id_offset = 0
    start_ms          = 0

    while start_ms < duration:
        end_ms   = min(start_ms + CHUNK_DURATION_MS, duration)
        chunk    = audio[start_ms:end_ms]
        offset_s = start_ms / 1000.0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            chunk.export(tmp_path, format="wav")
            segs, lang = _transcribe_file_grok(tmp_path, language_hint)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

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
        start_ms += CHUNK_DURATION_MS - CHUNK_OVERLAP_MS

    return _dedupe_overlap(all_segments), detected_language


def _dedupe_overlap(segments: list) -> list:
    if not segments:
        return segments
    deduped = [segments[0]]
    for seg in segments[1:]:
        if seg["start"] - deduped[-1]["start"] > 1.5:
            deduped.append(seg)
    return deduped
