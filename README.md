# Talos

> Local-first desktop AI for Fedora Atomic + KDE Plasma 6.
> Named after the bronze automaton from Greek mythology — an autonomous guardian that runs on your own hardware.

```
╭────────────────────────────╮  ╭─ system ──────────────────────────────────────────╮
│                            │  │  hivemind    connected http://localhost:8090      │
│  ╔╦╗╔═╗╦  ╔═╗╔═╗           │  │  model       HiveCoder-7B 88 tok/s online           │
│   ║ ╠═╣║  ║ ║╚═╗           │  │  rag         ━━━━━━━━━━━━╌╌╌╌ 75% 73 queries      │
│   ╩ ╩ ╩╩═╝╚═╝╚═╝           │  │  learning    ━━━━━━━━━━╌╌╌╌╌╌ 64% 32/50 samples   │
│   v0.7.3 — the bronze      │  │              ~3.7d to next train · v0.9.1         │
│ guardian                   │  │  gpu         ━━━━━━━━╌╌╌╌ 67% vram 59°C · 100%    │
╰────────────────────────────╯  │  redis       cluster 4.26M · 99 sessions          │
                                │  vault       found ~/Documents/Vault              │
                                ╰───────────────────────────────────────────────────╯
  arrows/history · tab-complete · !cmd for shell · ctrl-r search · F2 toggle stats
```

## Features

### TUI (Terminal)

- **Intelligent model routing** — queries auto-route to the best model:
  HiveCoder-7B (88 tok/s) for code/shell, R1-Distill-14B (55 tok/s) for
  reasoning. R1 answers auto-feed HiveCoder's LoRA training — the bigger
  model teaches the smaller one
- **Agentic shell execution** — Talos reasons through your question,
  proposes shell commands step-by-step, executes with confirmation, and
  summarizes results
- **Tool use** — 10 built-in tools via function calling (`<tool_call>` XML),
  results feed back into reasoning loop automatically
- **Step-by-step reasoning** — `reason <query>` triggers `<think>` block
  chain-of-thought displayed in amber panels
- **Ghost suggestions** — context-aware autocomplete via prompt_toolkit;
  dimmed text appears as you type, right-arrow accepts
- **Streaming output** — token-by-token SSE streaming with Rich Live display
- **Context injection** — cwd, git branch, and diff stats auto-injected into
  every query
- **Context window management** — smart pruning keeps first + last 6 turns,
  drops middle when history exceeds token budget
- **File & clipboard references** — `@file.py` injects file contents, `@clip`
  injects clipboard
- **Hive-Mind memory** — `remember`/`recall`/`facts` for persistent knowledge
  across sessions
- **Conversation persistence** — `save`/`load`/`sessions`/`export` via
  Hive-Mind Redis with 28-day TTL; auto-save on exit
- **Dangerous command detection** — destructive commands flagged with warnings
- **Auto-rating** — exit codes auto-rate interactions (positive/negative);
  manual `+`/`-` override feeds the learning pipeline
- **Live system dashboard** — model tok/s, RAG hit rate, learning progress,
  GPU VRAM/temp, Redis cluster status
- **Readline input** — arrow keys, persistent history, Ctrl-R reverse search,
  tab completion for commands, `@` file references, and paths
- **Semantic RAG** — the model knows your system, projects, and preferences
- **Obsidian vault integration** — search, read, create notes from the terminal
- **KDE desktop tools** — notifications, clipboard, file search (Baloo)
- **Self-improving** — every interaction feeds the continuous learning pipeline

### Firefox / Zen Browser Sidebar Extension

- **Browser chat** — same Talos chat interface in a sidebar panel
  (Alt+Shift+T to toggle). Works in Firefox and Zen Browser.
- **Streaming** — real-time token-by-token responses via background script
  SSE proxy
- **Markdown rendering** — bold, italic, lists, links, headers, blockquotes,
  code blocks with copy button
- **Bronze/gold dark theme** — near-black base with gold headings, bronze
  interactive elements, amber think blocks. Looks great with Dark Reader.
- **Page context injection** — right-click context menus (Send Selection,
  Send Page, Summarize Page) and keyboard shortcuts (Ctrl+Shift+S/P)
- **Web search & fetch** — `/search <query>` for DuckDuckGo results,
  `/web <url>` to fetch and inject page content
- **Step-by-step reasoning** — `/reason <query>` with collapsible think blocks
- **Smarter ghost suggestions** — context-aware ranking, slash command hints
  (`/se` → `arch <query>`), page-aware suggestions (GitHub, selections),
  preemptive suggestion chains with depth tracking
- **Conversation persistence** — auto-saves to `browser.storage.local`,
  history panel with load/delete, `/new` to start fresh
- **Input history** — up/down arrow to recall previous messages
- **Multi-provider** — Hive-Mind, Ollama, OpenAI, Anthropic, or custom
  endpoints with per-provider auth
