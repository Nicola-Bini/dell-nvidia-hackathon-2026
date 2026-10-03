# Build prompts: Nico (`nico` lane, Pro plan)

One prompt per work package, then the gate and freeze prompts. Each is a complete, separate
paste with its own `/goal`. Use them when:

- a session ended or ran out of usage and you want to restart at one package;
- you want a package done in its own fresh session (one package per session keeps context small);
- the clock hits a gate or the freeze.

The starter prompt in [nico.md](nico.md) already loops through all of these. Use the
starter by default and these when you need to target something.

Open your coding agent in the repo folder (or anywhere if you have not cloned yet), switch it
to its auto or accept-edits permission mode, and paste everything inside one block as one
message. Package details and proofs are in [../lanes/nico.md](../lanes/nico.md). In an
agent without `/goal`, delete the word `/goal` and paste the rest.

| Prompt | Use it for |
|---|---|
| wp1 | First-30-minute checks (PRD section 16, items 2 to 9) as box/checks |
| wp2 | Selection benchmark |
| wp3 | Agent says hello |
| wp4 | Agent skill and instructions |
| wp5 | Sandbox and recovery |
| wp6 | Deploy and load test |
| wp7 | P1, only after the 18:30 gate: services/mcp from Anthropic's MCP Apps  |
| 17:00 gate | Run the 17:00 checks, fix or apply the cut line |
| 18:30 gate | Run Flow 1 and Flow 3 acceptance on the real stack |
| Freeze at 20:00 | Rehearse, record backups, finalize status |

## wp1: First-30-minute checks (PRD section 16, items 2 to 9) as box/checks

````text
/goal Work package wp1 of lane `nico` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp1 row in `docs/team/status/nico.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Nico's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp1** in lane `nico`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **First-30-minute checks** (PRD section 16, items 2 to 9) as `box/checks.sh`: model answers; a structured-output call is valid with thinking off; embedder on disk and its vector length; free memory; pgvector image starts; sandbox can reach the host; concurrency setting. Results and decisions go in your status file under "Measured numbers"
>
> Proof: `box/checks.sh` prints a PASS or FAIL line per item and the numbers
> Unblocks: blake (model id, embedder, vector length)

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `nico/wp1-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/nico.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp2: Selection benchmark

````text
/goal Work package wp2 of lane `nico` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp2 row in `docs/team/status/nico.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Nico's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp2** in lane `nico`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Selection benchmark.** `bench/selection_bench.py`: the 30 texts in `demo/kenmore/intents.yaml` through one small constrained completion each, at 1 and 4 concurrent, straight at the model endpoint
>
> Proof: Prints median and p95 latency and tokens per second; numbers in the status file
> Unblocks: PRD latency targets

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `nico/wp2-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/nico.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp3: Agent says hello

````text
/goal Work package wp3 of lane `nico` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp3 row in `docs/team/status/nico.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Nico's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp3** in lane `nico`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Agent says hello.** One OpenClaw agent in the NemoClaw sandbox, heartbeat 5 minutes, sends a message on the owner channel (local dashboard). Time one agent turn with one tool call
>
> Proof: A message arrives; seconds per turn recorded
> Unblocks: wp4

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `nico/wp3-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/nico.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp4: Agent skill and instructions

````text
/goal Work package wp4 of lane `nico` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp4 row in `docs/team/status/nico.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Nico's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp4** in lane `nico`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Agent skill and instructions.** `agent/`: one skill wrapping je's Owner tools API with `OWNER_TOOLS_TOKEN`, and the agent's instructions for its two moves: ask the owner about the top gap and record the reply (`/owner/gaps/{id}/asked`, `/owner/answers` or `/owner/special-hours`, `/owner/publish`); or change the graph through `POST /owner/changes` with a reason and evidence. It reads topics and counts only
>
> Proof: Against je's API: a seeded gap is asked and, after a reply, answered and published; a seeded gift-card topic yields a pending `create_label`, two `create_node` and one `create_component` change
> Unblocks: gate 17:00

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `nico/wp4-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/nico.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp5: Sandbox and recovery

