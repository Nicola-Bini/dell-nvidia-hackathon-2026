import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App";
import { Overlay } from "../src/Overlay";
import { mockTransport } from "../src/transport/mock";
import type { Metrics } from "../src/types";

// OWNERSHIP seam 3: GET /v1/metrics returns exactly this shape.
const SEAM3: Metrics = {
  latency_ms: { p50: 0, p95: 0 },
  cache_hit_rate: 0.0,
  model_calls: 0,
  model_inflight: 0,
  graph_version: 1,
  leads_captured: 0,
  cta_shown: 0,
  cta_clicked: 0,
  model_host: "127.0.0.1:8000",
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("overlay (wp5 proof)", () => {
  it("renders the seam 3 metrics shape", async () => {
    const t = mockTransport();
    const live = { ...SEAM3, latency_ms: { p50: 840, p95: 1900 }, cache_hit_rate: 0.42,
      model_calls: 3, model_inflight: 1, leads_captured: 2, cta_shown: 5, cta_clicked: 1 };
    vi.spyOn(t, "metrics").mockResolvedValue(live);
    render(<Overlay transport={t} />);
    const box = await screen.findByLabelText("Live metrics");
    await screen.findByText("840 / 1900 ms");
    for (const text of ["42%", "127.0.0.1:8000", "5 / 1"]) {
      expect(box.textContent).toContain(text);
    }
    expect(screen.getByText("In flight").nextSibling?.textContent).toBe("1");
    expect(screen.getByText("Leads captured").nextSibling?.textContent).toBe("2");
  });

  it("renders the all-zero seam 3 response", async () => {
    const t = mockTransport();
    vi.spyOn(t, "metrics").mockResolvedValue(SEAM3);
    render(<Overlay transport={t} />);
    expect(await screen.findByText("0 / 0 ms")).toBeTruthy();
  });

  it("marks itself stale when polling fails", async () => {
    const t = mockTransport();
    vi.spyOn(t, "metrics").mockRejectedValue(new Error("down"));
    render(<Overlay transport={t} />);
    expect(await screen.findByText(/no response/)).toBeTruthy();
  });

  it("is toggled by the backquote key and by cac:overlay from the host page", async () => {
    render(<App transport={mockTransport()} />);
    expect(screen.queryByLabelText("Live metrics")).toBeNull();
    fireEvent.keyDown(window, { key: "`" });
    expect(await screen.findByLabelText("Live metrics")).toBeTruthy();
    await act(async () => {
      window.dispatchEvent(new MessageEvent("message", { data: { type: "cac:overlay" } }));
    });
    expect(screen.queryByLabelText("Live metrics")).toBeNull();
  });

  it("shows the offline state when the browser goes offline", async () => {
    render(<App transport={mockTransport()} />);
    await act(async () => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByText(/offline/i)).toBeTruthy();
    await act(async () => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.queryByText(/offline/i)).toBeNull();
  });
});
