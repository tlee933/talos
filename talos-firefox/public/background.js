const HIVE_MIND = 'http://localhost:8090';

browser.runtime.onConnect.addListener((port) => {
  if (port.name !== 'talos-sidebar') return;

  port.onMessage.addListener((msg) => {
    if (msg.type === 'CHAT') handleChat(port, msg);
    else if (msg.type === 'HEALTH_CHECK') handleHealth(port);
  });
});

async function handleHealth(port) {
  const start = Date.now();
  try {
    const res = await fetch(`${HIVE_MIND}/health`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      port.postMessage({ type: 'HEALTH_RESULT', ok: true, latency: Date.now() - start });
    } else {
      port.postMessage({ type: 'HEALTH_RESULT', ok: false, latency: 0 });
    }
  } catch {
    port.postMessage({ type: 'HEALTH_RESULT', ok: false, latency: 0 });
  }
}

async function handleChat(port, msg) {
  const { requestId, history } = msg;

  const systemPrompt = {
    role: 'system',
    content: 'You are Talos, a local-first AI assistant. Be concise and helpful. Format code with fenced code blocks.',
  };

  const body = JSON.stringify({
    model: 'hivecoder-7b',
    messages: [systemPrompt, ...history],
    temperature: 0.7,
    max_tokens: 1024,
    stream: true,
  });

  try {
    port.postMessage({ type: 'STREAM_START', requestId });

    const res = await fetch(`${HIVE_MIND}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      port.postMessage({ type: 'STREAM_ERROR', requestId, error: `HTTP ${res.status}: ${text}` });
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;

        const data = trimmed.slice(5).trim();
        if (data === '[DONE]') continue;

        try {
          const parsed = JSON.parse(data);
          const token = parsed.choices?.[0]?.delta?.content;
          if (token) {
            port.postMessage({ type: 'STREAM_TOKEN', requestId, token });
          }
        } catch {
          // skip malformed SSE lines
        }
      }
    }

    port.postMessage({ type: 'STREAM_END', requestId });
  } catch (err) {
    port.postMessage({
      type: 'STREAM_ERROR',
      requestId,
      error: err.message || 'Connection failed',
    });
  }
}
