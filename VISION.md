# Talos

Local-first desktop AI for Fedora Atomic + KDE Plasma 6.

Named after the bronze automaton from Greek mythology — an autonomous
guardian that runs on your own hardware.

```
╭────────────────────────────╮  ╭─ system ──────────────────────────────────────────╮
│                            │  │  hivemind    connected http://localhost:8090      │
│  ╔╦╗╔═╗╦  ╔═╗╔═╗           │  │  model       HiveCoder-7B 61.3 tok/s online       │
│   ║ ╠═╣║  ║ ║╚═╗           │  │  rag         ━━━━━━━━━━━━╌╌╌╌ 75% 73 queries      │
│   ╩ ╩ ╩╩═╝╚═╝╚═╝           │  │  learning    ━━━━━━━━━━╌╌╌╌╌╌ 64% 32/50 samples   │
│   v0.4.0 — the bronze       │  │              ~3.7d to next train · v0.9.1         │
│ guardian                   │  │  gpu         ━━━━━━━━╌╌╌╌ 67% vram 59°C · 100%    │
╰────────────────────────────╯  │  redis       cluster 4.26M · 99 sessions          │
                                │  vault       found ~/Documents/Vault              │
                                ╰───────────────────────────────────────────────────╯
  arrows/history · tab-complete · !cmd for shell · ctrl-r search · F2 toggle stats
```

## What it does

- **Agentic shell execution** — ask a question, Talos reasons through it,
  proposes commands step-by-step, executes with your confirmation, and
  summarizes results (Open Interpreter-style)
- **Streaming output** — token-by-token SSE streaming with Rich Live display
- **Context-aware** — cwd, git branch, and diff stats injected into every query
- **File & clipboard references** — `@file.py` injects file contents, `@clip`
  injects clipboard into your query
- **Persistent memory** — `remember`/`recall`/`facts` commands store knowledge
  in Hive-Mind across sessions; context saved on exit, restored on startup
- **Learning feedback** — interactions auto-logged to the learning pipeline;
  inline `+`/`-` rating after command execution enriches training signal
- **RAG gap analysis** — `suggest` command shows hit rate, missed queries,
  and recommends facts to add for better retrieval
- **Dangerous command detection** — destructive commands flagged with warnings
- **Semantic RAG** — the model knows your system, your projects, your preferences
- **Obsidian vault integration** — search, read, create notes from the terminal
- **KDE desktop tools** — notifications, clipboard, file search (Baloo)
- **Self-improving** — every interaction feeds the continuous learning pipeline
- **Firefox sidebar** — same chat interface in the browser via Ctrl+Shift+Y,
  streaming responses through a background script proxy to Hive-Mind

## Interactive mode

```
▸ what gpu do I have and how much vram is free?

  I'll check your GPU details and VRAM usage.

╭─ step 1 ─────────────────────────────────╮
│ rocm-smi --json                           │
╰───────────────────────────────────────────╯
  run? [y/n/a] y

╭─ output ──────────────────────────────────╮
│ Radeon AI PRO R9700 — 22.2/32.6 GB VRAM  │
│ 2x llama-server: 13.0 GB + 6.8 GB        │
╰───────────────────────────────────────────╯

  analyzing...

  You have ~10.4 GB VRAM free on your R9700.
  Two llama-server instances are loaded (HiveCoder-7B + Qwen3-14B).
```

Confirmation options during execution:
- **y** / **enter** — run the command
- **n** — skip
- **a** — auto-run all remaining steps

After execution, rate the response:
- **+** — positive feedback (feeds learning pipeline)
- **-** — negative feedback
- **enter** — skip rating

## Stack

- **OS**: Fedora 43 Kinoite (rpm-ostree, Wayland)
- **Desktop**: KDE Plasma 6
- **LLM**: HiveCoder-7B (local, LoRA fine-tuned, GGUF via llama.cpp)
- **Memory**: Hive-Mind (Redis cluster, semantic RAG, learning pipeline)
- **TUI**: Rich + prompt_toolkit (Python)
- **Browser**: Firefox sidebar extension (Svelte 5, Vite, MV2)
- **IPC**: D-Bus for KDE integration

## Usage

```bash
talos                        # interactive REPL (agentic mode)
talos ask "free disk space?" # one-shot query
talos do "kill zombie procs" # NL -> shell with confirmation
talos status                 # check hivemind + vault connections
talos vault search "pytorch" # search obsidian notes
talos vault recent           # recently modified notes
talos vault daily            # open/create today's daily note
```

### Interactive commands

| Command            | Description                          |
|--------------------|--------------------------------------|
| `@file.py <query>` | Inject file contents into query     |
| `@clip <query>`    | Inject clipboard into query          |
| `remember k = v`   | Store a fact in Hive-Mind            |
| `recall [key]`     | Recall a specific or all facts       |
| `facts`            | List all stored facts                |
| `suggest`          | RAG gap analysis & suggested facts   |
| `!cmd`             | Run a shell command directly         |
| `stats`            | Toggle the system stats panel        |
| `reset`            | Clear conversation history           |
| `clear`            | Redraw banner with fresh stats       |
| `help`             | Show all commands and keybindings    |

### Keybindings

| Key      | Action                                    |
|----------|-------------------------------------------|
| `F2`     | Toggle stats panel                        |
| `↑/↓`   | History navigation                        |
| `Ctrl-R` | Reverse history search                   |
| `Tab`    | Completion (commands, @files, paths, execs)|

## Configuration

`~/.config/talos/config.yaml`:

```yaml
hivemind_url: http://localhost:8090
obsidian_vault: ~/Documents/Vault
confirm_commands: always   # always | smart | never
context_injection: true    # inject cwd, git branch into LLM context
```

## Architecture

```
talos CLI/TUI
    |
    +-- tui.py ------- agentic REPL, commands, learning feedback, session lifecycle
    +-- agent.py ----- Hive-Mind HTTP API (chat, facts, memory, learning, streaming)
    +-- context.py --- env gathering (cwd, git), @file/@clip expansion
    +-- banner.py ---- startup banner with live system stats
    +-- shell.py ----- async subprocess execution
    +-- kde.py ------- notify-send, wl-clipboard, baloosearch
    +-- obsidian.py -- vault filesystem access + obsidian:// URI
```

```
talos-firefox/
    |
    +-- background.js -- SSE proxy to Hive-Mind, port message relay
    +-- sidebar.html --- Svelte 5 chat UI (bronze theme)
    +-- api.js --------- runtime.connect() port + message helpers
    +-- content.js ----- page context extraction (stub)
```

Hive-Mind provides the brain (inference, memory, learning). Talos is the
hands and eyes — desktop integration, user interface, tool execution.

## Lineage

Builds on [Hive-Mind](https://github.com/tlee933/hive-mind) for LLM
inference and memory. Takes inspiration from Open Interpreter (agentic
execution) and Charmbracelet (terminal aesthetics).
