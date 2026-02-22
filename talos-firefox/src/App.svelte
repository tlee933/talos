<script>
  import { onMount } from 'svelte';
  import {
    connect, setCallbacks, sendChat, sendWebFetch, sendWebSearch,
    checkHealth, getConfig, updateConfig, disconnect,
    saveConversation, listConversations, loadConversation, deleteConversation,
  } from './api.js';
  import { DEFAULT_CONFIG } from './providers.js';
  import Toolbar from './components/Toolbar.svelte';
  import MessageList from './components/MessageList.svelte';
  import InputBar from './components/InputBar.svelte';
  import ConversationPanel from './components/ConversationPanel.svelte';

  let messages = $state([]);
  let connected = $state(false);
  let streaming = $state(false);
  let activeRequestId = $state(null);
  let config = $state({ ...DEFAULT_CONFIG });
  let tokPerSec = $state(null);
  let tokUpdatedAt = $state(0);
  let lastModelUsed = $state('');
  let healthInterval;

  // Page context state
  let pageContext = $state(null);
  let contextMode = $state(null);

  // Conversation persistence state
  let conversationId = $state(null);
  let historyPanelOpen = $state(false);
  let conversations = $state([]);
  let saveTimer = null;

  function clearContext() {
    pageContext = null;
    contextMode = null;
  }

  function generateId() {
    return crypto.randomUUID().slice(0, 8);
  }

  function pruneHistory() {
    // Target: ~20K tokens worth of chars (~70K chars at 3.5 chars/token)
    // Leaves headroom for system prompt + RAG facts injected server-side
    const MAX_HISTORY_CHARS = 70000;
    const MAX_MSG_CHARS = 3000;
    const MIN_RECENT = 6;

    // Step 1: Strip think blocks from older messages (keep in most recent)
    for (let i = 0; i < messages.length - 2; i++) {
      const m = messages[i];
      if (m.role === 'assistant' && m.content?.includes('<think>')) {
        m.content = m.content.replace(/<think>[\s\S]*?<\/think>\s*/g, '').trim();
      }
    }

    // Step 2: Truncate bloated individual messages (except last 2)
    for (let i = 0; i < messages.length - 2; i++) {
      if ((messages[i].content || '').length > MAX_MSG_CHARS) {
        messages[i] = {
          ...messages[i],
          content: messages[i].content.slice(0, MAX_MSG_CHARS) + '\n...(truncated)',
        };
      }
    }

    // Step 3: Drop middle messages oldest-first if still over budget
    const totalChars = () => messages.reduce((sum, m) => sum + (m.content || '').length, 0);
    if (totalChars() < MAX_HISTORY_CHARS || messages.length <= MIN_RECENT + 1) return;

    const first = messages.slice(0, 1);
    const recent = messages.slice(-MIN_RECENT);
    let middle = messages.slice(1, -MIN_RECENT);

    while (middle.length > 0 && (
      first.reduce((s, m) => s + (m.content || '').length, 0) +
      middle.reduce((s, m) => s + (m.content || '').length, 0) +
      recent.reduce((s, m) => s + (m.content || '').length, 0)
    ) > MAX_HISTORY_CHARS) {
      middle.shift();
    }

    messages = [...first, ...middle, ...recent];
    if (middle.length === 0) {
      messages = [...first, { role: 'system', content: '[earlier messages pruned]' }, ...recent];
    }
  }

  function debouncedSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      if (conversationId && messages.length > 0) {
        saveConversation(conversationId, '', messages);
      }
    }, 2000);
  }

  function startNewConversation() {
    messages = [];
    conversationId = generateId();
    historyPanelOpen = false;
  }

  function handleSend(text) {
    // Handle /help command
    if (text.trim() === '/help') {
      messages.push({
        role: 'assistant',
        content:
          '**Talos Commands**\n\n' +
          '`/web <url>` — fetch a page and display its content\n' +
          '`/search <query>` — search DuckDuckGo\n' +
          '`/reason <query>` — ask with step-by-step reasoning\n' +
          '`/new` — start a fresh conversation\n' +
          '`/help` — show this help\n\n' +
          '**Keyboard Shortcuts**\n\n' +
          '`Ctrl+Shift+Y` — toggle sidebar\n' +
          '`Ctrl+Shift+S` — send selected text\n' +
          '`Ctrl+Shift+P` — send page content\n' +
          '`Tab` — accept ghost suggestion\n' +
          '`Shift+Enter` — newline\n' +
          '`↑ / ↓` — input history\n\n' +
          '**Context Menu**\n\n' +
          'Right-click any page for *Send Selection*, *Send Page*, or *Summarize Page*.',
      });
      return;
    }

    // Handle /new command
    if (text.trim() === '/new') {
      startNewConversation();
      return;
    }

    // Handle /reason command — inject step-by-step thinking prompt
    let reasonMode = false;
    if (text.startsWith('/reason ')) {
      text = text.slice(8).trim();
      reasonMode = true;
      if (!text) return;
    }

    // Handle /web command
    if (text.startsWith('/web ')) {
      const url = text.slice(5).trim();
      if (!url) return;
      messages.push({ role: 'user', content: text });
      messages.push({ role: 'assistant', content: 'Fetching...' });
      streaming = true;
      const reqId = sendWebFetch(url);
      activeRequestId = reqId;
      return;
    }

    // Handle /search command
    if (text.startsWith('/search ')) {
      const query = text.slice(8).trim();
      if (!query) return;
      messages.push({ role: 'user', content: text });
      messages.push({ role: 'assistant', content: 'Searching...' });
      streaming = true;
      const reqId = sendWebSearch(query);
      activeRequestId = reqId;
      return;
    }

    // Generate conversation ID on first message
    if (!conversationId) {
      conversationId = generateId();
    }

    let userContent = text;

    // Inject page context into the message
    if (pageContext) {
      const title = pageContext.title || 'Untitled';
      const url = pageContext.url || '';

      let contextBlock = `[Context: ${title}](${url})\n`;

      if (contextMode === 'selection' && pageContext.selection) {
        contextBlock += `> ${pageContext.selection}\n\n`;
      } else if (pageContext.text) {
        contextBlock += `> ${pageContext.text.slice(0, 2000)}\n\n`;
      }

      // For "summarize" with no user text, auto-fill
      if (contextMode === 'summarize' && text === 'Summarize this page.') {
        userContent = contextBlock + text;
      } else {
        userContent = contextBlock + text;
      }

      clearContext();
    }

    // Append reasoning prompt when in reason mode
    if (reasonMode) {
      userContent += '\n\nWhen solving this, think step by step. Show your reasoning process inside <think>...</think> tags before giving your final answer.';
    }

    messages.push({ role: 'user', content: userContent });

    // Prune if needed before sending
    pruneHistory();

    // Snapshot history including the new user message (exclude empty assistant placeholder)
    const history = messages
      .filter((m) => m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    messages.push({ role: 'assistant', content: '' });

    const reqId = sendChat(history, { reasonMode });
    if (!reqId) return;

    activeRequestId = reqId;
    streaming = true;
  }

  function handleConfigChange(newConfig) {
    config = { ...config, ...newConfig };
    updateConfig(config);
    // Re-check health with new URL
    checkHealth();
  }

  function handleLoadConversation(conv) {
    loadConversation(conv.id);
    historyPanelOpen = false;
  }

  function handleDeleteConversation(conv) {
    deleteConversation(conv.id);
    conversations = conversations.filter((c) => c.id !== conv.id);
  }

  function toggleHistoryPanel() {
    historyPanelOpen = !historyPanelOpen;
    if (historyPanelOpen) {
      listConversations();
    }
  }

  onMount(() => {
    setCallbacks({
      onStreamStart(reqId) {
        // already set up in handleSend
      },
      onToken(reqId, token) {
        if (reqId !== activeRequestId) return;
        const last = messages[messages.length - 1];
        if (last && last.role === 'assistant') {
          last.content += token;
        }
      },
      onStreamEnd(reqId, tps, routing) {
        if (reqId !== activeRequestId) return;
        streaming = false;
        activeRequestId = null;
        if (tps != null) {
          tokPerSec = tps;
          tokUpdatedAt = Date.now();
        }
        if (routing?.modelUsed) {
          lastModelUsed = routing.modelUsed;
        }
        // Auto-save after each response
        debouncedSave();
      },
      onStreamError(reqId, error) {
        if (reqId !== activeRequestId) return;
        const last = messages[messages.length - 1];
        if (last && last.role === 'assistant' && !last.content) {
          last.content = `Error: ${error}`;
        } else {
          messages.push({ role: 'assistant', content: `Error: ${error}` });
        }
        streaming = false;
        activeRequestId = null;
      },
      onHealth(ok, ms) {
        connected = ok;
      },
      onConfigLoaded(cfg) {
        config = { ...DEFAULT_CONFIG, ...cfg };
      },
      onContextReceived(context, mode) {
        pageContext = context;
        contextMode = mode;
      },
      onWebFetchResult(reqId, data) {
        if (reqId !== activeRequestId) return;
        streaming = false;
        activeRequestId = null;
        const last = messages[messages.length - 1];
        if (last && last.role === 'assistant') {
          if (data.error) {
            last.content = `Error: ${data.error}`;
          } else {
            const title = data.title || 'Untitled';
            const preview = (data.text || '').slice(0, 800);
            last.content = `**${title}**\n\n${preview}${data.text && data.text.length > 800 ? '\n\n*(truncated)*' : ''}`;
            // Inject full text into history for follow-up questions
            messages.push({ role: 'system', content: `[Web page content from ${data.url}]: ${(data.text || '').slice(0, 2000)}` });
          }
        }
      },
      onWebSearchResult(reqId, data) {
        if (reqId !== activeRequestId) return;
        streaming = false;
        activeRequestId = null;
        const last = messages[messages.length - 1];
        if (last && last.role === 'assistant') {
          if (data.error) {
            last.content = `Error: ${data.error}`;
          } else {
            const results = data.results || [];
            if (results.length === 0) {
              last.content = 'No results found.';
            } else {
              last.content = results.map((r, i) =>
                `**${i + 1}. ${r.title || 'Untitled'}**\n[${r.url}](${r.url})\n${r.snippet || ''}`
              ).join('\n\n');
            }
          }
        }
      },
      onConvSaved(result) {
        // Auto-save acknowledged — no UI feedback needed
      },
      onConvListResult(convs) {
        conversations = convs || [];
      },
      onConvLoaded(result) {
        if (result.success) {
          conversationId = result.id;
          messages = result.messages || [];
        }
      },
      onConvDeleted(result) {
        // Already removed from local state in handleDeleteConversation
      },
    });

    connect();
    getConfig();
    checkHealth();
    healthInterval = setInterval(checkHealth, 30000);

    // Load most recent conversation on mount
    listConversations();

    return () => {
      clearInterval(healthInterval);
      if (saveTimer) clearTimeout(saveTimer);
      disconnect();
    };
  });
</script>

<Toolbar
  {connected}
  {config}
  {tokPerSec}
  {tokUpdatedAt}
  modelUsed={lastModelUsed}
  onConfigChange={handleConfigChange}
  onToggleHistory={toggleHistoryPanel}
  onNewConversation={startNewConversation}
/>

{#if historyPanelOpen}
  <ConversationPanel
    {conversations}
    onLoad={handleLoadConversation}
    onDelete={handleDeleteConversation}
    onClose={() => { historyPanelOpen = false; }}
  />
{/if}

<MessageList {messages} streamingId={activeRequestId} />
<InputBar
  onSend={handleSend}
  disabled={streaming}
  context={pageContext}
  contextMode={contextMode}
  onDismissContext={clearContext}
  {messages}
/>
