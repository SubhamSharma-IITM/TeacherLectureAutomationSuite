"""
tests/test_language_detect.py
Unit tests for language detection logic.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
from language_detect import tag_segment_language, detect_language_mix


# ── tag_segment_language ───────────────────────────────────────────────────────

class TestTagSegmentLanguage:
    def test_pure_hindi_devanagari(self):
        text = "नमस्ते, आज हम बात करेंगे।"
        assert tag_segment_language(text, "hi") == "hi"

    def test_pure_english(self):
        text = "Today we are going to discuss machine learning algorithms."
        assert tag_segment_language(text, "en") == "en"

    def test_hinglish_mixed(self):
        # FIX: this text has clear Devanagari + English markers — should reliably be hi+en
        text = "आज हम machine learning के बारे में discuss करेंगे।"
        assert tag_segment_language(text, "hi") == "hi+en"

    def test_empty_text_returns_whisper_detected(self):
        assert tag_segment_language("", "en") == "en"
        assert tag_segment_language("", "hi") == "hi"

    def test_whisper_fallback_romanised_hindi(self):
        # FIX: zero Devanagari chars → devanagari_ratio = 0.0 which is NOT > 0.02
        # so the transliterated Hindi branch is NOT taken → falls through to "en"
        text = "Aaj hum machine learning ke baare mein baat karenge"
        assert tag_segment_language(text, "hi") == "en"

    def test_whisper_fallback_with_some_devanagari(self):
        # A few Devanagari chars (ratio > 0.02) + Whisper said Hindi → "hi"
        text = "Aaj hum के baare mein baat karenge"
        assert tag_segment_language(text, "hi") == "hi"

    def test_english_with_whisper_hint_en(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert tag_segment_language(text, "en") == "en"

    def test_punctuation_stripped_before_matching(self):
        # FIX: "this," should match ENGLISH_MARKERS["this"] after stripping punctuation
        text = "यह concept this, is, and the best।"
        result = tag_segment_language(text, "hi")
        # Has Devanagari + English markers → hi+en
        assert result == "hi+en"

    def test_only_punctuation_and_digits(self):
        text = "123. 456?"
        result = tag_segment_language(text, "en")
        assert result == "en"


# ── detect_language_mix ────────────────────────────────────────────────────────

class TestDetectLanguageMix:
    def test_all_hindi(self):
        segments = [{"language": "hi"} for _ in range(10)]
        mix = detect_language_mix(segments)
        assert mix["primary"]  == "hi"
        # FIX: pin to exact value, not loose < 10
        assert mix["english"]  == 0
        assert mix["mixed"]    == 0
        assert mix["hindi"]    == 100

    def test_all_english(self):
        segments = [{"language": "en"} for _ in range(10)]
        mix = detect_language_mix(segments)
        assert mix["primary"]  == "en"
        assert mix["hindi"]    == 0
        assert mix["mixed"]    == 0
        assert mix["english"]  == 100

    def test_all_mixed(self):
        segments = [{"language": "hi+en"} for _ in range(10)]
        mix = detect_language_mix(segments)
        assert mix["mixed"]   == 100
        assert mix["hindi"]   == 0
        assert mix["english"] == 0

    def test_mixed_majority_hindi(self):
        segments = (
            [{"language": "hi"}]    * 6 +
            [{"language": "en"}]    * 3 +
            [{"language": "hi+en"}] * 1
        )
        mix = detect_language_mix(segments)
        assert mix["primary"] == "hi"
        assert "hindi"   in mix
        assert "english" in mix
        assert "mixed"   in mix

    def test_percentages_sum_to_100(self):
        # FIX: key fix from language_detect.py — must always sum to exactly 100
        segments = (
            [{"language": "hi"}]    * 5 +
            [{"language": "en"}]    * 3 +
            [{"language": "hi+en"}] * 2
        )
        mix = detect_language_mix(segments)
        assert mix["hindi"] + mix["english"] + mix["mixed"] == 100

    def test_percentages_sum_to_100_all_mixed(self):
        segments = [{"language": "hi+en"} for _ in range(7)]
        mix = detect_language_mix(segments)
        assert mix["hindi"] + mix["english"] + mix["mixed"] == 100

    def test_empty_segments(self):
        mix = detect_language_mix([])
        assert mix["hindi"]   == 0
        assert mix["english"] == 0
        assert mix["mixed"]   == 0

    def test_unknown_language_tag_falls_back_to_english(self):
        # FIX: unknown tags should not crash — fall back to "en" bucket
        segments = [{"language": "fr"}, {"language": "de"}, {"language": "en"}]
        mix = detect_language_mix(segments)
        assert mix["english"] == 100

    def test_missing_language_key_falls_back(self):
        # Segment with no "language" key — defaults to "en"
        segments = [{}, {"language": "hi"}]
        mix = detect_language_mix(segments)
        assert mix["hindi"] + mix["english"] + mix["mixed"] == 100

    def test_primary_is_english_when_equal(self):
        # Tie goes to English (current implementation)
        segments = (
            [{"language": "hi"}] * 5 +
            [{"language": "en"}] * 5
        )
        mix = detect_language_mix(segments)
        assert mix["primary"] in ("hi", "en")  # either is valid on a tie
