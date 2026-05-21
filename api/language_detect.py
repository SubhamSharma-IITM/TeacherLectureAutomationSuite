"""
language_detect.py
Detect and tag language of transcript segments (Hindi / English / Hinglish).
"""
import re
from typing import List

# Unicode range for Devanagari script (covers Hindi)
DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")

# Thresholds
DEVANAGARI_THRESHOLD = 0.15
ENGLISH_MARKER_THRESHOLD = 0.15  # FIX: named constant instead of magic number

# Strip punctuation for word matching
_STRIP_PUNCT = re.compile(r"[^\w\s]")

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

    # FIX: strip punctuation before splitting so "this," matches "this"
    clean_text = _STRIP_PUNCT.sub("", text.lower())
    words = set(clean_text.split())
    english_word_count = len(words & ENGLISH_MARKERS)
    english_ratio = english_word_count / max(len(words), 1)

    # Decision logic
    if devanagari_ratio >= DEVANAGARI_THRESHOLD and english_ratio >= ENGLISH_MARKER_THRESHOLD:
        return "hi+en"   # Code-mixed / Hinglish
    elif devanagari_ratio >= DEVANAGARI_THRESHOLD:
        return "hi"
    elif whisper_detected == "hi" and devanagari_ratio > 0.02:
        # FIX: raised threshold from >0.0 to >0.02 to avoid single-punctuation false positives
        # Whisper said Hindi but text is mostly Roman → transliterated Hindi
        return "hi"
    else:
        return "en"


def detect_language_mix(segments: List[dict]) -> dict:
    """
    Given all segments, compute overall language composition percentages.
    Returns:
        {
            "hindi":   45,
            "english": 35,
            "mixed":   20,
            "primary": "hi"
        }

    NOTE: The three buckets are mutually exclusive and sum to ~100.
    """
    counts = {"hi": 0, "en": 0, "hi+en": 0}

    for seg in segments:
        lang = seg.get("language", "en")
        if lang in counts:
            counts[lang] += 1
        else:
            counts["en"] += 1  # unknown tag falls back to English

    total = sum(counts.values()) or 1

    # FIX: treat the three labels as exclusive buckets so percentages sum to ~100
    hindi_pct   = round(counts["hi"]    / total * 100)
    english_pct = round(counts["en"]    / total * 100)
    mixed_pct   = round(counts["hi+en"] / total * 100)

    # Absorb rounding error into the dominant bucket so total == 100
    diff = 100 - (hindi_pct + english_pct + mixed_pct)
    dominant = max(counts, key=counts.get)
    if dominant == "hi":
        hindi_pct += diff
    elif dominant == "en":
        english_pct += diff
    else:
        mixed_pct += diff

    primary = "hi" if counts["hi"] + counts["hi+en"] > counts["en"] else "en"

    return {
        "hindi":   hindi_pct,
        "english": english_pct,
        "mixed":   mixed_pct,
        "primary": primary,
    }
