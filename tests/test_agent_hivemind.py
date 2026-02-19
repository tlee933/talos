"""Tests for Agent Hive-Mind API methods using httpx MockTransport."""

import asyncio
import json

import httpx

from talos.agent import Agent


def _mock_handler(request: httpx.Request) -> httpx.Response:
    """Mock transport handler for Hive-Mind endpoints."""
    path = request.url.path
    body = json.loads(request.content) if request.content else {}

    if path == "/fact/store":
        return httpx.Response(200, json={"status": "ok", "key": body.get("key")})

    if path == "/fact/get":
        key = body.get("key")
        if key:
            return httpx.Response(200, json={"key": key, "value": "test-value"})
        return httpx.Response(200, json={"facts": {"os": "fedora", "gpu": "amd"}})

    if path == "/memory/store":
        return httpx.Response(200, json={"status": "ok", "session_id": "abc123"})

    if path == "/memory/recall":
        return httpx.Response(200, json={
            "context": "previous session context",
            "task": "testing",
        })

    return httpx.Response(404, json={"error": "not found"})


def _make_agent():
    """Agent with mocked transport — no real HTTP calls."""
    transport = httpx.MockTransport(_mock_handler)
    a = Agent("http://localhost:8090")
    a.http = httpx.AsyncClient(transport=transport, base_url="http://localhost:8090")
    return a


def test_fact_store():
    agent = _make_agent()
    result = asyncio.run(agent.fact_store("os", "fedora 43"))
    assert result["status"] == "ok"
    assert result["key"] == "os"


def test_fact_get_specific():
    agent = _make_agent()
    result = asyncio.run(agent.fact_get("os"))
    assert result["key"] == "os"
    assert result["value"] == "test-value"


def test_fact_get_all():
    agent = _make_agent()
    result = asyncio.run(agent.fact_get())
    assert "facts" in result
    assert result["facts"]["os"] == "fedora"


def test_memory_store():
    agent = _make_agent()
    result = asyncio.run(agent.memory_store("working on talos", files=["tui.py"], task="dev"))
    assert result["status"] == "ok"
    assert "session_id" in result


def test_memory_recall():
    agent = _make_agent()
    result = asyncio.run(agent.memory_recall())
    assert "context" in result
    assert result["context"] == "previous session context"


def test_fact_store_error():
    """Connection error should return error dict, not raise."""
    transport = httpx.MockTransport(
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused"))
    )
    a = Agent("http://localhost:8090")
    a.http = httpx.AsyncClient(transport=transport, base_url="http://localhost:8090")
    result = asyncio.run(a.fact_store("key", "val"))
    assert "error" in result


def test_context_threading():
    """Verify context parameter reaches the system message."""
    agent = _make_agent()
    agent.history = []
    msgs = agent._messages(context="Current environment:\n- cwd: /tmp")
    sys_msg = msgs[0]["content"]
    assert "Current environment:" in sys_msg
    assert "/tmp" in sys_msg
