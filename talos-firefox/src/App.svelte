<script>
  import { onMount } from 'svelte';
  import { connect, setCallbacks, sendChat, checkHealth, getConfig, updateConfig, disconnect } from './api.js';
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
  let healthInterval;

  // Page context state
  let pageContext = $state(null);
  let contextMode = $state(null);

  function clearContext() {
    pageContext = null;
    contextMode = null;
  }

  function handleSend(text) {
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
        if (tps != null) tokPerSec = tps;
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

        // For "summarize" mode, auto-fill the input hint
        // (the actual auto-send is handled via the InputBar text prop if desired,
        //  but we keep it simple — user sees the chip and can type or just hit enter)
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

<Toolbar {connected} {config} {tokPerSec} onConfigChange={handleConfigChange} />
<MessageList {messages} streamingId={activeRequestId} />
<InputBar
  onSend={handleSend}
  disabled={streaming}
  context={pageContext}
  contextMode={contextMode}
  onDismissContext={clearContext}
  {messages}
/>
