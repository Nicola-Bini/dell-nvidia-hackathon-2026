---
name: cac-owner
description: Read what visitors ask the business, ask the owner about the top unanswered question, record the owner's reply, and propose graph changes. Use on every heartbeat and when the owner messages.
---

# cac-owner

Run `python3 /sandbox/agent/cac_owner.py <command>` (it prints one JSON document). It reads
`OWNER_BASE_URL` and `OWNER_TOOLS_TOKEN` from the environment. Never print the token.

| Command | Use |
|---|---|
| `digest` | Counts only: questions today, top topics, open gaps, pending changes, new leads |
| `topics`, `gaps`, `schema`, `changes [--state pending]` | Read-only views |
| `ask-top-gap` | Marks the most-asked open gap `asked`; returns `message` to send to the owner |
| `answer <gap_id> "<owner's exact words>"` | Records the reply as a verified FAQ, then publishes |
| `special-hours <date> [--closed] [--opens HH:MM --closes HH:MM] [--note ..]` | Owner said "we're closed on the 24th" |
| `propose <plan.json> --topic "<topic>"` | Posts the plan's changes with reason and evidence from the topic's count |
| `change <action> --target JSON --after JSON --reason .. --evidence ..` | One change |
| `publish` | Publish and pre-warm |

Plans live in `plans/`: `gift_card.json` creates the GiftCard type, two cards and a request form.
