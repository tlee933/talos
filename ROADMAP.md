# Talos Roadmap

Current: **v0.2.0** — streaming, error recovery, dangerous command detection

---

## ~~Phase 1: Core Polish (v0.2)~~ ✓

- [x] Stream LLM output token-by-token via SSE with Rich Live display
- [x] `talos do` wired into full agentic step-through loop
- [x] `confirm_commands: always | smart | never` config with dangerous command detection
- [x] Graceful error recovery — retry on disconnect, red prompt when offline
- [x] 32 unit tests for parser, config, completers, dangerous patterns

---

## Phase 2: Deeper Hive-Mind Integration (v0.3)

### Direct MCP tool access from TUI
- Use Hive-Mind MCP tools from interactive mode (memory, facts, RAG)
- `remember <fact>` command → stores in Hive-Mind RAG knowledge base
- `recall` command → pull relevant context for current conversation
- Session persistence across restarts via `memory_store/recall`

### Context awareness
- Auto-inject current directory, git branch, recent commands into LLM context
- File content injection: `@file.py` syntax to include file contents in query
- Clipboard integration: paste context from KDE clipboard

### Learning feedback loop
- Rate responses (thumbs up/down) → feeds `learning_queue_add`
- Bad responses get negative training signal
- Track which queries lead to successful command execution

---

## Phase 3: Firefox Extension — Talos Sidebar (v0.4)

### Architecture

```
┌─ Firefox ──────────────────────────────────────────────┐
│                                                         │
│  ┌─ Sidebar Panel ──────┐  ┌─ Content Script ────────┐ │
│  │  Chat UI (Svelte)    │  │  Page text extraction   │ │
│  │  Streaming responses │  │  Selection capture      │ │
│  │  Command output      │  │  DOM reading            │ │
│  └──────────┬───────────┘  └──────────┬──────────────┘ │
│             │   runtime.connect()      │                │
│  ┌──────────▼──────────────────────────▼──────────────┐ │
│  │  Background Script (event page)                    │ │
│  │  - Routes messages between sidebar & content       │ │
│  │  - Handles localhost fetch to Hive-Mind API        │ │
│  │  - Manages streaming via long-lived ports          │ │
│  └──────────┬─────────────────────────────────────────┘ │
└─────────────┼───────────────────────────────────────────┘
              │ fetch() http://localhost:8090
┌─────────────▼─────────────────────────────────────────┐
│  Hive-Mind @ :8090                                     │
│  RAG + LLM + Memory + Learning Pipeline               │
└───────────────────────────────────────────────────────┘
```

### Technical decisions
- **Manifest V2** — Firefox supports it long-term, simpler than MV3
- **Sidebar via `sidebar_action`** — native Firefox sidebar panel
- **Svelte** for the UI — tiny bundles, no runtime overhead
- **Background script** handles all localhost fetch (avoids CORS)
- **`runtime.connect()`** long-lived ports for streaming responses
- **`_execute_sidebar_action`** command for keyboard toggle
- **`web-ext`** for dev (live-reload) and packaging

### Manifest skeleton

```json
{
  "manifest_version": 2,
  "name": "Talos",
  "version": "0.4.0",
  "description": "Local AI assistant sidebar — powered by Hive-Mind",
  "permissions": ["*://localhost/*", "activeTab", "storage"],
  "background": {
    "scripts": ["background.js"],
    "persistent": false
  },
  "sidebar_action": {
    "default_title": "Talos",
    "default_panel": "sidebar/index.html",
    "default_icon": "icons/talos.svg"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ],
  "commands": {
    "_execute_sidebar_action": {
      "suggested_key": { "default": "Ctrl+Shift+Y" },
      "description": "Toggle Talos sidebar"
    }
  }
}
```

### Features
- **Chat sidebar** — same agentic flow as TUI, in the browser
- **Page context** — select text on any page, send to Talos as context
- **Ctrl+Shift+Y** — toggle sidebar from anywhere
- **Streaming** — token-by-token output via long-lived ports
- **Bronze theme** — matching the TUI aesthetic
- **Hive-Mind memory** — conversations persist via Redis sessions
- **No cloud** — all traffic stays on localhost

### Dev setup
```bash
cd talos-firefox/
npm install
npx web-ext run --firefox-profile dev    # live-reload dev
npx web-ext build                        # package for AMO
```

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

*Last updated: 2026-02-18*
