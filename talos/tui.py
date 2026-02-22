"""Interactive REPL with readline-style input and agentic execution."""

import asyncio
import json
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

from talos.agent import Agent, ParsedResponse, Turn, parse_response
from talos.config import Config
from talos.context import gather_environment, expand_references_async
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
        "remember": "Store a fact (remember key = value)",
        "recall": "Recall stored facts",
        "facts": "List all stored facts",
        "suggest": "RAG gap analysis — missed queries & suggestions",
        "bridge": "View shared conversation history",
        "web": "Fetch URL and inject as context",
        "search": "Search DuckDuckGo for results",
        "save": "Save current conversation",
        "sessions": "List saved conversations",
        "load": "Resume a saved conversation",
        "export": "Export conversation (export <id> [json|md])",
        "reason": "Ask with step-by-step reasoning (reason <query>)",
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


class AtRefCompleter(Completer):
    """Completes @file references against files in cwd."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # Find the last @... token being typed
        idx = text.rfind("@")
        if idx == -1:
            return

        partial = text[idx + 1:]
        if " " in partial:
            return

        # Special completions
        for name in ("clip", "clipboard"):
            if name.startswith(partial):
                yield Completion("@" + name, start_position=-(len(partial) + 1), display=f"@{name}", display_meta="clipboard")

        # File completions from cwd
        p = Path(partial) if partial else Path(".")
        if partial.endswith("/"):
            parent = p
            frag = ""
        else:
            parent = p.parent if partial else Path(".")
            frag = p.name if partial else ""

        try:
            base = Path.cwd() / parent
            for entry in base.iterdir():
                name = entry.name
                if name.startswith(".") and not frag.startswith("."):
                    continue
                if name.startswith(frag):
                    suffix = "/" if entry.is_dir() else ""
                    rel = str(parent / name) + suffix if str(parent) != "." else name + suffix
                    yield Completion(
                        "@" + rel,
                        start_position=-(len(partial) + 1),
                        display=f"@{rel}",
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


def _render_thinking(text: str):
    """Show a <think> block in a distinctive amber panel."""
    if not text:
        return
    console.print()
    console.print(
        Panel(
            Text(text, style="dim italic"),
            title="[accent]thinking[/]",
            title_align="left",
            border_style=COLORS["amber"],
            padding=(0, 1),
        )
    )


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


def _render_tool_call(tc, tool_def):
    """Show a tool call panel."""
    args_str = json.dumps(tc.arguments, indent=2) if tc.arguments else "{}"
    confirm_note = " [dim](confirm)[/]" if tool_def and tool_def.requires_confirm else ""
    console.print()
    console.print(
        Panel(
            Syntax(f"{tc.name}({args_str})", "json", theme="monokai", line_numbers=False),
            title=f"[accent]tool call[/]{confirm_note}",
            title_align="left",
            border_style=COLORS["bronze"],
            padding=(0, 1),
        )
    )


def _render_tool_result(name: str, result: str, success: bool = True):
    """Show a tool result panel."""
    # Truncate for display
    display = result
    if len(display) > 2000:
        display = display[:1500] + "\n...(truncated)"

    console.print(
        Panel(
            Text(display),
            title=f"[dim]{name} result[/]",
            title_align="left",
            border_style=COLORS["verdigris"] if success else COLORS["oxidized"],
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

async def _stream_response(
    agent: Agent,
    message: str,
    context: str | None = None,
    tools: list[dict] | None = None,
    tool_prompt: str | None = None,
) -> ParsedResponse:
    """Stream a chat response with live display, return ParsedResponse."""
    accumulated = []
    display_text = Text()

    with Live(display_text, console=console, refresh_per_second=15, transient=True) as live:
        async for chunk in agent.stream_chat(message, context=context, tools=tools, tool_prompt=tool_prompt):
            accumulated.append(chunk)
            display_text.append(chunk, style="dim")
            live.update(display_text)

    full_text = "".join(accumulated)
    if not full_text:
        return ParsedResponse(segments=[("(no response)", None)], raw="")

    return parse_response(full_text)


async def _stream_feed_result(
    agent: Agent, command: str, output_text: str, context: str | None = None,
) -> ParsedResponse:
    """Stream the LLM's analysis of command output with live display."""
    accumulated = []
    display_text = Text()

    with Live(display_text, console=console, refresh_per_second=15, transient=True) as live:
        async for chunk in agent.stream_feed_result(command, output_text, context=context):
            accumulated.append(chunk)
            display_text.append(chunk, style="dim")
            live.update(display_text)

    full_text = "".join(accumulated)
    if not full_text:
        return ParsedResponse(segments=[("(no response)", None)], raw="")

    return parse_response(full_text)


