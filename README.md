# Talos

> Local-first desktop AI for Fedora Atomic + KDE Plasma 6.
> Named after the bronze automaton from Greek mythology — an autonomous guardian that runs on your own hardware.

```
╭────────────────────────────╮  ╭─ system ──────────────────────────────────────────╮
│                            │  │  hivemind    connected http://localhost:8090      │
│  ╔╦╗╔═╗╦  ╔═╗╔═╗           │  │  model       HiveCoder-7B 61.3 tok/s online       │
│   ║ ╠═╣║  ║ ║╚═╗           │  │  rag         ━━━━━━━━━━━━╌╌╌╌ 75% 73 queries      │
│   ╩ ╩ ╩╩═╝╚═╝╚═╝           │  │  learning    ━━━━━━━━━━╌╌╌╌╌╌ 64% 32/50 samples   │
│   v0.3.0 — the bronze      │  │              ~3.7d to next train · v0.9.1         │
│ guardian                   │  │  gpu         ━━━━━━━━╌╌╌╌ 67% vram 59°C · 100%    │
╰────────────────────────────╯  │  redis       cluster 4.26M · 99 sessions          │
                                │  vault       found ~/Documents/Vault              │
                                ╰───────────────────────────────────────────────────╯
  arrows/history · tab-complete · !cmd for shell · ctrl-r search · F2 toggle stats
```

## Features

- **Agentic shell execution** — ask a question, Talos reasons through it,
  proposes commands step-by-step, executes with your confirmation, and
  summarizes results (Open Interpreter-style)
- **Streaming output** — token-by-token SSE streaming with Rich Live display
- **Context injection** — cwd, git branch, and diff stats automatically injected
  into the LLM system prompt for every query
- **File & clipboard references** — `@file.py` injects file contents, `@clip`
  injects clipboard into your query
- **Hive-Mind memory** — `remember`/`recall`/`facts` commands for persistent
  knowledge storage across sessions
- **Session persistence** — conversation context saved on exit, restored on startup
- **Dangerous command detection** — destructive commands flagged with warnings,
  always prompted regardless of confirm mode
- **Live system dashboard** — startup banner shows model tok/s, RAG hit rate,
  learning pipeline progress, GPU VRAM/temp, Redis cluster status
- **Readline input** — arrow keys, persistent history, Ctrl-R reverse search,
  tab completion for commands, `@` file references, PATH executables, and paths
- **Semantic RAG** — the model knows your system, your projects, your preferences
- **Obsidian vault integration** — search, read, create notes from the terminal
- **KDE desktop tools** — notifications, clipboard, file search (Baloo)
- **Self-improving** — every interaction feeds the continuous learning pipeline
- **Multi-turn conversations** — context carries across the session

## Agentic execution

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

╭──────────────────────────────────────────╮
│ You have ~10.4 GB VRAM free on your      │
│ R9700. Two llama-server instances are    │
│ loaded (HiveCoder-7B + Qwen3-14B).      │
╰──────────────────────────────────────────╯
```

The LLM reasons, proposes shell commands as numbered steps, and you control execution:
- **y** / **enter** — run the command
- **n** — skip this step
- **a** — auto-run all remaining steps

Output feeds back to the LLM for continued reasoning (up to 8 steps).

## Quick start

```bash
pip install -e .
talos                        # interactive REPL (agentic mode)
```

Requires [Hive-Mind](https://github.com/tlee933/hive-mind) running locally for LLM inference and memory.

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
| `<query>`          | Ask Talos anything (agentic mode)    |
| `@file.py <query>` | Inject file contents into query     |
| `@clip <query>`    | Inject clipboard into query          |
| `remember k = v`   | Store a fact in Hive-Mind            |
| `recall [key]`     | Recall a specific or all facts       |
| `facts`            | List all stored facts                |
| `!cmd`             | Run a shell command directly         |
| `stats`            | Toggle the system stats panel        |
| `reset`            | Clear conversation history           |
| `clear`            | Redraw banner with fresh stats       |
| `help`             | Show all commands and keybindings    |
| `exit`             | Quit                                 |

### Keybindings

| Key      | Action                                    |
|----------|-------------------------------------------|
| `F2`     | Toggle stats panel                        |
| `↑/↓`   | History navigation                        |
| `Ctrl-R` | Reverse history search                   |
| `Tab`    | Completion (commands, @files, paths, execs)|

## Stack

| Component   | Technology                                         |
|-------------|----------------------------------------------------|
| **OS**      | Fedora 43 Kinoite (rpm-ostree, Wayland)            |
| **Desktop** | KDE Plasma 6                                       |
| **LLM**     | HiveCoder-7B (LoRA fine-tuned, GGUF via llama.cpp) |
| **Memory**  | Hive-Mind (Redis cluster, semantic RAG)             |
| **TUI**     | Rich + prompt_toolkit                               |
| **GPU**     | AMD Radeon R9700 (32GB VRAM, ROCm 7.12)            |

## Architecture

```
talos CLI/TUI
    │
    ├── tui.py ────── agentic REPL, commands, context injection, session lifecycle
    ├── agent.py ──── Hive-Mind HTTP API (chat, facts, memory, streaming)
    ├── context.py ── env gathering (cwd, git), @file/@clip expansion
    ├── banner.py ─── startup banner with live system stats + tok/s bench
    ├── shell.py ──── async subprocess execution
    ├── kde.py ────── notify-send, wl-clipboard, baloosearch
    └── obsidian.py ─ vault filesystem access + obsidian:// URI
         │
         ▼ /v1/chat/completions, /fact/*, /memory/*
    Hive-Mind @ :8090
    ├── HiveCoder-7B @ :8089 (inference, ~60 tok/s)
    ├── Redis Cluster @ :7000-7005 (memory, sessions, RAG)
    ├── Semantic RAG (bge-small-en-v1.5 embeddings)
    └── Continuous Learning Pipeline (LoRA → GGUF → hot-swap)
```

Hive-Mind provides the brain (inference, memory, learning). Talos is the
hands and eyes — desktop integration, user interface, tool execution.

## Configuration

`~/.config/talos/config.yaml`:

```yaml
hivemind_url: http://localhost:8090
obsidian_vault: ~/Documents/Vault
confirm_commands: always   # always | smart | never
context_injection: true    # inject cwd, git branch into LLM context
```

## License

MIT
