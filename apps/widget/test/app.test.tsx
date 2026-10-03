import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App";
import { fetchTransport } from "../src/transport/fetch";
import { mockTransport } from "../src/transport/mock";
import { sessionId } from "../src/transport/session";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function ask(text: string) {
  fireEvent.change(screen.getByLabelText("Ask a question"), { target: { value: text } });
  fireEvent.submit(screen.getByLabelText("Ask a question").closest("form")!);
}

function fill(label: RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("interaction (wp4 proof)", () => {
  it("submit success shows the confirmation", async () => {
    const t = mockTransport();
    const action = vi.spyOn(t, "action");
    render(<App transport={t} />);
    await ask("table for 4 on Friday at 7pm");
    await screen.findByLabelText(/party size/i);
    fill(/^date/i, "2099-01-01");
    fill(/^name/i, "Ada");
    fill(/phone or email/i, "ada@example.com");
    fireEvent.submit(screen.getByLabelText(/party size/i).closest("form")!);
    await screen.findByText(/request received/i);
    expect(action).toHaveBeenCalledWith(
      "submit_booking_request",
      expect.objectContaining({ party_size: 4, name: "Ada", time: "19:00" }),
      "BookingForm",
    );
  });

  it("submit 422 shows the field errors and keeps the form", async () => {
    render(<App transport={mockTransport()} />);
    await ask("do you cater for 40?");
    await screen.findByLabelText(/headcount/i);
    fireEvent.submit(screen.getByLabelText(/headcount/i).closest("form")!);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((a) => a.textContent).join(" ")).toMatch(/required/i);
    expect(screen.getByLabelText(/headcount/i)).toBeTruthy();
  });

  it("Add buttons update the cart count", async () => {
    render(<App transport={mockTransport()} />);
    await ask("I want to pick up something vegetarian");
    const adds = await screen.findAllByRole("button", { name: /add/i });
    fireEvent.click(adds[0]);
    fireEvent.click(adds[1]);
    expect(screen.getByTestId("cart-count").textContent).toContain("2");
  });

  it("the goal button opens its preset with src=cta", async () => {
    const t = mockTransport();
    const view = vi.spyOn(t, "view");
    const { container } = render(<App transport={t} />);
    await ask("vegetarian options");
    await screen.findByText(/confirmed/i);
    fireEvent.click(container.querySelector('[data-view="GoalCTA"] button')!);
    await waitFor(() => expect(view).toHaveBeenCalledWith("booking", { src: "cta" }));
    await screen.findByLabelText(/party size/i);
  });

  it("a cac:view message from the parent page opens the preset", async () => {
    const t = mockTransport();
    const view = vi.spyOn(t, "view");
    render(<App transport={t} />);
    await act(async () => {
      const data = { type: "cac:view", preset: "hours" };
      window.dispatchEvent(new MessageEvent("message", { data }));
    });
    await waitFor(() => expect(view).toHaveBeenCalledWith("hours", undefined));
  });

  it("chips submit their text as an intent", async () => {
    const t = mockTransport();
    const intent = vi.spyOn(t, "intent");
    render(<App transport={t} />);
    fireEvent.click(await screen.findByRole("button", { name: "Vegetarian options" }));
    await waitFor(() => expect(intent).toHaveBeenCalledWith("Vegetarian options"));
  });

  it("a failed request shows the error state with a way back to the menu", async () => {
    const t = mockTransport();
    vi.spyOn(t, "intent").mockRejectedValue(new Error("down"));
    render(<App transport={t} />);
    await ask("anything");
    expect((await screen.findByRole("alert")).textContent).toMatch(/try again/i);
  });
});

describe("session and fetch transport", () => {
  it("keeps one session_id in sessionStorage", () => {
    sessionStorage.clear();
    const a = sessionId();
    expect(sessionStorage.getItem("cac.session_id")).toBe(a);
    expect(sessionId()).toBe(a);
  });

  it("posts intents with the session_id and returns 422 bodies from actions", async () => {
    const calls: [string, RequestInit | undefined][] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        calls.push([url, init]);
        if (url.endsWith("/v1/action")) {
          const body = { ok: false, errors: [{ field: "date", message: "x" }] };
          return new Response(JSON.stringify(body), { status: 422 });
        }
        return new Response(JSON.stringify({ views: [] }), { status: 200 });
      }),
    );
    const t = fetchTransport("http://box.test");
    await t.intent("hi");
    expect(calls[0][0]).toBe("http://box.test/v1/intent");
    expect(JSON.parse(String(calls[0][1]?.body))).toEqual({ text: "hi", session_id: sessionId() });
    const res = await t.action("submit_catering_quote", {}, "CateringQuoteForm");
    expect(res.ok).toBe(false);
    await t.view("booking", { src: "cta" });
    expect(calls[2][0]).toBe("http://box.test/v1/view/booking?src=cta");
    vi.unstubAllGlobals();
  });
});
