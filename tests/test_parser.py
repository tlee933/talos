"""Tests for talos.agent.parse_response()."""

from talos.agent import parse_response, CodeBlock


def test_pure_reasoning():
    """No code blocks — everything is reasoning."""
    resp = parse_response("Just some explanation text.\nWith multiple lines.")
    assert len(resp.segments) == 1
    text, block = resp.segments[0]
    assert "Just some explanation" in text
    assert block is None


def test_single_code_block():
    """One bash block with surrounding reasoning."""
    raw = "Let me check:\n\n```bash\nls -la\n```\n\nDone."
    resp = parse_response(raw)

    # Should have: reasoning, code block, trailing reasoning
    assert len(resp.segments) == 3

    text0, block0 = resp.segments[0]
    assert "Let me check" in text0
    assert block0 is None

    text1, block1 = resp.segments[1]
    assert block1 is not None
    assert block1.command == "ls -la"
    assert block1.lang == "bash"

    text2, block2 = resp.segments[2]
    assert "Done" in text2
    assert block2 is None


def test_multiple_code_blocks():
    """Multiple code blocks with reasoning between them."""
    raw = (
        "First I'll list files:\n\n"
        "```bash\nls\n```\n\n"
        "Then check disk:\n\n"
        "```bash\ndf -h\n```\n\n"
        "All done."
    )
    resp = parse_response(raw)

    code_blocks = [(t, b) for t, b in resp.segments if b is not None]
    assert len(code_blocks) == 2
    assert code_blocks[0][1].command == "ls"
    assert code_blocks[1][1].command == "df -h"


def test_code_block_default_lang():
    """Code block without language tag defaults to bash."""
    raw = "Here:\n\n```\necho hello\n```"
    resp = parse_response(raw)
    code_blocks = [b for _, b in resp.segments if b is not None]
    assert len(code_blocks) == 1
    assert code_blocks[0].lang == "bash"
    assert code_blocks[0].command == "echo hello"


def test_code_block_python_lang():
    """Code block with python language tag."""
    raw = "```python\nprint('hi')\n```"
    resp = parse_response(raw)
    code_blocks = [b for _, b in resp.segments if b is not None]
    assert len(code_blocks) == 1
    assert code_blocks[0].lang == "python"


def test_unclosed_code_block():
    """Unclosed code block should be treated as reasoning."""
    raw = "Here is some text\n```bash\nls -la\nno closing"
    resp = parse_response(raw)
    # Regex won't match unclosed block — treat as pure reasoning
    code_blocks = [b for _, b in resp.segments if b is not None]
    assert len(code_blocks) == 0
    assert resp.segments[0][0]  # Has reasoning text


def test_empty_response():
    """Empty string should produce a single empty reasoning segment."""
    resp = parse_response("")
    assert len(resp.segments) == 1
    text, block = resp.segments[0]
    assert text == ""
    assert block is None


def test_empty_code_block():
    """Code block with no content should be skipped."""
    raw = "Text\n\n```bash\n\n```\n\nMore text"
    resp = parse_response(raw)
    code_blocks = [b for _, b in resp.segments if b is not None]
    assert len(code_blocks) == 0


def test_raw_preserved():
    """The raw field should contain the original text."""
    raw = "hello world"
    resp = parse_response(raw)
    assert resp.raw == raw


def test_multiline_command():
    """Code block with multiline command."""
    raw = "```bash\nfor f in *.txt; do\n  echo $f\ndone\n```"
    resp = parse_response(raw)
    code_blocks = [b for _, b in resp.segments if b is not None]
    assert len(code_blocks) == 1
    assert "for f in" in code_blocks[0].command
    assert "done" in code_blocks[0].command
