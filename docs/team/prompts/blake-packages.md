# Build prompts: Blake (`blake` lane, Max plan)

One prompt per work package, then the gate and freeze prompts. Each is a complete, separate
paste with its own `/goal`. Use them when:

- a session ended or ran out of usage and you want to restart at one package;
- you want a package done in its own fresh session (one package per session keeps context small);
- the clock hits a gate or the freeze.

The starter prompt in [blake.md](blake.md) already loops through all of these. Use the
starter by default and these when you need to target something.

Open your coding agent in the repo folder (or anywhere if you have not cloned yet), switch it
to its auto or accept-edits permission mode, and paste everything inside one block as one
message. Package details and proofs are in [../lanes/blake.md](../lanes/blake.md). In an
agent without `/goal`, delete the word `/goal` and paste the rest.

| Prompt | Use it for |
|---|---|
| wp1 | Graph write side |
| wp2 | Serve API stub and fake model |
| wp3 | Pipeline, front half |
| wp4 | Pipeline, back half |
| wp5 | Actions and presets |
| wp6 | Safety and steer |
| wp7 | Privacy proofs |
| wp8 | End to end with the other lanes |
| wp9 | P1, only after the 18:30 gate: slot-masked cache, then JSON-LD ingest  |
| 17:00 gate | Run the 17:00 checks, fix or apply the cut line |
| 18:30 gate | Run Flow 1 and Flow 3 acceptance on the real stack |
| Freeze at 20:00 | Rehearse, record backups, finalize status |

## wp1: Graph write side

````text
/goal Work package wp1 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp1 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp1** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Graph write side.** `cac_common` (settings, `reindex_node`, `publish`; OWNERSHIP seam 2). Seed loader and `make seed`: registries from SCHEMA 5 and 6, nodes and edges from `demo/kenmore/seed.yaml` then `demo-overlay.yaml` (`ref` items become a second `HAS_ITEM` edge), catalog as `UIComponent` nodes, goals and `ADVANCES` edges, canary customer, then publish. `pg_trgm` and a full-text index for the fallback
>
> Files you may change for this package: `packages/cac_common/`, `scripts/`, `db/`, `tests/graph/`, `Makefile`
>
> Proof: `make db-reset seed && uv run pytest tests/graph`: PRD Flow 0 acceptance (at least 20 items, hours, 2 special-hours dates, 2 services, 2 goals visible publicly only as `steer` on 2 components); a private prop on a public node is absent from `kg_public`; `make db-check`
> Unblocks: je

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp1-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp2: Serve API stub and fake model

````text
/goal Work package wp2 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp2 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp2** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Serve API stub and fake model.** All SCHEMA 8.5 routes. `/v1/intent` answers the texts in `fixtures/surfaces/index.json` with their golden surfaces, anything else with the off-topic surface. Real `/v1/bootstrap`, `/v1/view/{preset}`, `/healthz`, `/v1/metrics` (shape in seam 3), static mounts, CORS, start-up refusal when the model host is not local. `tools/fake_llm`
>
> Files you may change for this package: `services/serve/`, `tools/fake_llm/`
>
> Proof: `uv run pytest` in `services/serve`: every entry in `index.json` returns its golden surface; start-up fails with a non-local `LLM_BASE_URL`
> Unblocks: cj, nico

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp2-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp3: Pipeline, front half

````text
/goal Work package wp3 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp3 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp3** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Pipeline, front half.** Normalize, slots (date resolver pinned to 2026-10-03 in tests; `closes` earlier than `opens` means the next day), `retrieve()` with vector entry plus the fixed expansions and the full-text fallback, per-request JSON Schema builder (never an empty `enum`; generic components read from `kg_public` each request)
>
> Files you may change for this package: `services/serve/`
>
> Proof: Unit tests for SCHEMA 8.2 and section 6 expansions; schema builder reproduces the 8.1 example shape
> Unblocks: wp4

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp3-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp4: Pipeline, back half

````text
/goal Work package wp4 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp4 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp4** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Pipeline, back half.** One constrained model call (temperature 0, 96 tokens, thinking off, 6 s timeout, `MODEL_MAX_INFLIGHT`), validator with one retry, binder rules 1 to 10, exact cache, request log, busy fallback
>
> Files you may change for this package: `services/serve/`
>
> Proof: `uv run pytest -m intents` over `demo/kenmore/intents.yaml`: 30 of 30 schema-valid, at least 27 of 30 right component, against `fake_llm` locally and the real model on the box; same question twice makes one model call
> Unblocks: gate 17:00

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp4-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp5: Actions and presets

````text
/goal Work package wp5 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp5 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp5** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Actions and presets.** `/v1/action` for the three submits with validation and HTTP 422 errors, lead insert without `RETURNING`, rate limits, presets, metrics counters, CTA counting
>
> Files you may change for this package: `services/serve/`
>
> Proof: Tests: a lead row exists (checked as `cac_owner`); past date is 422; fourth lead in an hour is refused
> Unblocks: cj

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp5-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp6: Safety and steer

````text
/goal Work package wp6 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp6 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp6** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Safety and steer.** SCHEMA section 10 rows: unverified diet, allergen never yields a safe list, goal steer, generic components for an agent-created label and form
>
> Files you may change for this package: `services/serve/`, `tests/`
>
> Proof: Those section 10 rows as tests, all green
> Unblocks: gate 17:00

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp6-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp7: Privacy proofs

