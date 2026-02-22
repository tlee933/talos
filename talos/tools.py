"""Tool registry for LLM function calling.

Provides tool definitions, parsing of <tool_call> XML from Qwen2.5-Coder,
built-in tool handlers, and OpenAI-schema conversion.
"""

import json
import re
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any, Callable, Awaitable


@dataclass
class ToolDef:
    """Definition of a callable tool."""
    name: str
    description: str
    parameters: dict  # JSON Schema for arguments
    handler: Callable[..., Awaitable[str]]
    requires_confirm: bool = False


@dataclass
class ToolCall:
    """A tool call parsed from LLM output."""
    name: str
    arguments: dict
    raw: str = ""


# --- Parsing ---

_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL,
)


def parse_tool_calls(text: str) -> list[ToolCall]:
    """Extract tool calls from LLM output containing <tool_call> XML tags."""
    calls = []
    for m in _TOOL_CALL_RE.finditer(text):
        raw = m.group(0)
        try:
            data = json.loads(m.group(1))
            name = data.get("name", "")
            arguments = data.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if name:
                calls.append(ToolCall(name=name, arguments=arguments, raw=raw))
        except (json.JSONDecodeError, TypeError):
            continue
    return calls


def extract_reasoning(text: str) -> str:
    """Strip tool_call tags from text, returning plain reasoning."""
    return _TOOL_CALL_RE.sub("", text).strip()


# --- Built-in tool handlers ---

async def _shell_exec(command: str) -> str:
    from talos.shell import run
    result = await run(command)
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += ("\n" if output else "") + result.stderr
    if not output:
        output = "(no output)"
    # Truncate for context
    if len(output) > 4000:
        output = output[:2000] + "\n...(truncated)...\n" + output[-1500:]
    return f"exit code: {result.code}\n{output}"


async def _file_read(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"error: {path} not found"
    if not p.is_file():
        return f"error: {path} is not a file"
    try:
        text = p.read_text(errors="replace")
        if len(text) > 8000:
            text = text[:8000] + "\n...(truncated at 8K chars)"
        return text
    except Exception as e:
        return f"error: {e}"


async def _file_write(path: str, content: str) -> str:
    p = Path(path).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"error: {e}"


async def _file_list(directory: str = ".", pattern: str = "*") -> str:
    p = Path(directory).expanduser()
    if not p.exists():
        return f"error: {directory} not found"
    if not p.is_dir():
        return f"error: {directory} is not a directory"
    try:
        entries = sorted(p.glob(pattern))[:100]
        if not entries:
            return "(no matches)"
        return "\n".join(str(e) for e in entries)
    except Exception as e:
        return f"error: {e}"


async def _clipboard_read() -> str:
    from talos.kde import clip_read
    text = await clip_read()
    return text or "(clipboard empty)"


async def _clipboard_write(text: str) -> str:
    from talos.kde import clip_write
    await clip_write(text)
    return f"copied {len(text)} chars to clipboard"


async def _notify(title: str, body: str = "") -> str:
    from talos.kde import notify
    await notify(title, body)
    return f"notification sent: {title}"


async def _web_fetch(agent: Any, url: str) -> str:
    result = await agent.web_fetch(url)
    if "error" in result:
        return f"error: {result['error']}"
    title = result.get("title", "")
    text = result.get("text", "")
    if len(text) > 4000:
        text = text[:4000] + "\n...(truncated)"
    return f"title: {title}\n{text}"


async def _fact_store(agent: Any, key: str, value: str) -> str:
    result = await agent.fact_store(key, value)
    if "error" in result:
        return f"error: {result['error']}"
    return f"stored: {key} = {value}"


async def _fact_get(agent: Any, key: str = "") -> str:
    result = await agent.fact_get(key or None)
    if "error" in result:
        return f"error: {result['error']}"
    if key:
        return f"{key} = {result.get('value', '(not found)')}"
    facts = result.get("facts", {})
    if not facts:
        return "(no facts stored)"
    return "\n".join(f"{k} = {v}" for k, v in facts.items())


# --- Registry builder ---

def build_registry(agent: Any) -> dict[str, ToolDef]:
    """Build the tool registry with agent-bound handlers."""
    return {
        "shell_exec": ToolDef(
            name="shell_exec",
            description="Execute a shell command and return the output",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"}
                },
                "required": ["command"],
            },
            handler=_shell_exec,
            requires_confirm=True,
        ),
        "file_read": ToolDef(
            name="file_read",
            description="Read a file and return its contents (truncated to 8K chars)",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"}
                },
                "required": ["path"],
            },
            handler=_file_read,
        ),
        "file_write": ToolDef(
            name="file_write",
            description="Write content to a file (creates parent dirs if needed)",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            handler=_file_write,
            requires_confirm=True,
        ),
        "file_list": ToolDef(
            name="file_list",
            description="List files in a directory matching a glob pattern",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory to list", "default": "."},
                    "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
                },
            },
            handler=_file_list,
        ),
        "clipboard_read": ToolDef(
            name="clipboard_read",
            description="Read current clipboard contents (Wayland)",
            parameters={"type": "object", "properties": {}},
            handler=_clipboard_read,
        ),
        "clipboard_write": ToolDef(
            name="clipboard_write",
            description="Write text to the clipboard (Wayland)",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to copy to clipboard"}
                },
                "required": ["text"],
            },
            handler=_clipboard_write,
        ),
        "notify": ToolDef(
            name="notify",
            description="Send a desktop notification via KDE",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Notification title"},
                    "body": {"type": "string", "description": "Notification body", "default": ""},
                },
                "required": ["title"],
            },
            handler=_notify,
        ),
        "web_fetch": ToolDef(
            name="web_fetch",
            description="Fetch a URL and return its readable text content",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"}
                },
                "required": ["url"],
            },
            handler=partial(_web_fetch, agent),
        ),
        "fact_store": ToolDef(
            name="fact_store",
            description="Store a persistent fact in the knowledge base",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Fact key"},
                    "value": {"type": "string", "description": "Fact value"},
                },
                "required": ["key", "value"],
            },
            handler=partial(_fact_store, agent),
        ),
        "fact_get": ToolDef(
            name="fact_get",
            description="Retrieve a fact from the knowledge base (or all facts if no key)",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Fact key (optional)", "default": ""},
                },
            },
            handler=partial(_fact_get, agent),
        ),
    }


def tools_to_openai_schema(registry: dict[str, ToolDef]) -> list[dict]:
    """Convert tool registry to OpenAI function-calling `tools` array."""
    return [
        {
            "type": "function",
            "function": {
                "name": td.name,
                "description": td.description,
                "parameters": td.parameters,
            },
        }
        for td in registry.values()
    ]


def build_tool_system_prompt(registry: dict[str, ToolDef]) -> str:
    """Generate a system prompt suffix listing available tools."""
    lines = [
        "\n\nYou have access to the following tools. To use a tool, output a <tool_call> tag:",
        "<tool_call>{\"name\": \"tool_name\", \"arguments\": {...}}</tool_call>",
        "",
        "Available tools:",
    ]
    for td in registry.values():
        params = td.parameters.get("properties", {})
        param_strs = []
        for pname, pinfo in params.items():
            ptype = pinfo.get("type", "string")
            pdesc = pinfo.get("description", "")
            param_strs.append(f"    {pname} ({ptype}): {pdesc}")
        lines.append(f"- {td.name}: {td.description}")
        if param_strs:
            lines.extend(param_strs)
    return "\n".join(lines)
