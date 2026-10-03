# Build prompts: Je (`je` lane, Pro plan)

One prompt per work package, then the gate and freeze prompts. Each is a complete, separate
paste with its own `/goal`. Use them when:

- a session ended or ran out of usage and you want to restart at one package;
- you want a package done in its own fresh session (one package per session keeps context small);
- the clock hits a gate or the freeze.

The starter prompt in [je.md](je.md) already loops through all of these. Use the
starter by default and these when you need to target something.

Open your coding agent in the repo folder (or anywhere if you have not cloned yet), switch it
to its auto or accept-edits permission mode, and paste everything inside one block as one
message. Package details and proofs are in [../lanes/je.md](../lanes/je.md). In an
agent without `/goal`, delete the word `/goal` and paste the rest.

| Prompt | Use it for |
|---|---|
| wp1 | Skeleton and tiers |
| wp2 | Read endpoints |
| wp3 | Change engine |
| wp4 | Owner-only actions and inbox |
| wp5 | Topics, gaps, the owner's words |
| wp6 | Demo seeding |
| wp7 | P1, only after the 18:30 gate: digest wording, owner-initiated facts |
| 17:00 gate | Run the 17:00 checks, fix or apply the cut line |
| 18:30 gate | Run Flow 1 and Flow 3 acceptance on the real stack |
| Freeze at 20:00 | Rehearse, record backups, finalize status |

## wp1: Skeleton and tiers

````text
/goal Work package wp1 of lane `je` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp1 row in `docs/team/status/je.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Je's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp1** in lane `je`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Skeleton and tiers.** FastAPI on 8081, role `cac_owner`, `/healthz`. Two credentials: `OWNER_TOOLS_TOKEN` (agent) and `OWNER_INBOX_TOKEN` (owner). Tier assignment as a pure function of (action, target, current state, `CAC_AUTONOMY`) covering every row of the SCHEMA 8.6 tier table
>
> Proof: `uv run pytest` in `services/owner`: one test per tier-table cell; agent token refused on an owner-only route
> Unblocks: nico

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `je/wp1-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/je.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp2: Read endpoints

````text
/goal Work package wp2 of lane `je` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp2 row in `docs/team/status/je.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Je's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp2** in lane `je`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Read endpoints.** `/owner/schema`, `/owner/graph/search`, `/owner/changes`, `/owner/digest`. Locked labels by name only; never lead payloads or visitor text
>
> Proof: Tests: a Customer node and a Goal are never returned to the agent token
> Unblocks: nico

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `je/wp2-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/je.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp3: Change engine

````text
/goal Work package wp3 of lane `je` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp3 row in `docs/team/status/je.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Je's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp3** in lane `je`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Change engine.** `POST /owner/changes` for all ten actions: apply to `kg`, store `before` and `after`, force `source_type = agent` and `verified_by_owner = false`, call `reindex_node`, refuse the locked tier with a reason, publish when the tier is `auto`
>
> Proof: Tests: SCHEMA section 10 "Agent tags a dish" and "Agent tries the locked tier"
> Unblocks: gate 17:00

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `je/wp3-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/je.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp4: Owner-only actions and inbox

````text
/goal Work package wp4 of lane `je` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp4 row in `docs/team/status/je.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Je's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp4** in lane `je`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Owner-only actions and inbox.** `approve`, `reject`, `revert`, `/owner/verify`. `GET /owner/inbox` as an HTML page (pending changes with reason and evidence, unverified tags with confirm, applied changes with revert, new leads, open gaps) and `/owner/inbox.json`
>
> Proof: Tests: section 10 "Agent adds a node type", "Agent adds an element", "Agent edits a dish" (approve, then revert restores the old text)
> Unblocks: gate 17:00

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `je/wp4-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/je.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp5: Topics, gaps, the owner's words

````text
/goal Work package wp5 of lane `je` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp5 row in `docs/team/status/je.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Je's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp5** in lane `je`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Topics, gaps, the owner's words.** `/owner/topics` (fold new `ops.intent_log` rows using `ops.sync_state`, create or update `KnowledgeGap` nodes), `/owner/gaps`, `/owner/gaps/{id}/asked` (one `asked` at a time), `/owner/answers`, `/owner/special-hours`, `/owner/publish` with pre-warm (seam 5)
>
> Proof: Tests: section 10 "Gap loop" up to publish; topics never contain raw visitor text
> Unblocks: nico, blake wp8

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `je/wp5-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/je.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp6: Demo seeding

