import json
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx


SYSTEM_PROMPT = """\
You are Talos, a local desktop AI assistant running on Fedora Kinoite with KDE Plasma 6.
You have access to the shell and can execute commands to help the user.

When you need to run a command, output it in a fenced code block with the language tag `bash`:

```bash
command here
```

You may include multiple code blocks if a task requires several steps.
Between code blocks, briefly explain what you're doing and why.
After seeing command output, analyze the results and continue or summarize.

Be direct and concise. Focus on solving the task.\
"""


@dataclass
class CodeBlock:
    """A shell command extracted from LLM output."""
    command: str
    lang: str = "bash"


@dataclass
class Turn:
    """A single message in the conversation."""
    role: str
    content: str


@dataclass
class ParsedResponse:
    """LLM response split into reasoning segments and code blocks."""
    segments: list  # list of (str, CodeBlock | None) tuples
    raw: str
    error: str = ""  # non-empty if this is an error sentinel


_CODE_BLOCK_RE = re.compile(
    r"```(\w*)\n(.*?)```",
    re.DOTALL,
)


def parse_response(text: str) -> ParsedResponse:
    """Parse LLM output into alternating reasoning text and code blocks."""
    segments = []
    last_end = 0

    for m in _CODE_BLOCK_RE.finditer(text):
        # Reasoning text before this code block
        before = text[last_end:m.start()].strip()
        lang = m.group(1) or "bash"
        code = m.group(2).strip()
        if before:
            segments.append((before, None))
        if code:
            segments.append(("", CodeBlock(command=code, lang=lang)))
        last_end = m.end()

    # Trailing reasoning after the last code block
    trailing = text[last_end:].strip()
    if trailing:
        segments.append((trailing, None))

    # If no segments at all, treat the whole thing as reasoning
    if not segments:
        segments.append((text.strip(), None))

    return ParsedResponse(segments=segments, raw=text)


def _error_response(msg: str) -> ParsedResponse:
    """Create a sentinel ParsedResponse for connection errors."""
    return ParsedResponse(segments=[(msg, None)], raw="", error=msg)


_CONNECT_ERRORS = (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError)


