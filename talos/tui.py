"""Interactive REPL."""

import asyncio

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from talos.agent import Agent
from talos.config import Config
from talos.theme import THEME, COLORS
from talos import shell


console = Console(theme=THEME)


async def run(config: Config):
    from talos import __version__

    console.print(f"\n[prompt]⚙ talos {__version__}[/] [dim]— the bronze guardian[/]")
    console.print(f"[dim]  type help or ctrl-c to quit[/]\n")

    agent = Agent(config.hivemind_url)
    try:
        health = await agent.health()
        status = "ok" if health.get("status") in ("ok", "healthy") else "unreachable"
        style = "ok" if status == "ok" else "err"
        console.print(f"  [{style}]hivemind[/] [dim]{config.hivemind_url}[/]")
        if config.obsidian_vault:
            console.print(f"  [ok]vault[/]    [dim]{config.obsidian_vault}[/]")
        console.print()

        while True:
            try:
                line = Prompt.ask(f"[prompt]\u25b8[/]")
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            line = line.strip()
            if not line:
                continue
            if line in ("exit", "quit", "q"):
                break
            if line == "help":
                _help()
                continue

            # ! prefix = direct shell
            if line.startswith("!"):
                cmd = line[1:].strip()
                if cmd:
                    r = await shell.run(cmd)
                    if r.stdout:
                        console.print(r.stdout.rstrip())
                    if r.stderr:
                        console.print(f"[err]{r.stderr.rstrip()}[/]")
                continue

            with console.status("[dim]thinking...[/]", spinner="dots"):
                response = await agent.chat(line)

            console.print(
                Panel(Markdown(response), border_style=COLORS["verdigris"], padding=(0, 1))
            )
            console.print()
    finally:
        await agent.close()


def _help():
    console.print("""
  [accent]<query>[/]        ask talos anything
  [accent]!<cmd>[/]         run a shell command directly
  [accent]exit[/]           quit
""")
