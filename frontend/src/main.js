import { connectLedgerSocket } from "./websocketClient.js";
import { applyBlockPayload, mountRenderer, setVisual } from "./renderer.js";
import { appendLedgerBlock, renderLedger } from "./ui.js";

const THEME_KEY = "wineledger-theme";
const LANG_KEY = "wineledger-lang";
const SIM_PACE_KEY = "wineledger-sim-pace-ms";

const TRACKED_STAGES = [
  "HARVEST",
  "FERMENTATION",
  "BARREL_AGING",
  "BOTTLING",
  "TRANSPORT",
  "RETAIL",
];

const canvasRoot = document.getElementById("canvas-root");
const ledgerEl = document.getElementById("ledger");
const ledgerCountEl = document.getElementById("ledger-count");
const simulateBtn = document.getElementById("simulate");
const refreshBtn = document.getElementById("refresh-chain");
const connStatusEl = document.getElementById("conn-status");
const visualLabelEl = document.getElementById("visual-label");
const themeColorMeta = document.getElementById("theme-color-meta");
const paceSlider = document.getElementById("simulate-pace");
const paceValueEl = document.getElementById("simulate-pace-value");

const menuToggle = document.getElementById("menu-toggle");
const menuPanel = document.getElementById("top-menu-panel");
const langSelect = document.getElementById("lang-select");
const themeButtons = document.querySelectorAll(".theme-toggle__btn");
const siteHeader = document.querySelector(".site-header");

const heroStatBlocksEl = document.querySelector('[data-stat="blocks"]');
const heroStatStreamEl = document.querySelector('[data-stat="stream"]');

const stageCountEls = new Map();
TRACKED_STAGES.forEach((stage) => {
  const el = document.querySelector(`[data-stage-count="${stage}"]`);
  if (el) stageCountEls.set(stage, el);
});

mountRenderer(canvasRoot);

function setTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* ignore */
  }
  if (themeColorMeta) {
    themeColorMeta.setAttribute("content", next === "light" ? "#f5efe2" : "#140c08");
  }
  themeButtons.forEach((btn) => {
    const pressed = btn.getAttribute("data-theme-choice") === next;
    btn.setAttribute("aria-pressed", pressed ? "true" : "false");
  });
}

function loadStoredTheme() {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
      return;
    }
  } catch {
    /* ignore */
  }
  setTheme("dark");
}

function closeMenu() {
  if (!menuPanel || !menuToggle) return;
  menuPanel.hidden = true;
  menuToggle.setAttribute("aria-expanded", "false");
}

function openMenu() {
  if (!menuPanel || !menuToggle) return;
  menuPanel.hidden = false;
  menuToggle.setAttribute("aria-expanded", "true");
  const first = menuPanel.querySelector(".top-menu__item");
  first?.focus();
}

function toggleMenu() {
  if (!menuPanel?.hidden) closeMenu();
  else openMenu();
}

loadStoredTheme();

menuToggle?.addEventListener("click", (e) => {
  e.stopPropagation();
  toggleMenu();
});

document.addEventListener("click", () => {
  closeMenu();
});

menuPanel?.addEventListener("click", (e) => {
  e.stopPropagation();
});

document.querySelectorAll("[data-open-dialog]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const id = btn.getAttribute("data-open-dialog");
    const dlg = id ? document.getElementById(id) : null;
    if (dlg && typeof dlg.showModal === "function") {
      closeMenu();
      dlg.showModal();
    }
  });
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && menuPanel && !menuPanel.hidden) {
    closeMenu();
    menuToggle?.focus();
  }
});

try {
  const lang = localStorage.getItem(LANG_KEY);
  if (lang && langSelect) {
    const opt = langSelect.querySelector(`option[value="${lang}"]`);
    if (opt && !opt.disabled) {
      langSelect.value = lang;
      document.documentElement.lang = lang;
    }
  }
} catch {
  /* ignore */
}

langSelect?.addEventListener("change", () => {
  const v = langSelect.value;
  document.documentElement.lang = v;
  try {
    localStorage.setItem(LANG_KEY, v);
  } catch {
    /* ignore */
  }
});

themeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const choice = btn.getAttribute("data-theme-choice");
    if (choice === "light" || choice === "dark") setTheme(choice);
  });
});

/* ---------- Sticky header elevation on scroll ---------- */

function updateHeaderElevation() {
  if (!siteHeader) return;
  const elevated = window.scrollY > 8;
  siteHeader.dataset.elevated = elevated ? "true" : "false";
}

updateHeaderElevation();
window.addEventListener("scroll", updateHeaderElevation, { passive: true });

/* ---------- Active primary-nav section ---------- */

const navLinks = Array.from(document.querySelectorAll(".primary-nav__link"));
const sectionLinkMap = new Map();
navLinks.forEach((link) => {
  const href = link.getAttribute("href") || "";
  if (href.startsWith("#")) {
    const id = href.slice(1);
    const target = id ? document.getElementById(id) : null;
    if (target) sectionLinkMap.set(target, link);
  }
});

