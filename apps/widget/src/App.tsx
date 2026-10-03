import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import type { SurfaceContext } from "./components/types";
import { Overlay, useOverlayToggle } from "./Overlay";
import { SurfaceView } from "./SurfaceView";
import type { Transport } from "./transport";
import type { ActionResult, Bootstrap, Surface } from "./types";

export type Status = "idle" | "busy" | "error";

const MAX_INTENT = 300;
const PRESET_RE = /^[a-z][a-z0-9_]{0,31}$/;

export function useWidget(transport: Transport) {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [surface, setSurface] = useState<Surface | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [cartCount, setCartCount] = useState(0);

  useEffect(() => {
    transport.bootstrap().then(setBoot, () => setStatus("error"));
  }, [transport]);

  const run = useCallback(async (load: () => Promise<Surface>) => {
    setStatus("busy");
    try {
      setSurface(await load());
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  }, []);

  const ctx = useMemo<SurfaceContext>(
    () => ({
      cartCount,
      ask: (text) => run(() => transport.intent(text.slice(0, MAX_INTENT))),
      openView: (preset, src) => {
        if (PRESET_RE.test(preset)) run(() => transport.view(preset, src ? { src } : undefined));
      },
      addToCart: () => setCartCount((n) => n + 1),
      submit: async (name, payload, component): Promise<ActionResult> => {
        const result = await transport.action(name, payload, component);
        if (result.ok && result.surface) setSurface(result.surface);
        return result;
      },
    }),
    [transport, run, cartCount],
  );

  return { boot, surface, status, ctx };
}

/** The parent page's nav links arrive as postMessage({ type: "cac:view", preset }). */
function useParentNav(openView: (preset: string) => void) {
  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      const msg = e.data as { type?: unknown; preset?: unknown } | null;
      if (msg && msg.type === "cac:view" && typeof msg.preset === "string") openView(msg.preset);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [openView]);
}

function IntentBox({ onAsk, disabled }: { onAsk: (t: string) => void; disabled: boolean }) {
  const [text, setText] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || disabled) return;
    onAsk(t);
    setText("");
  };
  return (
    <form className="cac-intent" onSubmit={submit}>
      <input
        aria-label="Ask a question"
        placeholder="Ask about the menu, hours, bookings…"
        value={text}
        maxLength={MAX_INTENT}
        onChange={(e) => setText(e.target.value)}
      />
      <button type="submit" disabled={disabled || !text.trim()}>
        Ask
      </button>
    </form>
  );
}

function Chips({ chips, onAsk }: { chips: string[]; onAsk: (t: string) => void }) {
  if (!chips.length) return null;
  return (
    <div className="cac-chips">
      {chips.map((c) => (
        <button key={c} type="button" className="cac-chip" onClick={() => onAsk(c)}>
          {c}
        </button>
      ))}
    </div>
  );
}

/** Tracks the browser's online state, so a dropped connection reads as offline. */
function useOnline() {
  const [online, setOnline] = useState(() => navigator.onLine !== false);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

function StatusLine({ status, retry }: { status: Status; retry: () => void }) {
  const online = useOnline();
  if (!online) {
    return (
      <p className="cac-status cac-error" role="status">
        You seem to be offline. Answers will come back when you reconnect.
      </p>
    );
  }
  if (status === "busy") {
    return (
      <p className="cac-status cac-busy" role="status">
        One moment…
      </p>
    );
  }
  if (status !== "error") return null;
  return (
    <p className="cac-status cac-error" role="alert">
      Something went wrong. Please try again.{" "}
      <button type="button" onClick={retry}>
        Show the menu
      </button>
    </p>
  );
}

export function App({ transport, overlay = false }: { transport: Transport; overlay?: boolean }) {
  const { boot, surface, status, ctx } = useWidget(transport);
  const showOverlay = useOverlayToggle(overlay);
  const openView = useCallback((p: string) => ctx.openView(p), [ctx]);
  useParentNav(openView);
  const chips = surface?.chips ?? boot?.chips ?? [];
  return (
    <div className="cac-panel">
      <header className="cac-header">
        <h1>{boot?.business.name ?? "Ask us"}</h1>
        {ctx.cartCount > 0 ? (
          <span className="cac-cart" data-testid="cart-count">
            Cart: {ctx.cartCount}
          </span>
        ) : null}
      </header>
      <main className="cac-main">
        {surface ? (
          <SurfaceView surface={surface} ctx={ctx} />
        ) : (
          <p className="cac-say">
            {boot?.business.tagline ?? "Ask about our menu, hours and bookings."}
          </p>
        )}
        <StatusLine status={status} retry={() => ctx.openView("menu")} />
      </main>
      <footer className="cac-footer">
        <Chips chips={chips} onAsk={ctx.ask} />
        <IntentBox onAsk={ctx.ask} disabled={status === "busy"} />
      </footer>
      {showOverlay ? <Overlay transport={transport} /> : null}
    </div>
  );
}
