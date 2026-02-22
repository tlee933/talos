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
let sidebarPort = null;

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

// --- Context Menus ---
browser.contextMenus.create({
  id: 'talos-send-selection',
  title: 'Send Selection to Talos',
  contexts: ['selection'],
});

browser.contextMenus.create({
  id: 'talos-send-page',
  title: 'Send Page to Talos',
  contexts: ['page'],
});

browser.contextMenus.create({
  id: 'talos-summarize',
  title: 'Summarize Page',
  contexts: ['page'],
});

browser.contextMenus.onClicked.addListener(async (info, tab) => {
  const modeMap = {
    'talos-send-selection': 'selection',
    'talos-send-page': 'page',
    'talos-summarize': 'summarize',
  };
  const mode = modeMap[info.menuItemId];
  if (!mode) return;

  try {
    // Open sidebar so context has somewhere to go
    browser.sidebarAction.open();

    // Ask content script to extract page data
    const context = await browser.tabs.sendMessage(tab.id, {
      type: 'EXTRACT_CONTEXT',
      mode,
    });

    // Relay to sidebar
    if (sidebarPort) {
      sidebarPort.postMessage({ type: 'PAGE_CONTEXT', context, mode });
    }
  } catch (err) {
    // Content script might not be injected yet — ignore
    console.warn('Talos context extraction failed:', err.message);
  }
});

// Handle keyboard shortcut messages from content script
browser.runtime.onMessage.addListener((msg) => {
  if (msg.type !== 'CONTENT_SHORTCUT') return;

  // Open sidebar so the context has somewhere to go
  browser.sidebarAction.open();

  // Relay as PAGE_CONTEXT to sidebar (reuses existing ContextChip flow)
  if (sidebarPort) {
    sidebarPort.postMessage({
      type: 'PAGE_CONTEXT',
      context: msg.context,
      mode: msg.mode,
    });
  }
});

// Toolbar button toggles the sidebar
browser.browserAction.onClicked.addListener(() => {
  browser.sidebarAction.toggle();
});

// --- Conversation Storage ---
const MAX_CONVERSATIONS = 50;
const MAX_MESSAGES_PER_CONV = 200;
const MAX_MSG_CHARS = 2000;

function autoTitle(messages) {
  const first = messages.find((m) => m.role === 'user');
  if (!first) return 'Untitled';
  const text = first.content.slice(0, 80).trim();
  return text.length < first.content.length ? text + '...' : text;
}

