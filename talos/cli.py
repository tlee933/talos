import asyncio

import click
from rich.console import Console

from talos import __version__
from talos.config import Config
from talos.theme import THEME

console = Console(theme=THEME)


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="talos")
@click.pass_context
def main(ctx):
    """Talos — local desktop AI for Linux."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config.load()
    if ctx.invoked_subcommand is None:
        from talos.tui import run

        asyncio.run(run(ctx.obj["config"]))


@main.command()
@click.argument("query", nargs=-1, required=True)
@click.pass_context
def ask(ctx, query):
    """One-shot question."""
    from talos.agent import Agent

    async def _run():
        agent = Agent(ctx.obj["config"].hivemind_url)
        try:
            console.print(await agent.chat(" ".join(query)))
        finally:
            await agent.close()

    asyncio.run(_run())


@main.command()
@click.argument("task", nargs=-1, required=True)
@click.pass_context
def do(ctx, task):
    """Natural language to shell command (with confirmation)."""
    from talos.agent import Agent
    from talos import shell

    async def _run():
        agent = Agent(ctx.obj["config"].hivemind_url)
        try:
            cmd = await agent.chat(
                f"Output only the shell command, no explanation: {' '.join(task)}"
            )
            cmd = cmd.strip().removeprefix("```bash").removeprefix("```").removesuffix("```").strip()
            console.print(f"[ok]{cmd}[/]")
            if click.confirm("run?"):
                r = await shell.run(cmd)
                if r.stdout:
                    console.print(r.stdout.rstrip())
                if r.stderr:
                    console.print(f"[err]{r.stderr.rstrip()}[/]")
                console.print(f"[dim]exit {r.code}[/]")
        finally:
            await agent.close()

    asyncio.run(_run())


@main.command()
@click.pass_context
def status(ctx):
    """Check connections."""
    from talos.agent import Agent

    async def _run():
        cfg = ctx.obj["config"]
        agent = Agent(cfg.hivemind_url)
        try:
            h = await agent.health()
            ok = h.get("status") in ("ok", "healthy")
            console.print(f"hivemind  [{'ok' if ok else 'err'}]{cfg.hivemind_url} {'connected' if ok else 'down'}[/]")
        finally:
            await agent.close()

        if cfg.obsidian_vault:
            from pathlib import Path

            exists = Path(cfg.obsidian_vault).is_dir()
            console.print(f"obsidian  [{'ok' if exists else 'err'}]{cfg.obsidian_vault} {'found' if exists else 'missing'}[/]")

    asyncio.run(_run())


@main.group()
def vault():
    """Obsidian vault commands."""
    pass


@vault.command(name="search")
@click.argument("query")
@click.pass_context
def vault_search(ctx, query):
    """Search vault notes."""
    from talos.obsidian import Vault

    cfg = ctx.obj["config"]
    if not cfg.obsidian_vault:
        console.print("[err]no obsidian_vault configured[/]")
        return
    v = Vault(cfg.obsidian_vault)
    for hit in v.search(query):
        console.print(f"  [accent]{hit['relative']}[/]")


@vault.command(name="read")
@click.argument("name")
@click.pass_context
def vault_read(ctx, name):
    """Read a vault note."""
    from rich.markdown import Markdown
    from talos.obsidian import Vault

    cfg = ctx.obj["config"]
    if not cfg.obsidian_vault:
        console.print("[err]no obsidian_vault configured[/]")
        return
    v = Vault(cfg.obsidian_vault)
    content = v.read(name)
    if content is None:
        console.print(f"[err]not found: {name}[/]")
        return
    console.print(Markdown(content))


@vault.command(name="recent")
@click.option("-n", "--limit", default=10)
@click.pass_context
def vault_recent(ctx, limit):
    """List recently modified notes."""
    from talos.obsidian import Vault

    cfg = ctx.obj["config"]
    if not cfg.obsidian_vault:
        console.print("[err]no obsidian_vault configured[/]")
        return
    v = Vault(cfg.obsidian_vault)
    for note in v.list_recent(limit):
        console.print(f"  [accent]{note['name']}[/]  [dim]{note['path']}[/]")


@vault.command(name="daily")
@click.pass_context
def vault_daily(ctx):
    """Open or create today's daily note."""
    from talos.obsidian import Vault

    cfg = ctx.obj["config"]
    if not cfg.obsidian_vault:
        console.print("[err]no obsidian_vault configured[/]")
        return
    v = Vault(cfg.obsidian_vault)
    path = v.daily()
    console.print(f"[ok]{path.relative_to(v.root)}[/]")
    v.open_in_obsidian(str(path.relative_to(v.root)))


@vault.command(name="tags")
@click.pass_context
def vault_tags(ctx):
    """Show tag frequency across vault."""
    from talos.obsidian import Vault

    cfg = ctx.obj["config"]
    if not cfg.obsidian_vault:
        console.print("[err]no obsidian_vault configured[/]")
        return
    v = Vault(cfg.obsidian_vault)
    for tag, count in v.tags().items():
        console.print(f"  [accent]#{tag}[/] [dim]({count})[/]")
