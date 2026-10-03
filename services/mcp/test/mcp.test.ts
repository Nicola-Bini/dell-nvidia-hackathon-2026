// wp7 proof: the five tools of SCHEMA 8.7 over a fake Serve API, called the way a stateless
// Streamable HTTP client (Claude's connector, scripts/canary.py) calls them.
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";

import { createApp } from "../src/app.ts";
import { callTool, fixture, rpc, startFakeServe, type FakeServe } from "./helpers.ts";

const SURFACE_URI = "ui://cac/surface.html";
const BOOKING = {
  date: "2026-10-09", time: "19:00", party_size: 4, name: "Ada", contact: "ada@example.com",
};

let fake: FakeServe;
const servers: Server[] = [];

async function listen(surfaceHtmlPath: string | undefined): Promise<string> {
  const app = createApp({ serveBaseUrl: fake.url, surfaceHtmlPath, allowedHosts: [] });
  const server = await new Promise<Server>((done) => {
    const started = app.listen(0, "127.0.0.1", () => done(started));
  });
  servers.push(server);
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}

let textOnly: string;
let withElement: string;

before(async () => {
  fake = await startFakeServe();
  const html = join(mkdtempSync(join(tmpdir(), "cac-mcp-")), "surface.html");
  writeFileSync(html, "<!doctype html><title>CAC surface</title>");
  textOnly = await listen(undefined);
  withElement = await listen(html);
});

after(async () => {
  for (const server of servers) server.close();
  await fake.close();
});

test("lists the five tools; ask_restaurant names the business", async () => {
  const { tools } = await rpc(textOnly, "tools/list");
  assert.deepEqual(
    tools.map((tool: { name: string }) => tool.name).sort(),
    ["ask_restaurant", "get_business_profile", "get_view", "request_booking",
      "request_catering_quote"],
  );
  const ask = tools.find((tool: { name: string }) => tool.name === "ask_restaurant");
  assert.match(ask.description, /^Ask The Kenmore /);
  assert.equal(ask._meta?.ui, undefined, "no element is declared when the bundle is missing");
});

test("ask_restaurant returns the views' text and the Surface, on channel mcp", async () => {
  fake.seen.length = 0;
  const result = await callTool(textOnly, "ask_restaurant", { question: "vegetarian options?" });
  const surface = fixture("menu_vegetarian") as { views: { text: string }[] };
  const expected = surface.views.map((view) => view.text).filter(Boolean).join("\n\n");
  assert.equal(result.content[0].text, expected);
  assert.deepEqual(result.structuredContent, surface);
  const intent = fake.seen.find((seen) => seen.path === "/v1/intent");
  assert.equal(intent?.channel, "mcp");
  assert.equal(intent?.body.text, "vegetarian options?");
  assert.match(intent?.body.session_id, /^mcp_[0-9a-f-]{36}$/);
});

test("get_view returns a preset Surface and refuses an unknown one", async () => {
  const menu = await callTool(textOnly, "get_view", { preset: "menu" });
  assert.deepEqual(menu.structuredContent, fixture("preset_menu"));
  const unknown = await callTool(textOnly, "get_view", { preset: "nope" });
  assert.equal(unknown.isError, true);
});

test("get_business_profile gives name, tagline, services and hours", async () => {
  const result = await callTool(textOnly, "get_business_profile");
  const text: string = result.content[0].text;
  assert.match(text, /The Kenmore/);
  assert.match(text, /Craft beer and craft ingredients\./);
  assert.match(text, /Menu, Book a table/);
  assert.match(text, /Regular hours: Sunday 10:00 AM/);
  assert.equal(result.structuredContent.name, "The Kenmore");
});

test("request_booking stores a lead through the Serve API", async () => {
  fake.seen.length = 0;
  const result = await callTool(textOnly, "request_booking", BOOKING);
  const action = fake.seen.find((seen) => seen.path === "/v1/action");
  assert.equal(action?.channel, "mcp");
  assert.equal(action?.body.name, "submit_booking_request");
  assert.deepEqual(action?.body.payload, BOOKING);
  assert.match(result.content[0].text, /request received; the restaurant will confirm/i);
  assert.match(result.content[0].text, /lead-123/);
  assert.equal(result.structuredContent.lead_id, "lead-123");
});

test("request_catering_quote stores a lead and says what happens next", async () => {
  fake.seen.length = 0;
  const quote = { date: "2026-10-20", headcount: 40, name: "Ada", contact: "ada@example.com" };
  const result = await callTool(textOnly, "request_catering_quote", quote);
  const action = fake.seen.find((seen) => seen.path === "/v1/action");
  assert.equal(action?.body.name, "submit_catering_quote");
  assert.deepEqual(action?.body.payload, quote);
  assert.match(result.content[0].text, /lead-123/);
});

test("a rejected submission comes back as field errors, not a lead", async () => {
  const stored = fake.action;
  fake.action = {
    status: 422,
    body: { ok: false, errors: [{ field: "date", message: "That date is in the past." }] },
  };
  try {
    const result = await callTool(textOnly, "request_booking", BOOKING);
    assert.equal(result.isError, true);
    assert.match(result.content[0].text, /date: That date is in the past\./);
  } finally {
    fake.action = stored;
  }
});

test("a Serve API that is down gives a plain error with no internals", async () => {
  const app = createApp({ serveBaseUrl: "http://127.0.0.1:9", allowedHosts: [] });
  const server = await new Promise<Server>((done) => {
    const started = app.listen(0, "127.0.0.1", () => done(started));
  });
  servers.push(server);
  const base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  const result = await callTool(base, "ask_restaurant", { question: "hours?" });
  assert.equal(result.isError, true);
  assert.doesNotMatch(result.content[0].text, /127\.0\.0\.1|ECONNREFUSED|fetch/);
});

test("with the widget bundle, ask_restaurant declares the element and serves it", async () => {
  const { tools } = await rpc(withElement, "tools/list");
  const byName = Object.fromEntries(tools.map((tool: { name: string }) => [tool.name, tool]));
  assert.equal(byName.ask_restaurant._meta.ui.resourceUri, SURFACE_URI);
  assert.deepEqual(byName.get_view._meta.ui.visibility, ["app"]);
  const { contents } = await rpc(withElement, "resources/read", { uri: SURFACE_URI });
  assert.equal(contents[0].mimeType, "text/html;profile=mcp-app");
  assert.match(contents[0].text, /CAC surface/);
});

test("only POST /mcp, an allowed Host, and /health are served", async () => {
  const get = await fetch(`${textOnly}/mcp`);
  assert.equal(get.status, 405);
  const health = await fetch(`${textOnly}/health`);
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { status: "ok", serve: "ok", element: false });
  const port = new URL(textOnly).port;
  const { request } = await import("node:http");
  const status = await new Promise<number>((done) => {
    const req = request(
      { host: "127.0.0.1", port, path: "/mcp", method: "POST",
        headers: { host: "evil.example", "content-type": "application/json" } },
      (res) => { res.resume(); done(res.statusCode ?? 0); },
    );
    req.end("{}");
  });
  assert.equal(status, 403);
});
