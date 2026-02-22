# Journey

Development log for Talos — from first commit to the bronze guardian.

---

## v0.1.0 — First breath

The initial commit. A Click CLI with `ask`, `do`, `status`, and `vault`
subcommands. Obsidian vault integration for searching and reading notes.
The skeleton of what would become the agentic REPL.

## v0.2.0 — Streaming and safety

Added token-by-token SSE streaming with Rich Live display. Dangerous command
detection flags destructive operations (`rm -rf`, `dd`, `mkfs`, etc.) with
warnings before execution. Error recovery so a failed step doesn't kill the
whole session.

## v0.3.0 — Hive-Mind integration

The big one. Connected Talos to Hive-Mind for persistent memory, semantic RAG,
and session persistence. Added `@file.py` and `@clip` references to inject
file contents and clipboard into queries. Context injection sends cwd, git
branch, and diff stats with every request. `remember`/`recall`/`facts`
commands for knowledge storage across sessions. Conversation context saved on
exit, restored on startup.

## v0.3.1 — Learning pipeline

Wired up the learning feedback loop. Every interaction auto-logs to Hive-Mind's
continuous learning pipeline. Inline `+`/`-` rating after command execution
enriches the training signal. `suggest` command for RAG gap analysis — shows
hit rate, missed queries, and recommends facts to add.

## v0.4.0 — Firefox sidebar MVP

Built the Firefox sidebar extension from scratch. Svelte 5 + Vite, MV2
manifest, background script proxying SSE to dodge CORS. `runtime.connect()`
long-lived ports for streaming tokens. Bronze/forge/verdigris theme matching
the TUI. AMO-signed .xpi for distribution.

Learned the hard way that MV2 `persistent: false` event pages unload after
idle, killing the ports. Switched to `persistent: true` and added
auto-reconnect logic.

## v0.5.0 — The sidebar grows up

Multi-provider support — Hive-Mind, Ollama, OpenAI, Anthropic, or any custom
OpenAI-compatible endpoint. Settings panel with provider presets, dynamic auth
headers, API key storage. Tok/s calculated per response and displayed in the
toolbar.

Markdown rendering via snarkdown + XSS sanitizer for assistant messages.
Code blocks with copy button, auto-scroll during streaming.

Page context injection — right-click context menus (Send Selection, Send Page,
Summarize Page), content script extracts page data, ContextChip display above
input.

## v0.5.1 — Polish

Smart ghost suggestions — context-aware Tab-completion that adapts to the last
response. Preemptive suggestions on empty input after responses. Flame particle
burst on send.

## v0.6.0 — The bridge

Conversation bridge — shared history between TUI and Firefox via a Redis sorted
set in Hive-Mind. `bridge` command in the TUI to view cross-client conversations.
Fire-and-forget logging from both clients.

Web scraper MCP tools — `web <url>` fetches and injects page content,
`search <query>` hits DuckDuckGo. Both available in TUI.

Keyboard shortcuts in content script — Ctrl+Shift+S sends selection to sidebar,
Ctrl+Shift+P sends full page.

Unit tests — 70 Python tests, 15 JS tests (vitest). Extracted pure functions
from Svelte components into utils.js for testability.

## v0.6.1 — Sidebar search

Brought `/web` and `/search` commands to the Firefox sidebar. Type
`/search <query>` for DuckDuckGo results with clickable links, or
`/web <url>` to fetch page content and ask follow-up questions about it.

Fixed text selection in message bubbles — `user-select: text` on the bubble CSS.

## v0.6.2 — Input history and shortcuts

Up/down arrow navigates sent message history in the sidebar input box.
Tok/s display pulses bronze on update so you can see it refresh even when
the speed is consistent. Sidebar toggle shortcut changed from Ctrl+Shift+Y
to Alt+Shift+T to avoid conflicts.

---

## Lessons along the way

- **MV2 event pages kill ports** — `persistent: false` unloads background
  scripts after idle, breaking `runtime.connect()`. Use `persistent: true`.
- **AMO clock sync** — `web-ext sign` generates JWTs; if your system clock
  drifts, AMO rejects them. Fix with `chronyc makestep`.
- **AMO version uniqueness** — every re-sign needs a version bump.
- **Flatpak Firefox can't load temporary addons** — `moz-extension://` file
  serving is broken in the sandbox. Use native Firefox for extension dev.
- **Vite HTML entry placement** — must be at project root for flat `dist/`
  output.
- **Fedora CA trust restrictions** — Fedora's ca-certificates package
  restricts some roots (like Comodo AAA) to code-signing only. Cloudflare
  chains through this root. Fix by adding the cert to
  `/etc/pki/ca-trust/source/anchors/` and running `update-ca-trust extract`.
- **Selenium Remote vs Firefox** — `webdriver.Remote` lacks `install_addon()`.
  Use `webdriver.Firefox` directly.

## What's next

The guardian keeps learning. Every conversation, every correction, every rated
response feeds back into the LoRA training pipeline. The model gets sharper.
The RAG gets denser. The bronze grows a patina.
