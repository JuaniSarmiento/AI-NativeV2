"""Coherence evaluation prompt templates (B4).

Used by CognitiveService.close_session() to ask the LLM to score
the alignment between a student's chat discussion and their code.

IMPORTANT: This module has ZERO database I/O and ZERO FastAPI imports.
It contains only string constants and a pure function.
"""
from __future__ import annotations

COHERENCE_SYSTEM_PROMPT = """You are an educational assessment tool. Your task is to evaluate the coherence between a student's chat discussion with a tutor and the code they actually wrote.

Score from 0 to 100:
- 100: Perfect alignment — student discussed exactly what they coded
- 70-99: Good alignment with minor tangents
- 40-69: Partial alignment — some discussion doesn't relate to code or vice versa
- 0-39: Poor alignment — student discussed one thing but coded something else

Respond ONLY with valid JSON: {"score": <number>, "reasoning": "<brief explanation>"}"""


def build_coherence_prompt(chat_messages: list[str], code_content: str) -> str:
    """Build the user-facing coherence evaluation prompt.

    Args:
        chat_messages: List of student message strings (most recent last).
                       Caller should slice to a reasonable window (e.g. last 10).
        code_content:  The student's latest code submission.

    Returns:
        A formatted prompt string ready to send to the LLM.
    """
    chat_text = "\n".join(f"- {msg}" for msg in chat_messages)
    return f"""## Student Chat Messages
{chat_text}

## Student's Code
```
{code_content}
```

Evaluate the coherence between the chat discussion and the code."""
