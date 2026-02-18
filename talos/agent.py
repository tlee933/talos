import httpx


SYSTEM_PROMPT = (
    "You are Talos, a local desktop AI assistant running on Fedora Kinoite with KDE Plasma 6. "
    "You execute shell commands, search files, manage the desktop, and query an Obsidian vault. "
    "Be direct. When a task needs a command, give the exact command."
)


class Agent:
    def __init__(self, base_url: str):
        self.http = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    async def chat(self, message: str, system: str | None = None) -> str:
        resp = await self.http.post(
            "/v1/chat/completions",
            json={
                "model": "hivecoder-7b",
                "messages": [
                    {"role": "system", "content": system or SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def health(self) -> dict:
        try:
            resp = await self.http.get("/health")
            return resp.json()
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def close(self):
        await self.http.aclose()