async def _stream_feed_tool_result(
    agent: Agent,
    tool_name: str,
    result_str: str,
    context: str | None = None,
    tool_prompt: str | None = None,
) -> ParsedResponse:
    """Stream the LLM's analysis of a tool result with live display."""
    accumulated = []
    display_text = Text()

    with Live(display_text, console=console, refresh_per_second=15, transient=True) as live:
        async for chunk in agent.stream_feed_tool_result(tool_name, result_str, context=context, tool_prompt=tool_prompt):
            accumulated.append(chunk)
            display_text.append(chunk, style="dim")
            live.update(display_text)

    full_text = "".join(accumulated)
    if not full_text:
        return ParsedResponse(segments=[("(no response)", None)], raw="")

    return parse_response(full_text)


# --- Agentic loop ---

def build_interaction(query: str, commands: list[dict], response_summary: str = "") -> dict | None:
    """Build a learning-queue interaction dict from agentic step data.

    Returns None if no commands were executed (pure-reasoning query).
    """
    if not commands:
        return None
    return {
        "user_query": query,
        "commands": commands,
        "response_summary": response_summary[:500],
        "success": all(c.get("success", False) for c in commands),
    }


async def _agentic_step(
    agent: Agent,
    parsed: ParsedResponse,
    session: PromptSession,
    config: Config,
    context: str | None = None,
    query: str = "",
    registry: dict | None = None,
    tool_prompt: str | None = None,
) -> dict | None:
    """Process a parsed LLM response: show reasoning, execute commands/tools, loop.

    Returns an interaction dict (for learning queue) if commands were executed,
    or None for pure-reasoning responses.
    """
    # Check for error sentinel
    if parsed.error:
        console.print(f"\n  [err]{parsed.error}[/]\n")
        return None

    auto_run = False
    confirm_mode = config.confirm_commands
    step = 0
    executed_commands: list[dict] = []

    for _iteration in range(MAX_STEPS):
        # --- Think blocks (rendered before everything else) ---
        for tb in parsed.think_blocks:
            _render_thinking(tb)

        # --- Tool calls (checked BEFORE code blocks) ---
        if parsed.tool_calls and registry:
            # Show any reasoning text from segments
            for text, block in parsed.segments:
                if text:
                    _render_reasoning(text)

            for tc in parsed.tool_calls:
                tool_def = registry.get(tc.name)
                if not tool_def:
                    console.print(f"  [err]unknown tool: {tc.name}[/]")
                    continue

                _render_tool_call(tc, tool_def)

                # Confirm if required
                if tool_def.requires_confirm:
                    should_prompt = True
                    if auto_run:
                        should_prompt = False
                    elif confirm_mode == "never":
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

                # Execute tool handler
                try:
                    with console.status("  [dim]running...[/]", spinner="dots"):
                        result_str = await tool_def.handler(**tc.arguments)
                except Exception as e:
                    result_str = f"error: {e}"

                success = not result_str.startswith("error:")
                _render_tool_result(tc.name, result_str, success=success)
                executed_commands.append({
                    "command": f"tool:{tc.name}",
                    "success": success,
                    "exit_code": 0 if success else 1,
                })

                # Truncate for LLM context
                if len(result_str) > 4000:
                    result_str = result_str[:2000] + "\n...(truncated)...\n" + result_str[-1500:]

                # Feed result back
                parsed = await _stream_feed_tool_result(
                    agent, tc.name, result_str, context=context, tool_prompt=tool_prompt,
                )
                if parsed.error:
                    console.print(f"\n  [err]{parsed.error}[/]\n")
                    return build_interaction(query, executed_commands)

                # Continue outer loop with new parsed response
                break
            else:
                # All tool calls processed without break — check for more
                if not parsed.tool_calls:
                    final_text = "\n".join(
                        text for text, block in parsed.segments if text and block is None
                    )
                    if final_text:
                        _render_summary(final_text)
                    return build_interaction(query, executed_commands, final_text)
            continue

        # --- Code blocks (original path) ---
        for text, block in parsed.segments:
            if text:
                _render_reasoning(text)

            if block is None:
                continue

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
            executed_commands.append({
                "command": block.command,
                "success": result.ok,
                "exit_code": result.code,
            })

            # Feed result back to LLM for continued reasoning
            output_text = ""
            if result.stdout:
                output_text += result.stdout
            if result.stderr:
                output_text += ("\n" if output_text else "") + result.stderr

            # Truncate output fed to LLM to avoid blowing context
            if len(output_text) > 4000:
                output_text = output_text[:2000] + "\n...(truncated)...\n" + output_text[-1500:]

            parsed = await _stream_feed_result(agent, block.command, output_text, context=context)

            # Check for error from streaming
            if parsed.error:
                console.print(f"\n  [err]{parsed.error}[/]\n")
                return build_interaction(query, executed_commands)

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
            return build_interaction(query, executed_commands, final_text)

    # Safety: max steps reached
    console.print(f"\n  [dim]reached max {MAX_STEPS} steps[/]\n")
    return build_interaction(query, executed_commands)


