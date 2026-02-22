# Talos Roadmap

Current: **v0.7.0** — tool-use, reasoning, conversation persistence, 88 tok/s

---

## ~~Phase 1: Core Polish (v0.2)~~ ✓

- [x] Stream LLM output token-by-token via SSE with Rich Live display
- [x] `talos do` wired into full agentic step-through loop
- [x] `confirm_commands: always | smart | never` config with dangerous command detection
- [x] Graceful error recovery — retry on disconnect, red prompt when offline
- [x] 32 unit tests for parser, config, completers, dangerous patterns

---

## ~~Phase 2 Part 1: Hive-Mind Integration (v0.3)~~ ✓

- [x] `remember`/`recall`/`facts` commands — direct Hive-Mind fact store from TUI
- [x] `@file.py` / `@clip` reference expansion — inject file/clipboard into queries
- [x] Environment context injection — cwd, git branch, diff stats in LLM system prompt
- [x] Session persistence — `memory_store` on exit, `memory_recall` on startup
- [x] `AtRefCompleter` — tab-complete `@` references against cwd files
- [x] 55 unit tests

## ~~Phase 2 Part 2: Learning & RAG (v0.3.1)~~ ✓

- [x] Auto-log interactions to Hive-Mind learning queue (fire-and-forget)
- [x] Inline `+`/`-` rating after command execution → enriches learning signal
- [x] `suggest` command — RAG gap analysis (hit rate, missed queries, suggested facts)
- [x] 63 unit tests

---

## ~~Phase 3 Part 1: Firefox Sidebar MVP (v0.4.0)~~ ✓

- [x] Svelte 5 sidebar panel with bronze/forge theme
- [x] Background script SSE proxy to Hive-Mind
- [x] Streaming chat via `runtime.connect()` long-lived ports
- [x] Code block parsing with copy button
- [x] Health check on connect + every 30s
- [x] Toolbar button with coat-of-arms icon
- [x] MV2 manifest, `web-ext` dev workflow, AMO-signed .xpi

## ~~Phase 3 Part 2: Sidebar Features (v0.5.x)~~ ✓

- [x] Multi-provider settings panel — Hive-Mind, Ollama, OpenAI, Anthropic, custom
- [x] Dynamic auth headers (Bearer, x-api-key, none)
- [x] Tok/s display in toolbar with pulse animation on update
- [x] Markdown rendering — snarkdown + XSS sanitizer (bold, italic, lists, links, headers, blockquotes, code)
- [x] Page context injection — right-click menus (Send Selection, Send Page, Summarize Page)
- [x] Content script keyboard shortcuts — Ctrl+Shift+S (selection), Ctrl+Shift+P (page)
- [x] ContextChip display above input
- [x] Smart ghost suggestions — context-aware Tab-completion, preemptive after responses
- [x] Flame particle burst on send

---

## ~~Phase 4: Bridge & Web (v0.6.x)~~ ✓

- [x] Conversation bridge — shared Redis sorted set between TUI and Firefox
- [x] `bridge` command in TUI, fire-and-forget logging from both clients
- [x] Web scraper — `web <url>` and `search <query>` via Hive-Mind endpoints
- [x] `/web` and `/search` slash commands in Firefox sidebar
- [x] Web fetch injects page content into chat history for follow-up questions
- [x] Input history — up/down arrow recalls previous messages in sidebar
- [x] Sidebar shortcut changed to Alt+Shift+T
- [x] 70 Python tests, 15 JS tests (vitest)

---

## ~~Phase 5: Smarter Agent (v0.7.0)~~ ✓

### Tool use
- [x] Model calls tools directly via `<tool_call>` XML (10 built-in tools)
- [x] Built-in tools: shell, file read/write/list, clipboard, notify, web fetch, fact store/get
- [x] Tool results feed back into reasoning loop automatically
- [x] OpenAI-compatible `tools` array passthrough to llama-server

### Reasoning
- [x] `reason` command (TUI) and `/reason` (sidebar) trigger `<think>` block chain-of-thought
- [x] Native `reasoning_content` SSE field support — llama-server streams thinking separately
- [x] Collapsible amber panels in sidebar, Rich Panels in TUI
- [x] HiveCoder-7B hitting **88 tok/s** on R9700 XT with ROCm 7.12

### Conversation persistence
- [x] Sidebar auto-saves to `browser.storage.local`, restored on reopen
- [x] ConversationPanel with history browser (clock icon in toolbar)
- [x] TUI: `save`/`load`/`sessions`/`export` commands via Hive-Mind Redis (28-day TTL)
- [x] `/new` and `/help` sidebar commands

### Context window management
- [x] Token budgeting with char-based estimation (32K context)
- [x] Smart pruning — keep first turn + last 6, drop middle oldest-first
- [x] LLM-based summarization fallback for long histories

### Auto-rating
- [x] Exit code → automatic `▲ positive` / `▼ negative` learning signal
- [x] Manual `+`/`-` override still available
- [x] 116 Python tests, 26 JS tests, 0 lint errors

---

## Phase 6: Desktop Integration (v0.8)

### Smarter ghost suggestions
- [ ] Context-aware suggestion ranking — weigh by recent conversation topic, active page, time of day
- [ ] Slash command suggestions with parameter hints (`/web <url>`, `/search <query>`, `/reason <query>`)
- [ ] Preemptive suggestion chains — multi-step follow-ups based on last assistant response
- [ ] Expand `suggestions.test.js` — context-aware matching, slash commands, preemptive triggers, edge cases
- [ ] TUI suggestion parity — port ghost suggestions from sidebar to prompt_toolkit completer

### KDE Plasma widget
- [ ] Desktop widget showing Talos status, quick-ask input, recent conversations
- [ ] Drag-and-drop files onto widget to inject as context

### Notification actions
- [ ] Talos surfaces results as KDE notifications with action buttons
- [ ] Click notification to jump into full conversation in TUI or sidebar

### System automation
- [ ] Scheduled tasks — "remind me to push at 5pm", "check disk space every hour"
- [ ] D-Bus triggers — react to system events (USB mount, network change, battery low)

---

## Phase 7: Voice & Vision (v0.9)

### Voice input
- [ ] Whisper.cpp integration for local speech-to-text
- [ ] Push-to-talk via keybinding (global hotkey)
- [ ] Voice → Talos → execute → speak result (via KDE TTS)

### Screenshot understanding
- [ ] Capture screen region and send to vision-capable model
- [ ] "What's this error?" with a screenshot
- [ ] OCR fallback for local-only models without vision

---

## Phase 8: Multi-Agent (v1.0)

### Agent orchestration
- [ ] Spawn sub-agents for parallel tasks
- [ ] Researcher agent (web search) + coder agent (file edits) + executor (shell)
- [ ] Orchestrator coordinates, deduplicates, and merges results

### Obsidian plugin
- [ ] Companion Obsidian plugin that talks to Hive-Mind
- [ ] AI-powered note linking, summarization, daily briefings
- [ ] Semantic search across vault from within Obsidian

---

## Infrastructure

### Short term
- [ ] CI/CD with GitHub Actions (lint, test, build extension)
- [ ] PyPI package publishing
- [ ] Systemd user service for Talos daemon mode

### Long term
- [ ] Flatpak packaging for Fedora Atomic
- [ ] AMO public listing for Firefox extension
- [ ] Tailscale mesh — run Talos on laptop, inference on desktop

---

*Last updated: 2026-02-22*
