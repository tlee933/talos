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

## v0.7.0 — The smarter agent

The biggest single release. Three major capabilities landed in one shot:

**Tool-use via function calling.** The LLM now invokes tools directly through
`<tool_call>` XML tags instead of just proposing shell commands. Ten built-in
tools — shell execution, file read/write/list, clipboard, notifications, web
fetch, and fact store/get. Tool results feed back into the reasoning loop
automatically. The tool registry uses `functools.partial` to bind agent-dependent
handlers, and `tools_to_openai_schema()` generates the function-calling payload
for llama-server's native tool support.

**Step-by-step reasoning.** `reason <query>` (TUI) and `/reason <query>`
(sidebar) trigger chain-of-thought via `<think>` blocks. The SSE parser detects
llama-server's native `reasoning_content` field and wraps it in `<think>` tags
on-the-fly. TUI renders thinking in amber Rich Panels; the sidebar uses
collapsible `<details>` elements. Discovered during live testing that
llama-server streams reasoning as a separate delta field rather than inline
tags — had to update both Python and JS SSE parsers.

**Conversation persistence.** TUI gets `save`/`load`/`sessions`/`export`
commands backed by Hive-Mind Redis (28-day TTL). Firefox sidebar auto-saves to
`browser.storage.local` with debounced writes, a conversation history panel
(clock icon in toolbar), and `/new` to start fresh. Context window management
via smart pruning — keeps first turn + last 6, drops middle oldest-first,
truncates bloated turns.

**Auto-rating.** Command execution results now auto-rate the learning signal
based on exit codes (success → positive, failure → negative). Shows `▲`/`▼`
inline with manual `+`/`-` override. Enriches the training pipeline without
requiring user input on every interaction.

**Performance.** HiveCoder-7B hitting 88 tok/s on the R9700 XT — up from ~61
tok/s earlier. The Qwen2.5-Coder-7B Q5_K_M quantization with ROCm 7.12 and
RDNA4 optimizations is screaming.

116 Python tests, 26 JS tests. Zero lint errors. Everything signed and deployed.

## v0.7.2 — Gold and darkness

Extracted the suggestion engine into dedicated modules for both platforms.
`suggestions.js` powers the Firefox/Zen sidebar; `suggestions.py` mirrors the
logic for the TUI. All pure functions, fully testable.

**Smarter ghost suggestions.** Context-aware ranking puts follow-ups above base
suggestions. Slash command hints complete as you type — `/se` ghosts
`arch <query>`, `/w` ghosts `eb <url>`. Page-aware suggestions detect GitHub
URLs ("What does this PR do?") and text selections ("Explain this selection").
Suggestion chains track depth — Tab-complete a preemptive, send it, and the
next preemptive is a follow-up to the follow-up (8 chain mappings). TUI gets
ghost text via prompt_toolkit's `AutoSuggest` — dimmed suggestions appear as
you type, right-arrow accepts.

**Gold highlights.** Added `--gold` as a dedicated content emphasis color.
Headings, bold text, code block language labels, blockquote borders, inline
code underlines, the streaming cursor, the "T" logo, and the tok/s pulse all
glow gold. Bronze stays on interactive elements — buttons, input focus, hovers.
Clear visual hierarchy: gold draws the eye to content structure, bronze anchors
the interactive bits.

**Dark theme refresh for Zen Browser.** Switched the default browser to Zen
(Firefox fork, Flatpak). Darkened the base from navy (`#1A1A2E`) to near-black
(`#141418`) to match Zen's dark chrome. Brightened every accent color for punch
on the darker background — bronze, gold, amber, verdigris, warm text, muted
text all stepped up. Updated all hardcoded rgba values to match. Looks killer
with Dark Reader layered on top.

140 Python tests, 69 JS tests. Extension v0.7.2 signed and installed in Zen.

## v0.7.3 — The self-improving loop

Talos now has two brains. An intelligent model router classifies every query
and sends it to the right one — HiveCoder-7B (88 tok/s, code-tuned) for
code, shell, and tool-use queries, or DeepSeek-R1-Distill-Qwen-14B (55 tok/s,
chain-of-thought reasoning) for analysis, explanation, and "why" questions.

The router is a pure-function classifier with zero latency. It scores queries
against ~30 code signal keywords and ~25 reasoning signal keywords, with bonus
weight for code blocks, import patterns, and file paths. Priority order:
explicit model hint > `/reason` command > heuristic scoring > default to
HiveCoder. Ties go to the fast model.

The key insight: **R1's answers teach HiveCoder.** Every R1 response is
auto-rated positive and tagged with `model_source: "r1-distill"`. These
bypass the quality filter in the continuous learning pipeline and flow straight
into HiveCoder's LoRA training data. Pure-reasoning answers (no commands
executed) get captured too via a dedicated `build_reasoning_interaction()`
path — previously these were silently dropped. The bigger model teaches the
smaller model through the existing training loop, and HiveCoder gets smarter
over time while staying at 88 tok/s.

The HTTP server resolves model-specific endpoints, system prompts, and
`max_tokens` from a new `inference.models` config dict. Streaming responses
include `X-Model-Used`, `X-Model-Id`, and `X-Routing-Reason` headers. The TUI
captures these and shows "routed → R1-Distill-14B" when the reasoning model
handles a query. The Firefox toolbar dynamically updates to show the actual
model that answered.

147 Python tests, 14 router tests, 69 JS tests. Extension v0.7.3 signed and
installed in Zen.

## v0.7.4 — Context pruning

Fixed context overflow in the Firefox/Zen extension. Long reasoning sessions
with R1 were blowing through the 32K context window because `pruneHistory()`
wasn't aggressive enough. Three fixes: strip `<think>` blocks from older
messages (reasoning traces accumulate fast), truncate bloated individual
messages to 3K chars, and lower the history budget from ~25K to ~20K tokens.
Web page content injection reduced from 4K to 2K chars.

## v0.7.5 — Think block separation

The real fix for context overflow. R1's `<think>` reasoning blocks (2-5K chars
each) were being sent back to the LLM in conversation history on every turn —
the model was re-reading its own internal monologue. Now the API history
snapshot strips all think blocks from assistant messages before sending. The
blocks stay visible in the sidebar display but never waste context budget.

Also added the Self-Instruct citation (Wang et al., 2022) to the Hive-Mind
architecture docs — the knowledge distillation loop is a production
implementation of that technique.

Hive-Mind docs cleaned up: 13 stale files purged, README/ARCHITECTURE/
QUICKSTART/ROADMAP rewritten for the current dual-LLM stack. 486 insertions,
4,306 deletions.

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
- **llama-server reasoning_content** — when models think, llama-server streams
  reasoning as a separate `reasoning_content` delta field, not inline `<think>`
  tags. SSE parsers must detect this field and wrap it in tags for downstream
  rendering.
- **Zen Browser is a Flatpak** — profile lives at
  `~/.var/app/app.zen_browser.zen/.zen/`. Install signed .xpi to the
  `extensions/` dir under the profile. Same MV2 compat as Firefox.
- **Wayland and screenshots** — Zen is native Wayland, invisible to X tools
  (`xdotool`, `xprop`). Use KWin scripting or delayed `spectacle` with manual
  focus switch.
- **xdg-settings on Kinoite** — `qtpaths` missing warning is cosmetic.
  `xdg-mime default` works fine for setting the default browser.

## What's next

The guardian keeps learning. Every conversation, every correction, every rated
response feeds back into the LoRA training pipeline. The model gets sharper.
The RAG gets denser. The bronze grows a patina — and now, it teaches itself.