````text
/goal Work package wp5 of lane `nico` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp5 row in `docs/team/status/nico.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Nico's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp5** in lane `nico`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Sandbox and recovery.** OpenShell policy allowing only the Owner tools API, the model endpoint and the owner channel; a script that shows a blocked egress attempt; `box/up.sh` and `box/recover.sh` (seam 7); heartbeat digest from `/owner/digest`
>
> Proof: The blocked-egress script shows the refusal; `box/recover.sh` brings everything back to healthy
> Unblocks: demo

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `nico/wp5-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/nico.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp6: Deploy and load test

````text
/goal Work package wp6 of lane `nico` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp6 row in `docs/team/status/nico.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Nico's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp6** in lane `nico`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> **Deploy and load test.** `origin/main` running on the box through `box/up.sh`. `bench/load_test.py` against `/v1/intent` at 1, 4 and 8 concurrent, once with an agent turn in flight
>
> Proof: Latency table in the status file; no errors at 4 concurrent
> Unblocks: gate 18:30

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `nico/wp6-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/nico.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## wp7: P1, only after the 18:30 gate: services/mcp from Anthropic's MCP Apps 

````text
/goal Work package wp7 of lane `nico` is merged into origin/main through a pull request; its proof command was run in this session against the latest origin/main and passed; `tools/lane-check` passes; and the wp7 row in `docs/team/status/nico.md` on origin/main shows the PR link and the proof result. Not met while the proof fails or the PR is unmerged. Also met if `TZ=America/New_York date` is after 20:00 and the status file records what was cut and why.

You are Nico's build agent on CAC (hackathon, submission due 20:45 Eastern today). Build exactly one package: **wp7** in lane `nico`. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

The package, from your lane file:

> P1, only after the 18:30 gate: `services/mcp` from Anthropic's MCP Apps quickstart with the pins in SCHEMA 8.7, text-only `ask_restaurant` first, then the element from `apps/widget/dist-mcp/surface.html`, then the tunnel
>
> Proof: From Claude: the question returns the element; a booking request creates a lead
> Unblocks: Flow 2

This is a P1 package. Start only if the 18:30 gate in your lane file has passed (all P0 packages merged and the end-to-end checks green). If it has not, say so, name the failing check, and stop.

Loop until the goal is met:
1. Check the clock (`TZ=America/New_York date`). `git fetch origin` and read what other lanes merged since you last looked (`AGENTS.md` section 5, step 2). Adapt to any contract change first.
2. Write the failing proof first (red). Then build the smallest change that passes it (green).
3. Run the proof, then your lane's whole test suite, then `tools/lane-check`. Fix failures now. After three failed attempts at the same failure, change approach instead of retrying, and say why in the status file.
4. Cut a branch `nico/wp7-<slug>` from fresh `origin/main`, commit by explicit path, `git fetch origin && git rebase origin/main`, update your status row, push, open a PR (one-line business impact and the proof result in the body) and squash-merge it yourself.
5. Re-run the proof on the merged result. When it passes, stop and tell me which package is next in `docs/team/lanes/nico.md`. Do not start it.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git; give each subagent an exact file list and the proof to make pass, and run the proof yourself before committing what it returns. If something needs a person, say `NEED_INPUT: <question>` once and do whatever part of the package is not blocked.
````

## 17:00 gate

````text
/goal The 17:00 gate in docs/team/lanes/nico.md is decided: either every check it names passes against the latest origin/main and the result is recorded in docs/team/status/nico.md on origin/main, or the cut line for that gate has been applied, merged, and recorded with the reason. Also met if `TZ=America/New_York date` is after 17:30 and the status file records the state.

