import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BookingForm } from "../src/components/BookingForm";
import { CateringQuoteForm } from "../src/components/CateringQuoteForm";
import { FactCard } from "../src/components/FactCard";
import { FormCard } from "../src/components/FormCard";
import { ListCard } from "../src/components/ListCard";
import type { SurfaceComponent } from "../src/components/types";
import { makeCtx, viewOf } from "./helpers";

afterEach(cleanup);

const golden: [string, string, SurfaceComponent][] = [
  ["booking_form.json", "BookingForm", BookingForm],
  ["catering_form_40.json", "CateringQuoteForm", CateringQuoteForm],
  ["form_contact.json", "FormCard", FormCard],
  ["gift_cards.json", "ListCard", ListCard],
  ["gap.json", "FactCard", FactCard],
];

describe("golden views", () => {
  it.each(golden)("%s renders %s", (file, name, Comp) => {
    const v = viewOf(file, name);
    const { container } = render(<Comp view={v} data={v.data as never} ctx={makeCtx()} />);
    expect(container.textContent).not.toBe("");
  });
});

it("catering prefills headcount 40", () => {
  const v = viewOf("catering_form_40.json", "CateringQuoteForm");
  render(<CateringQuoteForm view={v} data={v.data as never} ctx={makeCtx()} />);
  expect((screen.getByLabelText("Headcount") as HTMLInputElement).value).toBe("40");
});

describe("BookingForm", () => {
  const v = viewOf("booking_form.json", "BookingForm");
  it("submits and confirms", async () => {
    const ctx = makeCtx();
    render(<BookingForm view={v} data={v.data as never} ctx={ctx} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ada" } });
    fireEvent.change(screen.getByLabelText("Phone or email"), { target: { value: "a@b.co" } });
    fireEvent.submit(screen.getByRole("form"));
    await waitFor(() => expect(screen.getByText("Request sent.")).toBeTruthy());
    expect(ctx.submit).toHaveBeenCalledWith(
      "submit_booking_request",
      expect.objectContaining({ party_size: 4, name: "Ada" }),
      "BookingForm",
    );
  });
  it("shows 422 errors", async () => {
    const ctx = makeCtx({
      submit: vi.fn(async () => ({
        ok: false,
        errors: [{ field: "contact", message: "Required." }],
      })),
    });
    render(<BookingForm view={v} data={v.data as never} ctx={ctx} />);
    fireEvent.submit(screen.getByRole("form"));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Required.");
  });
  it("shows a link when booking_url is set", () => {
    render(<BookingForm view={v} data={{ booking_url: "https://x.test" }} ctx={makeCtx()} />);
    expect(screen.getByRole("link").getAttribute("rel")).toBe("noopener noreferrer");
  });
});

it("FormCard submits values and renders select options", async () => {
  const v = viewOf("form_contact.json", "FormCard");
  const ctx = makeCtx();
  render(<FormCard view={v} data={v.data as never} ctx={ctx} />);
  expect(screen.getByRole("option", { name: "Press Inquiry" })).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ada" } });
  fireEvent.submit(screen.getByRole("form"));
  await waitFor(() => expect(ctx.submit).toHaveBeenCalled());
  expect(ctx.submit).toHaveBeenCalledWith(
    "submit_form",
    { form: "ui_form_contact", values: expect.objectContaining({ name: "Ada" }) },
    "ui_form_contact",
  );
});

it("ListCard shows both gift cards", () => {
  const v = viewOf("gift_cards.json", "ListCard");
  render(<ListCard view={v} data={v.data as never} ctx={makeCtx()} />);
  expect(screen.getByText("$25 gift card")).toBeTruthy();
  expect(screen.getByText("$50 gift card")).toBeTruthy();
});

it("FactCard renders a tel link", () => {
  const v = viewOf("gap.json", "FactCard");
  render(<FactCard view={v} data={v.data as never} ctx={makeCtx()} />);
  expect(screen.getByRole("link").getAttribute("href")).toBe("tel:+16172666662");
});

it("FactCard renders markup as text", () => {
  const v = viewOf("gap.json", "FactCard");
  const data = { title: "t", facts: [{ name: "x", value: "<img src=x onerror=alert(1)>" }] };
  const { container } = render(<FactCard view={v} data={data} ctx={makeCtx()} />);
  expect(container.querySelector("img")).toBeNull();
  expect(container.textContent).toContain("<img src=x");
});
