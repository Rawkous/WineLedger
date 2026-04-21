/**
 * Hydra renderer driven by `visual` payloads from the backend mapping layer.
 *
 * The mapping payload becomes a small set of Hydra parameters (osc/noise/kaleid/etc).
 * We rebuild the Hydra chain whenever `visual` changes (events are low frequency).
 */

import Hydra from "hydra-synth";

const defaults = {
  hue: 200,
  saturation: 0.75,
  brightness: 0.7,
  motion: 0.45,
  particle_burst: 80,
  label: "WineLedger",
};

let currentVisual = { ...defaults };
let hydra = null;
let hydraCanvas = null;

function clamp01(x) {
  if (Number.isNaN(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

function hsbToRgb(h, s, v) {
  // h: [0..360), s/v: [0..1] -> r/g/b: [0..1]
  const hh = ((h % 360) + 360) % 360;
  const c = v * s;
  const x = c * (1 - Math.abs(((hh / 60) % 2) - 1));
  const m = v - c;
  let rp = 0,
    gp = 0,
    bp = 0;
  if (hh < 60) [rp, gp, bp] = [c, x, 0];
  else if (hh < 120) [rp, gp, bp] = [x, c, 0];
  else if (hh < 180) [rp, gp, bp] = [0, c, x];
  else if (hh < 240) [rp, gp, bp] = [0, x, c];
  else if (hh < 300) [rp, gp, bp] = [x, 0, c];
  else [rp, gp, bp] = [c, 0, x];
  return [rp + m, gp + m, bp + m];
}

function ensureHydra(container) {
  if (hydra && hydraCanvas) return;

  container.replaceChildren();
  hydraCanvas = document.createElement("canvas");
  hydraCanvas.className = "hydra-canvas";
  container.appendChild(hydraCanvas);

  hydra = new Hydra({
    canvas: hydraCanvas,
    detectAudio: false,
    makeGlobal: true,
    autoLoop: true,
  });

  rebuildHydraPatch();

  const syncCanvasSize = () => {
    const rect = hydraCanvas.getBoundingClientRect();
    const w = Math.max(1, Math.floor(rect.width));
    const h = Math.max(1, Math.floor(rect.height));
    if (hydraCanvas.width !== w || hydraCanvas.height !== h) {
      hydraCanvas.width = w;
      hydraCanvas.height = h;
    }
  };

  syncCanvasSize();
  const ro = new ResizeObserver(syncCanvasSize);
  ro.observe(container);
}

function rebuildHydraPatch() {
  if (!hydra) return;
  const v = currentVisual;

  const sat = clamp01(v.saturation);
  const bri = clamp01(v.brightness);
  const motion = clamp01(v.motion);
  const burst = Math.max(8, Math.min(220, v.particle_burst | 0));

  const [r, g, b] = hsbToRgb(v.hue, Math.min(1, sat * 1.1), bri);

  // Translate WineLedger → Hydra controls.
  const freq = 2 + motion * 10 + (burst / 220) * 6;
  const sync = 0.08 + motion * 0.25;
  const offset = 0.6 + (v.hue % 60) / 120;
  const k = 2 + Math.round(2 + motion * 10);
  const rot = motion * 0.8;
  const modAmt = 0.05 + motion * 0.25;
  const noiseScale = 0.8 + motion * 3.2;

  // Hydra API is global when makeGlobal=true.
  // eslint-disable-next-line no-undef
  osc(freq, sync, offset)
    // eslint-disable-next-line no-undef
    .kaleid(k)
    // eslint-disable-next-line no-undef
    .rotate(rot)
    // eslint-disable-next-line no-undef
    .modulate(noise(noiseScale, 0.12), modAmt)
    // eslint-disable-next-line no-undef
    .color(r, g, b)
    // eslint-disable-next-line no-undef
    .contrast(1.1 + motion * 0.9)
    // eslint-disable-next-line no-undef
    .saturate(0.9 + sat * 2.2)
    // eslint-disable-next-line no-undef
    .out();
}

export function setVisual(visual) {
  currentVisual = { ...currentVisual, ...visual };
  rebuildHydraPatch();
}

export function mountRenderer(container) {
  ensureHydra(container);
  return { kind: "hydra" };
}

export function applyBlockPayload(payload) {
  if (payload && payload.visual) setVisual(payload.visual);
}
