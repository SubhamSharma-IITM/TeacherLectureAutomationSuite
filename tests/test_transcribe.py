"""
tests/test_transcribe.py
Unit tests for transcribe.py — mocking OpenAI Whisper API calls.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_mock_segment(id_, start, end, text, lang="en"):
    seg = MagicMock()
    seg.id    = id_
    seg.start = start
    seg.end   = end
    seg.text  = f"  {text}  "  # intentional whitespace — should be stripped
    return seg


def make_mock_transcript(segments, language="en"):
    t = MagicMock()
    t.language = language
    t.segments = segments
    return t


# ── _preprocess_audio ──────────────────────────────────────────────────────────

class TestPreprocessAudio:
    def test_small_file_returned_unchanged(self, tmp_path):
        """Files under 25 MB should be returned as-is without conversion."""
        audio = tmp_path / "short.mp3"
        audio.write_bytes(b"0" * 1024)  # 1 KB

        from transcribe import _preprocess_audio
        result = _preprocess_audio(str(audio))
        assert result == str(audio)

    def test_large_file_is_converted(self, tmp_path):
        """Files over 25 MB should be converted to WAV in a temp location."""
        audio = tmp_path / "long.mp3"
        audio.write_bytes(b"0" * (26 * 1024 * 1024))  # 26 MB

        mock_audio_segment = MagicMock()
        mock_audio_segment.set_channels.return_value = mock_audio_segment
        mock_audio_segment.set_frame_rate.return_value = mock_audio_segment

        with patch("transcribe.AudioSegment.from_file", return_value=mock_audio_segment):
            from transcribe import _preprocess_audio
            result = _preprocess_audio(str(audio))

        # Should write to a temp path, not overwrite original
        assert result != str(audio)
        assert result.endswith(".wav")

    def test_large_file_does_not_overwrite_original_wav(self, tmp_path):
        """If original is already .wav and large, should not overwrite it."""
        audio = tmp_path / "long.wav"
        audio.write_bytes(b"0" * (26 * 1024 * 1024))

        mock_seg = MagicMock()
        mock_seg.set_channels.return_value = mock_seg
        mock_seg.set_frame_rate.return_value = mock_seg

        with patch("transcribe.AudioSegment.from_file", return_value=mock_seg):
            from transcribe import _preprocess_audio
            result = _preprocess_audio(str(audio))

        # Must differ from original path (tempfile)
        assert result != str(audio)


# ── transcribe_audio ───────────────────────────────────────────────────────────

class TestTranscribeAudio:
    def _make_small_audio(self, tmp_path, name="test.mp3") -> str:
        p = tmp_path / name
        p.write_bytes(b"0" * 1024)
        return str(p)

    def test_returns_expected_keys(self, tmp_path):
        audio_path = self._make_small_audio(tmp_path)
        segments   = [make_mock_segment(0, 0.0, 3.0, "Hello world")]
        transcript = make_mock_transcript(segments, "en")

        with patch("transcribe.client") as mock_client:
            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            result = transcribe_audio(audio_path, language_hint="en")

        assert "detected_language" in result
        assert "segments"          in result
        assert "full_text"         in result

    def test_segment_text_is_stripped(self, tmp_path):
        audio_path = self._make_small_audio(tmp_path)
        segments   = [make_mock_segment(0, 0.0, 3.0, "  Hello world  ")]
        transcript = make_mock_transcript(segments, "en")

        with patch("transcribe.client") as mock_client:
            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            result = transcribe_audio(audio_path)

        assert result["segments"][0]["text"] == "Hello world"

    def test_timestamps_are_rounded(self, tmp_path):
        audio_path = self._make_small_audio(tmp_path)
        segments   = [make_mock_segment(0, 1.2345, 4.6789, "Test")]
        transcript = make_mock_transcript(segments, "en")

        with patch("transcribe.client") as mock_client:
            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            result = transcribe_audio(audio_path)

        seg = result["segments"][0]
        assert seg["start"] == 1.23
        assert seg["end"]   == 4.68

    def test_language_hint_auto_not_passed_to_whisper(self, tmp_path):
        """language_hint='auto' should NOT send a language param to Whisper."""
        audio_path = self._make_small_audio(tmp_path)
        segments   = [make_mock_segment(0, 0.0, 1.0, "Test")]
        transcript = make_mock_transcript(segments, "en")

        with patch("transcribe.client") as mock_client:
            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            transcribe_audio(audio_path, language_hint="auto")

        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        assert "language" not in call_kwargs

    def test_language_hint_hi_passed_to_whisper(self, tmp_path):
        audio_path = self._make_small_audio(tmp_path)
        segments   = [make_mock_segment(0, 0.0, 1.0, "नमस्ते")]
        transcript = make_mock_transcript(segments, "hi")

        with patch("transcribe.client") as mock_client:
            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            transcribe_audio(audio_path, language_hint="hi")

        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        assert call_kwargs.get("language") == "hi"

    def test_temp_file_cleaned_up_after_success(self, tmp_path):
        """Converted temp WAV should be deleted after successful transcription."""
        big_audio = tmp_path / "big.mp3"
        big_audio.write_bytes(b"0" * (26 * 1024 * 1024))

        mock_seg = MagicMock()
        mock_seg.set_channels.return_value = mock_seg
        mock_seg.set_frame_rate.return_value = mock_seg

        temp_wav = str(tmp_path / "temp_converted.wav")

        segments   = [make_mock_segment(0, 0.0, 1.0, "Test")]
        transcript = make_mock_transcript(segments, "en")

        with patch("transcribe.AudioSegment.from_file", return_value=mock_seg), \
             patch("transcribe.tempfile.mktemp", return_value=temp_wav), \
             patch("transcribe.client") as mock_client, \
             patch("transcribe.Path") as mock_path_cls:

            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            transcribe_audio(str(big_audio))

        # unlink should have been called on the temp path
        mock_path_cls.assert_any_call(temp_wav)

    def test_temp_file_cleaned_up_on_exception(self, tmp_path):
        """Temp WAV should be deleted even if Whisper raises an exception."""
        big_audio = tmp_path / "big.mp3"
        big_audio.write_bytes(b"0" * (26 * 1024 * 1024))

        mock_seg = MagicMock()
        mock_seg.set_channels.return_value = mock_seg
        mock_seg.set_frame_rate.return_value = mock_seg

        with patch("transcribe.AudioSegment.from_file", return_value=mock_seg), \
             patch("transcribe.client") as mock_client:

            mock_client.audio.transcriptions.create.side_effect = RuntimeError("API down")
            from transcribe import transcribe_audio
            with pytest.raises(RuntimeError, match="API down"):
                transcribe_audio(str(big_audio))

    def test_roman_script_transliterates_hindi_segments(self, tmp_path):
        audio_path = self._make_small_audio(tmp_path)
        segments   = [make_mock_segment(0, 0.0, 3.0, "नमस्ते दुनिया")]
        transcript = make_mock_transcript(segments, "hi")

        with patch("transcribe.client") as mock_client, \
             patch("transcribe.devanagari_to_roman", return_value="namaste duniya") as mock_tr:
            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            result = transcribe_audio(audio_path, language_hint="hi", script="roman")

        mock_tr.assert_called_once()
        assert result["segments"][0]["text"] == "namaste duniya"

    def test_full_text_joins_all_segments(self, tmp_path):
        audio_path = self._make_small_audio(tmp_path)
        segs = [
            make_mock_segment(0, 0.0, 2.0, "Hello"),
            make_mock_segment(1, 2.0, 4.0, "world"),
        ]
        transcript = make_mock_transcript(segs, "en")

        with patch("transcribe.client") as mock_client:
            mock_client.audio.transcriptions.create.return_value = transcript
            from transcribe import transcribe_audio
            result = transcribe_audio(audio_path)

        assert result["full_text"] == "Hello world"


# ── API key validation ─────────────────────────────────────────────────────────

class TestApiKeyValidation:
    def test_missing_api_key_raises_at_import(self, monkeypatch):
        """If OPENAI_API_KEY is not set, import should raise RuntimeError."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Remove cached module so it re-imports
        import importlib
        import transcribe
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            importlib.reload(transcribe)
