// Builds the demo "existing site" for The Kenmore from demo/kenmore/seed.yaml into dist/.
// The page stands in for the bar's real site: header and nav, menu, hours, contact, JSON-LD,
// nav links marked data-cac-preset, and the two-line CAC embed (SCHEMA section 7).
//
// CAC_BOX_URL sets the box origin for the embed script; empty (the default) means the page is
// served by the Serve API under /site/ and the script is /embed.js on the same origin.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";

const here = dirname(fileURLToPath(import.meta.url));
const seedPath = resolve(here, "../../demo/kenmore/seed.yaml");
const outDir = resolve(here, "dist");
const box = (process.env.CAC_BOX_URL ?? "").replace(/\/$/, "");

const DAY_NAMES = { mon: "Monday", tue: "Tuesday", wed: "Wednesday", thu: "Thursday",
  fri: "Friday", sat: "Saturday", sun: "Sunday" };
const SCHEMA_DAYS = { mon: "Monday", tue: "Tuesday", wed: "Wednesday", thu: "Thursday",
  fri: "Friday", sat: "Saturday", sun: "Sunday" };
const NAV = [
  { label: "Menu", preset: "menu", href: "#menu" },
  { label: "Hours", preset: "hours", href: "#hours" },
  { label: "Book a table", preset: "booking", href: "#contact" },
  { label: "Catering", preset: "catering", href: "#catering" },
];

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function price(cents) {
  return typeof cents === "number" ? `$${(cents / 100).toFixed(2)}` : "";
}

export function time12(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h >= 12 ? "PM" : "AM";
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${suffix}`;
}

function dayRange(days) {
  const first = DAY_NAMES[days[0]];
  return days.length === 1 ? first : `${first} – ${DAY_NAMES[days[days.length - 1]]}`;
}

/** Resolve `{ ref: id }` listings to the item defined in another section. */
export function menuSections(seed) {
  const byId = new Map();
  for (const s of seed.sections) for (const i of s.items) if (!i.ref) byId.set(i.id, i);
  return seed.sections.map((s) => ({
    id: s.id,
    name: s.name,
    items: s.items.map((i) => (i.ref ? byId.get(i.ref) : i)).filter(Boolean),
  }));
}

export function jsonLd(seed, sections) {
  const { business: b, location: l } = seed;
  const data = {
    "@context": "https://schema.org",
    "@type": "Restaurant",
    name: b.name,
    description: b.tagline,
    url: b.url,
    telephone: b.phone,
    servesCuisine: b.cuisine,
    priceRange: b.price_range,
    address: { "@type": "PostalAddress", streetAddress: l.street, addressLocality: l.city,
      addressRegion: l.region, postalCode: l.postal, addressCountry: "US" },
    openingHoursSpecification: seed.hours.map((h) => ({
      "@type": "OpeningHoursSpecification",
      dayOfWeek: h.days.map((d) => SCHEMA_DAYS[d]),
      opens: h.opens,
      closes: h.closes,
    })),
    hasMenu: {
      "@type": "Menu",
      hasMenuSection: sections.map((s) => ({
        "@type": "MenuSection",
        name: s.name,
        hasMenuItem: s.items.map((i) => ({
          "@type": "MenuItem",
          name: i.name,
          description: i.description || undefined,
          offers: { "@type": "Offer", price: (i.price_cents / 100).toFixed(2),
            priceCurrency: "USD" },
        })),
      })),
    },
  };
  // Escape "<" so no value can close the script element.
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

function navHtml() {
  return NAV.map((n) =>
    `<a href="${n.href}" data-cac-preset="${n.preset}">${esc(n.label)}</a>`).join("\n        ");
}

function menuHtml(sections) {
  return sections.map((s) => `
      <section class="menu-section" id="${esc(s.id)}">
        <h3>${esc(s.name)}</h3>
        <ul>${s.items.map((i) => `
          <li class="menu-item"><span class="name">${esc(i.name)}</span>
            <span class="price">${esc(price(i.price_cents))}</span>
            ${i.description ? `<p>${esc(i.description)}</p>` : ""}</li>`).join("")}
        </ul>
      </section>`).join("");
}

function hoursHtml(hours) {
  return hours.map((h) => {
    const next = h.closes < h.opens ? " (next day)" : "";
    return `<tr><th>${esc(dayRange(h.days))}</th>` +
      `<td>${esc(time12(h.opens))} – ${esc(time12(h.closes))}${next}</td></tr>`;
  }).join("\n          ");
}

function embedHtml(withRoot) {
  const root = withRoot ? `<div id="cac-root"></div>\n    ` : "";
  return `${root}<script src="${esc(box)}/embed.js" async></script>`;
}

export function page(seed, { withRoot = true } = {}) {
  const { business: b, location: l } = seed;
  const sections = menuSections(seed);
  const catering = seed.services.find((s) => s.kind === "catering");
  const tel = b.phone.replace(/\s+/g, "");
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${esc(b.name)} | Kenmore Square, Boston</title>
  <meta name="description" content="${esc(b.tagline)}" />
  <link rel="stylesheet" href="site.css" />
  <script type="application/ld+json">${jsonLd(seed, sections)}</script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="#top">${esc(b.name)}</a>
    <nav>
        ${navHtml()}
        <a href="#contact">Contact</a>
    </nav>
  </header>
  <main id="top">
    <section class="hero">
      <h1>${esc(b.name)}</h1>
      <p>${esc(b.tagline)}</p>
    </section>
    <section class="cac-slot" aria-label="Ask ${esc(b.name)}">
    ${embedHtml(withRoot)}
    </section>
    <section id="menu" class="menu">
      <h2>Menu</h2>${menuHtml(sections)}
    </section>
    <section id="hours" class="hours">
      <h2>Hours</h2>
      <table>
          ${hoursHtml(seed.hours)}
      </table>
    </section>
    <section id="catering" class="catering">
      <h2>Catering</h2>
      <p>${esc(catering?.details ?? "")}</p>
    </section>
    <section id="contact" class="contact">
      <h2>Location and contact</h2>
      <address>${esc(l.street)}<br />${esc(l.city)}, ${esc(l.region)} ${esc(l.postal)}</address>
      <p><a href="tel:${esc(tel)}">${esc(b.phone)}</a> ·
        <a href="${esc(l.maps_url)}" rel="noopener">Directions</a></p>
    </section>
  </main>
  <footer class="site-footer">Demo copy of ${esc(b.url)} for CAC. Facts from the site,
    captured 3 October 2026.</footer>
</body>
</html>
`;
}

