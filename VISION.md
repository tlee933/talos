# Talos

Local-first desktop AI for Fedora Atomic + KDE Plasma 6.

Named after the bronze automaton from Greek mythology — an autonomous
guardian that runs on your own hardware.

## What it does

- Agentic shell execution via local LLM (HiveCoder-7B through Hive-Mind)
- Semantic RAG — the model knows your system, your projects, your preferences
- Obsidian vault integration — search, read, create notes from the terminal
- KDE desktop tools — notifications, clipboard, file search (Baloo), KDE Connect
- Self-improving — every interaction feeds the continuous learning pipeline

## Stack

- **OS**: Fedora 43 Kinoite (rpm-ostree, Wayland)
- **Desktop**: KDE Plasma 6
- **LLM**: HiveCoder-7B (local, LoRA fine-tuned, GGUF via llama.cpp)
- **Memory**: Hive-Mind (Redis cluster, semantic RAG, learning pipeline)
- **TUI**: Rich (Python)
- **IPC**: D-Bus for KDE integration

## Usage

```bash
talos                        # interactive REPL
talos ask "free disk space?" # one-shot query
talos do "kill zombie procs" # NL -> shell with confirmation
talos status                 # check hivemind + vault connections
talos vault search "pytorch" # search obsidian notes
talos vault recent           # recently modified notes
talos vault daily            # open/create today's daily note
```

## Configuration

`~/.config/talos/config.yaml`:

```yaml
hivemind_url: http://localhost:8090
obsidian_vault: ~/Documents/Vault
confirm_commands: true
```

## Architecture

```
talos CLI/TUI
    |
    +-- agent.py ---- Hive-Mind HTTP API (RAG + LLM)
    +-- shell.py ---- async subprocess execution
    +-- kde.py ------ notify-send, wl-clipboard, baloosearch
    +-- obsidian.py - vault filesystem access + obsidian:// URI
```

Hive-Mind provides the brain (inference, memory, learning). Talos is the
hands and eyes — desktop integration, user interface, tool execution.

## Lineage

Builds on [Hive-Mind](https://github.com/tlee933/hive-mind) for LLM
inference and memory. Takes inspiration from Open Interpreter (agentic
execution) and Charmbracelet (terminal aesthetics).
