// Service: the five public tools of SCHEMA 8.7. Each is one or two Serve API calls; nothing
// here reads a database, and no question or lead payload is ever logged.
import { RESOURCE_MIME_TYPE, registerAppResource, registerAppTool }
  from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

import { ServeClient, ServeRejected, type Surface } from "./serve_client.ts";

export const SURFACE_URI = "ui://cac/surface.html";
const BUSY = "The restaurant's system is busy right now. Please try again in a moment.";
const BOOKING_RECEIVED = "Request received; the restaurant will confirm. This is not yet a "
  + "confirmed reservation.";
const QUOTE_RECEIVED = "Quote request received; the restaurant will reply with a quote using "
  + "the contact given.";

export interface ToolContext {
  client: ServeClient;
  businessName: string;
  /** The widget as one HTML file, or undefined to run text-only (cut line 1). */
  surfaceHtml: string | undefined;
}

const lead = {
  name: z.string().describe("Name the request is under"),
  contact: z.string().describe("Phone number or email the restaurant replies to"),
  notes: z.string().optional().describe("Anything the restaurant should know"),
};
const bookingInput = {
  date: z.string().describe("Date, YYYY-MM-DD"),
  time: z.string().describe("Time, 24-hour HH:MM"),
  party_size: z.number().int().min(1).max(20),
  ...lead,
};
const cateringInput = {
  date: z.string().describe("Event date, YYYY-MM-DD"),
  headcount: z.number().int().min(1),
  ...lead,
};

function fail(text: string): CallToolResult {
  return { isError: true, content: [{ type: "text", text }] };
}

/** Run a tool body; turn Serve API refusals and outages into tool errors without internals. */
async function guarded(name: string, run: () => Promise<CallToolResult>): Promise<CallToolResult> {
  const started = Date.now();
  let outcome = "ok";
  try {
    return await run();
  } catch (error) {
    if (error instanceof ServeRejected) {
      outcome = `rejected ${error.status}`;
      const lines = error.errors.map((e) => (e.field ? `${e.field}: ${e.message}` : e.message));
      return fail(lines.join("\n"));
    }
    outcome = "unavailable";
    return fail(BUSY);
  } finally {
    console.log(`tool=${name} outcome=${outcome} ms=${Date.now() - started}`);
  }
}

export function surfaceText(surface: Surface): string {
  const text = surface.views.map((view) => view.text).filter(Boolean).join("\n\n");
  return text || surface.say || "";
}

function surfaceResult(surface: Surface): CallToolResult {
  return { content: [{ type: "text", text: surfaceText(surface) }], structuredContent: surface };
}

async function profile(client: ServeClient): Promise<CallToolResult> {
  const [boot, hours] = await Promise.all([client.bootstrap(), client.view("hours")]);
  const summary = {
    name: boot.business.name,
    tagline: boot.business.tagline,
    services: boot.nav.map((entry) => entry.label),
    hours: surfaceText(hours),
  };
  const text = [
    `${summary.name}. ${summary.tagline}`.trim(),
    `Services: ${summary.services.join(", ")}.`,
    `Hours: ${summary.hours}`,
  ].join("\n");
  return { content: [{ type: "text", text }], structuredContent: summary };
}

async function submit(
  client: ServeClient, action: string, payload: Record<string, unknown>, received: string,
): Promise<CallToolResult> {
  const receipt = await client.action(action, payload);
  return {
    content: [{ type: "text", text: `${received} Reference: ${receipt.lead_id}.` }],
    structuredContent: { ok: true, lead_id: receipt.lead_id, surface: receipt.surface },
  };
}

function registerQuestionTools(server: McpServer, context: ToolContext): void {
  const { client, businessName, surfaceHtml } = context;
  const element = surfaceHtml !== undefined;
  const askConfig = {
    title: `Ask ${businessName}`,
    description: `Ask ${businessName} about its menu, dietary options, hours, bookings or `
      + "catering. Returns facts confirmed by the restaurant and an interactive card.",
    inputSchema: { question: z.string().min(1).max(300) },
    annotations: { readOnlyHint: true },
  };
  const viewConfig = {
    title: "Open a view",
    description: "Open one of the restaurant's standard views: menu, hours, booking, catering.",
    inputSchema: { preset: z.string().min(1).max(64) },
    annotations: { readOnlyHint: true },
  };
  const ask = ({ question }: { question: string }) =>
    guarded("ask_restaurant", async () => surfaceResult(await client.intent(question)));
  const view = ({ preset }: { preset: string }) =>
    guarded("get_view", async () => surfaceResult(await client.view(preset)));
  if (!element) {
    server.registerTool("ask_restaurant", askConfig, ask);
    server.registerTool("get_view", viewConfig, view);
    return;
  }
  const ui = { resourceUri: SURFACE_URI };
  registerAppTool(server, "ask_restaurant", { ...askConfig, _meta: { ui } }, ask);
  // App-only: lets buttons in the element open presets; the model does not see it.
  registerAppTool(
    server, "get_view", { ...viewConfig, _meta: { ui: { ...ui, visibility: ["app"] } } }, view);
  registerAppResource(
    server, "CAC surface", SURFACE_URI, { mimeType: RESOURCE_MIME_TYPE },
    async () => ({
      contents: [{ uri: SURFACE_URI, mimeType: RESOURCE_MIME_TYPE, text: surfaceHtml }],
    }),
  );
}

export function buildServer(context: ToolContext): McpServer {
  const { client, businessName } = context;
  const server = new McpServer({ name: "cac", version: "0.1.0" });
  server.registerTool(
    "get_business_profile",
    {
      title: `About ${businessName}`,
      description: `Name, what it is, services and opening hours of ${businessName}.`,
      annotations: { readOnlyHint: true },
    },
    () => guarded("get_business_profile", () => profile(client)),
  );
  registerQuestionTools(server, context);
  server.registerTool(
    "request_booking",
    {
      title: "Request a table",
      description: `Send a table request to ${businessName}. It is a request, not a confirmed `
        + "reservation: the restaurant confirms using the contact given. Ask the user for "
        + "every field; never invent a name or contact.",
      inputSchema: bookingInput,
    },
    (payload) => guarded("request_booking",
      () => submit(client, "submit_booking_request", payload, BOOKING_RECEIVED)),
  );
  server.registerTool(
    "request_catering_quote",
    {
      title: "Request a catering quote",
      description: `Ask ${businessName} for a catering quote. The restaurant replies using the `
        + "contact given. Ask the user for every field; never invent a name or contact.",
      inputSchema: cateringInput,
    },
    (payload) => guarded("request_catering_quote",
      () => submit(client, "submit_catering_quote", payload, QUOTE_RECEIVED)),
  );
  return server;
}
