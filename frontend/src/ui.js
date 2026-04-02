/**
 * Minimal ledger list for recent blocks.
 */

export function renderLedger(el, blocks) {
  if (!el) return;
  el.replaceChildren();
  for (const item of blocks) {
    appendBlockRowSimple(el, item);
  }
}

export function appendBlockRowSimple(el, payload) {
  if (!el || !payload || !payload.block) return;
  const row = document.createElement("div");
  row.className = "ledger-row";
  const b = payload.block;
  const meta = b.event.metadata || {};
  const region = meta.region_code ? ` · ${meta.region_code}` : "";
  const route =
    meta.route_km != null ? ` · ${Number(meta.route_km).toFixed(2)} km` : "";
  row.textContent = `#${b.index} ${b.event.event_type}${region}${route} · ${b.hash.slice(0, 14)}…`;
  el.appendChild(row);
  el.scrollTop = el.scrollHeight;
}
