"""Tests for talos.tools — parsing, schema, handlers."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

from talos.tools import (
    parse_tool_calls,
    extract_reasoning,
    ToolCall,
    ToolDef,
    build_registry,
    tools_to_openai_schema,
    build_tool_system_prompt,
    _file_read,
    _file_list,
)


def test_parse_valid_tool_call():
    text = 'Let me check.\n<tool_call>{"name": "shell_exec", "arguments": {"command": "ls"}}</tool_call>'
    calls = parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "shell_exec"
    assert calls[0].arguments == {"command": "ls"}


def test_parse_multiple_tool_calls():
    text = (
        '<tool_call>{"name": "file_read", "arguments": {"path": "/tmp/a"}}</tool_call>\n'
        'Some text\n'
        '<tool_call>{"name": "notify", "arguments": {"title": "Done"}}</tool_call>'
    )
    calls = parse_tool_calls(text)
    assert len(calls) == 2
    assert calls[0].name == "file_read"
    assert calls[1].name == "notify"


def test_parse_malformed_json():
    text = '<tool_call>not valid json</tool_call>'
    calls = parse_tool_calls(text)
    assert len(calls) == 0


def test_parse_no_tool_calls():
    text = "Just regular text without any tool calls."
    calls = parse_tool_calls(text)
    assert len(calls) == 0


def test_parse_tool_call_with_code_blocks():
    """Tool calls and code blocks can coexist."""
    text = (
        'I will use a tool:\n'
        '<tool_call>{"name": "file_read", "arguments": {"path": "/tmp/x"}}</tool_call>\n'
        '```bash\necho hello\n```'
    )
    calls = parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "file_read"


def test_parse_missing_name():
    """Tool call without name field should be skipped."""
    text = '<tool_call>{"arguments": {"key": "val"}}</tool_call>'
    calls = parse_tool_calls(text)
    assert len(calls) == 0


def test_parse_arguments_as_string():
    """Arguments can be a JSON string (double-encoded)."""
    text = '<tool_call>{"name": "test", "arguments": "{\\"key\\": \\"val\\"}"}</tool_call>'
    calls = parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].arguments == {"key": "val"}


def test_extract_reasoning():
    text = 'Before\n<tool_call>{"name": "x", "arguments": {}}</tool_call>\nAfter'
    result = extract_reasoning(text)
    assert "Before" in result
    assert "After" in result
    assert "<tool_call>" not in result


def test_extract_reasoning_no_tags():
    text = "Just plain text"
    assert extract_reasoning(text) == "Just plain text"


def test_file_read_valid(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("hello world")
    result = asyncio.run(_file_read(str(p)))
    assert "hello world" in result


def test_file_read_missing():
    result = asyncio.run(_file_read("/nonexistent/path/xyz.txt"))
    assert "error" in result
    assert "not found" in result


def test_file_read_truncation(tmp_path):
    p = tmp_path / "big.txt"
    p.write_text("x" * 10000)
    result = asyncio.run(_file_read(str(p)))
    assert "truncated" in result
    assert len(result) < 10000


def test_file_list(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.py").write_text("b")
    result = asyncio.run(_file_list(str(tmp_path), "*.txt"))
    assert "a.txt" in result
    assert "b.py" not in result


def test_tools_to_openai_schema():
    """Schema should produce valid OpenAI tools format."""
    agent = AsyncMock()
    registry = build_registry(agent)
    schema = tools_to_openai_schema(registry)

    assert isinstance(schema, list)
    assert len(schema) == 10  # 10 built-in tools

    for tool in schema:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]


def test_build_registry():
    agent = AsyncMock()
    registry = build_registry(agent)

    assert len(registry) == 10
    assert "shell_exec" in registry
    assert "file_read" in registry
    assert "web_fetch" in registry
    assert registry["shell_exec"].requires_confirm is True
    assert registry["file_read"].requires_confirm is False


def test_build_tool_system_prompt():
    agent = AsyncMock()
    registry = build_registry(agent)
    prompt = build_tool_system_prompt(registry)

    assert "tool_call" in prompt
    assert "shell_exec" in prompt
    assert "file_read" in prompt
    assert "Available tools:" in prompt