if (sectionLinkMap.size > 0 && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries
        .filter((e) => e.isIntersecting)
        .forEach((entry) => {
          navLinks.forEach((l) => l.removeAttribute("aria-current"));
          const link = sectionLinkMap.get(entry.target);
          if (link) link.setAttribute("aria-current", "true");
        });
    },
    { rootMargin: "-40% 0px -55% 0px", threshold: 0 },
  );
  sectionLinkMap.forEach((_, target) => observer.observe(target));
}

/* ---------- Ledger + stage stats ---------- */

function setLedgerCount(n) {
  if (ledgerCountEl) {
    ledgerCountEl.textContent = n === 1 ? "1 entry" : `${n} entries`;
  }
  if (heroStatBlocksEl) {
    heroStatBlocksEl.textContent = String(n);
  }
}

function flashStageCount(el) {
  if (!el) return;
  el.dataset.justChanged = "true";
  window.setTimeout(() => {
    if (el.dataset.justChanged === "true") delete el.dataset.justChanged;
  }, 700);
}

function setStageCount(stage, count) {
  const el = stageCountEls.get(stage);
  if (!el) return;
  const previous = parseInt(el.textContent || "0", 10) || 0;
  el.textContent = String(count);
  el.dataset.active = count > 0 ? "true" : "false";
  if (count !== previous) flashStageCount(el);
}

function recountStagesFromBlocks(blocks) {
  const counts = new Map(TRACKED_STAGES.map((s) => [s, 0]));
  for (const item of blocks) {
    const t = item?.block?.event?.event_type;
    if (typeof t === "string" && counts.has(t)) {
      counts.set(t, (counts.get(t) || 0) + 1);
    }
  }
  TRACKED_STAGES.forEach((s) => setStageCount(s, counts.get(s) || 0));
}

function bumpStageFromBlock(payload) {
  const t = payload?.block?.event?.event_type;
  if (typeof t !== "string" || !stageCountEls.has(t)) return;
  const el = stageCountEls.get(t);
  if (!el) return;
  const current = parseInt(el.textContent || "0", 10) || 0;
  setStageCount(t, current + 1);
}

function updateVisualCaption(payload) {
  if (!visualLabelEl) return;
  const label = payload?.visual?.label;
  visualLabelEl.textContent =
    typeof label === "string" && label.trim() ? label.trim() : "Live visual";
}

function setConnectionUi(state) {
  if (connStatusEl) {
    connStatusEl.dataset.state = state;
    const label = connStatusEl.querySelector(".conn-status__label");
    if (label) {
      const messages = {
        connecting: "Connecting…",
        open: "Live stream",
        closed: "Reconnecting…",
        error: "Connection issue",
      };
      label.textContent = messages[state] || state;
    }
  }
  if (heroStatStreamEl) {
    const messages = {
      connecting: "Connecting",
      open: "Live",
      closed: "Reconnecting",
      error: "Issue",
    };
    heroStatStreamEl.textContent = messages[state] || state;
  }
}

function applyChainBlocks(blocks) {
  const list = Array.isArray(blocks) ? blocks : [];
  renderLedger(ledgerEl, list);
  setLedgerCount(list.length);
  recountStagesFromBlocks(list);
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
      bumpStageFromBlock(msg.payload);
    }
  },
  onConnectionChange: setConnectionUi,
});

/* ---------- Sim-pace control ---------- */

function formatSimPace(ms) {
  if (ms <= 0) return "Off";
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  const t = s >= 10 ? s.toFixed(0) : s.toFixed(1).replace(/\.0$/, "");
  return `${t} s`;
}

function clampPaceSlider() {
  if (!paceSlider) return 0;
  const max = parseInt(paceSlider.getAttribute("max") || "10000", 10);
  let v = parseInt(paceSlider.value, 10);
  if (Number.isNaN(v)) v = 0;
  v = Math.max(0, Math.min(max, v));
  paceSlider.value = String(v);
  return v;
}

function updatePaceLabel() {
  if (!paceValueEl || !paceSlider) return;
  paceValueEl.textContent = formatSimPace(clampPaceSlider());
}

function loadStoredSimPace() {
  try {
    const raw = localStorage.getItem(SIM_PACE_KEY);
    if (raw == null || !paceSlider) return;
    const n = parseInt(raw, 10);
    if (Number.isNaN(n)) return;
    const max = parseInt(paceSlider.getAttribute("max") || "10000", 10);
    paceSlider.value = String(Math.max(0, Math.min(max, n)));
  } catch {
    /* ignore */
  }
  updatePaceLabel();
}

loadStoredSimPace();

paceSlider?.addEventListener("input", () => {
  updatePaceLabel();
  try {
    localStorage.setItem(SIM_PACE_KEY, paceSlider.value);
  } catch {
    /* ignore */
  }
});

simulateBtn?.addEventListener("click", async () => {
  simulateBtn.disabled = true;
  try {
    const paceMs = clampPaceSlider();
    const q = paceMs > 0 ? `?pace_ms=${encodeURIComponent(String(paceMs))}` : "";
    await fetch(`/simulate-once${q}`);
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
