import { connectLedgerSocket } from "./websocketClient.js";
import { applyBlockPayload, mountRenderer, setVisual } from "./renderer.js";
import { renderLedger } from "./ui.js";

const canvasRoot = document.getElementById("canvas-root");
const ledgerEl = document.getElementById("ledger");
const simulateBtn = document.getElementById("simulate");
const refreshBtn = document.getElementById("refresh-chain");

mountRenderer(canvasRoot);

connectLedgerSocket((msg) => {
  if (msg.type === "chain_snapshot" && Array.isArray(msg.blocks)) {
    renderLedger(ledgerEl, msg.blocks);
    const last = msg.blocks[msg.blocks.length - 1];
    if (last) applyBlockPayload(last);
  }
  if (msg.type === "block" && msg.payload) {
    applyBlockPayload(msg.payload);
  }
});

simulateBtn?.addEventListener("click", async () => {
  simulateBtn.disabled = true;
  try {
    await fetch("/simulate-once");
    const chain = await fetch("/chain").then((r) => r.json());
    renderLedger(ledgerEl, chain.blocks || []);
    const last = chain.blocks?.[chain.blocks.length - 1];
    if (last) applyBlockPayload(last);
  } finally {
    simulateBtn.disabled = false;
  }
});

refreshBtn?.addEventListener("click", async () => {
  const res = await fetch("/chain");
  const data = await res.json();
  renderLedger(ledgerEl, data.blocks || []);
  const last = data.blocks?.[data.blocks.length - 1];
  if (last) applyBlockPayload(last);
});

setVisual({ label: "Waiting for events…" });