````text
/goal Work package wp6 of lane `je` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp6 row in `docs/team/status/je.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Je's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp6** in lane `je`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Demo seeding.** A script that inserts the pre-demo traffic: 5 sessions asking about parking (a real gap in the Kenmore data; it stands in for the PRD's gluten-free pasta) and 12 about gift cards (PRD section 15)
>
> Proof: Running it makes `/owner/gaps` and `/owner/topics` show both topics
> Unblocks: demo

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `je/wp6-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/je.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp7: P1, only after the 18:30 gate: digest wording, owner-initiated facts

````text
/goal Work package wp7 of lane `je` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp7 row in `docs/team/status/je.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Je's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp7** in lane `je`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> P1, only after the 18:30 gate: digest wording, owner-initiated facts
>
> Proof: Tests per feature
> Unblocks: —

This is a P1 package. Start only if the 18:30 gate in your lane file has passed (all P0 packages merged and the end-to-end checks green). If it has not, say so, name the failing check, and stop.

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `je/wp7-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/je.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## 17:00 gate

````text
/goal The 17:00 gate in docs/team/lanes/je.md is decided: either every check it names passes against the latest origin/main and the result is recorded in docs/team/status/je.md on origin/main, or the cut line for that gate has been applied, merged, and recorded with the reason. Also met if `TZ=America/New_York date` is after 17:30 and the status file records the state.

You are Je's build agent on CAC (due 20:45 Eastern). Lane `je`. Run the 17:00 gate for your lane. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; check out `origin/main` in a scratch branch. Read the "Gates and cut lines" section of your lane file and the status files of the lanes you depend on.
2. Run the proof of every package your lane has merged, then your lane's whole test suite, against the real services of the neighbouring lanes (not your mocks). Start what you need with `make db-up` and the other lanes' documented commands.
3. List what fails, in a table: check, expected, actual. Fix what is yours, smallest change first, red then green, shipped by the normal PR path from `AGENTS.md` section 3. File a request (`AGENTS.md` section 6) for what is another lane's.
4. If a check will still fail within 30 minutes, apply the cut line your lane file names for this gate: reduce scope as written there, merge it, and record in the status file what was cut and why.
5. Write the result into your status file under "Decisions" and merge.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## 18:30 gate

````text
/goal The 18:30 gate in docs/team/lanes/je.md is decided: Flow 1 and Flow 3 acceptance (PRD sections 8) pass on the latest origin/main with every lane's real services, or the failing checks are fixed or cut with the reason, and the result is recorded in docs/team/status/je.md on origin/main. Also met if `TZ=America/New_York date` is after 19:00 and the status file records the state.

You are Je's build agent on CAC (due 20:45 Eastern). Lane `je`. Run the 18:30 gate. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; read all four status files and every open request addressed to your lane.
2. Run the PRD Flow 1 acceptance list and Flow 3 acceptance list end to end, as far as they touch your lane, against the real stack: Serve API, Owner tools API, widget, and (for Nico) the box. Use the demo script in PRD section 15 as the checklist.
3. For each failure: fix it if it is yours (red then green, normal PR path), file a request if it is another lane's, and apply the cut line from your lane file if it cannot be fixed in 30 minutes.
4. Only when this gate passes may P1 packages start. Record pass or fail per check in your status file, and merge.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## Freeze at 20:00

````text
/goal From 20:00 the lane `je` is frozen and demo-ready: origin/main contains everything your lane will ship, the demo script in PRD section 15 has been rehearsed twice end to end with your part working, docs/team/status/je.md is final (packages, measured numbers, what was cut), and every flow your lane owns has a recording saved. Also met if `TZ=America/New_York date` is after 20:30.

You are Je's build agent on CAC (submission due 20:45 Eastern). Lane `je`. This is the freeze. From 20:00 no new features: only fixes that a rehearsal exposed. Never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/je.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; confirm origin/main has all your merged packages; delete stale local branches and check no unmerged work of yours remains. Merge or discard it explicitly.
2. Rehearse the PRD section 15 demo script twice against the real stack, timing it. After each run list what broke or felt slow. Fix only what breaks the demo, red then green, shipped by the normal PR path.
3. Check your lane's fallbacks work: the busy and error states, the offline behaviour, and the recovery scripts or cut lines your lane file names.
4. Record every flow your lane owns as a backup (screen recording or terminal capture), saved outside the repo and listed in your status file.
5. Finalize `docs/team/status/je.md`: every package with its PR and proof result, measured numbers, what was cut and why, and anything the team must know for the pitch. Merge it.
6. Tell me the one-line state of your lane: ready, or the single blocking issue.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````
