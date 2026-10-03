# Agent harness

How coding agents are set up to build this repo. Update this file whenever a prompt, a
lane, or the loop changes.

| Piece | Where | What it does |
|---|---|---|
| Rules for every agent | [AGENTS.md](AGENTS.md) (`CLAUDE.md` imports it) | Lanes, git protocol, the work loop, subagent limits |
| Path ownership | [tools/lanes.conf](tools/lanes.conf), enforced by `tools/lane-check` and `.githooks/pre-push` | A branch may only change its own lane's paths |
| Seams between lanes | [docs/team/OWNERSHIP.md](docs/team/OWNERSHIP.md) | The interfaces lanes build against |
| Work packages | `docs/team/lanes/<lane>.md` | Ordered packages, each with a proof command, gates and cut lines |
| Start prompts | `docs/team/prompts/<lane>.md` | One paste per person: a `/goal` condition, setup, then the loop |
| Progress | `docs/team/status/<lane>.md` | Written by each lane's agent in every PR |
| Requests | `docs/team/requests/` | How one lane asks another for a change |

The product's own agent (the NemoClaw / OpenClaw agent in PRD Flow 3) lives in `agent/`
and is documented there by the `nico` lane.

## Changes

- 2026-10-03: initial harness. Four lanes (`blake`, `je`, `cj`, `nico`), one `/goal`
  prompt each, self-merged squash PRs gated by `tools/lane-check` and the package proof.
