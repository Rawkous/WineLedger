/**
 * Browser WebSocket client — JSON messages from FastAPI `/ws`.
 * Dev: Vite proxies `/ws` to the backend (vite.config.js).
 */

const RECONNECT_MS = 3200;

/**
 * @param {{
 *   onMessage: (msg: unknown) => void;
 *   onConnectionChange?: (state: "connecting" | "open" | "closed" | "error") => void;
 *   onError?: (err: Error) => void;
 * }} handlers
 * @returns {() => void} cleanup — stops reconnection and closes the socket
 */
export function connectLedgerSocket(handlers) {
  const { onMessage, onConnectionChange, onError } = handlers;
  let ws = null;
  let reconnectTimer = null;
  let stopped = false;

  function connect() {
    if (stopped) return;
    onConnectionChange?.("connecting");
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${window.location.host}/ws`;

    try {
      ws = new WebSocket(url);
    } catch (e) {
      onConnectionChange?.("error");
      if (onError) onError(e instanceof Error ? e : new Error(String(e)));
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      onConnectionChange?.("open");
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        onMessage(msg);
      } catch (e) {
        if (onError) onError(e instanceof Error ? e : new Error(String(e)));
      }
    };

    ws.onerror = () => {
      onConnectionChange?.("error");
      if (onError) onError(new Error("WebSocket error"));
    };

    ws.onclose = () => {
      onConnectionChange?.("closed");
      scheduleReconnect();
    };
  }

  function scheduleReconnect() {
    if (stopped) return;
    clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(connect, RECONNECT_MS);
  }

  connect();

  return function disconnect() {
    stopped = true;
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
    if (ws) {
      ws.onclose = null;
      ws.close();
      ws = null;
    }
  };
}
