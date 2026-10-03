import type { Surface } from "../types";
import index from "../../../../fixtures/surfaces/index.json";

// Every golden surface in fixtures/surfaces/, keyed by file name. index.json is not a Surface.
const files = import.meta.glob<Surface>("../../../../fixtures/surfaces/*.json", {
  eager: true,
  import: "default",
});

export const fixtureSurfaces: Record<string, Surface> = Object.fromEntries(
  Object.entries(files)
    .map(([path, surface]) => [path.split("/").pop() as string, surface] as const)
    .filter(([name]) => name !== "index.json"),
);

export const fixtureIndex: Record<string, string> = index;

export function normalize(text: string): string {
  return text.trim().toLowerCase().replace(/[?.!\s]+$/g, "").replace(/\s+/g, " ");
}
