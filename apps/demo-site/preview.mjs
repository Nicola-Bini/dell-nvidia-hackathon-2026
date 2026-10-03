// Local stand-in for the box, for looking at the demo before the Serve API is running:
// /site/ from apps/demo-site/dist, /widget/ and /embed.js from apps/widget/dist, and a
// /healthz that answers 200 (or 503 with FAKE_BOX_DOWN=1, to see the no-op path).
// Build the widget with VITE_SERVE_URL=mock first so it answers from the fixtures.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const roots = {
  "/site/": resolve(here, "dist"),
  "/widget/": resolve(here, "../widget/dist"),
};
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png" };
const port = Number(process.env.PORT ?? 8099);

function send(res, file) {
  res.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream" });
  createReadStream(file).pipe(res);
}

function resolveFile(urlPath) {
  if (urlPath === "/embed.js") return join(roots["/widget/"], "embed.js");
  for (const [prefix, dir] of Object.entries(roots)) {
    if (!urlPath.startsWith(prefix)) continue;
    const file = normalize(join(dir, urlPath.slice(prefix.length) || "index.html"));
    if (!file.startsWith(dir)) return null;
    if (existsSync(file) && statSync(file).isDirectory()) return join(file, "index.html");
    return file;
  }
  return null;
}

createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (path === "/healthz") {
    const down = process.env.FAKE_BOX_DOWN === "1";
    res.writeHead(down ? 503 : 200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ ok: !down, fake: true }));
  }
  if (path === "/") {
    res.writeHead(302, { Location: "/site/" });
    return res.end();
  }
  const file = resolveFile(path);
  if (file && existsSync(file)) return send(res, file);
  res.writeHead(404).end("not found");
}).listen(port, "127.0.0.1", () => console.log(`fake box on http://127.0.0.1:${port}/site/`));
