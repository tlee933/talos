"""Tests for talos.tui.TalosCommandCompleter."""

from unittest.mock import MagicMock

from talos.tui import TalosCommandCompleter


def _complete(completer, text):
    """Helper: run completer and return list of completion strings."""
    doc = MagicMock()
    doc.text_before_cursor = text
    event = MagicMock()
    return [c.text for c in completer.get_completions(doc, event)]


def test_empty_input():
    """Empty input should return all commands."""
    c = TalosCommandCompleter()
    results = _complete(c, "")
    assert "help" in results
    assert "exit" in results
    assert "stats" in results
    assert "reset" in results


def test_partial_match():
    """Partial input should return matching commands."""
    c = TalosCommandCompleter()
    results = _complete(c, "he")
    assert "help" in results
    assert "exit" not in results


def test_exact_match():
    """Exact command name should still complete."""
    c = TalosCommandCompleter()
    results = _complete(c, "exit")
    assert "exit" in results


def test_no_match():
    """Non-matching input returns nothing."""
    c = TalosCommandCompleter()
    results = _complete(c, "zzz")
    assert len(results) == 0


def test_space_stops_completion():
    """Input with a space (i.e., after a command) returns nothing."""
    c = TalosCommandCompleter()
    results = _complete(c, "help something")
    assert len(results) == 0


def test_remember_in_completions():
    """remember command should appear in completions."""
    c = TalosCommandCompleter()
    results = _complete(c, "rem")
    assert "remember" in results


def test_recall_in_completions():
    """recall command should appear in completions."""
    c = TalosCommandCompleter()
    results = _complete(c, "rec")
    assert "recall" in results


def test_facts_in_completions():
    """facts command should appear in completions."""
    c = TalosCommandCompleter()
    results = _complete(c, "fac")
    assert "facts" in results
