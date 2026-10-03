# Request: blake to nico: two fields in the agent's gift-card plan

`agent/plans/gift_card.json` was run through je's API (branch `je/wp4-owner-actions`) and the
real Serve API. All four changes were accepted and, once approved, "do you sell gift
cards?" returns the `ListCard` and the form with no restart.

1. The form is created with no `rail_label` (and `title` is not a catalog key), so it had no
   title. The Serve API now falls back to the node name, but please send
   `"rail_label": "Request a gift card"` in the `create_component` change.
2. The plan's fields arrive as `type: "text"` with no `required` and no `options`. For the
   demo form use `required: true` on name and contact, and
   `{ "name": "amount", "type": "select", "options": ["$25", "$50"], "required": true }`.
   The Serve API validates submissions against exactly these fields.

**By.** Before the 18:30 gate.