# --- Main REPL ---

async def run(config: Config):
    from talos.banner import show as show_banner, render_minimal, refresh as refresh_banner

    agent = Agent(config.hivemind_url)
    disconnected = False

    # Build tool registry if tool_use enabled
    registry = None
    tools_schema = None
    tool_prompt = None
    if config.tool_use:
        from talos.tools import build_registry, tools_to_openai_schema, build_tool_system_prompt
        registry = build_registry(agent)
        tools_schema = tools_to_openai_schema(registry)
        tool_prompt = build_tool_system_prompt(registry)

    try:
        # Clear screen and show full banner with live stats
        cached = await show_banner(config, agent)
        stats_visible = True

        # Session restore (best-effort)
        try:
            recalled = await agent.memory_recall()
            if recalled.get("context"):
                console.print("  [dim]session restored[/]\n")
        except Exception:
            pass

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
        completer = merge_completers([TalosCommandCompleter(), ShellCompleter(), AtRefCompleter()])
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

            # Hive-Mind commands
            if line.startswith("remember "):
                await _handle_remember(agent, line[9:])
                continue
            if line.startswith("recall"):
                key = line[6:].strip() or None
                await _handle_recall(agent, key)
                continue
            if line == "facts":
                await _handle_recall(agent, None)
                continue
            if line == "suggest":
                await _handle_suggest(agent)
                continue
            if line.startswith("bridge"):
                await _handle_bridge(agent, line[6:])
                continue
            if line.startswith("web "):
                await _handle_web(agent, line[4:].strip())
                continue
            if line.startswith("search "):
                await _handle_search(agent, line[7:].strip())
                continue

            # Conversation persistence commands
            if line == "save":
                await _handle_save(agent)
                continue
            if line == "sessions":
                await _handle_sessions(agent)
                continue
            if line.startswith("load "):
                await _handle_load(agent, line[5:].strip())
                continue
            if line.startswith("export "):
                await _handle_export(agent, line[7:].strip())
                continue

            # reason prefix — inject step-by-step thinking prompt
            reason_mode = False
            if line.startswith("reason "):
                line = line[7:].strip()
                reason_mode = True
                if not line:
                    console.print("  [dim]usage: reason <query>[/]\n")
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
            # Expand @file/@clip references
            message, ref_context = await expand_references_async(line)

            # Append reasoning suffix when in reason mode
            if reason_mode:
                from talos.agent import REASON_SUFFIX
                message = message + REASON_SUFFIX

            # Gather environment context
            env_context = ""
            if config.context_injection:
                try:
                    env_context = await gather_environment()
                except Exception:
                    pass

            # Combine contexts
            ctx_parts = [p for p in (env_context, ref_context) if p]
            full_context = "\n\n".join(ctx_parts) if ctx_parts else None

            parsed = await _stream_response(
                agent, message, context=full_context,
                tools=tools_schema, tool_prompt=tool_prompt,
            )

            # Handle connection errors with retry
            if parsed.error:
                console.print(f"\n  [err]hivemind unreachable — retrying in 3s...[/]")
                disconnected = True
                await asyncio.sleep(3)
                parsed = await _stream_response(
                    agent, message, context=full_context,
                    tools=tools_schema, tool_prompt=tool_prompt,
                )
                if parsed.error:
                    console.print(f"\n  [err]{parsed.error}[/]\n")
                    continue
                disconnected = False

            disconnected = False
            interaction = await _agentic_step(
                agent, parsed, session, config,
                context=full_context, query=message,
                registry=registry, tool_prompt=tool_prompt,
            )

            # Log to conversation bridge (fire-and-forget)
            asyncio.create_task(agent.conversation_log("user", message, "tui"))
            asyncio.create_task(agent.conversation_log("assistant", parsed.raw[:2000], "tui"))

            # Auto-rate and log interaction if commands were executed
            if interaction:
                # Auto-rate based on execution success
                if interaction.get("success"):
                    interaction["rating"] = "positive"
                    console.print("  [ok]\u25b2[/] [dim]auto-rated positive[/]")
                else:
                    interaction["rating"] = "negative"
                    console.print("  [err]\u25bc[/] [dim]auto-rated negative[/]")
                asyncio.create_task(agent.learning_queue_add(interaction))

                # Still allow manual override
                console.print("  [dim]+/- to override \u00b7 enter to continue[/]")
                try:
                    rating_input = await asyncio.to_thread(
                        session.prompt, _make_prompt()
                    )
                except (EOFError, KeyboardInterrupt):
                    rating_input = ""

                rating_input = rating_input.strip()
                if rating_input in ("+", "\U0001f44d"):
                    interaction["rating"] = "positive"
                    asyncio.create_task(agent.learning_queue_add(interaction))
                    console.print("  [dim]\u25b2 overridden to positive[/]\n")
                    continue
                elif rating_input in ("-", "\U0001f44e"):
                    interaction["rating"] = "negative"
                    asyncio.create_task(agent.learning_queue_add(interaction))
                    console.print("  [dim]\u25bc overridden to negative[/]\n")
                    continue
                elif rating_input:
                    # Not a rating — treat as a new query, re-enter dispatch
                    line = rating_input
                    if line in ("exit", "quit", "q"):
                        break
                    if line == "help":
                        _help()
                        continue
                    # Otherwise treat as a new query — expand and send
                    message, ref_context = await expand_references_async(line)
                    if reason_mode:
                        from talos.agent import REASON_SUFFIX
                        message = message + REASON_SUFFIX
                    env_context = ""
                    if config.context_injection:
                        try:
                            env_context = await gather_environment()
                        except Exception:
                            pass
                    ctx_parts = [p for p in (env_context, ref_context) if p]
                    full_context = "\n\n".join(ctx_parts) if ctx_parts else None
                    parsed = await _stream_response(
                        agent, message, context=full_context,
                        tools=tools_schema, tool_prompt=tool_prompt,
                    )
                    if parsed.error:
                        console.print(f"\n  [err]{parsed.error}[/]\n")
                        continue
                    interaction = await _agentic_step(
                        agent, parsed, session, config,
                        context=full_context, query=message,
                        registry=registry, tool_prompt=tool_prompt,
                    )
                    if interaction:
                        if interaction.get("success"):
                            interaction["rating"] = "positive"
                        else:
                            interaction["rating"] = "negative"
                        asyncio.create_task(agent.learning_queue_add(interaction))

    finally:
        # Auto-save conversation (best-effort)
        if config.auto_save and len(agent.history) > 2:
            try:
                await agent.conversation_save()
            except Exception:
                pass

        # Session save (best-effort)
        try:
            if agent.history:
                last_user = next(
                    (t.content for t in reversed(agent.history) if t.role == "user"),
                    "",
                )
                if last_user:
                    await agent.memory_store(f"Last topic: {last_user[:200]}")
        except Exception:
            pass
        await agent.close()


