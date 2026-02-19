"""Tests for interaction building and rating enrichment (learning pipeline)."""

from talos.tui import build_interaction


def test_build_interaction_with_commands():
    """Interaction dict has correct shape when commands were executed."""
    commands = [
        {"command": "ls -la", "success": True, "exit_code": 0},
        {"command": "cat README.md", "success": True, "exit_code": 0},
    ]
    result = build_interaction("show me the readme", commands, "Here are the files...")
    assert result is not None
    assert result["user_query"] == "show me the readme"
    assert len(result["commands"]) == 2
    assert result["success"] is True
    assert result["response_summary"] == "Here are the files..."


def test_build_interaction_empty_commands_returns_none():
    """No interaction logged when no commands were executed."""
    result = build_interaction("what is python?", [], "Python is a language.")
    assert result is None


def test_build_interaction_partial_failure():
    """success is False when any command failed."""
    commands = [
        {"command": "ls /tmp", "success": True, "exit_code": 0},
        {"command": "cat /nonexistent", "success": False, "exit_code": 1},
    ]
    result = build_interaction("check files", commands)
    assert result is not None
    assert result["success"] is False


def test_build_interaction_truncates_summary():
    """Response summary is truncated to 500 chars."""
    long_summary = "x" * 1000
    result = build_interaction("test", [{"command": "echo hi", "success": True}], long_summary)
    assert len(result["response_summary"]) == 500


def test_rating_enrichment():
    """Rating field can be added to an existing interaction dict."""
    commands = [{"command": "ls", "success": True, "exit_code": 0}]
    interaction = build_interaction("list files", commands)
    assert "rating" not in interaction

    interaction["rating"] = "positive"
    assert interaction["rating"] == "positive"

    interaction["rating"] = "negative"
    assert interaction["rating"] == "negative"
