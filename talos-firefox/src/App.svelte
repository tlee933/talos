<script>
  import { onMount } from 'svelte';
  import { connect, setCallbacks, sendChat, checkHealth, disconnect } from './api.js';
  import StatusBadge from './components/StatusBadge.svelte';
  import MessageList from './components/MessageList.svelte';
  import InputBar from './components/InputBar.svelte';

  let messages = $state([]);
  let connected = $state(false);
  let latency = $state(0);
  let streaming = $state(false);
  let activeRequestId = $state(null);
  let healthInterval;

  function handleSend(text) {
    messages.push({ role: 'user', content: text });

    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    messages.push({ role: 'assistant', content: '' });

    const reqId = sendChat(history.slice(0, -1));
    if (!reqId) return;

    activeRequestId = reqId;
    streaming = true;
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
      onStreamEnd(reqId) {
        if (reqId !== activeRequestId) return;
        streaming = false;
        activeRequestId = null;
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
        latency = ms;
      },
    });

    connect();
    checkHealth();
    healthInterval = setInterval(checkHealth, 30000);

    return () => {
      clearInterval(healthInterval);
      disconnect();
    };
  });
</script>

<StatusBadge {connected} {latency} />
<MessageList {messages} streamingId={activeRequestId} />
<InputBar onSend={handleSend} disabled={streaming} />
