// A fake Serve API that answers with the golden fixtures, and a JSON-RPC client for /mcp.
import { readFileSync } from "node:fs";
import { createServer, type IncomingMessage, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { fileURLToPath } from "node:url";

const FIXTURES = fileURLToPath(new URL("../../../fixtures/surfaces/", import.meta.url));

export const fixture = (name: string): unknown =>
  JSON.parse(readFileSync(`${FIXTURES}${name}.json`, "utf8"));

export interface Seen {
  method: string;
  path: string;
  channel: string | undefined;
  body: any;
}

export interface FakeServe {
  url: string;
  seen: Seen[];
  action: { status: number; body: unknown };
  close(): Promise<void>;
}

const BOOTSTRAP = {
  business: { name: "The Kenmore", tagline: "Craft beer and craft ingredients." },
  theme: {},
  nav: [{ label: "Menu", preset: "menu" }, { label: "Book a table", preset: "booking" }],
  chips: [],
};

async function readBody(req: IncomingMessage): Promise<any> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : undefined;
}

function route(fake: FakeServe, seen: Seen): { status: number; body: unknown } {
  if (seen.path === "/v1/bootstrap") return { status: 200, body: BOOTSTRAP };
  if (seen.path === "/healthz") return { status: 200, body: { status: "ok" } };
  if (seen.path === "/v1/intent") return { status: 200, body: fixture("menu_vegetarian") };
  if (seen.path === "/v1/view/menu") return { status: 200, body: fixture("preset_menu") };
  if (seen.path === "/v1/view/hours") return { status: 200, body: fixture("hours_saturday") };
  if (seen.path === "/v1/action") return fake.action;
  return { status: 404, body: { detail: "unknown preset" } };
}

export async function startFakeServe(): Promise<FakeServe> {
  const fake: FakeServe = {
    url: "",
    seen: [],
    action: { status: 200, body: { ok: true, lead_id: "lead-123", surface: fixture("gap") } },
    close: () => new Promise((done) => server.close(() => done())),
  };
  const server: Server = createServer(async (req, res) => {
    const seen: Seen = {
      method: req.method ?? "",
      path: req.url ?? "",
      channel: req.headers["x-cac-channel"] as string | undefined,
      body: await readBody(req),
    };
    fake.seen.push(seen);
    const { status, body } = route(fake, seen);
    res.writeHead(status, { "content-type": "application/json" }).end(JSON.stringify(body));
  });
  await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
  fake.url = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  return fake;
}

let nextId = 1;

// The same bare call scripts/canary.py makes: no initialize, no session.
export async function rpc(base: string, method: string, params: unknown = {}): Promise<any> {
  const response = await fetch(`${base}/mcp`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json, text/event-stream" },
    body: JSON.stringify({ jsonrpc: "2.0", id: nextId++, method, params }),
  });
  const message = await response.json();
  if (message.error) throw new Error(`rpc ${method}: ${JSON.stringify(message.error)}`);
  return message.result;
}

export const callTool = (base: string, name: string, args: unknown = {}): Promise<any> =>
  rpc(base, "tools/call", { name, arguments: args });
