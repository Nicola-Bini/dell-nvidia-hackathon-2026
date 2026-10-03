import { afterEach, describe, expect, it, vi } from "vitest";
import { install } from "../src/embed/embed";

const BOX = "http://box.test";

function page(withRoot = true) {
  document.body.innerHTML = `
    <nav><a id="menu" href="#menu" data-cac-preset="menu">Menu</a>
    <a id="plain" href="#about">About</a></nav>
    ${withRoot ? '<div id="cac-root"></div>' : ""}`;
}

const up = vi.fn(async () => new Response("{}", { status: 200 })) as unknown as typeof fetch;
const down = vi.fn(async () => {
  throw new TypeError("Failed to fetch");
}) as unknown as typeof fetch;

function click(el: Element) {
  const e = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
  el.dispatchEvent(e);
  return e;
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("embed.js (wp3 proof)", () => {
  it("does nothing when the box is unreachable: no iframe, links still work", async () => {
    page();
    expect(await install({ box: BOX, fetchImpl: down })).toBeNull();
    expect(document.querySelector("iframe")).toBeNull();
    expect(click(document.getElementById("menu")!).defaultPrevented).toBe(false);
  });

  it("gives up after the timeout when /healthz hangs", async () => {
    page();
    const hang = ((_: string, init?: RequestInit) =>
      new Promise((_r, reject) =>
        init?.signal?.addEventListener("abort", () => reject(new Error("aborted"))),
      )) as typeof fetch;
    expect(await install({ box: BOX, fetchImpl: hang, timeoutMs: 20 })).toBeNull();
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("does nothing when /healthz answers an error status", async () => {
    page();
    const bad = (async () => new Response("", { status: 503 })) as typeof fetch;
    expect(await install({ box: BOX, fetchImpl: bad })).toBeNull();
  });

  it("mounts a sandboxed iframe in #cac-root", async () => {
    page();
    const e = await install({ box: BOX, fetchImpl: up });
    const iframe = document.querySelector("#cac-root iframe")!;
    expect(e).not.toBeNull();
    expect(iframe.getAttribute("src")).toBe(`${BOX}/widget/`);
    expect(iframe.getAttribute("sandbox")).toBe("allow-scripts allow-forms allow-same-origin");
  });

  it("a preset link posts cac:view to the widget", async () => {
    page();
    const post = vi.fn();
    const win = vi
      .spyOn(HTMLIFrameElement.prototype, "contentWindow", "get")
      .mockReturnValue({ postMessage: post } as unknown as Window);
    const e = (await install({ box: BOX, fetchImpl: up }))!;
    e.iframe.dispatchEvent(new Event("load"));
    expect(click(document.getElementById("menu")!).defaultPrevented).toBe(true);
    expect(post).toHaveBeenCalledWith({ type: "cac:view", preset: "menu" }, BOX);
    win.mockRestore();
  });

  it("leaves links without data-cac-preset alone", async () => {
    page();
    await install({ box: BOX, fetchImpl: up });
    expect(click(document.getElementById("plain")!).defaultPrevented).toBe(false);
  });

  it("adds a launcher when #cac-root is absent", async () => {
    page(false);
    await install({ box: BOX, fetchImpl: up });
    const launcher = document.querySelector<HTMLButtonElement>("[data-cac-launcher]")!;
    expect(launcher).not.toBeNull();
    expect(document.querySelector("[data-cac-panel] iframe")).not.toBeNull();
    launcher.click();
    expect(launcher.getAttribute("aria-expanded")).toBe("true");
  });
});