You are Nico's build agent on CAC (due 20:45 Eastern). Lane `nico`. Run the 17:00 gate for your lane. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; check out `origin/main` in a scratch branch. Read the "Gates and cut lines" section of your lane file and the status files of the lanes you depend on.
2. Run the proof of every package your lane has merged, then your lane's whole test suite, against the real services of the neighbouring lanes (not your mocks). Start what you need with `make db-up` and the other lanes' documented commands.
3. List what fails, in a table: check, expected, actual. Fix what is yours, smallest change first, red then green, shipped by the normal PR path from `AGENTS.md` section 3. File a request (`AGENTS.md` section 6) for what is another lane's.
4. If a check will still fail within 30 minutes, apply the cut line your lane file names for this gate: reduce scope as written there, merge it, and record in the status file what was cut and why.
5. Write the result into your status file under "Decisions" and merge.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## 18:30 gate

````text
/goal The 18:30 gate in docs/team/lanes/nico.md is decided: Flow 1 and Flow 3 acceptance (PRD sections 8) pass on the latest origin/main with every lane's real services, or the failing checks are fixed or cut with the reason, and the result is recorded in docs/team/status/nico.md on origin/main. Also met if `TZ=America/New_York date` is after 19:00 and the status file records the state.

You are Nico's build agent on CAC (due 20:45 Eastern). Lane `nico`. Run the 18:30 gate. Work without waiting for me and never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; read all four status files and every open request addressed to your lane.
2. Run the PRD Flow 1 acceptance list and Flow 3 acceptance list end to end, as far as they touch your lane, against the real stack: Serve API, Owner tools API, widget, and (for Nico) the box. Use the demo script in PRD section 15 as the checklist.
3. For each failure: fix it if it is yours (red then green, normal PR path), file a request if it is another lane's, and apply the cut line from your lane file if it cannot be fixed in 30 minutes.
4. Only when this gate passes may P1 packages start. Record pass or fail per check in your status file, and merge.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````

## Freeze at 20:00

````text
/goal From 20:00 the lane `nico` is frozen and demo-ready: origin/main contains everything your lane will ship, the demo script in PRD section 15 has been rehearsed twice end to end with your part working, docs/team/status/nico.md is final (packages, measured numbers, what was cut), and every flow your lane owns has a recording saved. Also met if `TZ=America/New_York date` is after 20:30.

You are Nico's build agent on CAC (submission due 20:45 Eastern). Lane `nico`. This is the freeze. From 20:00 no new features: only fixes that a rehearsal exposed. Never change a file outside your lane.

Setup. Skip any step already done: use the repo folder whose `origin` ends in `dell-nvidia-hackathon-2026` (clone `Nicola-Bini/dell-nvidia-hackathon-2026` with `gh repo clone` if there is none); `git fetch origin`; run `make hooks env`; read `AGENTS.md`, `docs/team/OWNERSHIP.md` and `docs/team/lanes/nico.md` in full, then only the PRD and SCHEMA sections that lane file names.

1. `git fetch origin`; confirm origin/main has all your merged packages; delete stale local branches and check no unmerged work of yours remains. Merge or discard it explicitly.
2. Rehearse the PRD section 15 demo script twice against the real stack, timing it. After each run list what broke or felt slow. Fix only what breaks the demo, red then green, shipped by the normal PR path.
3. Check your lane's fallbacks work: the busy and error states, the offline behaviour, and the recovery scripts or cut lines your lane file names.
4. Record every flow your lane owns as a backup (screen recording or terminal capture), saved outside the repo and listed in your status file.
5. Finalize `docs/team/status/nico.md`: every package with its PR and proof result, measured numbers, what was cut and why, and anything the team must know for the pitch. Merge it.
6. Tell me the one-line state of your lane: ready, or the single blocking issue.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, only for parts that touch different files. Only you run git. If something needs a person, say `NEED_INPUT: <question>` once and continue.
````
