import { fetchTransport } from "./fetch";
import { mockTransport } from "./mock";
import type { Transport } from "./types";

export type { Transport } from "./types";

/**
 * VITE_SERVE_URL picks the transport: "mock" is the fixture mock, "same-origin" is the
 * Serve API that also serves /widget/, anything else is the Serve API's origin. Unset means
 * the mock in `npm run dev` and same-origin in a build. `?mock=1` forces the mock.
 * There is deliberately no run-time override of the origin: forms post visitor data.
 */
export function createTransport(search = globalThis.location?.search ?? ""): Transport {
  const forced = new URLSearchParams(search).get("mock") === "1";
  const serve = import.meta.env.VITE_SERVE_URL || (import.meta.env.DEV ? "mock" : "same-origin");
  if (forced || serve === "mock") return mockTransport({ delayMs: 250 });
  return fetchTransport(serve === "same-origin" ? "" : serve);
}
