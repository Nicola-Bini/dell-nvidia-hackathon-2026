// Wire types from docs/SCHEMA.md 8.4 and 8.5. Component data stays loose here; each
// component narrows its own `data`.

export interface ViewAction {
  name: string;
  handler: "client" | "server";
}

export interface View {
  id: string;
  component: string;
  data: Record<string, unknown> | null;
  actions: ViewAction[];
  text: string;
}

export interface Surface {
  surface_id: string;
  kind: "answer" | "gap" | "off_topic" | "preset" | string;
  title: string;
  say: string;
  views: View[];
  chips: string[];
  meta: { cache: string; latency_ms: number; graph_version: number; model: string };
}

export interface Bootstrap {
  business: { name: string; tagline: string };
  theme: Record<string, string>;
  nav: { label: string; preset: string }[];
  chips: string[];
}

export interface FieldError {
  field: string;
  message: string;
}

export interface ActionResult {
  ok: boolean;
  lead_id?: string;
  surface?: Surface;
  errors?: FieldError[];
}

export interface Metrics {
  latency_ms: { p50: number; p95: number };
  cache_hit_rate: number;
  model_calls: number;
  model_inflight: number;
  graph_version: number;
  leads_captured: number;
  cta_shown: number;
  cta_clicked: number;
  model_host: string;
}
