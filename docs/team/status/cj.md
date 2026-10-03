# Status: `cj` (CJ)

Updated by this lane's agent in every PR. Format: AGENTS.md section 9.

| Package | State | PR | Proof and result |
|---|---|---|---|
| wp1 Widget shell | merged in this PR | (this PR) | `npm test` in `apps/widget` -> 21 passed (every file in `fixtures/surfaces/` renders); `npm run build` writes `dist/` (14:53 ET) |
| wp2 Components | merged in this PR | (this PR) | `npm test` in `apps/widget` -> 46 passed: a test per component on its golden view, "an unverified badge never shows the verified mark", XSS strings render as text (15:05 ET) |
| wp3 Demo site and embed | merged in this PR | (this PR) | `npm test` in `apps/widget` -> 53 passed (embed: box unreachable or slow -> no iframe and links still work; a preset link posts `cac:view`); `npm test` in `apps/demo-site` -> 5 passed (15:20 ET) |
| wp4 Interaction | not started | | |
| wp5 Overlay and states | not started | | |
| wp6 MCP build, history rail (P1) | not started | | |

## What other lanes can rely on now

- `npm ci && npm run build` in `apps/widget` writes `apps/widget/dist/` with relative asset
  paths, so the Serve API can mount it at `/widget/` (seam 3).
- A build talks to the Serve API on the same origin (`/v1/...`). `VITE_SERVE_URL=<origin>`
  points it elsewhere; `VITE_SERVE_URL=mock` or `?mock=1` uses the golden fixtures.
- `npm run dev` uses the fixture mock; `#/gallery` renders every golden surface.
- `npm run build` in `apps/widget` also writes `dist/embed.js` (one IIFE, about 2.6 kB). It
  takes the box origin from its own `src`.
- `npm run build` in `apps/demo-site` writes `dist/index.html` (embed in `#cac-root`),
  `dist/launcher.html` (no `#cac-root`, so a launcher appears) and `dist/site.css`. The
  embed is `<script src="/embed.js">`, the same origin as `/site/`; set `CAC_BOX_URL` to point
  it at another box.
- `npm run preview` in `apps/demo-site` is a fake box on :8099 for looking at the demo
  without the Serve API (`/healthz` 200, `/site/`, `/widget/`, `/embed.js`).

## Measured numbers

## Decisions

- 14:50 Transport chosen at build time: `VITE_SERVE_URL` unset means the mock in dev and
  same-origin in a build. There is no URL-parameter override of the API origin, because
  forms post visitor data (only `?mock=1`, which sends nothing anywhere).
- 14:50 Components never call the transport; the shell passes a `SurfaceContext`
  (`openView`, `submit`, `addToCart`, `ask`). An unknown component, or one that throws,
  renders nothing (error boundary per view).
- 14:50 The mock answers `index.json` intents with their golden files, "do you sell gift
  cards" with `gift_cards.json`, and everything else with `off_topic.json`. Presets: menu
  -> `preset_menu`, hours -> `hours_saturday`, booking and catering -> the form fixtures with
  an empty prefill.
- 14:50 Node 24 on this laptop; `engines` says `>=22`, matching SCHEMA's Node 22.

- 15:05 Forms keep native `required` attributes, but the widget never blocks a submit in
  JS: the server's 422 errors are shown next to each field (unknown fields at the top).
- 15:05 `BookingForm` with a `booking_url` shows only a link to that booking page.

- 15:20 embed.js treats any non-2xx `/healthz` as down, as well as a timeout. Only the four
  P0 presets are intercepted, and modified clicks (ctrl, cmd, shift, middle) are left to the
  browser. Messages go to the box origin only.

## Requests handled

None yet.

## Blocked on

- `gh auth login` on this laptop (NEED_INPUT), so PRs can be opened and merged.
