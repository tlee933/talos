"""Context window management for bounded LLM context.

Provides token estimation, budget calculation, and smart pruning
to keep conversations within the 32K token window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from talos.agent import Agent, Turn

# Constants tuned for Qwen2.5-Coder-7B (32K context)
MAX_CONTEXT_TOKENS = 32768
RESERVED_TOKENS = 4096  # headroom for response generation
CHARS_PER_TOKEN = 3.5
MIN_RECENT_TURNS = 6


def estimate_tokens(text: str) -> int:
    """Approximate token count from character length."""
    return int(len(text) / CHARS_PER_TOKEN)


@dataclass
class ContextBudget:
    """Token budget breakdown for the current conversation."""
    system_tokens: int
    history_tokens: int
    total: int
    remaining: int
    needs_pruning: bool


def calculate_budget(system_prompt: str, history: list[Turn]) -> ContextBudget:
    """Calculate token budget and determine if pruning is needed."""
    system_tokens = estimate_tokens(system_prompt)
    history_tokens = sum(estimate_tokens(t.content) for t in history)
    total = system_tokens + history_tokens
    remaining = MAX_CONTEXT_TOKENS - RESERVED_TOKENS - total
    needs_pruning = remaining < 0

    return ContextBudget(
        system_tokens=system_tokens,
        history_tokens=history_tokens,
        total=total,
        remaining=remaining,
        needs_pruning=needs_pruning,
    )


def smart_prune(history: list[Turn], target_tokens: int) -> list[Turn]:
    """Prune conversation history to fit within target token count.

    Strategy:
    - Always keep the first turn (establishes context)
    - Always keep the last MIN_RECENT_TURNS turns
    - Drop middle turns oldest-first
    - Truncate individual turns longer than 1000 tokens to 500 tokens
    """
    if not history:
        return []

    # Truncate long individual turns first
    truncated = []
    for turn in history:
        tokens = estimate_tokens(turn.content)
        if tokens > 1000:
            # Keep first ~500 tokens worth of chars
            max_chars = int(500 * CHARS_PER_TOKEN)
            from talos.agent import Turn as _Turn
            truncated.append(_Turn(
                role=turn.role,
                content=turn.content[:max_chars] + "\n...(truncated)",
            ))
        else:
            truncated.append(turn)

    # Check if truncation alone is enough
    total = sum(estimate_tokens(t.content) for t in truncated)
    if total <= target_tokens:
        return truncated

    # Split into first, middle, recent
    if len(truncated) <= MIN_RECENT_TURNS + 1:
        return truncated  # too short to prune further

    first = [truncated[0]]
    recent = truncated[-MIN_RECENT_TURNS:]
    middle = truncated[1:-MIN_RECENT_TURNS]

    # Drop middle turns oldest-first until we fit
    while middle:
        total = (
            sum(estimate_tokens(t.content) for t in first)
            + sum(estimate_tokens(t.content) for t in middle)
            + sum(estimate_tokens(t.content) for t in recent)
        )
        if total <= target_tokens:
            break
        middle.pop(0)

    result = first + middle + recent

    # If still over budget after dropping all middle, just return first + recent
    total = sum(estimate_tokens(t.content) for t in result)
    if total > target_tokens:
        return first + recent

    return result


async def summarize_history(agent: Agent, history: list[Turn]) -> list[Turn]:
    """Compress old conversation turns into a summary via LLM.

    Falls back to smart_prune if summarization fails.
    """
    target = MAX_CONTEXT_TOKENS - RESERVED_TOKENS

    # If history is short enough, no need to summarize
    total = sum(estimate_tokens(t.content) for t in history)
    if total <= target:
        return history

    # Try LLM-based summarization of old turns
    if len(history) <= MIN_RECENT_TURNS + 1:
        return smart_prune(history, target)

    recent = history[-MIN_RECENT_TURNS:]
    old = history[:-MIN_RECENT_TURNS]

    # Build summary prompt
    old_text = "\n".join(f"{t.role}: {t.content[:500]}" for t in old)
    summary_prompt = (
        "Summarize the following conversation history in 2-3 sentences, "
        "preserving key facts, decisions, and context:\n\n"
        f"{old_text[:3000]}"
    )

    try:
        resp = await agent.http.post(
            "/v1/chat/completions",
            json={
                "model": "hivecoder-7b",
                "messages": [
                    {"role": "system", "content": "You are a concise summarizer."},
                    {"role": "user", "content": summary_prompt},
                ],
                "max_tokens": 200,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        summary = resp.json()["choices"][0]["message"]["content"]

        from talos.agent import Turn as _Turn
        summary_turn = _Turn(
            role="system",
            content=f"[Conversation summary]: {summary}",
        )
        return [summary_turn] + recent

    except Exception:
        # Fallback to token-based pruning
        return smart_prune(history, target)