async function saveConversation(id, title, messages) {
  try {
    const result = await browser.storage.local.get('talos-conversations');
    const convs = result['talos-conversations'] || {};

    // Truncate messages
    const trimmed = messages.slice(-MAX_MESSAGES_PER_CONV).map((m) => ({
      role: m.role,
      content: (m.content || '').slice(0, MAX_MSG_CHARS),
    }));

    convs[id] = {
      title: title || autoTitle(messages),
      messages: trimmed,
      messageCount: trimmed.length,
      updatedAt: Date.now(),
    };

    // Cap total conversations
    const ids = Object.keys(convs);
    if (ids.length > MAX_CONVERSATIONS) {
      ids.sort((a, b) => (convs[a].updatedAt || 0) - (convs[b].updatedAt || 0));
      for (let i = 0; i < ids.length - MAX_CONVERSATIONS; i++) {
        delete convs[ids[i]];
      }
    }

    await browser.storage.local.set({ 'talos-conversations': convs });
    return { success: true, id, title: convs[id].title };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

async function loadConversations() {
  try {
    const result = await browser.storage.local.get('talos-conversations');
    const convs = result['talos-conversations'] || {};
    return Object.entries(convs)
      .map(([id, data]) => ({
        id,
        title: data.title || 'Untitled',
        messageCount: data.messageCount || 0,
        updatedAt: data.updatedAt || 0,
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

async function loadConversation(id) {
  try {
    const result = await browser.storage.local.get('talos-conversations');
    const convs = result['talos-conversations'] || {};
    const conv = convs[id];
    if (!conv) return { success: false, error: 'Not found' };
    return { success: true, id, title: conv.title, messages: conv.messages || [] };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

async function deleteConversation(id) {
  try {
    const result = await browser.storage.local.get('talos-conversations');
    const convs = result['talos-conversations'] || {};
    delete convs[id];
    await browser.storage.local.set({ 'talos-conversations': convs });
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// Load config on startup
loadConfig();

browser.runtime.onConnect.addListener((port) => {
  if (port.name !== 'talos-sidebar') return;

  sidebarPort = port;

  port.onMessage.addListener((msg) => {
    if (msg.type === 'CHAT') handleChat(port, msg);
    else if (msg.type === 'HEALTH_CHECK') handleHealth(port);
    else if (msg.type === 'CONFIG_GET') handleConfigGet(port);
    else if (msg.type === 'CONFIG_UPDATE') handleConfigUpdate(port, msg);
    else if (msg.type === 'WEB_FETCH') handleWebFetch(port, msg);
    else if (msg.type === 'WEB_SEARCH') handleWebSearch(port, msg);
    else if (msg.type === 'CONV_SAVE') handleConvSave(port, msg);
    else if (msg.type === 'CONV_LIST') handleConvList(port);
    else if (msg.type === 'CONV_LOAD') handleConvLoad(port, msg);
    else if (msg.type === 'CONV_DELETE') handleConvDelete(port, msg);
  });

  port.onDisconnect.addListener(() => {
    if (sidebarPort === port) sidebarPort = null;
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

function logConversation(role, content) {
  // Fire-and-forget POST to conversation bridge
  const base = config.apiUrl.replace(/\/+$/, '');
  fetch(`${base}/conversation/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, content: content.slice(0, 2000), source: 'firefox' }),
  }).catch(() => {});
}

async function handleWebFetch(port, msg) {
  const { requestId, url } = msg;
  try {
    const base = config.apiUrl.replace(/\/+$/, '');
    const res = await fetch(`${base}/web/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();
    port.postMessage({ type: 'WEB_FETCH_RESULT', requestId, data });
  } catch (err) {
    port.postMessage({ type: 'WEB_FETCH_RESULT', requestId, data: { error: err.message } });
  }
}

async function handleWebSearch(port, msg) {
  const { requestId, query } = msg;
  try {
    const base = config.apiUrl.replace(/\/+$/, '');
    const res = await fetch(`${base}/web/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, num_results: 5 }),
    });
    const data = await res.json();
    port.postMessage({ type: 'WEB_SEARCH_RESULT', requestId, data });
  } catch (err) {
    port.postMessage({ type: 'WEB_SEARCH_RESULT', requestId, data: { error: err.message } });
  }
}

async function handleConvSave(port, msg) {
  const result = await saveConversation(msg.id, msg.title, msg.messages || []);
  port.postMessage({ type: 'CONV_SAVED', ...result });
}

async function handleConvList(port) {
  const conversations = await loadConversations();
  port.postMessage({ type: 'CONV_LIST_RESULT', conversations });
}

async function handleConvLoad(port, msg) {
  const result = await loadConversation(msg.id);
  port.postMessage({ type: 'CONV_LOADED', ...result });
}

async function handleConvDelete(port, msg) {
  const result = await deleteConversation(msg.id);
  port.postMessage({ type: 'CONV_DELETED', id: msg.id, ...result });
}

async function handleChat(port, msg) {
  const { requestId, history, reasonMode } = msg;

  const systemPrompt = {
    role: 'system',
    content: 'You are Talos, a local-first AI assistant. Be concise and helpful. Format code with fenced code blocks.',
  };

  const payload = {
    model: config.model,
    messages: [systemPrompt, ...history],
    temperature: config.temperature,
    max_tokens: config.maxTokens,
    stream: true,
  };

  if (reasonMode) {
    payload.reason_mode = true;
  }

  const body = JSON.stringify(payload);

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

    // Capture routing headers
    const modelUsed = res.headers.get('x-model-used') || '';
    const modelId = res.headers.get('x-model-id') || '';
    const routingReason = res.headers.get('x-routing-reason') || '';

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let tokenCount = 0;
    let fullResponse = '';
    const streamStart = Date.now();
    let inReasoning = false;

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
        if (data === '[DONE]') {
          // Close any open think block
          if (inReasoning) {
            const closeTag = '</think>\n';
            fullResponse += closeTag;
            port.postMessage({ type: 'STREAM_TOKEN', requestId, token: closeTag });
            inReasoning = false;
          }
          continue;
        }

        try {
          const parsed = JSON.parse(data);
          const delta = parsed.choices?.[0]?.delta;
          const reasoning = delta?.reasoning_content;
          const content = delta?.content;

          // Handle reasoning_content (llama-server native thinking)
          if (reasoning) {
            let token = reasoning;
            if (!inReasoning) {
              inReasoning = true;
              token = '<think>' + reasoning;
            }
            tokenCount++;
            fullResponse += token;
            port.postMessage({ type: 'STREAM_TOKEN', requestId, token });
          }

          // Handle regular content
          if (content) {
            let token = content;
            if (inReasoning) {
              inReasoning = false;
              token = '</think>\n' + content;
            }
            tokenCount++;
            fullResponse += token;
            port.postMessage({ type: 'STREAM_TOKEN', requestId, token });
          }
        } catch {
          // skip malformed SSE lines
        }
      }
    }

    const elapsed = (Date.now() - streamStart) / 1000;
    const tokPerSec = elapsed > 0 ? Math.round(tokenCount / elapsed) : 0;
    port.postMessage({
      type: 'STREAM_END',
      requestId,
      tokPerSec,
      modelUsed,
      modelId,
      routingReason,
    });

    // Log to conversation bridge
    const lastUserMsg = history.filter((m) => m.role === 'user').pop();
    if (lastUserMsg) logConversation('user', lastUserMsg.content);
    if (fullResponse) logConversation('assistant', fullResponse);
  } catch (err) {
    port.postMessage({
      type: 'STREAM_ERROR',
      requestId,
      error: err.message || 'Connection failed',
    });
  }
}
