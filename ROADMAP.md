# Talos Roadmap

Current: **v0.4.0** — Firefox sidebar extension MVP

---

## ~~Phase 1: Core Polish (v0.2)~~ ✓

- [x] Stream LLM output token-by-token via SSE with Rich Live display
- [x] `talos do` wired into full agentic step-through loop
- [x] `confirm_commands: always | smart | never` config with dangerous command detection
- [x] Graceful error recovery — retry on disconnect, red prompt when offline
- [x] 32 unit tests for parser, config, completers, dangerous patterns

---

## ~~Phase 2 Part 1: Core Hive-Mind Integration (v0.3)~~ ✓

- [x] `remember`/`recall`/`facts` commands — direct Hive-Mind fact store from TUI
- [x] `@file.py` / `@clip` reference expansion — inject file/clipboard content into queries
- [x] Environment context injection — cwd, git branch, diff stats in LLM system prompt
- [x] Session persistence — `memory_store` on exit, `memory_recall` on startup
- [x] `AtRefCompleter` — tab-complete `@` references against cwd files
- [x] `context_injection` config toggle
- [x] 55 unit tests (7 agent hivemind, 12 context, 3 completers, 2 config + existing)

## ~~Phase 2 Part 2: Learning & RAG (v0.3.x)~~ ✓

- [x] Auto-log interactions to Hive-Mind learning queue after agentic steps (fire-and-forget)
- [x] Inline `+`/`-` rating after command execution → enriches learning signal
- [x] `suggest` command — RAG gap analysis (hit rate, missed queries, suggested facts)
- [x] `learning_queue_add` + `fact_suggestions` agent API methods
- [x] 63 unit tests (5 learning, 2 agent hivemind, 1 completer + existing)

---

## ~~Phase 3 Part 1: Firefox Sidebar MVP (v0.4.0)~~ ✓

- [x] Svelte 5 sidebar panel with bronze/forge theme
- [x] Background script SSE proxy to Hive-Mind at localhost:8090
- [x] Streaming chat via `runtime.connect()` long-lived ports
- [x] Message protocol: `CHAT`, `HEALTH_CHECK`, `STREAM_TOKEN`, `STREAM_END`, `STREAM_ERROR`
- [x] Code block parsing with copy button
- [x] Health check on connect + every 30s with status badge
- [x] Ctrl+Shift+Y keyboard toggle
- [x] MV2 manifest, `web-ext` dev workflow, Vite build (76KB dist)

## Phase 3 Part 2: Page Context & Polish (v0.4.x)

- [ ] Content script: page text extraction, selection capture
- [ ] `@page` / `@selection` context injection into chat
- [ ] Conversation persistence via `browser.storage.local`
- [ ] System stats panel (model, RAG, latency)
- [ ] Fact management from sidebar (`remember`/`recall`)
- [ ] Settings panel (Hive-Mind URL, model, temperature)

---

## Phase 4: Advanced Features (v0.5+)

### Textual TUI upgrade
- Migrate from Rich REPL to Textual for full TUI framework
- Split panes: chat left, system stats right (persistent)
- File browser panel, command history panel
- Mouse support

### Voice input
- Whisper.cpp integration for local speech-to-text
- Push-to-talk via keybinding
- Voice → Talos → execute → speak result (via KDE TTS)

### Multi-agent
- Spawn sub-agents for parallel tasks
- Researcher agent (web search) + coder agent (file edits) + executor (shell)
- Orchestrator coordinates between them

### Obsidian plugin
- Companion Obsidian plugin that talks to Hive-Mind
- AI-powered note linking, summarization, daily briefings
- Semantic search across vault from within Obsidian

---

## Infrastructure

### Short term
- [ ] CI/CD with GitHub Actions (lint, test)
- [ ] PyPI package publishing
- [ ] Systemd user service for Talos daemon mode

### Long term
- [ ] Flatpak packaging for Fedora Atomic
- [ ] KDE Plasma widget (desktop dashboard)
- [ ] Tailscale mesh — run Talos on laptop, inference on desktop

---

*Last updated: 2026-02-20*
