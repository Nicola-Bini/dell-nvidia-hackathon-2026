# Lane `cj`: surfaces

You build everything a visitor sees: the panel on the business's site, the site itself for
the demo, and the live overlay. Paths: `apps/` only.

Read: PRD sections 5, 8 (Flow 1 table and layout), 9 (rows W1 to W4, O1), 15 (demo
script). SCHEMA sections 7, 8.4, 8.5 (routes only), 8.7 (the `transport`).
`demo/kenmore/README.md`, `fixtures/README.md` and every file in `fixtures/surfaces/`. OWNERSHIP seams 3 and 4.

You are on a Pro plan: at most 2 subagents at a time, on `sonnet`. wp2 splits well: one
subagent per group of components, each with its own files.

## Work packages

| # | Package | Proof (one command, passing) | Unblocks |
|---|---|---|---|
| wp1 | **Widget shell.** Vite, React, TypeScript in `apps/widget`. The `transport` interface with a fixture mock (reads `fixtures/surfaces/` through `index.json`) and a `fetch` implementation chosen by `VITE_SERVE_URL`. Layout: current surface in the centre, intent box and chips at the bottom. A gallery route that renders every golden surface | `npm test` in `apps/widget`: each file in `fixtures/surfaces/` renders without error; `npm run build` writes `dist/` | everything below |
| wp2 | **Components.** `Answer`, `MenuList` (badges: verified, or "not verified, ask staff"; `add_to_cart` only when the action is present), `HoursCard`, `BookingForm`, `CateringQuoteForm`, `AllergenNotice`, `GoalCTA`, and the generic `FactCard`, `ListCard`, `FormCard` (fields from configuration). Every string rendered as text, never as HTML. An unknown component renders nothing and does not crash | Tests per component against its golden surface; one test that an unverified badge never shows the verified mark | gate 17:00 |
| wp3 | **Demo site and embed.** `apps/demo-site`: a static site built from `demo/kenmore/seed.yaml`, using its `brand` colors and fonts (menu, hours, contact; JSON-LD; nav links with `data-cac-preset`; the two-line embed). `embed.js`: `/healthz` with a 1 s timeout and a silent no-op on failure, sandboxed iframe, launcher when `#cac-root` is absent, nav interception by `postMessage` | Tests: with the box unreachable the page has no iframe and links still work; a preset link posts `cac:view` | blake wp8 |
| wp4 | **Interaction.** Presets through `view()`; forms through `action()` with field errors from HTTP 422; confirmation state; cart count; `session_id` in `sessionStorage`; goal button opens its preset with `?src=cta` | Tests with the mock transport for submit success, submit 422, and cart count | gate 17:00 |
| wp5 | **Overlay and states.** Overlay polling `/v1/metrics` (latency, cache hits, model calls in flight, model host, leads, goal buttons shown and clicked), toggled by a key. Busy, error and offline states | Test: the overlay renders the seam 3 metrics shape | demo |
| wp6 | P1, only after the 18:30 gate: `npm run build:mcp` writing one self-contained `dist-mcp/surface.html` with the host-tool transport (for nico's MCP server), then the history rail | Build output is a single file with no external URLs | nico wp7 |

## Working before the other lanes land

- Build against `fixtures/surfaces/` from the first minute; they are the contract. Blake's
  stub Serve API (his wp2) serves the same files; switch `VITE_SERVE_URL` to it when it
  lands and keep the mock for tests.
- If a fixture is wrong or a shape is missing, file a request to `blake`. Do not edit
  `fixtures/` or `demo/`.
- Look at the result in a browser at each package: phone width first, then desktop. The
  demo is judged on this screen.

## Gates and cut lines

- **17:00**: the widget renders every fixture and both forms submit.
- **18:30**: the demo script in PRD section 15 runs start to finish in the browser against
  the real Serve API on the box.
- If you are behind at 17:00: one plain style for all three generic components, no
  launcher (require `#cac-root`), overlay as plain text.
