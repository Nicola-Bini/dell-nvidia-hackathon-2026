// Routes: stateless Streamable HTTP at POST /mcp, plus /health for box/up.sh (SCHEMA 8.7).
import { existsSync, readFileSync } from "node:fs";

import { createMcpExpressApp } from "@modelcontextprotocol/sdk/server/express.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import type { Express, NextFunction, Request, Response } from "express";

import { ServeClient } from "./serve_client.ts";
import { buildServer } from "./tools.ts";

export interface AppOptions {
  serveBaseUrl: string;
  /** apps/widget/dist-mcp/surface.html; when missing the server runs text-only. */
  surfaceHtmlPath?: string;
  /** Public hostnames (the tunnel) allowed in the Host header, besides localhost. */
  allowedHosts: string[];
}

const LOCAL_HOSTS = ["localhost", "127.0.0.1", "[::1]"];
const NAME_TTL_MS = 60_000;
const FALLBACK_NAME = "the restaurant";

function rpcError(res: Response, status: number, message: string): void {
  res.status(status).json({ jsonrpc: "2.0", error: { code: -32000, message }, id: null });
}

/** The business name for tool descriptions, re-read from the Serve API once a minute. */
function nameSource(client: ServeClient): () => Promise<string> {
  let cached: { name: string; at: number } | undefined;
  return async () => {
    if (cached && Date.now() - cached.at < NAME_TTL_MS) return cached.name;
    try {
      cached = { name: (await client.bootstrap()).business.name, at: Date.now() };
      return cached.name;
    } catch {
      return cached?.name ?? FALLBACK_NAME;
    }
  };
}

/** Through the tunnel only /mcp exists; /health answers local callers only. */
function publicPathsOnly(req: Request, res: Response, next: NextFunction): void {
  const hostname = new URL(`http://${req.headers.host}`).hostname;
  if (req.path === "/mcp" || LOCAL_HOSTS.includes(hostname)) next();
  else res.status(404).end();
}

export function createApp(options: AppOptions): Express {
  const client = new ServeClient(options.serveBaseUrl);
  const businessName = nameSource(client);
  const path = options.surfaceHtmlPath;
  const readSurface = () => (path && existsSync(path) ? readFileSync(path, "utf8") : undefined);
  const app = createMcpExpressApp({ allowedHosts: [...LOCAL_HOSTS, ...options.allowedHosts] });
  app.use(publicPathsOnly);

  app.get("/health", async (_req, res) => {
    const serve = (await client.healthy()) ? "ok" : "down";
    res.json({ status: "ok", serve, element: readSurface() !== undefined });
  });

  app.post("/mcp", async (req, res) => {
    const context = { client, businessName: await businessName(), surfaceHtml: readSurface() };
    const server = buildServer(context);
    // No sessions; JSON responses so a Cloudflare Quick Tunnel does not buffer a stream.
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, enableJsonResponse: true,
    });
    res.on("close", () => {
      void transport.close();
      void server.close();
    });
    try {
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch {
      if (!res.headersSent) rpcError(res, 500, "Internal server error");
    }
  });

  app.all("/mcp", (_req, res) => rpcError(res.set("Allow", "POST"), 405, "Method not allowed"));
  return app;
}
