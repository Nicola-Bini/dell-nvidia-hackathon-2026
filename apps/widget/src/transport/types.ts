import type { ActionResult, Bootstrap, Metrics, Surface } from "../types";

/** SCHEMA 8.7: the widget talks only through this. Web uses fetch; tests use the mock. */
export interface Transport {
  bootstrap(): Promise<Bootstrap>;
  intent(text: string): Promise<Surface>;
  view(preset: string, opts?: { src?: "cta" }): Promise<Surface>;
  action(name: string, payload: unknown, component: string): Promise<ActionResult>;
  metrics(): Promise<Metrics>;
}
