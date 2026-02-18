import re
import time
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


class Agent:
    def __init__(self, base_url: str):
        self.http = httpx.AsyncClient(base_url=base_url, timeout=120.0)
        self.history: list[Turn] = []
        self.max_history = 20  # keep last N turns to fit context

    def _messages(self, system: str | None = None) -> list[dict]:
        msgs = [{"role": "system", "content": system or SYSTEM_PROMPT}]
        # Trim to max_history (keep most recent)
        history = self.history[-self.max_history:]
        for turn in history:
            msgs.append({"role": turn.role, "content": turn.content})
        return msgs

    async def chat(self, message: str, system: str | None = None) -> ParsedResponse:
        """Send a message, get a parsed response. Maintains conversation history."""
        self.history.append(Turn(role="user", content=message))

        resp = await self.http.post(
            "/v1/chat/completions",
            json={
                "model": "hivecoder-7b",
                "messages": self._messages(system),
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        self.history.append(Turn(role="assistant", content=content))
        return parse_response(content)

    async def feed_result(self, command: str, result: str, system: str | None = None) -> ParsedResponse:
        """Feed command output back to the LLM for continued reasoning."""
        output_msg = f"Command: `{command}`\nOutput:\n```\n{result}\n```"
        self.history.append(Turn(role="user", content=output_msg))

        resp = await self.http.post(
            "/v1/chat/completions",
            json={
                "model": "hivecoder-7b",
                "messages": self._messages(system),
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        self.history.append(Turn(role="assistant", content=content))
        return parse_response(content)

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