````text
/goal Work package wp7 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp7 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp7** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Privacy proofs.** Permission script for the demo, canary script over every public endpoint (40 prompts)
>
> Files you may change for this package: `scripts/`, `tests/`
>
> Proof: `scripts/canary.py` exits 0 and the canary name is in no response
> Unblocks: demo

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp7-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp8: End to end with the other lanes

````text
/goal Work package wp8 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp8 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp8** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **End to end with the other lanes.** Gap loop and gift-card loop through je's API with no restart; pre-warm on publish; widget served at `/widget/`; then the same on the box with nico
>
> Files you may change for this package: `tests/e2e/`
>
> Proof: `uv run pytest tests/e2e`: SCHEMA section 10 "Gap loop" and "Agent adds a node type" rows
> Unblocks: gate 18:30

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp8-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp9: P1, only after the 18:30 gate: slot-masked cache, then JSON-LD ingest 

````text
/goal Work package wp9 of lane `blake` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp9 row in `docs/team/status/blake.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Blake's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp9** in lane `blake`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> P1, only after the 18:30 gate: slot-masked cache, then JSON-LD ingest of the demo site, then refinement
>
> Files you may change for this package: `services/serve/`, `scripts/`
>
> Proof: Tests per feature
> Unblocks: —

This is a P1 package. Start only if the 18:30 gate in your lane file has passed (all P0 packages merged and the end-to-end checks green). If it has not, say so, name the failing check, and stop.

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `blake/wp9-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/blake.md`. Do not start it.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## 17:00 gate

````text
/goal The 17:00 gate in docs/team/lanes/blake.md is decided: either every check it names passes against the latest origin/main and the result is recorded in docs/team/status/blake.md on origin/main, or the cut line for that gate has been applied, merged, and recorded with the reason. Also met if `TZ=America/New_York date` is after 17:30 and the status file records the state.

You are Blake's build agent on CAC (due 20:45 Eastern). Lane `blake`. Run the 17:00 gate for your lane. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; check out `origin/main` in a scratch branch. Read the "Gates and cut lines" section of your lane file and the status files of the lanes you depend on.
2. Run the proof of every package your lane has merged, then your lane's whole test suite, against the real services of the neighbouring lanes (not your mocks). Start what you need with `make db-up` and the other lanes' documented commands.
3. List what fails, in a table: check, expected, actual. Fix what is yours, smallest change first, red then green, shipped by the normal PR path from `AGENTS.md` section 3. File a request (`AGENTS.md` section 6) for what is another lane's.
4. If a check will still fail within 30 minutes, apply the cut line your lane file names for this gate: reduce scope as written there, merge it, and record in the status file what was cut and why.
5. Write the result into your status file under "Decisions" and merge.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## 18:30 gate

````text
/goal The 18:30 gate in docs/team/lanes/blake.md is decided: Flow 1 and Flow 3 acceptance (PRD sections 8) pass on the latest origin/main with every lane's real services, or the failing checks are fixed or cut with the reason, and the result is recorded in docs/team/status/blake.md on origin/main. Also met if `TZ=America/New_York date` is after 19:00 and the status file records the state.

You are Blake's build agent on CAC (due 20:45 Eastern). Lane `blake`. Run the 18:30 gate. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; read all four status files and every open request addressed to your lane.
2. Run the PRD Flow 1 acceptance list and Flow 3 acceptance list end to end, as far as they touch your lane, against the real stack: Serve API, Owner tools API, widget, and (for Nico) the box. Use the demo script in PRD section 15 as the checklist.
3. For each failure: fix it if it is yours (red then green, normal PR path), file a request if it is another lane's, and apply the cut line from your lane file if it cannot be fixed in 30 minutes.
4. Only when this gate passes may P1 packages start. Record pass or fail per check in your status file, and merge.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## Freeze at 20:00

````text
/goal From 20:00 the lane `blake` is frozen and demo-ready: origin/main contains everything your lane will ship, the demo script in PRD section 15 has been rehearsed twice end to end with your part working, docs/team/status/blake.md is final (packages, measured numbers, what was cut), and every flow your lane owns has a recording saved. Also met if `TZ=America/New_York date` is after 20:30.

You are Blake's build agent on CAC (submission due 20:45 Eastern). Lane `blake`. This is the freeze. From 20:00 no new features: only fixes that a rehearsal exposed. Never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/blake.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; confirm origin/main has all your merged packages; delete stale local branches and check no unmerged work of yours remains. Merge or discard it explicitly.
2. Rehearse the PRD section 15 demo script twice against the real stack, timing it. After each run list what broke or felt slow. Fix only what breaks the demo, red then green, shipped by the normal PR path.
3. Check your lane's fallbacks work: the busy and error states, the offline behaviour, and the recovery scripts or cut lines your lane file names.
4. Record every flow your lane owns as a backup (screen recording or terminal capture), saved outside the repo and listed in your status file.
5. Finalize `docs/team/status/blake.md`: every package with its PR and proof result, measured numbers, what was cut and why, and anything the team must know for the pitch. Merge it.
6. Tell me the one-line state of your lane: ready, or the single blocking issue.

You are on a Max plan: up to 5 subagents at once for parts of this package that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````
