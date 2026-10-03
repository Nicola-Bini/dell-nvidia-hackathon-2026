# Build prompts: CJ (`cj` lane, Pro plan)

One prompt per work package, then the gate and freeze prompts. Each is a complete, separate
paste with its own `/goal`. Use them when:

- a session ended or ran out of usage and you want to restart at one package;
- you want a package done in its own fresh session (one package per session keeps context small);
- the clock hits a gate or the freeze.

The starter prompt in [cj.md](cj.md) already loops through all of these. Use the
starter by default and these when you need to target something.

Open your coding agent in the repo folder (or anywhere if you have not cloned yet), switch it
to its auto or accept-edits permission mode, and paste everything inside one block as one
message. Package details and proofs are in [../lanes/cj.md](../lanes/cj.md). In an
agent without `/goal`, delete the word `/goal` and paste the rest.

| Prompt | Use it for |
|---|---|
| wp1 | Widget shell |
| wp2 | Components |
| wp3 | Demo site and embed |
| wp4 | Interaction |
| wp5 | Overlay and states |
| wp6 | P1, only after the 18:30 gate: npm run build:mcp writing one self-cont |
| 17:00 gate | Run the 17:00 checks, fix or apply the cut line |
| 18:30 gate | Run Flow 1 and Flow 3 acceptance on the real stack |
| Freeze at 20:00 | Rehearse, record backups, finalize status |

## wp1: Widget shell

````text
/goal Work package wp1 of lane `cj` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp1 row in `docs/team/status/cj.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are CJ's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp1** in lane `cj`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Widget shell.** Vite, React, TypeScript in `apps/widget`. The `transport` interface with a fixture mock (reads `fixtures/surfaces/` through `index.json`) and a `fetch` implementation chosen by `VITE_SERVE_URL`. Layout: current surface in the centre, intent box and chips at the bottom. A gallery route that renders every golden surface
>
> Proof: `npm test` in `apps/widget`: each file in `fixtures/surfaces/` renders without error; `npm run build` writes `dist/`
> Unblocks: everything below

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `cj/wp1-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/cj.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp2: Components

````text
/goal Work package wp2 of lane `cj` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp2 row in `docs/team/status/cj.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are CJ's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp2** in lane `cj`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Components.** `Answer`, `MenuList` (badges: verified, or "not verified, ask staff"; `add_to_cart` only when the action is present), `HoursCard`, `BookingForm`, `CateringQuoteForm`, `AllergenNotice`, `GoalCTA`, and the generic `FactCard`, `ListCard`, `FormCard` (fields from configuration). Every string rendered as text, never as HTML. An unknown component renders nothing and does not crash
>
> Proof: Tests per component against its golden surface; one test that an unverified badge never shows the verified mark
> Unblocks: gate 17:00

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `cj/wp2-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/cj.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp3: Demo site and embed

````text
/goal Work package wp3 of lane `cj` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp3 row in `docs/team/status/cj.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are CJ's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp3** in lane `cj`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Demo site and embed.** `apps/demo-site`: a static site built from `demo/kenmore/seed.yaml`, using its `brand` colors and fonts (menu, hours, contact; JSON-LD; nav links with `data-cac-preset`; the two-line embed). `embed.js`: `/healthz` with a 1 s timeout and a silent no-op on failure, sandboxed iframe, launcher when `#cac-root` is absent, nav interception by `postMessage`
>
> Proof: Tests: with the box unreachable the page has no iframe and links still work; a preset link posts `cac:view`
> Unblocks: blake wp8

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `cj/wp3-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/cj.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp4: Interaction

````text
/goal Work package wp4 of lane `cj` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp4 row in `docs/team/status/cj.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are CJ's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp4** in lane `cj`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Interaction.** Presets through `view()`; forms through `action()` with field errors from HTTP 422; confirmation state; cart count; `session_id` in `sessionStorage`; goal button opens its preset with `?src=cta`
>
> Proof: Tests with the mock transport for submit success, submit 422, and cart count
> Unblocks: gate 17:00

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `cj/wp4-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/cj.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp5: Overlay and states

````text
/goal Work package wp5 of lane `cj` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp5 row in `docs/team/status/cj.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are CJ's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp5** in lane `cj`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Overlay and states.** Overlay polling `/v1/metrics` (latency, cache hits, model calls in flight, model host, leads, goal buttons shown and clicked), toggled by a key. Busy, error and offline states
>
> Proof: Test: the overlay renders the seam 3 metrics shape
> Unblocks: demo

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `cj/wp5-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/cj.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp6: P1, only after the 18:30 gate: npm run build:mcp writing one self-cont

````text
/goal Work package wp6 of lane `cj` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp6 row in `docs/team/status/cj.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are CJ's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp6** in lane `cj`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> P1, only after the 18:30 gate: `npm run build:mcp` writing one self-contained `dist-mcp/surface.html` with the host-tool transport (for nico's MCP server), then the history rail
>
> Proof: Build output is a single file with no external URLs
> Unblocks: nico wp7

