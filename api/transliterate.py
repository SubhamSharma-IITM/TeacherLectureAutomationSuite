"""
transliterate.py
Devanagari ↔ Roman (ITRANS) transliteration for Hindi text.

Uses indic-transliteration library (preferred) with a fallback char-map.

NOTES:
- The fallback map is intentionally lossy and one-way only.
  ट/त both map to "t", ड/द to "d", etc. — do not roundtrip through fallback.
- The fallback also does not model the inherent schwa vowel: bare consonants
  like क produce "k" not "ka". Output is readable but not phonetically exact.
- For production Hindi support, install indic-transliteration:
      pip install indic-transliteration
"""

import re

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate as _transliterate
    INDIC_AVAILABLE = True
except ImportError:
    INDIC_AVAILABLE = False

# ── Constants ──────────────────────────────────────────────────────────────────

DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]+")

# FIX: fast translation table for Devanagari digit normalisation
# Applied as a post-processing step regardless of which path is used
_DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Fallback char-map (used when indic-transliteration is not installed)
DEVANAGARI_ROMAN_MAP = {
    # Vowels (independent)
    "अ": "a",  "आ": "aa", "इ": "i",  "ई": "ee", "उ": "u",  "ऊ": "oo",
    "ए": "e",  "ऐ": "ai", "ओ": "o",  "औ": "au",
    "अं": "an", "अः": "ah",
    # Consonants
    "क": "k",  "ख": "kh", "ग": "g",  "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh","ज": "j",  "झ": "jh", "ञ": "ny",
    "ट": "t",  "ठ": "th", "ड": "d",  "ढ": "dh", "ण": "n",
    "त": "t",  "थ": "th", "द": "d",  "ध": "dh", "न": "n",
    "प": "p",  "फ": "ph", "ब": "b",  "भ": "bh", "म": "m",
    "य": "y",  "र": "r",  "ल": "l",  "व": "v",
    "श": "sh", "ष": "sh", "स": "s",  "ह": "h",
    # Vowel matras (dependent)
    "ा": "a",  "ि": "i",  "ी": "ee", "ु": "u",  "ू": "oo",
    "े": "e",  "ै": "ai", "ो": "o",  "ौ": "au",
    # Diacritics
    "ं": "n",  "ः": "h",  "्": "",   "़": "",
    # Punctuation
    "।": ".",  "॥": ".",
    # Digits — also handled by _DEVA_DIGITS but kept here for fallback path
    "०": "0",  "१": "1",  "२": "2",  "३": "3",  "४": "4",
    "५": "5",  "६": "6",  "७": "7",  "८": "8",  "९": "9",
}


# ── Public API ─────────────────────────────────────────────────────────────────

def is_high_quality_available() -> bool:
    """
    FIX: expose whether the indic-transliteration library is installed.
    Callers can use this to warn users when only the fallback is active.
    """
    return INDIC_AVAILABLE


def devanagari_to_roman(text: str) -> str:
    """
    Transliterate Devanagari characters in text to Roman (ITRANS) script.
    Non-Devanagari characters (English words, punctuation) are left unchanged.

    Preference: indic-transliteration library → fallback char-map.
    """
    if not text or not DEVANAGARI_RANGE.search(text):
        return text  # Nothing to transliterate

    if INDIC_AVAILABLE:
        # FIX: split on Devanagari spans so English words are never passed
        # through the ITRANS encoder (which would garble them)
        result = _transliterate_mixed(text)
    else:
        result = _fallback_transliterate(text)

    # FIX: normalise Devanagari digits regardless of path taken
    return result.translate(_DEVA_DIGITS)


def roman_to_devanagari(text: str) -> str:
    """
    Convert ITRANS Roman text to Devanagari.
    Requires indic-transliteration library (pip install indic-transliteration).
    """
    if not INDIC_AVAILABLE:
        raise RuntimeError(
            "indic-transliteration is required for Roman → Devanagari conversion.\n"
            "Install it with:  pip install indic-transliteration"
        )
    return _transliterate(text, sanscript.ITRANS, sanscript.DEVANAGARI)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _transliterate_mixed(text: str) -> str:
    """
    FIX: split the string into Devanagari spans and non-Devanagari spans.
    Only Devanagari spans are passed to the library; Roman spans are kept as-is.
    This prevents English words in Hinglish segments from being mangled.

    Example:
        "यह good है"  →  ["यह", " good ", "है"]
        Devanagari spans transliterated, " good " passed through unchanged.
    """
    # re.split with a capturing group keeps the delimiters in the result list
    parts = re.split(r"([\u0900-\u097F]+)", text)
    result = []
    for part in parts:
        if part and DEVANAGARI_RANGE.search(part):
            result.append(
                _transliterate(part, sanscript.DEVANAGARI, sanscript.ITRANS)
            )
        else:
            result.append(part)
    return "".join(result)


def _fallback_transliterate(text: str) -> str:
    """
    Character-by-character mapping when indic-transliteration is unavailable.
    Lossy and one-way — see module docstring for limitations.
    """
    result = []
    i = 0
    while i < len(text):
        # Check two-char sequences first (e.g. "अं", "अः")
        two = text[i:i + 2]
        if two in DEVANAGARI_ROMAN_MAP:
            result.append(DEVANAGARI_ROMAN_MAP[two])
            i += 2
        else:
            result.append(DEVANAGARI_ROMAN_MAP.get(text[i], text[i]))
            i += 1
    return "".join(result)
