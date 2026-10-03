// Entry point. Environment: SERVE_BASE_URL (loopback only), MCP_PORT (8090), MCP_HOST
// (127.0.0.1: the tunnel client runs on this machine), MCP_ALLOWED_HOSTS (the tunnel
// hostname, comma-separated), MCP_SURFACE_HTML (the widget's single-file build).
import { fileURLToPath } from "node:url";

import { createApp } from "./app.ts";

const LOOPBACK = ["127.0.0.1", "localhost", "[::1]"];
const DEFAULT_SURFACE = fileURLToPath(
  new URL("../../../apps/widget/dist-mcp/surface.html", import.meta.url));

const serveBaseUrl = (process.env.SERVE_BASE_URL ?? "http://127.0.0.1:8080").replace(/\/+$/, "");
if (!LOOPBACK.includes(new URL(serveBaseUrl).hostname)) {
  console.error("SERVE_BASE_URL must be the Serve API on this machine (loopback). Refusing.");
  process.exit(1);
}
const port = Number(process.env.MCP_PORT ?? 8090);
const host = process.env.MCP_HOST ?? "127.0.0.1";
const allowedHosts = (process.env.MCP_ALLOWED_HOSTS ?? "")
  .split(",").map((entry) => entry.trim()).filter(Boolean);

const app = createApp({
  serveBaseUrl,
  surfaceHtmlPath: process.env.MCP_SURFACE_HTML ?? DEFAULT_SURFACE,
  allowedHosts,
});
app.listen(port, host, () => {
  const extra = allowedHosts.length ? allowedHosts.join(", ") : "none";
  console.log(`cac-mcp on http://${host}:${port}/mcp (public hosts: ${extra})`);
});
