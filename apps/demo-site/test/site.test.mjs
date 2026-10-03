import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { esc, time12 } from "../build.mjs";

const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const html = readFileSync(resolve(dist, "index.html"), "utf8");

test("has the two-line embed", () => {
  assert.match(html, /<div id="cac-root"><\/div>\s*<script src="\/embed\.js" async><\/script>/);
});

test("nav links carry data-cac-preset and still work as links", () => {
  for (const p of ["menu", "hours", "booking", "catering"]) {
    assert.match(html, new RegExp(`<a href="#[a-z]+" data-cac-preset="${p}">`));
  }
});

test("JSON-LD has the menu and the hours", () => {
  const m = html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s);
  assert.ok(m);
  const ld = JSON.parse(m[1]);
  assert.equal(ld["@type"], "Restaurant");
  assert.equal(ld.openingHoursSpecification.length, 3);
  const items = ld.hasMenu.hasMenuSection.flatMap((s) => s.hasMenuItem);
  assert.ok(items.length >= 110);
  assert.ok(items.some((i) => i.name.includes("Beyond Meat Burger")));
});

test("the launcher variant has no #cac-root", () => {
  const launcher = readFileSync(resolve(dist, "launcher.html"), "utf8");
  assert.doesNotMatch(launcher, /id="cac-root"/);
  assert.match(launcher, /<script src="\/embed\.js" async>/);
});

test("helpers escape and format", () => {
  assert.equal(esc(`<a href="x">'`), "&lt;a href=&quot;x&quot;&gt;&#39;");
  assert.equal(time12("02:00"), "2:00 AM");
  assert.equal(time12("13:05"), "1:05 PM");
  assert.equal(time12("00:30"), "12:30 AM");
});
