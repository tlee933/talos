"""KDE Plasma helpers — notify, clipboard, file search."""

import asyncio
import os
import subprocess


async def notify(summary: str, body: str = "", urgency: str = "normal"):
    cmd = ["notify-send", f"--app-name=Talos", f"--urgency={urgency}", summary]
    if body:
        cmd.append(body)
    env = os.environ.copy()
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
    proc = await asyncio.create_subprocess_exec(
        *cmd, env=env, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    await proc.wait()


async def clip_read() -> str:
    proc = await asyncio.create_subprocess_exec(
        "wl-paste", "--no-newline",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode(errors="replace") if proc.returncode == 0 else ""


async def clip_write(text: str):
    proc = await asyncio.create_subprocess_exec(
        "wl-copy", stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate(input=text.encode())


async def file_search(query: str, limit: int = 20) -> list[str]:
    """Search files via Baloo."""
    proc = await asyncio.create_subprocess_exec(
        "baloosearch", query,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return []
    return [l.strip() for l in stdout.decode().splitlines()[:limit] if l.strip()]
