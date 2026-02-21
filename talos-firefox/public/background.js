// Provider presets (duplicated here — background has no build step)
const PROVIDERS = [
  { id: 'hive-mind',  url: 'http://localhost:8090',      model: 'hivecoder-7b',             auth: 'none' },
  { id: 'ollama',     url: 'http://localhost:11434',     model: 'llama3.1',                 auth: 'none' },
  { id: 'openai',     url: 'https://api.openai.com',     model: 'gpt-4o-mini',              auth: 'bearer' },
  { id: 'anthropic',  url: 'https://api.anthropic.com',  model: 'claude-sonnet-4-20250514', auth: 'x-api-key' },
  { id: 'custom',     url: '',                            model: '',                         auth: 'bearer' },
];

const DEFAULT_CONFIG = {
  provider: 'hive-mind',
  apiUrl: 'http://localhost:8090',
  model: 'hivecoder-7b',
  apiKey: '',
  temperature: 0.7,
  maxTokens: 1024,
};

let config = { ...DEFAULT_CONFIG };

async function loadConfig() {
  try {
    const result = await browser.storage.local.get('talos-config');
    if (result['talos-config']) {
      config = { ...DEFAULT_CONFIG, ...result['talos-config'] };
    }
  } catch {
    // storage unavailable — keep defaults
  }
  return config;
}

async function saveConfig(newConfig) {
  config = { ...DEFAULT_CONFIG, ...newConfig };
  try {
    await browser.storage.local.set({ 'talos-config': config });
  } catch {
    // storage unavailable
  }
  return config;
}

function buildAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const preset = PROVIDERS.find((p) => p.id === config.provider);
  const authType = preset?.auth || 'none';

  if (config.apiKey) {
    if (authType === 'bearer') {
      headers['Authorization'] = `Bearer ${config.apiKey}`;
    } else if (authType === 'x-api-key') {
      headers['x-api-key'] = config.apiKey;
    }
  }
  return headers;
}

function chatEndpoint() {
  const base = config.apiUrl.replace(/\/+$/, '');
  // Ollama uses the same /v1/chat/completions path
  return `${base}/v1/chat/completions`;
}

// Toolbar button toggles the sidebar
browser.browserAction.onClicked.addListener(() => {
  browser.sidebarAction.toggle();
});

// Load config on startup
loadConfig();

browser.runtime.onConnect.addListener((port) => {
  if (port.name !== 'talos-sidebar') return;

  port.onMessage.addListener((msg) => {
    if (msg.type === 'CHAT') handleChat(port, msg);
    else if (msg.type === 'HEALTH_CHECK') handleHealth(port);
    else if (msg.type === 'CONFIG_GET') handleConfigGet(port);
    else if (msg.type === 'CONFIG_UPDATE') handleConfigUpdate(port, msg);
  });
});

async function handleConfigGet(port) {
  const cfg = await loadConfig();
  port.postMessage({ type: 'CONFIG_LOADED', config: cfg });
}

async function handleConfigUpdate(port, msg) {
  const cfg = await saveConfig(msg.config);
  port.postMessage({ type: 'CONFIG_LOADED', config: cfg });
}

async function handleHealth(port) {
  const start = Date.now();
  try {
    const base = config.apiUrl.replace(/\/+$/, '');
    const res = await fetch(`${base}/health`, { signal: AbortSignal.timeout(5000) });
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
    model: config.model,
    messages: [systemPrompt, ...history],
    temperature: config.temperature,
    max_tokens: config.maxTokens,
    stream: true,
  });

  try {
    port.postMessage({ type: 'STREAM_START', requestId });

    const res = await fetch(chatEndpoint(), {
      method: 'POST',
      headers: buildAuthHeaders(),
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
    let tokenCount = 0;
    const streamStart = Date.now();

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
            tokenCount++;
            port.postMessage({ type: 'STREAM_TOKEN', requestId, token });
          }
        } catch {
          // skip malformed SSE lines
        }
      }
    }

    const elapsed = (Date.now() - streamStart) / 1000;
    const tokPerSec = elapsed > 0 ? Math.round(tokenCount / elapsed) : 0;
    port.postMessage({ type: 'STREAM_END', requestId, tokPerSec });
  } catch (err) {
    port.postMessage({
      type: 'STREAM_ERROR',
      requestId,
      error: err.message || 'Connection failed',
    });
  }
}
