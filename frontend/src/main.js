import { connectLedgerSocket } from "./websocketClient.js";
import { applyBlockPayload, mountRenderer, setVisual } from "./renderer.js";
import { appendLedgerBlock, renderLedger } from "./ui.js";

const canvasRoot = document.getElementById("canvas-root");
const ledgerEl = document.getElementById("ledger");
const ledgerCountEl = document.getElementById("ledger-count");
const simulateBtn = document.getElementById("simulate");
const refreshBtn = document.getElementById("refresh-chain");
const connStatusEl = document.getElementById("conn-status");
const visualLabelEl = document.getElementById("visual-label");

mountRenderer(canvasRoot);

function setLedgerCount(n) {
  if (!ledgerCountEl) return;
  const label = n === 1 ? "1 entry" : `${n} entries`;
  ledgerCountEl.textContent = label;
}

function updateVisualCaption(payload) {
  if (!visualLabelEl) return;
  const label = payload?.visual?.label;
  visualLabelEl.textContent =
    typeof label === "string" && label.trim() ? label.trim() : "Live visual";
}

function setConnectionUi(state) {
  if (!connStatusEl) return;
  connStatusEl.dataset.state = state;
  const label = connStatusEl.querySelector(".conn-status__label");
  if (!label) return;
  const messages = {
    connecting: "Connecting…",
    open: "Live stream",
    closed: "Reconnecting…",
    error: "Connection issue",
  };
  label.textContent = messages[state] || state;
}

function applyChainBlocks(blocks) {
  const list = Array.isArray(blocks) ? blocks : [];
  renderLedger(ledgerEl, list);
  setLedgerCount(list.length);
  const last = list[list.length - 1];
  if (last) {
    applyBlockPayload(last);
    updateVisualCaption(last);
  }
}

connectLedgerSocket({
  onMessage: (msg) => {
    if (msg.type === "chain_snapshot" && Array.isArray(msg.blocks)) {
      applyChainBlocks(msg.blocks);
    }
    if (msg.type === "block" && msg.payload) {
      applyBlockPayload(msg.payload);
      updateVisualCaption(msg.payload);
      const n = appendLedgerBlock(ledgerEl, msg.payload);
      if (n > 0) setLedgerCount(n);
    }
  },
  onConnectionChange: setConnectionUi,
});

simulateBtn?.addEventListener("click", async () => {
  simulateBtn.disabled = true;
  try {
    await fetch("/simulate-once");
    const chain = await fetch("/chain").then((r) => r.json());
    applyChainBlocks(chain.blocks || []);
  } finally {
    simulateBtn.disabled = false;
  }
});

refreshBtn?.addEventListener("click", async () => {
  const res = await fetch("/chain");
  const data = await res.json();
  applyChainBlocks(data.blocks || []);
});

setVisual({ label: "Waiting for events…" });
if (visualLabelEl) visualLabelEl.textContent = "Waiting for events…";

fetch("/chain")
  .then((r) => (r.ok ? r.json() : null))
  .then((data) => {
    if (data && Array.isArray(data.blocks)) applyChainBlocks(data.blocks);
  })
  .catch(() => {});
