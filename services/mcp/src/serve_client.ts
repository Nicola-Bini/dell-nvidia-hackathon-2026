// Infra: the only thing this process talks to is the Serve API on localhost (SCHEMA 8.7).
import { randomUUID } from "node:crypto";

export interface View {
  component: string;
  text: string;
}

export interface Surface {
  say?: string;
  views: View[];
  [key: string]: unknown;
}

export interface Bootstrap {
  business: { name: string; tagline: string };
  nav: { label: string; preset: string }[];
}

export interface FieldError {
  field: string;
  message: string;
}

export interface LeadReceipt {
  ok: true;
  lead_id: string;
  surface?: Surface;
}

/** The Serve API could not be reached, timed out, or failed. */
export class ServeUnavailable extends Error {}

/** The Serve API refused the request (422 validation, 429 rate limit, 404 unknown preset). */
export class ServeRejected extends Error {
  constructor(readonly status: number, readonly errors: FieldError[]) {
    super(`serve rejected the request (${status})`);
  }
}

const CHANNEL = { "x-cac-channel": "mcp" };
const TIMEOUT_MS = 20_000;

function rejection(status: number, body: any): ServeRejected {
  const errors = Array.isArray(body?.errors) ? body.errors : [];
  const detail = typeof body?.detail === "string" ? body.detail : "The request was refused.";
  return new ServeRejected(status, errors.length ? errors : [{ field: "", message: detail }]);
}

export class ServeClient {
  constructor(private readonly baseUrl: string) {}

  private async call<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: body === undefined ? CHANNEL : { ...CHANNEL, "content-type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
    } catch {
      throw new ServeUnavailable("serve unreachable");
    }
    if (response.status >= 500) throw new ServeUnavailable(`serve answered ${response.status}`);
    const parsed = await response.json().catch(() => undefined);
    if (!response.ok) throw rejection(response.status, parsed);
    return parsed as T;
  }

  bootstrap(): Promise<Bootstrap> {
    return this.call("GET", "/v1/bootstrap");
  }

  /** Every question is its own anonymous session: an assistant gives us no visitor id. */
  intent(text: string): Promise<Surface> {
    return this.call("POST", "/v1/intent", { text, session_id: `mcp_${randomUUID()}` });
  }

  view(preset: string): Promise<Surface> {
    return this.call("GET", `/v1/view/${encodeURIComponent(preset)}`);
  }

  action(name: string, payload: Record<string, unknown>): Promise<LeadReceipt> {
    return this.call("POST", "/v1/action", { name, payload, session_id: `mcp_${randomUUID()}` });
  }

  async healthy(): Promise<boolean> {
    try {
      await this.call("GET", "/healthz");
      return true;
    } catch {
      return false;
    }
  }
}
