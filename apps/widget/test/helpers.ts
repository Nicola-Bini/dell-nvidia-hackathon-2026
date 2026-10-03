import { vi } from "vitest";
import type { SurfaceContext } from "../src/components/types";
import { fixtureSurfaces } from "../src/transport/fixtures";
import type { Surface, View } from "../src/types";

/** A context whose callbacks are spies. Pass overrides for the ones a test drives. */
export function makeCtx(over: Partial<SurfaceContext> = {}): SurfaceContext {
  return {
    cartCount: 0,
    ask: vi.fn(),
    openView: vi.fn(),
    addToCart: vi.fn(),
    submit: vi.fn(async () => ({ ok: true })),
    ...over,
  };
}

export function surface(file: string): Surface {
  return structuredClone(fixtureSurfaces[file]);
}

/** The first view of `component` in a golden file. */
export function viewOf(file: string, component: string): View {
  const v = surface(file).views.find((x) => x.component === component);
  if (!v) throw new Error(`${file} has no ${component}`);
  return v;
}
