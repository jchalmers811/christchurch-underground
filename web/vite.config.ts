import { defineConfig } from "vite";

// Relative base so the build works under any path (GitHub Pages serves it at /<repo>/3d/).
export default defineConfig({
  base: "./",
  build: { chunkSizeWarningLimit: 1500 },
});
