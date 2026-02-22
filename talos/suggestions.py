"""Ghost suggestion engine for the TUI — mirrors the Firefox extension logic."""

from __future__ import annotations

import re

BASE_SUGGESTIONS: list[str] = [
    "Summarize this page",
    "Explain this code",
    "What does this do?",
    "Write a function that ",
    "Help me understand ",
    "How do I ",
    "Fix this bug",
    "Refactor this to ",
    "What are the key points?",
    "Compare these approaches",
    "Give me an example of ",
    "Debug this error",
    "Optimize this code",
    "What is the difference between ",
]


def detect_response_patterns(content: str) -> dict[str, bool]:
    """Detect patterns in assistant response content."""
    if not content:
        return {"has_code": False, "has_list": False, "has_error": False, "has_explanation": False}
    c = content.lower()
    return {
        "has_code": "```" in c or "function" in c or "class " in c,
        "has_list": "1." in c or "- " in c or "* " in c,
        "has_error": "error" in c or "bug" in c or "fix" in c or "issue" in c,
        "has_explanation": "means" in c or "because" in c or "essentially" in c,
    }


def get_context_suggestions(last_content: str) -> list[str]:
    """Build context-aware follow-up suggestions from last assistant content."""
    if not last_content:
        return []

    patterns = detect_response_patterns(last_content)
    follow: list[str] = []

    if patterns["has_code"]:
        follow.extend([
            "Explain this step by step",
            "Can you add error handling?",
            "Write tests for this",
            "Can you optimize this?",
            "Show me a different approach",
        ])
    if patterns["has_list"]:
        follow.extend([
            "Tell me more about the first one",
            "Which do you recommend?",
            "Can you elaborate on that?",
            "Give me a comparison table",
        ])
    if patterns["has_error"]:
        follow.extend([
            "What caused this error?",
            "How do I prevent this?",
            "Are there other edge cases?",
            "Show me the fix",
        ])
    if patterns["has_explanation"]:
        follow.extend([
            "Can you give me an example?",
            "Explain it more simply",
            "How does this relate to ",
            "What are the tradeoffs?",
        ])

    # General follow-ups always available
    follow.extend(["Go deeper on that", "Can you rewrite that?", "Thanks, now ", "What about "])

    return follow


def match_suggestion(input_text: str, suggestions: list[str]) -> str:
    """Match user input against suggestions (case-insensitive prefix).

    Returns the remaining text of the best match, or empty string.
    """
    if not input_text or len(input_text) < 2:
        return ""
    lower = input_text.lower()
    for s in suggestions:
        if s.lower().startswith(lower):
            return s[len(input_text):]
    return ""


def get_ghost(input_text: str, last_assistant: str = "") -> str:
    """Get the ghost suggestion for the current input.

    - Empty input with context → preemptive (first context suggestion)
    - Typing → prefix-match with context suggestions ranked first, then base
    """
    context_suggestions = get_context_suggestions(last_assistant)

    # Empty input — show preemptive
    if not input_text:
        return context_suggestions[0] if context_suggestions else ""

    # Merge: context first, then base
    all_suggestions = context_suggestions + BASE_SUGGESTIONS
    return match_suggestion(input_text, all_suggestions)
