/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const repoRoot = fileURLToPath(new URL("../..", import.meta.url));

// base "./" so the same dist/ works under the Serve API's /widget/ and from a file.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { fs: { allow: [repoRoot] } },
  test: { environment: "jsdom", include: ["test/**/*.test.{ts,tsx}"] },
});
