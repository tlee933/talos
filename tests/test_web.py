"""Tests for Agent web scraper methods."""

import asyncio
import json

import httpx

from talos.agent import Agent


def _mock_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    body = json.loads(request.content) if request.content else {}

    if path == "/web/fetch":
        return httpx.Response(200, json={
            "title": "Example Page",
            "text": "This is the page content extracted from the URL.",
            "url": body.get("url", ""),
        })

    if path == "/web/search":
        return httpx.Response(200, json={
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "First result"},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "Second result"},
            ]
        })

    return httpx.Response(404, json={"error": "not found"})


def _make_agent():
    transport = httpx.MockTransport(_mock_handler)
    a = Agent("http://localhost:8090")
    a.http = httpx.AsyncClient(transport=transport, base_url="http://localhost:8090")
    return a


def test_web_fetch():
    agent = _make_agent()
    result = asyncio.run(agent.web_fetch("https://example.com"))
    assert result["title"] == "Example Page"
    assert "page content" in result["text"]
    assert result["url"] == "https://example.com"


def test_web_search():
    agent = _make_agent()
    result = asyncio.run(agent.web_search("python asyncio"))
    assert "results" in result
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "Result 1"


def test_web_fetch_error():
    """Connection error should return error dict, not raise."""
    transport = httpx.MockTransport(
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused"))
    )
    a = Agent("http://localhost:8090")
    a.http = httpx.AsyncClient(transport=transport, base_url="http://localhost:8090")
    result = asyncio.run(a.web_fetch("https://example.com"))
    assert "error" in result
