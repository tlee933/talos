"""Interactive REPL with readline-style input and agentic execution."""

import asyncio
import os
import shlex
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, Completion, merge_completers
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from talos.agent import Agent, ParsedResponse, parse_response
from talos.config import Config
from talos.theme import THEME, COLORS
from talos import shell


console = Console(theme=THEME)

# History file location
HISTORY_PATH = Path.home() / ".local" / "share" / "talos" / "history"

# Max agentic loop iterations (safety valve)
MAX_STEPS = 8

# Dangerous command patterns — always prompt in smart mode, warn in all modes
DANGEROUS_PATTERNS = [
    "rm -rf",
    "dd ",
    "mkfs",
    "fdisk",
    "parted",
    "systemctl stop",
    "kill -9",
    "chmod 777",
    "> /dev/",
    ":(){ :|:& };:",
]


def is_dangerous(command: str) -> bool:
    """Check if a command matches any dangerous pattern."""
    cmd = command.strip()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd:
            return True
    return False


# --- Completers ---

class TalosCommandCompleter(Completer):
    """Completes built-in talos commands."""

    COMMANDS = {
        "help": "Show help",
        "exit": "Quit talos",
        "quit": "Quit talos",
        "clear": "Clear screen",
        "stats": "Toggle system stats",
        "reset": "Reset conversation",
    }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        if " " in text:
            return
        for cmd, desc in self.COMMANDS.items():
            if cmd.startswith(text):
                yield Completion(cmd, start_position=-len(text), display_meta=desc)


class ShellCompleter(Completer):
    """Completes paths and executables after ! prefix."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("!"):
            return

        shell_text = text[1:]
        try:
            parts = shlex.split(shell_text)
        except ValueError:
            parts = shell_text.split()

        if shell_text.endswith(" "):
            current = ""
        elif parts:
            current = parts[-1]
        else:
            current = ""

        completing_command = len(parts) <= 1 and not shell_text.endswith(" ")

        if completing_command:
            yield from self._complete_executables(current)
        yield from self._complete_paths(current)

    def _complete_executables(self, prefix):
        seen = set()
        for directory in os.environ.get("PATH", "").split(":"):
            try:
                for entry in os.scandir(directory):
                    if (
                        entry.name.startswith(prefix)
                        and entry.name not in seen
                        and os.access(entry.path, os.X_OK)
                    ):
                        seen.add(entry.name)
                        yield Completion(entry.name, start_position=-len(prefix))
            except (OSError, PermissionError):
                continue

    def _complete_paths(self, prefix):
        if not prefix:
            return
        p = Path(prefix).expanduser()
        if prefix.endswith("/"):
            parent = p
            partial = ""
        else:
            parent = p.parent
            partial = p.name
        try:
            for entry in parent.iterdir():
                name = entry.name
                if name.startswith(".") and not partial.startswith("."):
                    continue
                if name.startswith(partial):
                    suffix = "/" if entry.is_dir() else ""
                    full = str(entry) + suffix
                    display = name + suffix
                    yield Completion(
                        full,
                        start_position=-len(prefix),
                        display=display,
                    )
        except (OSError, PermissionError):
            return


# prompt_toolkit style to match our bronze theme
PT_STYLE = PTStyle.from_dict({
    "prompt": "#CD7F32 bold",
    "prompt.err": "#C1440E bold",
    "": "#e0d6c8",
})


def _make_prompt(disconnected: bool = False):
    if disconnected:
        return HTML("<prompt.err>\u25b8 </prompt.err>")
    return HTML("<prompt>\u25b8 </prompt>")


def _confirm_prompt():
    return HTML("<prompt>  run? [y/n/a] </prompt>")


class _StatsToggle:
    """Mutable flag shared between keybinding handler and main loop."""

    def __init__(self):
        self.requested = False

    def fire(self):
        self.requested = True


# --- Rendering helpers ---

def _render_reasoning(text: str):
    """Show reasoning text in a muted style."""
    if not text:
        return
    console.print()
    for line in text.split("\n"):
        console.print(f"  [dim]{line}[/]")


def _render_command(cmd: str, step: int, dangerous: bool = False):
    """Show a command block Open-Interpreter style."""
    console.print()
    warn = " [err]\u26a0 dangerous[/]" if dangerous else ""
    console.print(
        Panel(
            Syntax(cmd, "bash", theme="monokai", line_numbers=False),
            title=f"[accent]step {step}[/]{warn}",
            title_align="left",
            border_style=COLORS["oxidized"] if dangerous else COLORS["bronze"],
            padding=(0, 1),
        )
    )


def _render_output(result, cmd: str):
    """Show command output."""
    output = ""
    if result.stdout:
        output += result.stdout.rstrip()
    if result.stderr:
        if output:
            output += "\n"
        output += result.stderr.rstrip()

    if not output:
        output = "(no output)"

    # Truncate very long output for display (full output goes to LLM)
    lines = output.split("\n")
    if len(lines) > 30:
        display = "\n".join(lines[:25])
        display += f"\n  ... ({len(lines) - 25} more lines)"
    else:
        display = output

    style = "ok" if result.ok else "err"
    exit_label = "" if result.ok else f" [err]exit {result.code}[/]"

    console.print(
        Panel(
            Text.from_ansi(display),
            title=f"[dim]output[/]{exit_label}",
            title_align="left",
            border_style=COLORS["verdigris"] if result.ok else COLORS["oxidized"],
            padding=(0, 1),
        )
    )


def _render_summary(text: str):
    """Show final summary in a panel."""
    if not text:
        return
    console.print()
    console.print(
        Panel(Markdown(text), border_style=COLORS["verdigris"], padding=(0, 1))
    )
    console.print()


# --- Streaming display ---

async def _stream_response(agent: Agent, message: str) -> ParsedResponse:
    """Stream a chat response with live display, return ParsedResponse."""
    accumulated = []
    display_text = Text()

    with Live(display_text, console=console, refresh_per_second=15, transient=True) as live:
        async for chunk in agent.stream_chat(message):
            accumulated.append(chunk)
            display_text.append(chunk, style="dim")
            live.update(display_text)

    full_text = "".join(accumulated)
    if not full_text:
        return ParsedResponse(segments=[("(no response)", None)], raw="")

    return parse_response(full_text)


async def _stream_feed_result(
    agent: Agent, command: str, output_text: str
) -> ParsedResponse:
    """Stream the LLM's analysis of command output with live display."""
    accumulated = []
    display_text = Text()

    with Live(display_text, console=console, refresh_per_second=15, transient=True) as live:
        async for chunk in agent.stream_feed_result(command, output_text):
            accumulated.append(chunk)
            display_text.append(chunk, style="dim")
            live.update(display_text)

    full_text = "".join(accumulated)
    if not full_text:
        return ParsedResponse(segments=[("(no response)", None)], raw="")

    return parse_response(full_text)


