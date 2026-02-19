"""Tests for talos.context — regex matching and reference expansion."""

import asyncio
from unittest.mock import patch, AsyncMock

from talos.context import _REF_RE, expand_references_async


# --- Regex tests ---


def test_ref_file_match():
    """@file.py should match."""
    m = _REF_RE.search("look at @main.py please")
    assert m is not None
    assert m.group(1) == "main.py"


def test_ref_path_with_slashes():
    """@src/utils/helper.ts should match."""
    m = _REF_RE.search("check @src/utils/helper.ts")
    assert m is not None
    assert m.group(1) == "src/utils/helper.ts"


def test_ref_clipboard_match():
    """@clip and @clipboard should match."""
    m = _REF_RE.search("explain @clip")
    assert m is not None
    assert m.group(1) == "clip"

    m2 = _REF_RE.search("explain @clipboard")
    assert m2 is not None
    assert m2.group(1) == "clipboard"


def test_ref_bare_word_no_match():
    """Bare words without extension should not match."""
    m = _REF_RE.search("look at @something")
    assert m is None


def test_ref_dotfile_no_match():
    """Dotfiles like @.gitignore should not match (starts with dot)."""
    m = _REF_RE.search("look at @.gitignore")
    assert m is None


def test_ref_multiple():
    """Multiple refs in one line."""
    matches = _REF_RE.findall("compare @foo.py and @bar.js")
    assert matches == ["foo.py", "bar.js"]


# --- expand_references_async tests ---


def test_expand_no_refs():
    """Text without refs should pass through unchanged."""
    cleaned, ctx = asyncio.run(expand_references_async("just a normal query"))
    assert cleaned == "just a normal query"
    assert ctx == ""


def test_expand_file_ref(tmp_path):
    """@file.txt should read and inject file content."""
    test_file = tmp_path / "notes.txt"
    test_file.write_text("hello world")

    with patch("talos.context.Path.cwd", return_value=tmp_path):
        cleaned, ctx = asyncio.run(expand_references_async("explain @notes.txt"))

    assert cleaned == "explain"
    assert "[notes.txt]" in ctx
    assert "hello world" in ctx


def test_expand_clipboard_ref():
    """@clip should read clipboard content."""
    with patch("talos.context.kde.clip_read", new_callable=AsyncMock, return_value="pasted text"):
        cleaned, ctx = asyncio.run(expand_references_async("explain @clip please"))

    assert "explain" in cleaned
    assert "please" in cleaned
    assert "[clipboard]" in ctx
    assert "pasted text" in ctx


def test_expand_missing_file(tmp_path):
    """Missing file ref should produce 'file not found' marker."""
    with patch("talos.context.Path.cwd", return_value=tmp_path):
        cleaned, ctx = asyncio.run(expand_references_async("read @nonexistent.py"))

    assert cleaned == "read"
    assert "file not found" in ctx


def test_expand_large_file_truncated(tmp_path):
    """Files over 8000 chars should be truncated."""
    test_file = tmp_path / "big.txt"
    test_file.write_text("x" * 10000)

    with patch("talos.context.Path.cwd", return_value=tmp_path):
        _, ctx = asyncio.run(expand_references_async("@big.txt summarize"))

    assert "...(truncated)" in ctx
    assert len(ctx) < 10000
