import "./content.css";
import type { ComponentProps } from "./types";

interface CtaData {
  label?: string;
}

const PREFIX = "open_view:";

export function GoalCTA({ view, data, ctx }: ComponentProps<CtaData>) {
  const action = view.actions.find((a) => a.name.startsWith(PREFIX));
  const preset = action ? action.name.slice(PREFIX.length) : "";
  if (!preset) return null;
  return (
    <button
      type="button"
      className="cac-cta"
      data-component="GoalCTA"
      onClick={() => ctx.openView(preset, "cta")}
    >
      {data?.label ?? "Book a table"}
    </button>
  );
}
