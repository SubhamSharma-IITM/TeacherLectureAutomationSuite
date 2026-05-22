"""
tests/test_transliterate.py
Unit tests for Devanagari ↔ Roman transliteration.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
from unittest.mock import patch
from transliterate import (
    devanagari_to_roman,
    roman_to_devanagari,
    is_high_quality_available,
    _fallback_transliterate,
    DEVANAGARI_RANGE,
)


# ── devanagari_to_roman ────────────────────────────────────────────────────────

class TestDevanagariToRoman:
    def test_pure_english_unchanged(self):
        """Text with no Devanagari should pass through untouched."""
        text = "Hello world, this is English."
        assert devanagari_to_roman(text) == text

    def test_empty_string(self):
        assert devanagari_to_roman("") == ""

    def test_devanagari_numerals_converted(self):
        """Devanagari digits ०–९ should become 0–9 regardless of library."""
        result = devanagari_to_roman("०१२३४५६७८९")
        assert result == "0123456789"

    def test_mixed_hinglish_english_words_preserved(self):
        """English words in mixed text should not be garbled."""
        text = "आज हम machine learning सीखेंगे"
        result = devanagari_to_roman(text)
        assert "machine" in result
        assert "learning" in result

    def test_devanagari_chars_are_converted(self):
        """After conversion, no Devanagari code points should remain."""
        text = "नमस्ते दुनिया"
        result = devanagari_to_roman(text)
        assert not DEVANAGARI_RANGE.search(result), (
            f"Devanagari chars remain in output: {result!r}"
        )

    def test_punctuation_preserved(self):
        """Punctuation should not be stripped."""
        text = "नमस्ते! आप कैसे हैं?"
        result = devanagari_to_roman(text)
        assert "!" in result
        assert "?" in result


# ── Fallback transliterator ────────────────────────────────────────────────────

class TestFallbackTransliterate:
    def test_basic_consonants(self):
        assert _fallback_transliterate("क") == "k"
        assert _fallback_transliterate("म") == "m"
        assert _fallback_transliterate("न") == "n"

    def test_devanagari_numerals(self):
        assert _fallback_transliterate("०") == "0"
        assert _fallback_transliterate("५") == "5"
        assert _fallback_transliterate("९") == "9"

    def test_two_char_sequences(self):
        """Two-char sequences like अं and अः must be handled before single chars."""
        result = _fallback_transliterate("अं")
        assert result == "an"

    def test_punctuation_danda(self):
        assert _fallback_transliterate("।") == "."
        assert _fallback_transliterate("॥") == "."

    def test_unknown_char_passed_through(self):
        """Characters not in the map should be returned as-is."""
        assert _fallback_transliterate("X") == "X"
        assert _fallback_transliterate("3") == "3"

    def test_empty_string(self):
        assert _fallback_transliterate("") == ""


# ── roman_to_devanagari ────────────────────────────────────────────────────────

class TestRomanToDevanagari:
    def test_raises_without_indic_library(self):
        """If indic-transliteration is not available, should raise RuntimeError."""
        with patch("transliterate.INDIC_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="indic-transliteration"):
                roman_to_devanagari("namaste")

    @pytest.mark.skipif(
        not is_high_quality_available(),
        reason="indic-transliteration not installed",
    )
    def test_roundtrip_approximate(self):
        """ITRANS → Devanagari should produce Devanagari output."""
        result = roman_to_devanagari("namaste")
        assert DEVANAGARI_RANGE.search(result), (
            f"Expected Devanagari in output, got: {result!r}"
        )


# ── is_high_quality_available ─────────────────────────────────────────────────

class TestIsHighQualityAvailable:
    def test_returns_bool(self):
        result = is_high_quality_available()
        assert isinstance(result, bool)

    def test_reflects_indic_available_flag(self):
        import transliterate as tr_module
        with patch.object(tr_module, "INDIC_AVAILABLE", True):
            assert is_high_quality_available() is True
        with patch.object(tr_module, "INDIC_AVAILABLE", False):
            assert is_high_quality_available() is False


# ── Mixed Hinglish edge cases ─────────────────────────────────────────────────

class TestEdgeCases:
    def test_only_digits_devanagari(self):
        result = devanagari_to_roman("प्रश्न १: क्या आप ठीक हैं?")
        assert "1" in result

    def test_numbers_not_garbled(self):
        """Latin digits inline with Devanagari should survive."""
        text = "slide 5: यह महत्वपूर्ण है"
        result = devanagari_to_roman(text)
        assert "5" in result
        assert "slide" in result

    def test_special_regex_chars_in_text(self):
        """Text with regex special chars like + ( ) should not crash."""
        text = "C++ और Python (दोनों) अच्छे हैं"
        result = devanagari_to_roman(text)
        assert "C++" in result
        assert "Python" in result