# --- Agentic loop ---

async def _agentic_step(agent: Agent, parsed: ParsedResponse, session: PromptSession, config: Config):
    """Process a parsed LLM response: show reasoning, execute commands, loop."""
    # Check for error sentinel
    if parsed.error:
        console.print(f"\n  [err]{parsed.error}[/]\n")
        return

    auto_run = False
    confirm_mode = config.confirm_commands
    step = 0

    for _iteration in range(MAX_STEPS):
        has_code = False

        for text, block in parsed.segments:
            if text:
                _render_reasoning(text)

            if block is None:
                continue

            has_code = True
            step += 1
            dangerous = is_dangerous(block.command)
            _render_command(block.command, step, dangerous=dangerous)

            # Determine whether to prompt
            should_prompt = True
            if auto_run and not dangerous:
                should_prompt = False
            elif confirm_mode == "never" and not dangerous:
                should_prompt = False
            elif confirm_mode == "smart" and not dangerous and not auto_run:
                should_prompt = False

            if should_prompt:
                try:
                    answer = await asyncio.to_thread(
                        session.prompt, _confirm_prompt()
                    )
                except (EOFError, KeyboardInterrupt):
                    console.print("  [dim]skipped[/]")
                    continue

                answer = answer.strip().lower()
                if answer in ("a", "all", "yes all"):
                    auto_run = True
                elif answer not in ("y", "yes", ""):
                    console.print("  [dim]skipped[/]")
                    continue

            # Execute
            with console.status("  [dim]running...[/]", spinner="dots"):
                result = await shell.run(block.command)

            _render_output(result, block.command)

            # Feed result back to LLM for continued reasoning
            output_text = ""
            if result.stdout:
                output_text += result.stdout
            if result.stderr:
                output_text += ("\n" if output_text else "") + result.stderr

            # Truncate output fed to LLM to avoid blowing context
            if len(output_text) > 4000:
                output_text = output_text[:2000] + "\n...(truncated)...\n" + output_text[-1500:]

            parsed = await _stream_feed_result(agent, block.command, output_text)

            # Check for error from streaming
            if parsed.error:
                console.print(f"\n  [err]{parsed.error}[/]\n")
                return

            # Continue the outer loop with new parsed response
            break
        else:
            # No code blocks in this iteration — we're done
            # Show any final reasoning as a summary
            final_text = "\n".join(
                text for text, block in parsed.segments if text and block is None
            )
            if final_text:
                _render_summary(final_text)
            return

    # Safety: max steps reached
    console.print(f"\n  [dim]reached max {MAX_STEPS} steps[/]\n")


