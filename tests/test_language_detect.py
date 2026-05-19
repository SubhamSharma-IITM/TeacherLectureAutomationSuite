"""
tests/test_language_detect.py
Unit tests for language detection logic.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
from language_detect import tag_segment_language, detect_language_mix


class TestTagSegmentLanguage:

    def test_pure_hindi_devanagari(self):
        text = "नमस्ते, आज हम बात करेंगे।"
        assert tag_segment_language(text, "hi") == "hi"

    def test_pure_english(self):
        text = "Today we are going to discuss machine learning algorithms."
        assert tag_segment_language(text, "en") == "en"

    def test_hinglish_mixed(self):
        text = "आज हम machine learning के बारे में discuss करेंगे।"
        result = tag_segment_language(text, "hi")
        assert result in ("hi", "hi+en")  # could go either way depending on ratio

    def test_empty_text(self):
        assert tag_segment_language("", "en") == "en"
        assert tag_segment_language("", "hi") == "hi"

    def test_whisper_fallback_to_detected(self):
        # Text with no Devanagari but Whisper says Hindi → return "hi"
        text = "Aaj hum machine learning ke baare mein baat karenge"
        result = tag_segment_language(text, "hi")
        # Romanized Hindi — whisper_detected = "hi" but no Devanagari
        assert result == "hi"  # respects whisper hint

    def test_english_with_whisper_hint_en(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert tag_segment_language(text, "en") == "en"


class TestDetectLanguageMix:

    def test_all_hindi(self):
        segments = [{"language": "hi"} for _ in range(10)]
        mix = detect_language_mix(segments)
        assert mix["primary"] == "hi"
        assert mix["english"] < 10

    def test_all_english(self):
        segments = [{"language": "en"} for _ in range(10)]
        mix = detect_language_mix(segments)
        assert mix["primary"] == "en"

    def test_mixed_majority_hindi(self):
        segments = (
            [{"language": "hi"}] * 6 +
            [{"language": "en"}] * 3 +
            [{"language": "hi+en"}] * 1
        )
        mix = detect_language_mix(segments)
        assert mix["primary"] == "hi"
        assert "hindi" in mix
        assert "english" in mix
        assert "mixed" in mix

    def test_empty_segments(self):
        mix = detect_language_mix([])
        assert mix["hindi"] == 0
        assert mix["english"] == 0
