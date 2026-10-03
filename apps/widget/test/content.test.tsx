import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AllergenNotice } from "../src/components/AllergenNotice";
import { Answer } from "../src/components/Answer";
import { GoalCTA } from "../src/components/GoalCTA";
import { HoursCard } from "../src/components/HoursCard";
import { MenuList } from "../src/components/MenuList";
import type { SurfaceComponent } from "../src/components/types";
import type { View } from "../src/types";
import { makeCtx, viewOf } from "./helpers";

afterEach(cleanup);

function show(Comp: SurfaceComponent, v: View, ctx = makeCtx()) {
  return render(<Comp view={v} data={v.data as never} ctx={ctx} />);
}

describe("golden views", () => {
  it("Answer", () => {
    const v = viewOf("answer_kitchen_hours.json", "Answer");
    const d = v.data as { question: string; answer: string };
    show(Answer, v);
    expect(screen.getByText(d.question)).toBeTruthy();
    expect(screen.getByText(d.answer)).toBeTruthy();
  });
  it("AllergenNotice", () => {
    const v = viewOf("allergen_peanuts.json", "AllergenNotice");
    show(AllergenNotice, v);
    expect(screen.getByRole("note").textContent).toContain(v.text);
  });
  it("MenuList renders items for the preset menu", () => {
    const v = viewOf("preset_menu.json", "MenuList");
    const { container } = show(MenuList, v);
    expect(container.querySelectorAll(".cac-item").length).toBeGreaterThan(0);
  });
});

describe("MenuList", () => {
  it("shows no Add buttons without the action", () => {
    show(MenuList, viewOf("menu_vegetarian.json", "MenuList"));
    expect(screen.queryAllByRole("button", { name: "Add" })).toHaveLength(0);
  });
  it("Add calls addToCart with the item id", () => {
    const ctx = makeCtx();
    const v = viewOf("menu_vegetarian_order.json", "MenuList");
    show(MenuList, v, ctx);
    const btns = screen.getAllByRole("button", { name: "Add" });
    fireEvent.click(btns[0]);
    const first = (v.data as { items: { id: string }[] }).items[0].id;
    expect(ctx.addToCart).toHaveBeenCalledWith(first);
  });
  it("an unverified badge never shows the verified mark", () => {
    const base = viewOf("menu_vegetarian.json", "MenuList");
    const data = base.data as { items: { badges: { diet: string; verified: boolean }[] }[] };
    for (const it of data.items) it.badges = it.badges.map((b) => ({ ...b, verified: false }));
    const { container } = show(MenuList, base);
    expect(container.querySelector(".cac-badge-verified")).toBeNull();
    expect(container.textContent).not.toContain("✓");
    expect(container.textContent?.toLowerCase()).not.toContain("confirmed");
    cleanup();

    const real = viewOf("menu_vegetarian.json", "MenuList");
    const items = (real.data as { items: { badges: { verified: boolean }[] }[] }).items;
    const expected = items.flatMap((i) => i.badges).filter((b) => b.verified).length;
    const r = show(MenuList, real);
    expect(r.container.querySelectorAll(".cac-badge-verified").length).toBe(expected);
  });
  it("renders hostile names as literal text", () => {
    const v = viewOf("menu_vegetarian.json", "MenuList");
    const name = "<img src=x onerror=alert(1)>";
    v.data = { title: "T", items: [{ id: "x", name, price: "$1", description: "", badges: [] }] };
    const { container } = show(MenuList, v);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(name)).toBeTruthy();
  });
  it("tolerates missing items", () => {
    const v = viewOf("menu_vegetarian.json", "MenuList");
    v.data = {};
    expect(() => show(MenuList, v)).not.toThrow();
  });
});

describe("HoursCard", () => {
  it("shows Closed on July 4", () => {
    show(HoursCard, viewOf("hours_july4.json", "HoursCard"));
    expect(screen.getAllByText("Closed").length).toBeGreaterThan(0);
  });
  it("shows next-day closing on Saturday", () => {
    const { container } = show(HoursCard, viewOf("hours_saturday.json", "HoursCard"));
    expect(container.textContent).toContain("11:00 AM – 2:00 AM (next day)");
    expect(container.textContent).toContain("Mon–Wed");
  });
});

describe("GoalCTA", () => {
  it("opens the booking preset", () => {
    const ctx = makeCtx();
    const v = viewOf("hours_saturday.json", "GoalCTA");
    show(GoalCTA, v, ctx);
    fireEvent.click(screen.getByRole("button", { name: "Book a table" }));
    expect(ctx.openView).toHaveBeenCalledWith("booking", "cta");
  });
  it("renders nothing without the action", () => {
    const v = viewOf("hours_saturday.json", "GoalCTA");
    v.actions = [];
    const { container } = show(GoalCTA, v);
    expect(container.innerHTML).toBe("");
  });
});