class Agent:
    def __init__(self, base_url: str):
        self.http = httpx.AsyncClient(base_url=base_url, timeout=120.0)
        self.history: list[Turn] = []
        self.max_history = 20  # keep last N turns to fit context

    def _messages(self, system: str | None = None, context: str | None = None) -> list[dict]:
        sys_text = system or SYSTEM_PROMPT
        if context:
            sys_text = f"{sys_text}\n\n{context}"
        msgs = [{"role": "system", "content": sys_text}]
        # Trim to max_history (keep most recent)
        history = self.history[-self.max_history:]
        for turn in history:
            msgs.append({"role": turn.role, "content": turn.content})
        return msgs

    def _payload(self, system: str | None = None, stream: bool = False, context: str | None = None) -> dict:
        payload = {
            "model": "hivecoder-7b",
            "messages": self._messages(system, context=context),
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        if stream:
            payload["stream"] = True
        return payload

    # --- Non-streaming (fallback) ---

    async def chat(self, message: str, system: str | None = None, context: str | None = None) -> ParsedResponse:
        """Send a message, get a parsed response. Maintains conversation history."""
        self.history.append(Turn(role="user", content=message))
        try:
            resp = await self.http.post(
                "/v1/chat/completions",
                json=self._payload(system, context=context),
            )
            resp.raise_for_status()
        except _CONNECT_ERRORS as exc:
            return _error_response(f"hivemind unreachable: {exc}")

        content = resp.json()["choices"][0]["message"]["content"]
        self.history.append(Turn(role="assistant", content=content))
        return parse_response(content)

    async def feed_result(self, command: str, result: str, system: str | None = None, context: str | None = None) -> ParsedResponse:
        """Feed command output back to the LLM for continued reasoning."""
        output_msg = f"Command: `{command}`\nOutput:\n```\n{result}\n```"
        self.history.append(Turn(role="user", content=output_msg))
        try:
            resp = await self.http.post(
                "/v1/chat/completions",
                json=self._payload(system, context=context),
            )
            resp.raise_for_status()
        except _CONNECT_ERRORS as exc:
            return _error_response(f"hivemind unreachable: {exc}")

        content = resp.json()["choices"][0]["message"]["content"]
        self.history.append(Turn(role="assistant", content=content))
        return parse_response(content)

    # --- Streaming ---

    async def stream_chat(self, message: str, system: str | None = None, context: str | None = None) -> AsyncIterator[str]:
        """Stream a chat response, yielding delta content strings.

        Accumulates the full response and appends to history when done.
        """
        self.history.append(Turn(role="user", content=message))
        accumulated = []

        try:
            async with self.http.stream(
                "POST",
                "/v1/chat/completions",
                json=self._payload(system, stream=True, context=context),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    chunk = _parse_sse_line(line)
                    if chunk is None:
                        continue
                    if chunk == "":
                        # Stream done
                        break
                    accumulated.append(chunk)
                    yield chunk
        except _CONNECT_ERRORS as exc:
            error_msg = f"\n[hivemind unreachable: {exc}]"
            accumulated.append(error_msg)
            yield error_msg

        full_text = "".join(accumulated)
        if full_text:
            self.history.append(Turn(role="assistant", content=full_text))

    async def stream_feed_result(
        self, command: str, result: str, system: str | None = None, context: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream the LLM's analysis of command output."""
        output_msg = f"Command: `{command}`\nOutput:\n```\n{result}\n```"
        self.history.append(Turn(role="user", content=output_msg))
        accumulated = []

        try:
            async with self.http.stream(
                "POST",
                "/v1/chat/completions",
                json=self._payload(system, stream=True, context=context),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    chunk = _parse_sse_line(line)
                    if chunk is None:
                        continue
                    if chunk == "":
                        break
                    accumulated.append(chunk)
                    yield chunk
        except _CONNECT_ERRORS as exc:
            error_msg = f"\n[hivemind unreachable: {exc}]"
            accumulated.append(error_msg)
            yield error_msg

        full_text = "".join(accumulated)
        if full_text:
            self.history.append(Turn(role="assistant", content=full_text))

    # --- Hive-Mind tool API ---

    async def fact_store(self, key: str, value: str) -> dict:
        """Store a fact via Hive-Mind."""
        try:
            resp = await self.http.post("/fact/store", json={"key": key, "value": value})
            resp.raise_for_status()
            return resp.json()
        except _CONNECT_ERRORS as exc:
            return {"error": str(exc)}

    async def fact_get(self, key: str | None = None) -> dict:
        """Retrieve a fact (or all facts) via Hive-Mind."""
        try:
            payload = {"key": key} if key else {}
            resp = await self.http.post("/fact/get", json=payload)
            resp.raise_for_status()
            return resp.json()
        except _CONNECT_ERRORS as exc:
            return {"error": str(exc)}

    async def memory_store(self, context: str, files: list[str] | None = None, task: str | None = None) -> dict:
        """Store session context via Hive-Mind."""
        try:
            payload: dict = {"context": context}
            if files:
                payload["files"] = files
            if task:
                payload["task"] = task
            resp = await self.http.post("/memory/store", json=payload)
            resp.raise_for_status()
            return resp.json()
        except _CONNECT_ERRORS as exc:
            return {"error": str(exc)}

    async def memory_recall(self, session_id: str | None = None) -> dict:
        """Recall session context from Hive-Mind."""
        try:
            payload = {"session_id": session_id} if session_id else {}
            resp = await self.http.post("/memory/recall", json=payload)
            resp.raise_for_status()
            return resp.json()
        except _CONNECT_ERRORS as exc:
            return {"error": str(exc)}

    # --- Connection health ---

    @property
    async def connected(self) -> bool:
        """Quick health check — is Hive-Mind reachable?"""
        try:
            resp = await self.http.get("/health", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def reset(self):
        """Clear conversation history."""
        self.history.clear()

    async def health(self) -> dict:
        try:
            resp = await self.http.get("/health")
            return resp.json()
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def stats(self) -> dict:
        try:
            resp = await self.http.get("/stats")
            return resp.json()
        except Exception:
            return {}

    async def bench(self, tokens: int = 40) -> dict:
        """Quick generation benchmark. Returns tok/sec."""
        try:
            start = time.monotonic()
            resp = await self.http.post(
                "/v1/chat/completions",
                json={
                    "model": "hivecoder-7b",
                    "messages": [{"role": "user", "content": "Count: 1, 2, 3, 4, 5..."}],
                    "max_tokens": tokens,
                    "temperature": 0.0,
                },
            )
            elapsed = time.monotonic() - start
            usage = resp.json().get("usage", {})
            gen = usage.get("completion_tokens", 0)
            return {
                "gen_tok_s": round(gen / elapsed, 1) if elapsed else 0,
                "elapsed": round(elapsed, 2),
            }
        except Exception:
            return {}

    async def close(self):
        await self.http.aclose()


def _parse_sse_line(line: str) -> str | None:
    """Parse a single SSE line from llama-server.

    Returns:
        - content string (may be empty for keep-alive)
        - "" (empty string) on stream end ([DONE] or finish_reason: stop)
        - None for non-data lines (comments, blank lines)
    """
    line = line.strip()
    if not line or line.startswith(":"):
        return None
    if not line.startswith("data: "):
        return None

    payload = line[6:]  # strip "data: "

    if payload.strip() == "[DONE]":
        return ""

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    choices = data.get("choices", [])
    if not choices:
        return None

    choice = choices[0]

    # Check finish_reason
    if choice.get("finish_reason") in ("stop", "length"):
        return ""

    delta = choice.get("delta", {})
    return delta.get("content", "")
