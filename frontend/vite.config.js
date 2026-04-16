import { defineConfig } from "vite";

export default defineConfig({
  // hydra-synth (and some deps) expect a Node-like `global`.
  // In the browser, mapping it to globalThis avoids `ReferenceError: global is not defined`.
  define: {
    global: "globalThis",
  },
  server: {
    port: 5173,
    proxy: {
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
      "/simulate-once": "http://127.0.0.1:8000",
      "/chain": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
