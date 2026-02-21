let port = null;
let callbacks = {
  onToken: null,
  onStreamStart: null,
  onStreamEnd: null,
  onStreamError: null,
  onHealth: null,
  onConfigLoaded: null,
};

export function setCallbacks(cbs) {
  Object.assign(callbacks, cbs);
}

export function connect() {
  port = browser.runtime.connect({ name: 'talos-sidebar' });

  port.onMessage.addListener((msg) => {
    switch (msg.type) {
      case 'STREAM_START':
        callbacks.onStreamStart?.(msg.requestId);
        break;
      case 'STREAM_TOKEN':
        callbacks.onToken?.(msg.requestId, msg.token);
        break;
      case 'STREAM_END':
        callbacks.onStreamEnd?.(msg.requestId, msg.tokPerSec);
        break;
      case 'STREAM_ERROR':
        callbacks.onStreamError?.(msg.requestId, msg.error);
        break;
      case 'HEALTH_RESULT':
        callbacks.onHealth?.(msg.ok, msg.latency);
        break;
      case 'CONFIG_LOADED':
        callbacks.onConfigLoaded?.(msg.config);
        break;
    }
  });

  port.onDisconnect.addListener(() => {
    port = null;
    // Auto-reconnect after a short delay
    setTimeout(() => {
      connect();
      checkHealth();
    }, 500);
  });

  return port;
}

export function sendChat(history) {
  if (!port) connect();
  if (!port) return null;
  const requestId = crypto.randomUUID();
  port.postMessage({ type: 'CHAT', requestId, history });
  return requestId;
}

export function checkHealth() {
  if (!port) return;
  port.postMessage({ type: 'HEALTH_CHECK' });
}

export function getConfig() {
  if (!port) return;
  port.postMessage({ type: 'CONFIG_GET' });
}

export function updateConfig(config) {
  if (!port) return;
  port.postMessage({ type: 'CONFIG_UPDATE', config });
}

export function disconnect() {
  if (port) {
    port.disconnect();
    port = null;
  }
}
