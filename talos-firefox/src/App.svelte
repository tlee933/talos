<script>
  import { onMount } from 'svelte';
  import { connect, setCallbacks, sendChat, sendWebFetch, sendWebSearch, checkHealth, getConfig, updateConfig, disconnect } from './api.js';
  import { DEFAULT_CONFIG } from './providers.js';
  import Toolbar from './components/Toolbar.svelte';
  import MessageList from './components/MessageList.svelte';
  import InputBar from './components/InputBar.svelte';

  let messages = $state([]);
  let connected = $state(false);
  let streaming = $state(false);
  let activeRequestId = $state(null);
  let config = $state({ ...DEFAULT_CONFIG });
  let tokPerSec = $state(null);
  let tokUpdatedAt = $state(0);
  let healthInterval;

  // Page context state
  let pageContext = $state(null);
  let contextMode = $state(null);

  function clearContext() {
    pageContext = null;
    contextMode = null;
  }

  function handleSend(text) {
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

    messages.push({ role: 'user', content: userContent });

    // Snapshot history including the new user message (exclude empty assistant placeholder)
    const history = messages
      .filter((m) => m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    messages.push({ role: 'assistant', content: '' });

    const reqId = sendChat(history);
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
      onStreamEnd(reqId, tps) {
        if (reqId !== activeRequestId) return;
        streaming = false;
        activeRequestId = null;
        if (tps != null) {
          tokPerSec = tps;
          tokUpdatedAt = Date.now();
        }
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
            messages.push({ role: 'system', content: `[Web page content from ${data.url}]: ${(data.text || '').slice(0, 4000)}` });
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
    });

    connect();
    getConfig();
    checkHealth();
    healthInterval = setInterval(checkHealth, 30000);

    return () => {
      clearInterval(healthInterval);
      disconnect();
    };
  });
</script>

<Toolbar {connected} {config} {tokPerSec} {tokUpdatedAt} onConfigChange={handleConfigChange} />
<MessageList {messages} streamingId={activeRequestId} />
<InputBar
  onSend={handleSend}
  disabled={streaming}
  context={pageContext}
  contextMode={contextMode}
  onDismissContext={clearContext}
  {messages}
/>