# --- Main REPL ---

async def run(config: Config):
    from talos.banner import show as show_banner, render_minimal, refresh as refresh_banner

    agent = Agent(config.hivemind_url)
    disconnected = False
    try:
        # Clear screen and show full banner with live stats
        cached = await show_banner(config, agent)
        stats_visible = True

        # Stats toggle — shared between keybinding and main loop
        toggle = _StatsToggle()

        # Key bindings
        kb = KeyBindings()

        @kb.add(Keys.F2)
        def _toggle_stats(event):
            toggle.fire()
            buf = event.app.current_buffer
            buf.text = "\x00__F2__"
            buf.validate_and_handle()

        # Set up prompt_toolkit session
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        completer = merge_completers([TalosCommandCompleter(), ShellCompleter()])
        session: PromptSession = PromptSession(
            history=FileHistory(str(HISTORY_PATH)),
            completer=completer,
            complete_while_typing=False,
            style=PT_STYLE,
            enable_history_search=True,
            key_bindings=kb,
        )

        while True:
            try:
                line = await asyncio.to_thread(
                    session.prompt, _make_prompt(disconnected=disconnected)
                )
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            # Handle F2 toggle sentinel
            if toggle.requested:
                toggle.requested = False
                stats_visible = not stats_visible
                if stats_visible:
                    cached = await refresh_banner(config, agent)
                else:
                    render_minimal()
                continue

            line = line.strip()
            if not line:
                continue
            if line in ("exit", "quit", "q"):
                break
            if line == "help":
                _help()
                continue
            if line == "clear":
                if stats_visible:
                    cached = await refresh_banner(config, agent)
                else:
                    render_minimal()
                continue
            if line == "stats":
                stats_visible = not stats_visible
                if stats_visible:
                    cached = await refresh_banner(config, agent)
                else:
                    render_minimal()
                continue
            if line == "reset":
                agent.reset()
                console.print("  [dim]conversation reset[/]\n")
                continue

            # ! prefix = direct shell (bypass LLM)
            if line.startswith("!"):
                cmd = line[1:].strip()
                if cmd:
                    r = await shell.run(cmd)
                    if r.stdout:
                        console.print(r.stdout.rstrip())
                    if r.stderr:
                        console.print(f"[err]{r.stderr.rstrip()}[/]")
                continue

            # --- Agentic flow ---
            parsed = await _stream_response(agent, line)

            # Handle connection errors with retry
            if parsed.error:
                console.print(f"\n  [err]hivemind unreachable — retrying in 3s...[/]")
                disconnected = True
                await asyncio.sleep(3)
                parsed = await _stream_response(agent, line)
                if parsed.error:
                    console.print(f"\n  [err]{parsed.error}[/]\n")
                    continue
                disconnected = False

            disconnected = False
            await _agentic_step(agent, parsed, session, config)

    finally:
        await agent.close()


def _help():
    console.print("""
  [accent]<query>[/]        ask talos anything (agentic mode)
  [accent]!<cmd>[/]         run a shell command directly
  [accent]stats[/]          toggle system stats panel
  [accent]reset[/]          clear conversation history
  [accent]clear[/]          redraw banner
  [accent]exit[/]           quit

  [dim]F2[/]             toggle stats panel
  [dim]\u2191/\u2193[/]            history navigation
  [dim]ctrl-r[/]         reverse history search
  [dim]tab[/]            completion (commands, paths, executables)

  [dim]during execution:[/]
  [dim]y/enter[/]        run the command
  [dim]n[/]              skip this command
  [dim]a[/]              auto-run all remaining commands
""")
