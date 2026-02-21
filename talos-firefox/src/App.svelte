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

  function handleSend(text) {
    messages.push({ role: 'user', content: text });

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
<InputBar onSend={handleSend} disabled={streaming} />
