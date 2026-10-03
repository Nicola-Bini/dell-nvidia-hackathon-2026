# Fixtures

Golden Surface JSON (docs/SCHEMA.md 8.4) for the widget, the stub Serve API and the binder
tests. Every fact comes from `demo/kenmore/seed.yaml` plus `demo-overlay.yaml`; the 30 intents
live in `demo/kenmore/intents.yaml` and are not copied here. Dates assume 2026-10-03.

Check everything with `uv run --with pyyaml python fixtures/validate.py`. It exits non-zero if
an id is not in the seed or overlay, a title is too long, a menu item has drifted from the
seed, or `index.json` points at a missing intent or file.

`surfaces/index.json` maps an intent text (exact, as in `intents.yaml`) to the surface file a
stub should return for it. It is not a Surface, so skip it when globbing `surfaces/*.json`.
Intents with no entry have no golden surface. `busy_fallback`, `preset_menu`, `gift_cards`
(what appears after the agent adds a GiftCard type and form) and `fact_card` have no intent.

| Topic | Convention |
|---|---|
| Badges | `badges` lists every diet tag on the item as `{ diet, verified }`, in seed diet order, not only the diet asked for. `verified: false` renders "not verified, ask staff", never a badge. Only the Beyond Meat Burger is verified |
| List order | Diet lists: owner-verified items first, then unverified, each in menu order. Section lists: site order |
| Cap | At most 12 items, then `more: { label: "Full menu", preset: "menu" }`; otherwise `more: null`. Preset surfaces are exempt |
| Missing description | `description` is `""` when the seed has none |
| Two prices | `price` is the first listed price; the rest is the "Listed prices: ..." sentence the seed appends to `description` |
| Unavailable items | Still listed; the schema has no `available` field in MenuList data, so the description is the only marker |
| Items in two sections | Appear under both sections in `preset_menu`, with the same id |
| `add_to_cart` | One view-level action `{ name: "add_to_cart", handler: "client" }` on the MenuList, only when `order` is true. The client applies it per item |
| AllergenNotice | `data.allergen` is the lowercased allergen name ("peanuts"), ready to drop into the fixed sentence, or `null` for the notice inserted beside a MenuList. `contains` is empty: the seed has no allergen edges |
| GoalCTA | Last view, at most one, on every bound surface with no BookingForm or CateringQuoteForm. Label is the booking entry's `cta_label`; action `open_view:booking`, handler client. The fixed gap and off-topic surfaces have none |
| Title | First view's `data.title` if it has one, else the catalog `rail_label`; 24 characters at most. Gap is "Call us", off topic is "Help" |
| `say` | The catalog entry's `say`; `""` when the catalog has `null`. HoursCard gets the computed sentence. Presets say "Here is our menu." |
| Chips | The first view's catalog `chips`; gap and off topic use `bootstrap.chips` |
| Hours past midnight | `opens` and `closes` stay as stored ("11:00", "02:00"). `closes` earlier than `opens` means the next day; `status` is for the service day in `date`. `say` and `text` spell it out in 12-hour time |
| Closed day | `status: "closed"`, `opens` and `closes` null, `note` from SpecialHours |
| Verification | `verified` is false and `verified_at` null on Answer and FactCard: nothing in the seed is owner-verified |
| Missing props | `min_headcount: null` (the site states none); FactCard omits props the node does not have |
| Configured forms | FormCard `data.form` is the catalog id, `fields` and `submit_label` are copied from the entry, `title` is its `rail_label` |
| `meta` | `cache` is "miss", or "preset" for `preset_menu` and `busy_fallback`. `model` is always "local". `graph_version` is 7, and 8 in `gift_cards`. `latency_ms` is illustrative |
| `kind` | "answer", "gap", "off_topic", or "preset" for surfaces served with no model call |
