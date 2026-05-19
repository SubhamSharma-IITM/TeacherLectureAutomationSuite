"""
transliterate.py
Devanagari ↔ Roman (IAST / simplified) transliteration for Hindi text.
Uses indic-transliteration library with fallback regex mapping.
"""

import re

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate as _transliterate
    INDIC_AVAILABLE = True
except ImportError:
    INDIC_AVAILABLE = False


# Simple fallback mapping for common Devanagari chars
DEVANAGARI_ROMAN_MAP = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "अं": "an", "अः": "ah",
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ं": "n", "ः": "h", "्": "", "़": "",
    "।": ".", "॥": ".",
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
}

DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")


def devanagari_to_roman(text: str) -> str:
    """
    Transliterate Devanagari characters in text to Roman script.
    Non-Devanagari characters (English words, punctuation) are left unchanged.

    Preference: indic-transliteration library → fallback char-map.
    """
    if not DEVANAGARI_RANGE.search(text):
        return text  # Nothing to transliterate

    if INDIC_AVAILABLE:
        return _transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)

    return _fallback_transliterate(text)


def roman_to_devanagari(text: str) -> str:
    """
    Convert ITRANS Roman text to Devanagari.
    Requires indic-transliteration library.
    """
    if not INDIC_AVAILABLE:
        raise RuntimeError(
            "indic-transliteration is required for Roman→Devanagari conversion. "
            "Install it with: pip install indic-transliteration"
        )
    return _transliterate(text, sanscript.ITRANS, sanscript.DEVANAGARI)


def _fallback_transliterate(text: str) -> str:
    """
    Simple character-by-character mapping when the library is unavailable.
    Less accurate than indic-transliteration but works without dependencies.
    """
    result = []
    for char in text:
        result.append(DEVANAGARI_ROMAN_MAP.get(char, char))
    return "".join(result)
