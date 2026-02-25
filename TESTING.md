# Testing

## Quick Run

```bash
# All tests
./talos-firefox/node_modules/.bin/vitest run && .venv/bin/python -m pytest tests/ -v

# Python only (147 tests)
.venv/bin/python -m pytest tests/ -v

# Firefox extension only (89 tests)
cd talos-firefox && npx vitest run
```

## Python Tests (`tests/`)

| File | Coverage |
|------|----------|
| `test_agent_hivemind.py` | Hive-Mind integration — facts, memory, learning queue, context threading |
| `test_bridge.py` | Conversation logging and recent history |
| `test_completers.py` | Tab completion for commands (/remember, /recall, /facts, /suggest) |
| `test_config.py` | Config loading, defaults, overrides, unknown keys |
| `test_context.py` | @file and @clipboard reference expansion |
| `test_context_manager.py` | Token estimation, budget calculation, smart pruning |
| `test_conversation_persistence.py` | Save, load, list, export (markdown/JSON) |
| `test_dangerous.py` | Command safety — blocks rm -rf, dd, mkfs, fork bombs, etc. |
| `test_learning.py` | Interaction building, rating, R1 distillation tagging, reasoning |
| `test_parser.py` | Response parsing — code blocks, think blocks, tool calls, SSE |
| `test_suggestions.py` | Ghost text, context-aware suggestions, pattern detection |
| `test_tools.py` | Tool call parsing, file read, tool registry, OpenAI schema |
| `test_web.py` | Web fetch and search |

## Firefox Extension Tests (`talos-firefox/tests/`)

| File | Coverage |
|------|----------|
| `context-pruning.test.js` | Think block stripping, context budget, message truncation, pruning, mode-switch continuity |
| `conversation-storage.test.js` | Conversation save/load in extension storage |
| `message-parse.test.js` | Message content parsing for display |
| `suggestions.test.js` | Ghost text suggestions and matching |

## Router Tests (hive-mind)

```bash
cd /var/mnt/build/MCP/hive-mind/mcp-server && .venv/bin/python -m pytest test_router.py -v
```

14 tests covering explicit hints, reason mode routing, heuristics, code/reasoning signal detection, tie-breaking.