- **Tok/s display** — live tokens-per-second in the toolbar with gold pulse;
  shows which model answered (HiveCoder-7B or R1-Distill-14B)

### Cross-Client

- **Conversation bridge** — shared history between TUI and Firefox via
  Hive-Mind; `bridge` command to view cross-client conversations
- **Web scraper** — `web <url>` and `search <query>` available in both TUI
  and sidebar

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

  You have ~10.4 GB VRAM free on your R9700.
  Two llama-server instances are loaded (HiveCoder-7B + R1-Distill-14B).
```

Confirmation during execution:
- **y** / **enter** — run the command
- **n** — skip this step
- **a** — auto-run all remaining steps

After execution, rate the response with **+** / **-** to feed the learning
pipeline.

## Quick start

```bash
pip install -e .
talos                        # interactive REPL (agentic mode)
```

Requires [Hive-Mind](https://github.com/tlee933/hive-mind) running locally
for LLM inference and memory.

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
| `reason <query>`   | Ask with step-by-step reasoning      |
| `@file.py <query>` | Inject file contents into query     |
| `@clip <query>`    | Inject clipboard into query          |
| `remember k = v`   | Store a fact in Hive-Mind            |
| `recall [key]`     | Recall a specific or all facts       |
| `facts`            | List all stored facts                |
| `suggest`          | RAG gap analysis & suggested facts   |
| `bridge [N]`       | View shared conversation history     |
| `web <url>`        | Fetch URL and inject as context      |
| `search <query>`   | Search DuckDuckGo for results        |
| `save`             | Save current conversation            |
| `sessions`         | List saved conversations             |
| `load <id>`        | Resume a saved conversation          |
| `export <id>`      | Export conversation (json or md)     |
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

## Stack

| Component    | Technology                                         |
|--------------|----------------------------------------------------|
| **OS**       | Fedora 43 Kinoite (rpm-ostree, Wayland)            |
| **Desktop**  | KDE Plasma 6                                       |
| **LLM**      | HiveCoder-7B (code, 88 tok/s) + R1-Distill-14B (reasoning, 55 tok/s) |
| **Memory**   | Hive-Mind (Redis cluster, semantic RAG)             |
| **TUI**      | Rich + prompt_toolkit (Python 3.12+)               |
| **Browser**  | Zen / Firefox sidebar extension (Svelte 5, Vite, MV2) |
| **GPU**      | AMD Radeon R9700 (32GB VRAM, ROCm 7.12)           |

## Architecture

```
talos CLI/TUI
    │
    ├── tui.py ────────── agentic REPL, commands, TalosAutoSuggest, session lifecycle
    ├── agent.py ──────── Hive-Mind HTTP API (chat, facts, memory, learning, streaming)
    ├── tools.py ──────── tool registry, 10 built-in tools, schema conversion
    ├── suggestions.py ── ghost suggestion engine (context, matching, get_ghost)
    ├── context_manager.py ─ token budget, smart pruning (first + last 6 turns)
    ├── context.py ──────── env gathering (cwd, git), @file/@clip expansion
    ├── banner.py ───────── startup banner with live system stats + tok/s bench
    ├── shell.py ────────── async subprocess execution
    ├── kde.py ──────────── notify-send, wl-clipboard, baloosearch
    └── obsidian.py ─────── vault filesystem access + obsidian:// URI

talos-firefox/
    │
    ├── background.js ──── SSE proxy, port relay, web fetch/search, conversation storage
    ├── sidebar.html ───── Svelte 5 chat UI (bronze/gold dark theme)
    ├── suggestions.js ─── suggestion engine (ranking, context, slash hints, chains)
    ├── api.js ──────────── runtime.connect() port + message helpers
    ├── utils.js ────────── sanitize, parseContent, matchSuggestion
    ├── theme.css ───────── CSS variables (bronze/gold/amber dark palette)
    ├── content.js ──────── page context extraction + keyboard shortcuts (Ctrl+Shift+S/P)
    └── src/components/ ── Toolbar, SettingsPanel, MessageList, Message, CodeBlock, InputBar

         │
         ▼ /v1/chat/completions, /fact/*, /memory/*, /conversation/*, /web/*
    Hive-Mind @ :8090
    ├── Model Router (intent classifier → code or reasoning)
    ├── HiveCoder-7B @ :8089 (code/shell/tools, 88 tok/s)
    ├── R1-Distill-14B @ :8080 (reasoning/analysis, 55 tok/s)
    ├── Redis Cluster @ :7000-7005 (memory, sessions, RAG)
    ├── Semantic RAG (bge-small-en-v1.5 embeddings)
    └── Continuous Learning Pipeline (LoRA → GGUF → hot-swap)
        └── R1 answers auto-feed HiveCoder's training (knowledge distillation)
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
tool_use: true             # enable function calling (10 built-in tools)
auto_save: true            # auto-save conversation on exit
```

## License

MIT
