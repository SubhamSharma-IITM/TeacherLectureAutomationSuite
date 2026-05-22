"""
assignment.py
Generate practice assignment questions from a lecture transcript using Claude.
"""
import os
import json
import anthropic

# ── Config ─────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Types ──────────────────────────────────────────────────────────────────────

VALID_QUESTION_TYPES = {"mcq", "short_answer", "true_false"}
VALID_DIFFICULTIES   = {"easy", "medium", "hard"}


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_assignment(
    full_text: str,
    question_types: list[str],
    difficulty: str        = "medium",
    num_questions: int     = 10,
    language: str          = "en",
) -> dict:
    """
    Generate a practice assignment from a lecture transcript.

    Args:
        full_text:       The complete transcript text.
        question_types:  List from ["mcq", "short_answer", "true_false"].
        difficulty:      "easy", "medium", or "hard".
        num_questions:   Total number of questions to generate.
        language:        Primary language of the transcript ("hi", "en", "hi+en").

    Returns:
        dict with keys: title, questions, metadata
    """
    # Validate inputs
    invalid_types = set(question_types) - VALID_QUESTION_TYPES
    if invalid_types:
        raise ValueError(f"Invalid question types: {invalid_types}")
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {VALID_DIFFICULTIES}")
    if not full_text or not full_text.strip():
        raise ValueError("Transcript text is empty.")
    if num_questions < 1 or num_questions > 50:
        raise ValueError("num_questions must be between 1 and 50.")

    # Truncate very long transcripts to avoid token limits
    # ~12000 chars ≈ 3000 tokens, well within Claude's context
    transcript_excerpt = full_text[:12000]
    if len(full_text) > 12000:
        transcript_excerpt += "\n\n[Transcript truncated for length]"

    prompt = _build_prompt(
        transcript_excerpt, question_types, difficulty, num_questions, language
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    return _parse_response(raw, question_types, difficulty, num_questions)


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_prompt(
    transcript: str,
    question_types: list[str],
    difficulty: str,
    num_questions: int,
    language: str,
) -> str:
    type_instructions = {
        "mcq": (
            "Multiple Choice Questions (MCQ): each with exactly 4 options (A, B, C, D), "
            "one correct answer, and a brief explanation of why it is correct."
        ),
        "short_answer": (
            "Short Answer Questions: open-ended questions requiring 2-3 sentence answers, "
            "with a model answer provided."
        ),
        "true_false": (
            "True/False Questions: a clear statement that is either true or false, "
            "with the correct answer and a brief explanation."
        ),
    }

    difficulty_instructions = {
        "easy":   "Focus on basic recall and comprehension of key facts.",
        "medium": "Focus on understanding and application of concepts.",
        "hard":   "Focus on analysis, synthesis, and critical thinking.",
    }

    lang_instruction = (
        "Generate questions in Hindi (Devanagari script) matching the lecture language."
        if language == "hi" else
        "Generate questions in both Hindi and English where the transcript mixes languages."
        if language == "hi+en" else
        "Generate questions in English."
    )

    types_str = "\n".join(
        f"- {type_instructions[t]}" for t in question_types if t in type_instructions
    )

    return f"""You are an expert educational content creator. Generate a practice assignment from this lecture transcript.

TRANSCRIPT:
{transcript}

REQUIREMENTS:
- Total questions: {num_questions}
- Difficulty: {difficulty} — {difficulty_instructions[difficulty]}
- Question types to include:
{types_str}
- Language: {lang_instruction}
- Questions must be directly based on the lecture content only.
- Distribute questions evenly across the requested types.

Return ONLY a valid JSON object with this exact structure (no markdown, no preamble):
{{
  "title": "Practice Assignment: [topic derived from transcript]",
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct_answer": "A",
      "explanation": "..."
    }},
    {{
      "id": 2,
      "type": "short_answer",
      "question": "...",
      "model_answer": "..."
    }},
    {{
      "id": 3,
      "type": "true_false",
      "question": "...",
      "correct_answer": true,
      "explanation": "..."
    }}
  ],
  "metadata": {{
    "difficulty": "{difficulty}",
    "total_questions": {num_questions},
    "question_types": {json.dumps(question_types)}
  }}
}}"""


# ── Response parser ────────────────────────────────────────────────────────────

def _parse_response(raw: str, question_types: list, difficulty: str, num_questions: int) -> dict:
    """Parse and validate Claude's JSON response."""
    # Strip markdown fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        clean = "\n".join(clean.split("\n")[1:])
    if clean.endswith("```"):
        clean = "\n".join(clean.split("\n")[:-1])
    clean = clean.strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse assignment response: {e}") from e

    # Basic validation
    if "questions" not in data or not isinstance(data["questions"], list):
        raise RuntimeError("Invalid assignment response: missing questions array")

    # Ensure every question has required base fields
    for i, q in enumerate(data["questions"]):
        if "id" not in q:
            q["id"] = i + 1
        if "type" not in q:
            q["type"] = question_types[0] if question_types else "short_answer"

    return data