# --- Conversation persistence handlers ---

async def _handle_save(agent: Agent):
    """Save the current conversation."""
    if not agent.history:
        console.print("  [dim]nothing to save[/]\n")
        return
    result = await agent.conversation_save()
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
    else:
        title = result.get("title", "")
        conv_id = result.get("conversation_id", agent.conversation_id)
        console.print(f"  [ok]saved:[/] [accent]{conv_id}[/] — {title}\n")


async def _handle_sessions(agent: Agent):
    """List saved conversations."""
    result = await agent.conversation_list_saved()
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
        return

    conversations = result.get("conversations", [])
    if not conversations:
        console.print("  [dim]no saved conversations[/]\n")
        return

    for conv in conversations:
        conv_id = conv.get("conversation_id", "?")
        title = conv.get("title", "(untitled)")
        count = conv.get("message_count", 0)
        source = conv.get("source", "?")
        console.print(f"  [accent]{conv_id}[/] [{source}] {title} [dim]({count} msgs)[/]")
    console.print()


async def _handle_load(agent: Agent, conv_id: str):
    """Load a saved conversation."""
    if not conv_id:
        console.print("  [err]usage: load <conversation_id>[/]\n")
        return
    result = await agent.conversation_load(conv_id)
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
    elif not result.get("success"):
        console.print(f"  [err]{result.get('error', 'not found')}[/]\n")
    else:
        title = result.get("title", "")
        count = len(result.get("messages", []))
        console.print(f"  [ok]loaded:[/] [accent]{conv_id}[/] — {title} [dim]({count} msgs)[/]\n")


