import { Component, type ReactNode } from "react";
import { registry } from "./components/registry";
import type { SurfaceContext } from "./components/types";
import type { Surface, View } from "./types";

/** One bad view must not take the panel down: it renders nothing instead. */
class ViewBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

function ViewSlot({ view, ctx }: { view: View; ctx: SurfaceContext }) {
  const Comp = registry[view.component];
  if (!Comp) return null;
  return (
    <ViewBoundary>
      <div className="cac-view" data-view={view.component}>
        <Comp view={view} data={view.data ?? {}} ctx={ctx} />
      </div>
    </ViewBoundary>
  );
}

export function SurfaceView({ surface, ctx }: { surface: Surface; ctx: SurfaceContext }) {
  return (
    <article className="cac-surface" data-kind={surface.kind} aria-live="polite">
      {surface.say ? <p className="cac-say">{surface.say}</p> : null}
      {surface.views.map((v) => (
        <ViewSlot key={v.id} view={v} ctx={ctx} />
      ))}
    </article>
  );
}
