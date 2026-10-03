import { useEffect, useState } from "react";
import type { Transport } from "./transport";
import type { Metrics } from "./types";

const POLL_MS = 1000;
export const OVERLAY_KEY = "`";

/** Polls /v1/metrics while shown. Stops on unmount; a failed poll keeps the last numbers. */
export function useMetrics(transport: Transport, enabled: boolean) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [stale, setStale] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const tick = () =>
      transport.metrics().then(
        (m) => alive && (setMetrics(m), setStale(false)),
        () => alive && setStale(true),
      );
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [transport, enabled]);
  return { metrics, stale };
}

/** Shown with the backquote key, or from the start with ?overlay=1. */
export function useOverlayToggle(initial: boolean) {
  const [shown, setShown] = useState(initial);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName)) return;
      if (e.key === OVERLAY_KEY) setShown((s) => !s);
    };
    // embed.js forwards the key from the host page, which the iframe cannot hear.
    const onMessage = (e: MessageEvent) => {
      if ((e.data as { type?: unknown } | null)?.type === "cac:overlay") setShown((s) => !s);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("message", onMessage);
    };
  }, []);
  return shown;
}

const pct = (x: number) => `${Math.round(x * 100)}%`;

export function metricRows(m: Metrics): [string, string][] {
  return [
    ["Latency p50 / p95", `${m.latency_ms.p50} / ${m.latency_ms.p95} ms`],
    ["Cache hits", pct(m.cache_hit_rate)],
    ["Model calls", String(m.model_calls)],
    ["In flight", String(m.model_inflight)],
    ["Model host", m.model_host],
    ["Leads captured", String(m.leads_captured)],
    ["Goal buttons shown / clicked", `${m.cta_shown} / ${m.cta_clicked}`],
    ["Graph version", String(m.graph_version)],
  ];
}

export function Overlay({ transport }: { transport: Transport }) {
  const { metrics, stale } = useMetrics(transport, true);
  return (
    <aside className="cac-overlay" aria-label="Live metrics" data-stale={stale || undefined}>
      <h2>Live on the box{stale ? " (no response)" : ""}</h2>
      {metrics ? (
        <dl>
          {metricRows(metrics).map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p>Waiting for metrics…</p>
      )}
    </aside>
  );
}
