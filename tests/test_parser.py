"""Tests for talos.agent.parse_response() and _parse_sse_line()."""

from talos.agent import parse_response, CodeBlock, _parse_sse_line, _SSEState


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


def test_parse_response_with_tool_calls():
    """parse_response should populate tool_calls field."""
    raw = 'Let me read that.\n<tool_call>{"name": "file_read", "arguments": {"path": "/tmp/test"}}</tool_call>'
    resp = parse_response(raw)
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "file_read"
    # Reasoning should still be extracted
    assert any("Let me read" in text for text, _ in resp.segments)


def test_parse_response_with_tool_calls_and_code_blocks():
    """Both tool calls and code blocks can coexist."""
    raw = (
        'I will use tools and code:\n'
        '<tool_call>{"name": "notify", "arguments": {"title": "hi"}}</tool_call>\n'
        '```bash\necho done\n```'
    )
    resp = parse_response(raw)
    assert len(resp.tool_calls) == 1
    code_blocks = [b for _, b in resp.segments if b is not None]
    assert len(code_blocks) == 1


def test_parse_response_no_tool_calls():
    """Regular response should have empty tool_calls list."""
    raw = "Just a normal response."
    resp = parse_response(raw)
    assert resp.tool_calls == []


def test_parse_response_think_block():
    """<think> blocks should be extracted into think_blocks."""
    raw = "<think>Let me analyze this step by step.\n1. First check X\n2. Then Y</think>\n\nThe answer is 42."
    resp = parse_response(raw)
    assert len(resp.think_blocks) == 1
    assert "step by step" in resp.think_blocks[0]
    # Think block text should be stripped from segments
    reasoning = resp.segments[0][0]
    assert "<think>" not in reasoning
    assert "The answer is 42" in reasoning


def test_parse_response_think_block_with_code():
    """Think blocks and code blocks can coexist."""
    raw = (
        "<think>I need to list files first.</think>\n\n"
        "Let me check:\n\n```bash\nls -la\n```"
    )
    resp = parse_response(raw)
    assert len(resp.think_blocks) == 1
    assert "list files" in resp.think_blocks[0]
    code_blocks = [b for _, b in resp.segments if b is not None]
    assert len(code_blocks) == 1
    assert code_blocks[0].command == "ls -la"


def test_parse_response_multiple_think_blocks():
    """Multiple think blocks should all be extracted."""
    raw = "<think>First thought.</think>\nSome text.\n<think>Second thought.</think>\nMore text."
    resp = parse_response(raw)
    assert len(resp.think_blocks) == 2
    assert resp.think_blocks[0] == "First thought."
    assert resp.think_blocks[1] == "Second thought."


def test_parse_response_no_think_blocks():
    """Regular response should have empty think_blocks."""
    raw = "Just a normal response."
    resp = parse_response(raw)
    assert resp.think_blocks == []


# --- SSE parser tests ---

def test_sse_regular_content():
    """Regular content delta should be returned."""
    line = 'data: {"choices":[{"delta":{"content":"hello"},"index":0,"finish_reason":null}]}'
    assert _parse_sse_line(line) == "hello"


def test_sse_done():
    """[DONE] should return empty string."""
    assert _parse_sse_line("data: [DONE]") == ""


def test_sse_skip_non_data():
    """Non-data lines should return None."""
    assert _parse_sse_line("") is None
    assert _parse_sse_line(": keep-alive") is None
    assert _parse_sse_line("event: ping") is None


def test_sse_reasoning_content():
    """reasoning_content should be wrapped in <think> tags."""
    state = _SSEState()

    # First reasoning chunk opens the tag
    line1 = 'data: {"choices":[{"delta":{"reasoning_content":"Let me think"},"index":0,"finish_reason":null}]}'
    result1 = _parse_sse_line(line1, state)
    assert result1 == "<think>Let me think"
    assert state.in_reasoning is True

    # Continued reasoning doesn't re-open
    line2 = 'data: {"choices":[{"delta":{"reasoning_content":" about this"},"index":0,"finish_reason":null}]}'
    result2 = _parse_sse_line(line2, state)
    assert result2 == " about this"
    assert state.in_reasoning is True

    # Content closes the think tag
    line3 = 'data: {"choices":[{"delta":{"content":"The answer is 42."},"index":0,"finish_reason":null}]}'
    result3 = _parse_sse_line(line3, state)
    assert result3 == "</think>\nThe answer is 42."
    assert state.in_reasoning is False


def test_sse_reasoning_closed_on_done():
    """Think tag should close on stream end."""
    state = _SSEState()
    state.in_reasoning = True

    result = _parse_sse_line("data: [DONE]", state)
    assert result == "</think>\n"
    assert state.in_reasoning is False


def test_sse_no_state_ignores_reasoning():
    """Without state, reasoning_content is ignored (backwards compat)."""
    line = 'data: {"choices":[{"delta":{"reasoning_content":"thinking"},"index":0,"finish_reason":null}]}'
    # No state passed — reasoning_content ignored, content is empty
    result = _parse_sse_line(line)
    assert result == ""
