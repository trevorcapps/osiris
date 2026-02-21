const WS_URL = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws`;

let ws = null;
let listeners = [];
let reconnectTimer = null;
let statusListeners = [];

function emitStatus(state) {
  statusListeners.forEach(fn => fn(state));
}

export function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  try {
    ws = new WebSocket(WS_URL);
    ws.binaryType = 'arraybuffer';
    emitStatus('connecting');
    ws.onopen = () => emitStatus('open');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(event.data));
        listeners.forEach(fn => fn(data));
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };
    ws.onclose = () => {
      emitStatus('closed');
      reconnectTimer = setTimeout(connect, 5000);
    };
    ws.onerror = () => {
      emitStatus('error');
      ws.close();
    };
  } catch (e) {
    console.error('WS connect error:', e);
  }
}

export function subscribe(fn) {
  listeners.push(fn);
  return () => { listeners = listeners.filter(f => f !== fn); };
}

export function disconnect() {
  clearTimeout(reconnectTimer);
  if (ws) ws.close();
}

export function subscribeStatus(fn) {
  statusListeners.push(fn);
  return () => { statusListeners = statusListeners.filter(f => f !== fn); };
}
