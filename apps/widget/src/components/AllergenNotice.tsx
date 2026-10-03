import type { ComponentProps } from "./types";

// wp1 stub: renders the view's plain-text fallback. Replaced in wp2.
export function AllergenNotice({ view }: ComponentProps) {
  return <p className="cac-text" data-component="AllergenNotice">{view.text}</p>;
}
