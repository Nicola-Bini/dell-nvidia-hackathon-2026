import type { ActionResult, Bootstrap, FieldError, Metrics, Surface } from "../types";
import { fixtureIndex, fixtureSurfaces, normalize } from "./fixtures";
import type { Transport } from "./types";

// Extra intents the demo needs that index.json leaves out (fixtures/README.md: no intent).
const EXTRA: Record<string, string> = {
  "do you sell gift cards": "gift_cards.json",
  "gift cards": "gift_cards.json",
  "see the menu": "preset_menu.json",
  "book a table": "booking_form.json",
};

const PRESETS: Record<string, () => Surface> = {
  menu: () => fixtureSurfaces["preset_menu.json"],
  hours: () => fixtureSurfaces["hours_saturday.json"],
  booking: () => withPrefill(fixtureSurfaces["booking_form.json"], "booking"),
  catering: () => withPrefill(fixtureSurfaces["catering_form_40.json"], "catering"),
};

function withPrefill(surface: Surface, preset: string): Surface {
  const copy = structuredClone(surface);
  copy.kind = "preset";
  copy.surface_id = `s_preset_${preset}`;
  copy.views[0].data = { ...copy.views[0].data, prefill: {} };
  return copy;
}

const BOOTSTRAP: Bootstrap = {
  business: { name: "The Kenmore", tagline: "We are a local's establishment focusing on craft beer and craft ingredients." },
  theme: {
    background: "#111111",
    text: "#FFFFFF",
    heading: "Engravers",
    body: "Cormorant Garamond",
  },
  nav: [
    { label: "Menu", preset: "menu" },
    { label: "Hours", preset: "hours" },
    { label: "Book", preset: "booking" },
    { label: "Catering", preset: "catering" },
  ],
  chips: ["What's on draft?", "Vegetarian options", "Are you open tonight?"],
};

const REQUIRED: Record<string, string[]> = {
  submit_booking_request: ["date", "time", "party_size", "name", "contact"],
  submit_catering_quote: ["date", "headcount", "name", "contact"],
};

export function validate(name: string, payload: Record<string, unknown>): FieldError[] {
  const values = (name === "submit_form" ? payload.values : payload) as Record<string, unknown>;
  const errors: FieldError[] = (REQUIRED[name] ?? [])
    .filter((f) => values?.[f] === undefined || values?.[f] === "")
    .map((field) => ({ field, message: "Required." }));
  const date = values?.date;
  if (typeof date === "string" && date && date < new Date().toISOString().slice(0, 10)) {
    errors.push({ field: "date", message: "That date is in the past." });
  }
  return errors;
}

function confirmation(name: string): Surface {
  const say =
    name === "submit_booking_request"
      ? "Request received. The restaurant will confirm your table."
      : "Thanks, we have your request and will be in touch.";
  return {
    surface_id: `s_confirm_${Date.now()}`,
    kind: "preset",
    title: "Request sent",
    say,
    views: [],
    chips: BOOTSTRAP.chips,
    meta: { cache: "preset", latency_ms: 0, graph_version: 7, model: "local" },
  };
}

export interface MockOptions {
  delayMs?: number;
}

/** Serves the golden fixtures exactly as the stub Serve API does (OWNERSHIP seam 3). */
export function mockTransport(opts: MockOptions = {}): Transport {
  const delay = <T>(value: T) =>
    new Promise<T>((resolve) =>
      setTimeout(() => resolve(structuredClone(value)), opts.delayMs ?? 0),
    );
  let leads = 0;
  let ctaClicked = 0;
  return {
    bootstrap: () => delay(BOOTSTRAP),
    intent: (text) => {
      const key = normalize(text);
      const hit = Object.entries(fixtureIndex).find(([k]) => normalize(k) === key);
      const file = hit?.[1] ?? EXTRA[key] ?? "off_topic.json";
      return delay(fixtureSurfaces[file]);
    },
    view: (preset, o) => {
      if (o?.src === "cta") ctaClicked += 1;
      const make = PRESETS[preset];
      return make ? delay(make()) : Promise.reject(new Error(`unknown preset ${preset}`));
    },
    action: (name, payload) => {
      const errors = validate(name, (payload ?? {}) as Record<string, unknown>);
      if (errors.length) return delay<ActionResult>({ ok: false, errors });
      leads += 1;
      const lead_id = `lead-${leads}`;
      return delay<ActionResult>({ ok: true, lead_id, surface: confirmation(name) });
    },
    metrics: () =>
      delay<Metrics>({
        latency_ms: { p50: 12, p95: 40 },
        cache_hit_rate: 0.5,
        model_calls: 0,
        model_inflight: 0,
        graph_version: 7,
        leads_captured: leads,
        cta_shown: 0,
        cta_clicked: ctaClicked,
        model_host: "fixtures (mock)",
      }),
  };
}
