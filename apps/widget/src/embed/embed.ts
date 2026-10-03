// embed.js (SCHEMA section 7): the one script tag a business adds to its existing site.
// If the box does not answer /healthz within 1 s it does nothing at all, so the site behaves
// exactly as before. Otherwise it mounts the widget in a sandboxed iframe and routes nav links
// marked data-cac-preset to the widget.

export interface EmbedOptions {
  /** Box origin, e.g. https://box.example. */
  box: string;
  doc?: Document;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

export interface Embedded {
  iframe: HTMLIFrameElement;
  open(preset?: string): void;
}

const PRESETS = new Set(["menu", "booking", "catering", "hours"]);

export async function healthy(box: string, fetchImpl: typeof fetch, timeoutMs: number) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetchImpl(`${box}/healthz`, { signal: ctrl.signal, cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

function makeIframe(doc: Document, box: string): HTMLIFrameElement {
  const iframe = doc.createElement("iframe");
  // ?cac_overlay=1 on the host page starts the widget with the metrics overlay shown.
  const overlay = new URLSearchParams(doc.location?.search ?? "").get("cac_overlay") === "1";
  iframe.src = `${box}/widget/${overlay ? "?overlay=1" : ""}`;
  iframe.title = "Ask us";
  iframe.setAttribute("sandbox", "allow-scripts allow-forms allow-same-origin");
  iframe.setAttribute("loading", "lazy");
  iframe.style.cssText = "display:block;width:100%;height:100%;min-height:560px;border:0;";
  return iframe;
}

/** No #cac-root: a launcher button bottom right that toggles a floating panel. */
function mountLauncher(doc: Document, iframe: HTMLIFrameElement) {
  const panel = doc.createElement("div");
  panel.setAttribute("data-cac-panel", "");
  panel.style.cssText =
    "position:fixed;right:16px;bottom:84px;z-index:2147483646;" +
    "width:min(400px,calc(100vw - 32px));" +
    "height:min(640px,calc(100vh - 120px));border-radius:12px;overflow:hidden;display:none;" +
    "box-shadow:0 8px 32px rgba(0,0,0,.45);background:#111;";
  panel.appendChild(iframe);
  const button = doc.createElement("button");
  button.type = "button";
  button.setAttribute("data-cac-launcher", "");
  button.setAttribute("aria-expanded", "false");
  button.textContent = "Ask us";
  button.style.cssText =
    "position:fixed;right:16px;bottom:16px;z-index:2147483647;padding:14px 20px;border:0;" +
    "border-radius:999px;background:#c9a45c;color:#111;font:600 16px system-ui,sans-serif;" +
    "cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.4);";
  const show = (visible: boolean) => {
    panel.style.display = visible ? "block" : "none";
    button.setAttribute("aria-expanded", String(visible));
    button.textContent = visible ? "Close" : "Ask us";
  };
  button.addEventListener("click", () => show(panel.style.display === "none"));
  doc.body.appendChild(panel);
  doc.body.appendChild(button);
  return () => show(true);
}

/** The backquote key on the host page toggles the widget's metrics overlay. */
function forwardOverlayKey(doc: Document, iframe: HTMLIFrameElement, box: string) {
  doc.addEventListener("keydown", (e) => {
    const t = e.target as HTMLElement | null;
    if (e.key !== "`" || (t && ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName))) return;
    iframe.contentWindow?.postMessage({ type: "cac:overlay" }, box);
  });
}

/** Post `cac:view` to the widget once it has loaded; queue until then. */
function viewSender(iframe: HTMLIFrameElement, box: string) {
  let loaded = false;
  let pending: string | null = null;
  const post = (preset: string) =>
    iframe.contentWindow?.postMessage({ type: "cac:view", preset }, box);
  iframe.addEventListener("load", () => {
    loaded = true;
    if (pending) post(pending);
    pending = null;
  });
  return (preset: string) => (loaded ? post(preset) : (pending = preset));
}

function interceptNav(doc: Document, open: (preset: string) => void) {
  doc.addEventListener("click", (e) => {
    const target = e.target as Element | null;
    const link = target?.closest?.("[data-cac-preset]");
    const preset = link?.getAttribute("data-cac-preset") ?? "";
    if (!link || !PRESETS.has(preset)) return;
    if (e instanceof MouseEvent && (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0)) return;
    e.preventDefault();
    open(preset);
  });
}

export async function install(opts: EmbedOptions): Promise<Embedded | null> {
  const doc = opts.doc ?? document;
  const box = opts.box.replace(/\/$/, "");
  const ok = await healthy(box, opts.fetchImpl ?? fetch.bind(globalThis), opts.timeoutMs ?? 1000);
  if (!ok) return null;
  const iframe = makeIframe(doc, box);
  const root = doc.getElementById("cac-root");
  let reveal = () => root?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  if (root) root.appendChild(iframe);
  else reveal = mountLauncher(doc, iframe);
  const send = viewSender(iframe, box);
  const open = (preset?: string) => {
    reveal();
    if (preset) send(preset);
  };
  interceptNav(doc, open);
  forwardOverlayKey(doc, iframe, box);
  return { iframe, open };
}