This is a P1 package. Start only if the 18:30 gate in your lane file has passed (all P0 packages merged and the end-to-end checks green). If it has not, say so, name the failing check, and stop.

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `cj/wp6-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/cj.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## 17:00 gate

````text
/goal The 17:00 gate in docs/team/lanes/cj.md is decided: either every check it names passes against the latest origin/main and the result is recorded in docs/team/status/cj.md on origin/main, or the cut line for that gate has been applied, merged, and recorded with the reason. Also met if `TZ=America/New_York date` is after 17:30 and the status file records the state.

You are CJ's build agent on CAC (due 20:45 Eastern). Lane `cj`. Run the 17:00 gate for your lane. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; check out `origin/main` in a scratch branch. Read the "Gates and cut lines" section of your lane file and the status files of the lanes you depend on.
2. Run the proof of every package your lane has merged, then your lane's whole test suite, against the real services of the neighbouring lanes (not your mocks). Start what you need with `make db-up` and the other lanes' documented commands.
3. List what fails, in a table: check, expected, actual. Fix what is yours, smallest change first, red then green, shipped by the normal PR path from `AGENTS.md` section 3. File a request (`AGENTS.md` section 6) for what is another lane's.
4. If a check will still fail within 30 minutes, apply the cut line your lane file names for this gate: reduce scope as written there, merge it, and record in the status file what was cut and why.
5. Write the result into your status file under "Decisions" and merge.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## 18:30 gate

````text
/goal The 18:30 gate in docs/team/lanes/cj.md is decided: Flow 1 and Flow 3 acceptance (PRD sections 8) pass on the latest origin/main with every lane's real services, or the failing checks are fixed or cut with the reason, and the result is recorded in docs/team/status/cj.md on origin/main. Also met if `TZ=America/New_York date` is after 19:00 and the status file records the state.

You are CJ's build agent on CAC (due 20:45 Eastern). Lane `cj`. Run the 18:30 gate. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; read all four status files and every open request addressed to your lane.
2. Run the PRD Flow 1 acceptance list and Flow 3 acceptance list end to end, as far as they touch your lane, against the real stack: Serve API, Owner tools API, widget, and (for Nico) the box. Use the demo script in PRD section 15 as the checklist.
3. For each failure: fix it if it is yours (red then green, normal PR path), file a request if it is another lane's, and apply the cut line from your lane file if it cannot be fixed in 30 minutes.
4. Only when this gate passes may P1 packages start. Record pass or fail per check in your status file, and merge.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## Freeze at 20:00

````text
/goal From 20:00 the lane `cj` is frozen and demo-ready: origin/main contains everything your lane will ship, the demo script in PRD section 15 has been rehearsed twice end to end with your part working, docs/team/status/cj.md is final (packages, measured numbers, what was cut), and every flow your lane owns has a recording saved. Also met if `TZ=America/New_York date` is after 20:30.

You are CJ's build agent on CAC (submission due 20:45 Eastern). Lane `cj`. This is the freeze. From 20:00 no new features: only fixes that a rehearsal exposed. Never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/cj.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; confirm origin/main has all your merged packages; delete stale local branches and check no unmerged work of yours remains. Merge or discard it explicitly.
2. Rehearse the PRD section 15 demo script twice against the real stack, timing it. After each run list what broke or felt slow. Fix only what breaks the demo, red then green, shipped by the normal PR path.
3. Check your lane's fallbacks work: the busy and error states, the offline behaviour, and the recovery scripts or cut lines your lane file names.
4. Record every flow your lane owns as a backup (screen recording or terminal capture), saved outside the repo and listed in your status file.
5. Finalize `docs/team/status/cj.md`: every package with its PR and proof result, measured numbers, what was cut and why, and anything the team must know for the pitch. Merge it.
6. Tell me the one-line state of your lane: ready, or the single blocking issue.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````