async def _handle_export(agent: Agent, args: str):
    """Export a conversation."""
    parts = args.split()
    if not parts:
        console.print("  [err]usage: export <conversation_id> [json|md][/]\n")
        return
    conv_id = parts[0]
    fmt = parts[1] if len(parts) > 1 else "markdown"
    if fmt == "md":
        fmt = "markdown"

    result = await agent.conversation_export(conv_id, fmt)
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
    elif not result.get("success"):
        console.print(f"  [err]{result.get('error', 'export failed')}[/]\n")
    else:
        content = result.get("content", "")
        console.print(content)
        console.print()


# --- Existing command handlers ---

async def _handle_remember(agent: Agent, text: str):
    """Parse 'key = value' or auto-key from text, store via Hive-Mind."""
    if "=" in text:
        key, _, value = text.partition("=")
        key = key.strip()
        value = value.strip()
    else:
        words = text.split()
        key = "_".join(words[:3]).lower()
        value = text

    if not key or not value:
        console.print("  [err]usage: remember key = value[/]\n")
        return

    result = await agent.fact_store(key, value)
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
    else:
        console.print(f"  [ok]remembered:[/] [accent]{key}[/] = {value}\n")


async def _handle_recall(agent: Agent, key: str | None):
    """Recall a specific fact or list all facts."""
    result = await agent.fact_get(key)
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
        return

    if key:
        value = result.get("value", "(not found)")
        console.print(f"  [accent]{key}[/] = {value}\n")
    else:
        facts = result.get("facts", {})
        if not facts:
            console.print("  [dim]no facts stored[/]\n")
            return
        for k, v in facts.items():
            console.print(f"  [accent]{k}[/] = {v}")
        console.print()


async def _handle_suggest(agent: Agent):
    """Show RAG gap analysis — missed queries and suggested topics."""
    result = await agent.fact_suggestions()
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
        return

    # Retrieval stats
    hit_rate = result.get("hit_rate")
    if hit_rate is not None:
        console.print(f"  [accent]RAG hit rate:[/] {hit_rate:.0%}")

    methods = result.get("retrieval_methods", {})
    if methods:
        for method, count in methods.items():
            console.print(f"    {method}: {count}")

    # Missed queries
    missed = result.get("missed_queries", [])
    if missed:
        console.print("\n  [accent]top missed queries:[/]")
        for q in missed:
            if isinstance(q, dict):
                console.print(f"    \u2022 {q.get('query', q)}")
            else:
                console.print(f"    \u2022 {q}")

    # Suggested topics
    suggestions = result.get("suggested_topics", result.get("suggestions", []))
    if suggestions:
        console.print("\n  [accent]suggested facts to add:[/]")
        for s in suggestions:
            if isinstance(s, dict):
                console.print(f"    \u2022 [dim]{s.get('key', '')}[/] = {s.get('value', s)}")
            else:
                console.print(f"    \u2022 {s}")

    if not missed and not suggestions and hit_rate is None:
        console.print("  [dim]no RAG data yet — ask some queries first[/]")

    console.print()


