"""Environment context gathering and @reference expansion."""

import asyncio
import os
import re
from pathlib import Path

from talos import kde, shell

# Matches @file.py, @src/main.py, @clip, @clipboard
_REF_RE = re.compile(r"@(clip(?:board)?|[\w./_-]+\.\w+)")

MAX_FILE_CHARS = 8000


async def gather_environment() -> str:
    """Collect cwd, git branch, and short diff stats. Returns context string or ''."""
    parts = [f"- cwd: {os.getcwd()}"]

    branch_result = await shell.run(
        "git rev-parse --abbrev-ref HEAD", timeout=5.0
    )
    if branch_result.ok and branch_result.stdout.strip():
        parts.append(f"- git branch: {branch_result.stdout.strip()}")

        diff_result = await shell.run(
            "git diff --stat HEAD", timeout=5.0
        )
        if diff_result.ok and diff_result.stdout.strip():
            # Summarize: just the last summary line
            lines = diff_result.stdout.strip().splitlines()
            parts.append(f"- git changes: {lines[-1].strip()}")

    if len(parts) == 1:
        return ""  # Only cwd, not very useful on its own

    return "Current environment:\n" + "\n".join(parts)


def expand_references(text: str) -> tuple[str, str]:
    """Expand @file and @clip references in user input.

    Returns (cleaned_text, context_block):
      - cleaned_text: input with @refs removed
      - context_block: file/clipboard contents for injection (may be empty)
    """
    matches = list(_REF_RE.finditer(text))
    if not matches:
        return text, ""

    blocks: list[str] = []
    cleaned = text

    for m in reversed(matches):  # reverse to preserve positions
        ref = m.group(1)
        cleaned = cleaned[:m.start()] + cleaned[m.end():]

        if ref in ("clip", "clipboard"):
            content = asyncio.get_event_loop().run_until_complete(kde.clip_read())
            if content:
                blocks.append(f"[clipboard]\n{content[:MAX_FILE_CHARS]}")
        else:
            path = Path(ref)
            if not path.is_absolute():
                path = Path.cwd() / path
            try:
                content = path.read_text(errors="replace")
                if content:
                    label = ref
                    if len(content) > MAX_FILE_CHARS:
                        content = content[:MAX_FILE_CHARS] + "\n...(truncated)"
                    blocks.append(f"[{label}]\n{content}")
            except (OSError, PermissionError):
                blocks.append(f"[{ref}] (file not found)")

    cleaned = cleaned.strip()
    # Reverse blocks so they appear in original order
    blocks.reverse()
    context = "\n\n".join(blocks) if blocks else ""
    return cleaned, context


async def expand_references_async(text: str) -> tuple[str, str]:
    """Async version of expand_references for use in async contexts."""
    matches = list(_REF_RE.finditer(text))
    if not matches:
        return text, ""

    blocks: list[str] = []
    cleaned = text

    for m in reversed(matches):
        ref = m.group(1)
        cleaned = cleaned[:m.start()] + cleaned[m.end():]

        if ref in ("clip", "clipboard"):
            content = await kde.clip_read()
            if content:
                blocks.append(f"[clipboard]\n{content[:MAX_FILE_CHARS]}")
        else:
            path = Path(ref)
            if not path.is_absolute():
                path = Path.cwd() / path
            try:
                content = path.read_text(errors="replace")
                if content:
                    label = ref
                    if len(content) > MAX_FILE_CHARS:
                        content = content[:MAX_FILE_CHARS] + "\n...(truncated)"
                    blocks.append(f"[{label}]\n{content}")
            except (OSError, PermissionError):
                blocks.append(f"[{ref}] (file not found)")

    cleaned = cleaned.strip()
    blocks.reverse()
    context = "\n\n".join(blocks) if blocks else ""
    return cleaned, context
