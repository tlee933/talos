"""Tests for conversation persistence via Agent CRUD methods."""

import asyncio
import json

import httpx

from talos.agent import Agent, Turn


def _mock_handler(request: httpx.Request) -> httpx.Response:
    """Mock transport for conversation persistence endpoints."""
    path = request.url.path
    body = json.loads(request.content) if request.content else {}

    if path == "/conversation/save":
        conv_id = body.get("conversation_id", "test-id")
        title = body.get("title", "")
        msgs = body.get("messages", [])
        if not title and msgs:
            for m in msgs:
                if m.get("role") == "user":
                    title = m.get("content", "")[:80]
                    break
        return httpx.Response(200, json={
            "success": True,
            "conversation_id": conv_id,
            "title": title or "Untitled",
        })

    if path == "/conversation/load":
        conv_id = body.get("conversation_id", "")
        if conv_id == "missing":
            return httpx.Response(200, json={
                "success": False,
                "error": f"Conversation {conv_id} not found",
            })
        return httpx.Response(200, json={
            "success": True,
            "conversation_id": conv_id,
            "title": "Test conversation",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ],
        })

    if path == "/conversation/list":
        return httpx.Response(200, json={
            "success": True,
            "conversations": [
                {
                    "conversation_id": "abc",
                    "title": "First chat",
                    "source": "tui",
                    "message_count": 4,
                },
                {
                    "conversation_id": "def",
                    "title": "Second chat",
                    "source": "firefox",
                    "message_count": 8,
                },
            ],
        })

    if path == "/conversation/export":
        fmt = body.get("format", "markdown")
        if fmt == "json":
            content = json.dumps({"title": "Test", "messages": []})
        else:
            content = "# Test\n\n**User:** hello\n"
        return httpx.Response(200, json={
            "success": True,
            "format": fmt,
            "content": content,
        })

    return httpx.Response(404, json={"error": "not found"})


def _make_agent():
    transport = httpx.MockTransport(_mock_handler)
    a = Agent("http://localhost:8090")
    a.http = httpx.AsyncClient(transport=transport, base_url="http://localhost:8090")
    return a


def test_conversation_save():
    agent = _make_agent()
    agent.history = [
        Turn(role="user", content="What is Fedora?"),
        Turn(role="assistant", content="Fedora is a Linux distribution."),
    ]
    result = asyncio.run(agent.conversation_save())
    assert result["success"] is True
    assert result["conversation_id"] == agent.conversation_id


def test_conversation_save_auto_title():
    """Title should be auto-generated from first user message."""
    agent = _make_agent()
    agent.history = [
        Turn(role="user", content="How do I install packages?"),
        Turn(role="assistant", content="Use dnf."),
    ]
    result = asyncio.run(agent.conversation_save())
    assert result["success"] is True
    assert "install packages" in result.get("title", "").lower()


def test_conversation_load():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_load("abc123"))
    assert result["success"] is True
    assert len(agent.history) == 2
    assert agent.history[0].role == "user"
    assert agent.history[0].content == "hello"
    assert agent.conversation_id == "abc123"


def test_conversation_load_missing():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_load("missing"))
    assert result["success"] is False
    assert "not found" in result.get("error", "")


def test_conversation_list_saved():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_list_saved())
    assert result["success"] is True
    convs = result.get("conversations", [])
    assert len(convs) == 2
    assert convs[0]["conversation_id"] == "abc"


def test_conversation_export_markdown():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_export("test-id", "markdown"))
    assert result["success"] is True
    assert result["format"] == "markdown"
    assert "# Test" in result.get("content", "")


def test_conversation_export_json():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_export("test-id", "json"))
    assert result["success"] is True
    assert result["format"] == "json"
    content = json.loads(result.get("content", "{}"))
    assert "title" in content
