import { cleanup, render } from "@testing-library/react";
import { readdirSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SurfaceView } from "../src/SurfaceView";
import { fixtureIndex, fixtureSurfaces } from "../src/transport/fixtures";
import { mockTransport } from "../src/transport/mock";
import { makeCtx } from "./helpers";

const dir = resolve(__dirname, "../../../fixtures/surfaces");
const onDisk = readdirSync(dir).filter((f) => f.endsWith(".json") && f !== "index.json");

const inertCtx = makeCtx();

afterEach(cleanup);

describe("golden surfaces (wp1 proof)", () => {
  it("loads every file in fixtures/surfaces/", () => {
    expect(Object.keys(fixtureSurfaces).sort()).toEqual(onDisk.sort());
  });

  it.each(onDisk)("%s renders without error", (file) => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { container } = render(<SurfaceView surface={fixtureSurfaces[file]} ctx={inertCtx} />);
    expect(container.querySelector(".cac-surface")).not.toBeNull();
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });

  it("an unknown component renders nothing and does not crash", () => {
    const surface = structuredClone(fixtureSurfaces["gap.json"]);
    surface.views = [{ id: "x", component: "NoSuchThing", data: {}, actions: [], text: "boom" }];
    const { container } = render(<SurfaceView surface={surface} ctx={inertCtx} />);
    expect(container.querySelector("[data-view]")).toBeNull();
    expect(container.textContent).not.toContain("boom");
  });
});

describe("mock transport", () => {
  it("answers every index.json intent with its golden file", async () => {
    const t = mockTransport();
    for (const [text, file] of Object.entries(fixtureIndex)) {
      expect((await t.intent(text)).surface_id).toBe(fixtureSurfaces[file].surface_id);
    }
  });

  it("answers anything else with the off-topic surface", async () => {
    const s = await mockTransport().intent("what is the meaning of life");
    expect(s.kind).toBe("off_topic");
  });

  it("serves the P0 presets", async () => {
    const t = mockTransport();
    for (const p of ["menu", "booking", "catering", "hours"]) {
      expect((await t.view(p)).views.length).toBeGreaterThan(0);
    }
  });
});
