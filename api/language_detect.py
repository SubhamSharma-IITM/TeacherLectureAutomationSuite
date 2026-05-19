"""
language_detect.py
Detect and tag language of transcript segments (Hindi / English / Hinglish).
"""

import re
from typing import List


# Unicode range for Devanagari script (covers Hindi)
DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")

# Threshold: if ≥ this fraction of chars are Devanagari → mark as Hindi
DEVANAGARI_THRESHOLD = 0.15

# Common English function words (fast heuristic for code-mixed text)
ENGLISH_MARKERS = {
    "the", "is", "are", "was", "were", "a", "an", "of", "in", "on",
    "and", "but", "or", "for", "to", "with", "this", "that", "it",
    "we", "you", "i", "he", "she", "they", "not", "have", "has",
    "do", "does", "can", "will", "would", "should", "could", "may",
}


def tag_segment_language(text: str, whisper_detected: str = "en") -> str:
    """
    Determine the language of a single segment.

    Returns one of:
        "hi"     — predominantly Hindi (Devanagari)
        "en"     — predominantly English
        "hi+en"  — code-mixed (Hinglish)

    Strategy:
        1. Count Devanagari chars → primary signal
        2. Count English function words → secondary signal
        3. Combine to produce label
    """
    if not text:
        return whisper_detected or "en"

    total_chars = len(text.replace(" ", ""))
    devanagari_chars = len(DEVANAGARI_PATTERN.findall(text))

    devanagari_ratio = devanagari_chars / max(total_chars, 1)

    words = set(text.lower().split())
    english_word_count = len(words & ENGLISH_MARKERS)
    english_ratio = english_word_count / max(len(words), 1)

    # Decision logic
    if devanagari_ratio >= DEVANAGARI_THRESHOLD and english_ratio >= 0.15:
        return "hi+en"   # Code-mixed / Hinglish
    elif devanagari_ratio >= DEVANAGARI_THRESHOLD:
        return "hi"
    elif whisper_detected == "hi" and devanagari_ratio > 0.0:
        # Whisper said Hindi but text is mostly Roman → transliterated Hindi
        return "hi"
    else:
        return "en"


def detect_language_mix(segments: List[dict]) -> dict:
    """
    Given all segments, compute overall language composition percentages.

    Returns:
        {
            "hindi": 65,
            "english": 28,
            "mixed": 7,
            "primary": "hi"
        }
    """
    counts = {"hi": 0, "en": 0, "hi+en": 0}

    for seg in segments:
        lang = seg.get("language", "en")
        counts[lang] = counts.get(lang, 0) + 1

    total = sum(counts.values()) or 1

    hindi_pct = round((counts["hi"] + counts["hi+en"] * 0.5) / total * 100)
    english_pct = round((counts["en"] + counts["hi+en"] * 0.5) / total * 100)
    mixed_pct = round(counts["hi+en"] / total * 100)

    primary = "hi" if counts["hi"] + counts["hi+en"] > counts["en"] else "en"

    return {
        "hindi": hindi_pct,
        "english": english_pct,
        "mixed": mixed_pct,
        "primary": primary,
    }
