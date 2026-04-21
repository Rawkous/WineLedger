/**
 * Ledger list — readable cards aligned with supply-chain event types.
 */

const EVENT_BADGE_CLASS = {
  HARVEST: "event-badge--harvest",
  FERMENTATION: "event-badge--fermentation",
  BARREL_AGING: "event-badge--barrel",
  BOTTLING: "event-badge--bottling",
  TRANSPORT: "event-badge--transport",
  RETAIL: "event-badge--retail",
};

function badgeClassForEventType(eventType) {
  if (!eventType) return "event-badge--default";
  return EVENT_BADGE_CLASS[eventType] || "event-badge--default";
}

function formatWhen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatMetaLine(b) {
  const meta = b.event?.metadata || {};
  const parts = [];
  if (meta.region_code) parts.push(String(meta.region_code));
  if (meta.route_km != null && !Number.isNaN(Number(meta.route_km))) {
    parts.push(`${Number(meta.route_km).toFixed(1)} km route`);
  }
  return parts.length ? parts.join(" · ") : "";
}

/**
 * @param {HTMLElement | null} el
 * @param {unknown[]} blocks
 */
export function renderLedger(el, blocks) {
  if (!el) return;
  el.replaceChildren();

  if (!Array.isArray(blocks) || blocks.length === 0) {
    const empty = document.createElement("p");
    empty.className = "ledger-empty";
    empty.textContent =
      "No blocks yet. Click “Simulate supply chain” (with the API running) or wait for live WebSocket events.";
    el.appendChild(empty);
    return;
  }

  for (const item of blocks) {
    const row = createLedgerCard(item);
    if (row) el.appendChild(row);
  }
  el.scrollTop = el.scrollHeight;
}

/**
 * Append one block (e.g. live `block` WebSocket messages). Deduplicates by block index.
 * @param {HTMLElement | null} el
 * @param {unknown} payload
 * @returns {number} current number of ledger cards
 */
export function appendLedgerBlock(el, payload) {
  if (!el || !payload || !payload.block) return el?.querySelectorAll(".ledger-card").length ?? 0;
  const idx = payload.block.index;
  const existing = el.querySelector(`[data-block-index="${idx}"]`);
  if (existing) return el.querySelectorAll(".ledger-card").length;

  const empty = el.querySelector(".ledger-empty");
  empty?.remove();

  const row = createLedgerCard(payload);
  if (row) {
    row.dataset.blockIndex = String(idx);
    el.appendChild(row);
    el.scrollTop = el.scrollHeight;
  }
  return el.querySelectorAll(".ledger-card").length;
}

function createLedgerCard(payload) {
  if (!payload || !payload.block) return null;
  const b = payload.block;
  const card = document.createElement("article");
  card.className = "ledger-card";
  card.dataset.blockIndex = String(b.index);

  const top = document.createElement("div");
  top.className = "ledger-card__top";

  const index = document.createElement("span");
  index.className = "ledger-card__index";
  index.textContent = `Block ${b.index}`;

  const badge = document.createElement("span");
  badge.className = `event-badge ${badgeClassForEventType(b.event?.event_type)}`;
  badge.textContent = (b.event?.event_type || "EVENT").replace(/_/g, " ");

  top.append(index, badge);
  card.appendChild(top);

  const when = formatWhen(b.timestamp);
  const metaLine = formatMetaLine(b);
  const meta = document.createElement("p");
  meta.className = "ledger-card__meta";
  const metaBits = [when, metaLine].filter(Boolean);
  meta.textContent = metaBits.join(" · ") || "On-chain event";

  const hash = document.createElement("p");
  hash.className = "ledger-card__hash";
  const h = b.hash || "";
  hash.textContent = h ? `${h.slice(0, 18)}…` : "—";

  card.append(meta, hash);
  return card;
}
