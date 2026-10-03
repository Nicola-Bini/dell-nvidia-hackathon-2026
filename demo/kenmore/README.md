# Demo business: The Kenmore

Seed data for running CAC against a real site, [thekenmorebar.com](https://www.thekenmorebar.com/),
shaped to [docs/SCHEMA.md](../../docs/SCHEMA.md) section 9. Captured 3 October 2026.

| File | Contents |
|---|---|
| [seed.yaml](seed.yaml) | Facts read from the site, and nothing else |
| [demo-overlay.yaml](demo-overlay.yaml) | Assumptions the demo needs that the site does not state, plus the UI catalog |
| [intents.yaml](intents.yaml) | The 30 intent fixtures (schema section 10), written against this data |

The schema asks for one seed file. This folder splits it in two because the business is real:
`seed.yaml` can be shown to anyone, and every invented value sits in the overlay under a
comment that says so. The loader applies `seed.yaml`, then the overlay.

## What is in the seed

| Label | Count | Source |
|---|---|---|
| Business | 1 | Home page, JSON-LD |
| Location | 1 | Hours and Location page, JSON-LD |
| HoursSpec | 3 | Hours and Location page |
| Service | 3 | takeout (Toast link), catering, private events |
| MenuSection | 13 | Menus page |
| MenuItem | 110 | Menus page (121 listings; 11 appear in two sections) |
| Diet | 3 | vegetarian, vegan, gluten-free |
| Allergen | 9 | The FDA major allergens; no item edges |
| FAQ | 15 | About, kitchen hours, brunch, takeout, private events, burger add-ons, contact, jobs, press |
| BrandTrait | 4 | Site colors and fonts |

The overlay adds 1 Service (reservations), 2 SpecialHours, 2 Goals, the canary Customer, and
10 UIComponent entries.

## Assumptions in the overlay

These are not facts about The Kenmore. Each is needed by a flow or test in the schema.

| Assumption | Why the demo needs it | What the site actually says |
|---|---|---|
| The bar takes table requests (`svc_reservations`) | `BookingForm`, the bookings goal, the goal-steer test | No reservation flow. The JSON-LD has a `ReserveAction` pointing at a placeholder anchor |
| Closed on Thanksgiving 2026 and 4 July 2027 | Date-resolver fixtures | No holiday hours listed |
| The Beyond Meat Burger's vegetarian tag is owner-verified | A verified badge; the two-friends MCP test | The item is named "(Vegetarian)", but no owner has verified anything |
| Two goals with priorities 5 and 4 | `steer` weights for `GoalCTA` | Nothing; goals are private by design |

## Where this site does not fit the schema

Loading a real site turned up six points the schema does not cover yet.

1. **Hours run past midnight.** The bar closes at 01:00 or 02:00. `HoursSpec` has only
   `opens` and `closes`, so the seed uses the rule "`closes` earlier than `opens` means the
   next day". `HoursCard` must apply it, and "are you open at 12:30am Saturday" must check
   Friday's row.
2. **The same item is listed in two sections.** Eleven beers are under Draft Beer and under
   their style. The seed defines each once and uses `{ ref: mi_... }` for the second listing:
   one node, two `HAS_ITEM` edges. The section 9 format nests items under one section and has
   no `ref`.
3. **Items with two prices.** Wines list two prices with no labels (probably glass and
   bottle), and the nachos list full and half trays. `MenuItem` has a single `price_cents`.
   The seed stores the first price and appends "Listed prices: …" to the description.
4. **The cooked-to-order asterisk.** Five burgers carry the raw-or-undercooked mark. The seed
   keeps it as `cooked_to_order: true`, which is not in `MenuItem.public_props`, so publish
   drops it. The advisory is also an FAQ. Adding the prop is a ready-made `add_prop` change
   for the agent demo.
5. **Kitchen hours and brunch hours** have no typed label. They are FAQs, as section 5
   prescribes, so "is the kitchen open at midnight" gets the FAQ text, not a computed answer.
6. **Takeout has no component.** `Service[takeout]` carries the Toast `booking_url`, but no
   P0 component binds it, and `FactCard` is for labels with no purpose-built component. The
   seed adds an FAQ with the ordering link so the question is answerable.

`logo_url` on Business is in the same position as `cooked_to_order`: stored, not published.

## Open gaps

The site does not answer these, so they should come back as `kind: gap` and make good
material for the gap loop: parking and transit, holiday hours, catering minimum headcount and
menu, allergen content of any item, vegan options, happy hour or game-day specials, whether
the bar takes reservations, and desserts and specials (both tabs are empty).

## Refreshing

The site says the beer list rotates weekly, so the menu block in `seed.yaml` goes stale. It
was generated from the Menus page markup (`.tabs-panel` → `.menu-section` → `li.menu-item`);
the text is verbatim, typos included. Re-run `intents.yaml` id checks after any refresh:
`mi_guinness`, `mi_chicken_wings`, `mi_shroom_lover_burger` and `mi_the_veg_dog` are
referenced by name.
