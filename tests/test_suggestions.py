"""Tests for the TUI ghost suggestion engine."""

import pytest

from talos.suggestions import (
    BASE_SUGGESTIONS,
    detect_response_patterns,
    get_context_suggestions,
    get_ghost,
    match_suggestion,
)


class TestDetectResponsePatterns:
    def test_code_with_fenced_block(self):
        r = detect_response_patterns("Here is ```python\ncode```")
        assert r["has_code"] is True

    def test_code_with_function_keyword(self):
        r = detect_response_patterns("This function handles auth")
        assert r["has_code"] is True

    def test_code_with_class_keyword(self):
        r = detect_response_patterns("The class UserManager inherits...")
        assert r["has_code"] is True

    def test_list_with_numbered(self):
        r = detect_response_patterns("1. First\n2. Second")
        assert r["has_list"] is True

    def test_list_with_bullets(self):
        r = detect_response_patterns("- item one\n- item two")
        assert r["has_list"] is True

    def test_error_patterns(self):
        r = detect_response_patterns("There was an error in the build")
        assert r["has_error"] is True

    def test_explanation_patterns(self):
        r = detect_response_patterns("This essentially means the cache is stale")
        assert r["has_explanation"] is True

    def test_multiple_patterns(self):
        r = detect_response_patterns("```js\nfunction fix() {}\n```\n1. step")
        assert r["has_code"] is True
        assert r["has_list"] is True

    def test_empty_content(self):
        r = detect_response_patterns("")
        assert r["has_code"] is False
        assert r["has_list"] is False
        assert r["has_error"] is False
        assert r["has_explanation"] is False


class TestGetContextSuggestions:
    def test_code_follow_ups(self):
        s = get_context_suggestions("Here is ```python\ncode```")
        assert "Explain this step by step" in s
        assert "Write tests for this" in s

    def test_error_follow_ups(self):
        s = get_context_suggestions("There was an error in the build")
        assert "What caused this error?" in s

    def test_empty_content(self):
        assert get_context_suggestions("") == []

    def test_general_follow_ups_always_present(self):
        s = get_context_suggestions("Hello world")
        assert "Go deeper on that" in s
        assert "What about " in s


class TestMatchSuggestion:
    def test_short_input(self):
        assert match_suggestion("", BASE_SUGGESTIONS) == ""
        assert match_suggestion("S", BASE_SUGGESTIONS) == ""

    def test_prefix_match(self):
        assert match_suggestion("Su", BASE_SUGGESTIONS) == "mmarize this page"

    def test_no_match(self):
        assert match_suggestion("zzz no match", BASE_SUGGESTIONS) == ""

    def test_case_insensitive(self):
        assert match_suggestion("su", BASE_SUGGESTIONS) == "mmarize this page"

    def test_exact_match(self):
        assert match_suggestion("Summarize this page", BASE_SUGGESTIONS) == ""


class TestGetGhost:
    def test_empty_with_context(self):
        ghost = get_ghost("", last_assistant="```python\ncode```")
        assert ghost == "Explain this step by step"

    def test_empty_no_context(self):
        ghost = get_ghost("", last_assistant="")
        assert ghost == ""

    def test_typing_matches_context_first(self):
        ghost = get_ghost("Ex", last_assistant="```python\ncode```")
        assert ghost == "plain this step by step"

    def test_typing_falls_through_to_base(self):
        ghost = get_ghost("Su", last_assistant="")
        assert ghost == "mmarize this page"

    def test_no_match(self):
        ghost = get_ghost("zzz nothing", last_assistant="hello")
        assert ghost == ""

    def test_single_char_returns_empty(self):
        ghost = get_ghost("S", last_assistant="code ```block```")
        assert ghost == ""
