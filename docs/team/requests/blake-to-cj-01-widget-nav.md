# Request: blake to cj: three small widget points from the integration run

Your branch `cj/wp5-overlay` was built and served by the real Serve API (`/widget/`,
`/embed.js`, `/site/`) and driven in a browser: every flow works, with no CORS, 404 or
shape error (bootstrap, nine typed intents, presets from the nav links, the goal button and
`?src=cta`, booking, catering and FormCard submits, 422 field errors, the 429 refusal, the
launcher, the overlay). Nothing here blocks the demo.

1. **`bootstrap.nav` is not rendered.** `/v1/bootstrap` returns `nav` (Menu, Hours, Book,
   Catering) but `App.tsx` uses only the name, tagline and chips, so opened directly (or in
   the launcher panel) the widget has no way to the Hours or Catering presets.
   **Proposal.** Render `boot.nav` as header buttons that call `ctx.openView(n.preset)`.
2. **HoursCard shows the raw ISO date** ("2026-10-03") beside the status. The surface's
   `say` already has the sentence ("Open on Saturday 3 October 2026, 11:00 AM to 2:00 AM.").
3. **The overlay covers the first line of the surface** at the top right.

Served by the Serve API as of PR "chips resolve": a chip or nav label that names a preset
("See the menu", "Book a table", "Menu", "Hours") returns that preset surface
(`kind: "preset"`) from `/v1/intent` with no model call, so chips sent as text always
resolve. No change needed on your side.

**By.** Before the 18:30 gate, if time allows.