async def _handle_bridge(agent: Agent, arg: str):
    """Show shared conversation history from the bridge."""
    limit = 20
    if arg.strip().isdigit():
        limit = int(arg.strip())
    result = await agent.conversation_recent(limit=limit)
    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
        return

    messages = result.get("messages", [])
    if not messages:
        console.print("  [dim]no shared messages yet[/]\n")
        return

    for msg in messages:
        source = msg.get("source", "?")
        role = msg.get("role", "?")
        content = msg.get("content", "")
        # Truncate long messages
        if len(content) > 200:
            content = content[:200] + "..."
        badge = f"[accent][{source}][/]"
        role_style = "ok" if role == "assistant" else "dim"
        console.print(f"  {badge} [{role_style}]{role}:[/] {content}")
    console.print()


async def _handle_web(agent: Agent, url: str):
    """Fetch a URL and inject its content as context."""
    if not url:
        console.print("  [err]usage: web <url>[/]\n")
        return

    with console.status("  [dim]fetching...[/]", spinner="dots"):
        result = await agent.web_fetch(url)

    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
        return

    title = result.get("title", "(no title)")
    text = result.get("text", "")
    console.print(f"  [accent]{title}[/]")
    # Show preview (first 500 chars)
    preview = text[:500] + ("..." if len(text) > 500 else "")
    console.print(f"  [dim]{preview}[/]")
    console.print(f"  [dim]{len(text)} chars fetched — injecting as context[/]\n")

    # Inject full text into agent history as context
    agent.history.append(
        Turn(role="user", content=f"[Web page: {title}]\n{text}")
    )


async def _handle_search(agent: Agent, query: str):
    """Search DuckDuckGo and display results."""
    if not query:
        console.print("  [err]usage: search <query>[/]\n")
        return

    with console.status("  [dim]searching...[/]", spinner="dots"):
        result = await agent.web_search(query)

    if "error" in result:
        console.print(f"  [err]{result['error']}[/]\n")
        return

    results = result.get("results", [])
    if not results:
        console.print("  [dim]no results found[/]\n")
        return

    for i, r in enumerate(results, 1):
        title = r.get("title", "(no title)")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        console.print(f"  [accent]{i}.[/] {title}")
        console.print(f"     [dim]{url}[/]")
        if snippet:
            console.print(f"     {snippet}")
    console.print()


def _help():
    console.print("""
  [accent]<query>[/]        ask talos anything (agentic mode)
  [accent]reason[/] [dim]<query>[/] ask with step-by-step reasoning
  [accent]!<cmd>[/]         run a shell command directly
  [accent]remember[/]       store a fact (remember key = value)
  [accent]recall[/]         recall stored facts (recall [key])
  [accent]facts[/]          list all stored facts
  [accent]suggest[/]        RAG gap analysis — missed queries & suggestions
  [accent]bridge[/] [dim][N][/]     view shared conversation history
  [accent]web[/] [dim]<url>[/]      fetch URL and inject as context
  [accent]search[/] [dim]<query>[/] search DuckDuckGo for results
  [accent]save[/]           save current conversation
  [accent]sessions[/]       list saved conversations
  [accent]load[/] [dim]<id>[/]      resume a saved conversation
  [accent]export[/] [dim]<id>[/]    export conversation (json or md)
  [accent]stats[/]          toggle system stats panel
  [accent]reset[/]          clear conversation history
  [accent]clear[/]          redraw banner
  [accent]exit[/]           quit

  [dim]@file.py[/]       inject file content into query
  [dim]@clip[/]          inject clipboard content into query

  [dim]F2[/]             toggle stats panel
  [dim]\u2191/\u2193[/]            history navigation
  [dim]ctrl-r[/]         reverse history search
  [dim]tab[/]            completion (commands, paths, @files)

  [dim]during execution:[/]
  [dim]y/enter[/]        run the command
  [dim]n[/]              skip this command
  [dim]a[/]              auto-run all remaining commands

  [dim]after execution:[/]
  [dim]auto-rated[/]     based on exit codes
  [dim]+/-[/]            override auto-rating
  [dim]enter[/]          accept and continue
""")
