import type { ActionResult, Bootstrap, Metrics, Surface } from "../types";
import { sessionId } from "./session";
import type { Transport } from "./types";

export class HttpError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`HTTP ${status}`);
  }
}

async function json<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new HttpError(res.status, body);
  return body as T;
}

/** The Serve API over fetch (SCHEMA 8.5). `base` is "" for same-origin. */
export function fetchTransport(base: string): Transport {
  const url = (path: string) => base.replace(/\/$/, "") + path;
  const post = (path: string, body: unknown) =>
    fetch(url(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  return {
    bootstrap: () => fetch(url("/v1/bootstrap")).then((r) => json<Bootstrap>(r)),
    intent: (text) =>
      post("/v1/intent", { text, session_id: sessionId() }).then((r) => json<Surface>(r)),
    view: (preset, opts) => {
      const q = opts?.src ? `?src=${encodeURIComponent(opts.src)}` : "";
      return fetch(url(`/v1/view/${encodeURIComponent(preset)}${q}`)).then((r) =>
        json<Surface>(r),
      );
    },
    action: async (name, payload, component) => {
      const res = await post("/v1/action", { name, payload, session_id: sessionId(), component });
      const body = (await res.json().catch(() => null)) as ActionResult | null;
      if (body && (res.ok || res.status === 422 || res.status === 429)) return body;
      throw new HttpError(res.status, body);
    },
    metrics: () => fetch(url("/v1/metrics")).then((r) => json<Metrics>(r)),
  };
}
