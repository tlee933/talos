"""Tests for talos.context_manager — token estimation, budget, pruning."""

from talos.agent import Turn
from talos.context_manager import (
    estimate_tokens,
    calculate_budget,
    smart_prune,
    CHARS_PER_TOKEN,
    MAX_CONTEXT_TOKENS,
    RESERVED_TOKENS,
    MIN_RECENT_TURNS,
)


def test_estimate_tokens():
    """Token estimation should be roughly chars / 3.5."""
    text = "Hello world, this is a test."
    tokens = estimate_tokens(text)
    expected = int(len(text) / CHARS_PER_TOKEN)
    assert tokens == expected


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_calculate_budget_small():
    """Small history should not need pruning."""
    history = [Turn(role="user", content="hello")]
    budget = calculate_budget("System prompt", history)
    assert budget.needs_pruning is False
    assert budget.remaining > 0


def test_calculate_budget_over():
    """Large history should trigger pruning."""
    # Create history that blows the budget
    big_content = "x" * int(MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN)
    history = [Turn(role="user", content=big_content)]
    budget = calculate_budget("System", history)
    assert budget.needs_pruning is True
    assert budget.remaining < 0


def test_smart_prune_short_history():
    """Short history should be returned as-is."""
    history = [
        Turn(role="user", content="hi"),
        Turn(role="assistant", content="hello"),
    ]
    result = smart_prune(history, 5000)
    assert len(result) == 2


def test_smart_prune_keeps_first_and_last():
    """Pruning should keep first turn and last MIN_RECENT_TURNS."""
    # Each turn ~143 tokens, 20 turns = ~2860 tokens — budget of 1200 forces pruning
    history = [Turn(role="user", content=f"msg {i} " + "x" * 500) for i in range(20)]
    result = smart_prune(history, 1200)
    # Should have first + last MIN_RECENT_TURNS
    assert result[0].content.startswith("msg 0")
    assert result[-1].content.startswith("msg 19")
    assert len(result) <= 1 + MIN_RECENT_TURNS + 1  # first + possible middle remnant + recent


def test_smart_prune_drops_middle():
    """Middle turns should be dropped when budget is tight."""
    history = [Turn(role="user", content="x" * 500) for _ in range(20)]
    # Very tight budget that can only fit first + recent
    target = int((1 + MIN_RECENT_TURNS) * 500 / CHARS_PER_TOKEN) + 100
    result = smart_prune(history, target)
    assert len(result) < 20
    assert result[0].content == history[0].content
    assert result[-1].content == history[-1].content


def test_smart_prune_truncates_long_turns():
    """Individual turns over 1000 tokens should be truncated."""
    long_content = "y" * int(2000 * CHARS_PER_TOKEN)
    history = [
        Turn(role="user", content="short"),
        Turn(role="assistant", content=long_content),
        Turn(role="user", content="also short"),
    ]
    result = smart_prune(history, 99999)
    # The long turn should be truncated
    assert len(result[1].content) < len(long_content)
    assert "truncated" in result[1].content


def test_smart_prune_idempotent():
    """Pruning already-small history shouldn't change it."""
    history = [
        Turn(role="user", content="hello"),
        Turn(role="assistant", content="world"),
    ]
    result = smart_prune(history, 99999)
    assert len(result) == len(history)
    assert result[0].content == history[0].content


def test_smart_prune_empty():
    assert smart_prune([], 5000) == []
