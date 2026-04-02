/**
 * Browser WebSocket client — expects JSON messages from the FastAPI `/ws` endpoint.
 * In dev, Vite proxies `/ws` to the backend (see vite.config.js).
 */

export function connectLedgerSocket(onMessage, onError) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${window.location.host}/ws`;
  const ws = new WebSocket(url);
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      onMessage(msg);
    } catch (e) {
      if (onError) onError(e);
    }
  };
  ws.onerror = () => {
    if (onError) onError(new Error("WebSocket error"));
  };
  return ws;
}
