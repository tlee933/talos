"""Tests for Agent conversation bridge methods."""

import asyncio
import json

import httpx

from talos.agent import Agent


def _mock_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    body = json.loads(request.content) if request.content else {}

    if path == "/conversation/log":
        return httpx.Response(200, json={
            "success": True, "role": body.get("role"), "source": body.get("source"),
        })

    if path == "/conversation/recent":
        messages = [
            {"role": "user", "content": "hello", "source": "tui", "timestamp": 1.0},
            {"role": "assistant", "content": "hi there", "source": "tui", "timestamp": 2.0},
            {"role": "user", "content": "from firefox", "source": "firefox", "timestamp": 3.0},
        ]
        source_filter = body.get("source")
        if source_filter:
            messages = [m for m in messages if m["source"] == source_filter]
        limit = body.get("limit", 20)
        return httpx.Response(200, json={"success": True, "messages": messages[:limit]})

    return httpx.Response(404, json={"error": "not found"})


def _make_agent():
    transport = httpx.MockTransport(_mock_handler)
    a = Agent("http://localhost:8090")
    a.http = httpx.AsyncClient(transport=transport, base_url="http://localhost:8090")
    return a


def test_conversation_log():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_log("user", "hello world", "tui"))
    assert result["success"] is True
    assert result["role"] == "user"
    assert result["source"] == "tui"


def test_conversation_recent():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_recent(limit=20))
    assert result["success"] is True
    assert len(result["messages"]) == 3


def test_conversation_recent_filtered():
    agent = _make_agent()
    result = asyncio.run(agent.conversation_recent(limit=20, source="firefox"))
    assert result["success"] is True
    assert len(result["messages"]) == 1
    assert result["messages"][0]["source"] == "firefox"


def test_conversation_log_error():
    """Connection error should return error dict, not raise."""
    transport = httpx.MockTransport(
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused"))
    )
    a = Agent("http://localhost:8090")
    a.http = httpx.AsyncClient(transport=transport, base_url="http://localhost:8090")
    result = asyncio.run(a.conversation_log("user", "test", "tui"))
    assert "error" in result
