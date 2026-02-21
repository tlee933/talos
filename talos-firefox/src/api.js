let port = null;
let callbacks = {
  onToken: null,
  onStreamStart: null,
  onStreamEnd: null,
  onStreamError: null,
  onHealth: null,
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
        callbacks.onStreamEnd?.(msg.requestId);
        break;
      case 'STREAM_ERROR':
        callbacks.onStreamError?.(msg.requestId, msg.error);
        break;
      case 'HEALTH_RESULT':
        callbacks.onHealth?.(msg.ok, msg.latency);
        break;
    }
  });

  port.onDisconnect.addListener(() => {
    callbacks.onHealth?.(false, 0);
    port = null;
  });

  return port;
}

export function sendChat(history) {
  if (!port) return null;
  const requestId = crypto.randomUUID();
  port.postMessage({ type: 'CHAT', requestId, history });
  return requestId;
}

export function checkHealth() {
  if (!port) return;
  port.postMessage({ type: 'HEALTH_CHECK' });
}

export function disconnect() {
  if (port) {
    port.disconnect();
    port = null;
  }
}
