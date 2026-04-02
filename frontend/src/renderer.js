/**
 * p5.js instance-mode sketch driven by `visual` payloads from the mapping layer.
 */

import p5 from "p5";

const defaults = {
  hue: 200,
  saturation: 0.75,
  brightness: 0.7,
  motion: 0.45,
  particle_burst: 80,
  label: "WineLedger",
};

let currentVisual = { ...defaults };

export function setVisual(visual) {
  currentVisual = { ...currentVisual, ...visual };
}

export function mountRenderer(container) {
  const sketch = (p) => {
    p.setup = () => {
      const w = Math.min(880, container.clientWidth || 800);
      p.createCanvas(w, 420);
      p.colorMode(p.HSB, 360, 1, 1);
      p.noStroke();
    };

    p.windowResized = () => {
      const w = Math.min(880, container.clientWidth || 800);
      p.resizeCanvas(w, 420);
    };

    p.draw = () => {
      const v = currentVisual;
      const bgHue = (v.hue + p.frameCount * 0.03) % 360;
      p.background(bgHue, 0.12, 0.08);

      p.fill(v.hue, v.saturation * 0.9, v.brightness);
      p.textAlign(p.CENTER, p.CENTER);
      p.textSize(14);
      p.text(v.label || "WineLedger", p.width / 2, 24);

      const n = Math.min(220, Math.max(8, v.particle_burst | 0));
      const t = p.frameCount * 0.012;
      for (let i = 0; i < n; i += 1) {
        const a = (i / n) * p.TWO_PI + t * (0.5 + v.motion);
        const wave = p.sin(t + i * 0.1) * 0.5 + 0.5;
        const r = 40 + 140 * v.motion + 60 * wave;
        const x = p.width / 2 + p.cos(a) * r;
        const y = p.height / 2 + p.sin(a) * r * 0.85;
        const sz = 3 + v.motion * 5 + (i % 7) * 0.1;
        p.fill((v.hue + i * 0.4) % 360, v.saturation, v.brightness);
        p.circle(x, y, sz);
      }
    };
  };

  return new p5(sketch, container);
}

export function applyBlockPayload(payload) {
  if (payload && payload.visual) {
    setVisual(payload.visual);
  }
}
