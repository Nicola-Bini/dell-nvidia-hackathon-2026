import type { ComponentType } from "react";
import type { ActionResult, View } from "../types";

/** What the shell hands every component. Components never call the transport directly. */
export interface SurfaceContext {
  /** Open a preset (`open_view:<preset>`); src "cta" counts a goal-button click. */
  openView(preset: string, src?: "cta"): void;
  /** Server actions (`submit_*`). Resolves with field errors on HTTP 422. */
  submit(name: string, payload: unknown, component: string): Promise<ActionResult>;
  /** Client `add_to_cart`. */
  addToCart(itemId: string): void;
  /** Submit a text as a typed intent (chips). */
  ask(text: string): void;
  cartCount: number;
}

export interface ComponentProps<D = Record<string, unknown>> {
  view: View;
  data: D;
  ctx: SurfaceContext;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type SurfaceComponent = ComponentType<ComponentProps<any>>;

export function hasAction(view: View, name: string): boolean {
  return view.actions.some((a) => a.name === name);
}
