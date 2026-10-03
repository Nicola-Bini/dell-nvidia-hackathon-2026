import { defineConfig } from "vite";

// Second build pass: dist/embed.js, one classic script with no imports, next to the widget.
export default defineConfig({
  build: {
    emptyOutDir: false,
    outDir: "dist",
    lib: {
      entry: "src/embed/entry.ts",
      formats: ["iife"],
      name: "cacEmbed",
      fileName: () => "embed.js",
    },
  },
});
