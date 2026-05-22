"""
tests/test_assignment.py
Unit tests for assignment.py — Claude-powered question generation.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import json
import pytest
from unittest.mock import patch, MagicMock
from assignment import (
    generate_assignment,
    _build_prompt,
    _parse_questions,
    AssignmentRequest,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

SAMPLE_TRANSCRIPT = """
Today we will discuss neural networks and deep learning.
A neural network is a set of algorithms modeled after the human brain.
Deep learning uses multiple layers to progressively extract features.
Gradient descent is the primary optimisation algorithm used in training.
"""

SAMPLE_MCQ_JSON = json.dumps([
    {
        "type": "mcq",
        "question": "What is gradient descent primarily used for?",
        "options": ["A. Data preprocessing", "B. Training optimisation", "C. Feature extraction", "D. Model deployment"],
        "answer": "B",
        "explanation": "Gradient descent minimises the loss function during training.",
    }
])

SAMPLE_SHORT_ANSWER_JSON = json.dumps([
    {
        "type": "short_answer",
        "question": "Explain what a neural network is.",
        "answer": "A neural network is a set of algorithms modeled after the human brain.",
        "explanation": "As defined in the lecture.",
    }
])

SAMPLE_TRUE_FALSE_JSON = json.dumps([
    {
        "type": "true_false",
        "question": "Deep learning uses only a single layer to extract features.",
        "answer": "False",
        "explanation": "Deep learning uses multiple layers.",
    }
])


def _mock_claude_response(content: str):
    """Build a mock Anthropic API response containing `content`."""
    message = MagicMock()
    block   = MagicMock()
    block.type = "text"
    block.text = content
    message.content = [block]
    return message


# ── _build_prompt ──────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_includes_transcript(self):
        req = AssignmentRequest(
            transcript=SAMPLE_TRANSCRIPT,
            question_types=["mcq"],
            difficulty="medium",
            count=5,
        )
        prompt = _build_prompt(req)
        assert SAMPLE_TRANSCRIPT.strip() in prompt

    def test_includes_question_types(self):
        req = AssignmentRequest(
            transcript=SAMPLE_TRANSCRIPT,
            question_types=["mcq", "short_answer"],
            difficulty="hard",
            count=10,
        )
        prompt = _build_prompt(req)
        assert "mcq" in prompt.lower() or "multiple choice" in prompt.lower()
        assert "short_answer" in prompt.lower() or "short answer" in prompt.lower()

    def test_includes_difficulty(self):
        req = AssignmentRequest(
            transcript=SAMPLE_TRANSCRIPT,
            question_types=["true_false"],
            difficulty="easy",
            count=3,
        )
        prompt = _build_prompt(req)
        assert "easy" in prompt.lower()

    def test_includes_count(self):
        req = AssignmentRequest(
            transcript=SAMPLE_TRANSCRIPT,
            question_types=["mcq"],
            difficulty="medium",
            count=15,
        )
        prompt = _build_prompt(req)
        assert "15" in prompt


# ── _parse_questions ──────────────────────────────────────────────────────────

class TestParseQuestions:
    def test_parses_valid_json(self):
        questions = _parse_questions(SAMPLE_MCQ_JSON)
        assert len(questions) == 1
        assert questions[0]["type"] == "mcq"

    def test_strips_markdown_fences(self):
        wrapped = f"```json\n{SAMPLE_MCQ_JSON}\n```"
        questions = _parse_questions(wrapped)
        assert len(questions) == 1

    def test_returns_empty_list_on_invalid_json(self):
        questions = _parse_questions("this is not json")
        assert questions == []

    def test_returns_empty_list_on_non_list_json(self):
        questions = _parse_questions('{"key": "value"}')
        assert questions == []

    def test_handles_extra_whitespace(self):
        padded = f"   \n{SAMPLE_MCQ_JSON}\n   "
        questions = _parse_questions(padded)
        assert len(questions) == 1

    def test_short_answer_parsed(self):
        questions = _parse_questions(SAMPLE_SHORT_ANSWER_JSON)
        assert questions[0]["type"] == "short_answer"
        assert "question" in questions[0]
        assert "answer" in questions[0]

    def test_true_false_parsed(self):
        questions = _parse_questions(SAMPLE_TRUE_FALSE_JSON)
        assert questions[0]["type"] == "true_false"


# ── generate_assignment ────────────────────────────────────────────────────────

class TestGenerateAssignment:
    def _make_request(self, **kwargs):
        defaults = dict(
            transcript=SAMPLE_TRANSCRIPT,
            question_types=["mcq"],
            difficulty="medium",
            count=5,
        )
        defaults.update(kwargs)
        return AssignmentRequest(**defaults)

    def test_returns_questions_list(self):
        req     = self._make_request()
        mock_response = _mock_claude_response(SAMPLE_MCQ_JSON)

        with patch("assignment.anthropic_client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            result = generate_assignment(req)

        assert "questions" in result
        assert isinstance(result["questions"], list)

    def test_returns_metadata(self):
        req     = self._make_request()
        mock_response = _mock_claude_response(SAMPLE_MCQ_JSON)

        with patch("assignment.anthropic_client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            result = generate_assignment(req)

        assert "difficulty"      in result
        assert "question_types"  in result
        assert "generated_count" in result

    def test_claude_called_with_correct_model(self):
        req           = self._make_request()
        mock_response = _mock_claude_response(SAMPLE_MCQ_JSON)

        with patch("assignment.anthropic_client") as mock_client, \
             patch("assignment.CLAUDE_MODEL", "claude-sonnet-4-20250514"):
            mock_client.messages.create.return_value = mock_response
            generate_assignment(req)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"

    def test_empty_transcript_raises(self):
        req = self._make_request(transcript="")
        with pytest.raises((ValueError, Exception)):
            with patch("assignment.anthropic_client"):
                generate_assignment(req)

    def test_invalid_question_type_raises(self):
        with pytest.raises((ValueError, Exception)):
            AssignmentRequest(
                transcript=SAMPLE_TRANSCRIPT,
                question_types=["invalid_type"],
                difficulty="medium",
                count=5,
            )

    def test_count_clamped_to_valid_range(self):
        """Count should be between 1 and 30."""
        with pytest.raises((ValueError, Exception)):
            AssignmentRequest(
                transcript=SAMPLE_TRANSCRIPT,
                question_types=["mcq"],
                difficulty="medium",
                count=0,
            )
        with pytest.raises((ValueError, Exception)):
            AssignmentRequest(
                transcript=SAMPLE_TRANSCRIPT,
                question_types=["mcq"],
                difficulty="medium",
                count=31,
            )

    def test_invalid_difficulty_raises(self):
        with pytest.raises((ValueError, Exception)):
            AssignmentRequest(
                transcript=SAMPLE_TRANSCRIPT,
                question_types=["mcq"],
                difficulty="impossible",
                count=5,
            )

    def test_claude_api_error_raises_http_exception(self):
        req = self._make_request()
        with patch("assignment.anthropic_client") as mock_client:
            mock_client.messages.create.side_effect = Exception("API error")
            with pytest.raises(Exception):
                generate_assignment(req)

    def test_malformed_claude_response_returns_empty_questions(self):
        """If Claude returns unparseable JSON, result should have empty questions list."""
        req           = self._make_request()
        mock_response = _mock_claude_response("I could not generate questions.")

        with patch("assignment.anthropic_client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            result = generate_assignment(req)

        assert result["questions"] == []

    def test_multiple_question_types(self):
        req = self._make_request(question_types=["mcq", "short_answer", "true_false"])
        combined = json.dumps(
            json.loads(SAMPLE_MCQ_JSON) +
            json.loads(SAMPLE_SHORT_ANSWER_JSON) +
            json.loads(SAMPLE_TRUE_FALSE_JSON)
        )
        mock_response = _mock_claude_response(combined)

        with patch("assignment.anthropic_client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            result = generate_assignment(req)

        types_in_result = {q["type"] for q in result["questions"]}
        assert "mcq"          in types_in_result
        assert "short_answer" in types_in_result
        assert "true_false"   in types_in_result