export function css(seed) {
  const trait = (id) => seed.brand.find((t) => t.id === id)?.value;
  return `:root { --bg: ${trait("trait_color_background") ?? "#111"};
  --fg: ${trait("trait_color_text") ?? "#fff"}; --accent: #c9a45c;
  --heading: "${trait("trait_font_heading") ?? "serif"}", "Copperplate", "Cinzel", Georgia, serif;
  --body: "${trait("trait_font_body") ?? "serif"}", Garamond, Georgia, serif; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 18px/1.5 var(--body); }
a { color: var(--accent); }
h1, h2, h3, .brand { font-family: var(--heading); text-transform: uppercase; letter-spacing: .08em; }
.site-header { position: sticky; top: 0; z-index: 10; display: flex; flex-wrap: wrap; gap: 8px 24px;
  align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--bg);
  border-bottom: 1px solid #333; }
.brand { color: var(--fg); text-decoration: none; font-size: 20px; }
nav { display: flex; flex-wrap: wrap; gap: 4px 16px; }
nav a { color: var(--fg); text-decoration: none; font-size: 15px; text-transform: uppercase;
  letter-spacing: .06em; }
nav a:hover { color: var(--accent); }
main { max-width: 960px; margin: 0 auto; padding: 0 16px 48px; }
.hero { text-align: center; padding: 40px 0 24px; }
.hero h1 { font-size: clamp(32px, 8vw, 56px); margin: 0 0 8px; }
.cac-slot { margin: 0 0 32px; }
#cac-root iframe { display: block; width: 100%; height: min(640px, 80vh); border: 1px solid #333;
  border-radius: 12px; background: var(--bg); }
.menu-section ul { list-style: none; padding: 0; margin: 0; }
.menu-item { padding: 8px 0; border-bottom: 1px solid #2a2a2a; }
.menu-item .name { font-weight: 600; }
.menu-item .price { float: right; }
.menu-item p { margin: 2px 0 0; color: #bbb; font-size: 16px; }
.hours th { text-align: left; padding-right: 24px; font-weight: 400; }
.site-footer { text-align: center; color: #888; font-size: 14px; padding: 24px 16px; }
`;
}

function main() {
  const seed = parse(readFileSync(seedPath, "utf8"));
  mkdirSync(outDir, { recursive: true });
  writeFileSync(resolve(outDir, "index.html"), page(seed));
  // Same site with no #cac-root: the embed adds its launcher button instead.
  writeFileSync(resolve(outDir, "launcher.html"), page(seed, { withRoot: false }));
  writeFileSync(resolve(outDir, "site.css"), css(seed));
  console.log(`demo-site: wrote ${outDir} (index.html, launcher.html, site.css)`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
