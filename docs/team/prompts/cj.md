# Start prompt: CJ (`cj` lane, Pro plan)

Open your coding agent in the repo folder if you have it, or in any folder if you have not
cloned yet. Switch it to its auto or accept-edits permission mode so it does not stop to ask
for every command. Paste everything inside the block as one message.

`/goal` keeps Claude Code working turn after turn until the condition on the first line is
true. In an agent without `/goal`, delete the word `/goal` and paste the rest.

If the session ends or runs out of usage, start a new one and paste the same prompt: it
picks up from `docs/team/status/cj.md` and what is on `origin/main`.

To target one package, a gate or the freeze instead, use the separate prompts in
[cj-packages.md](cj-packages.md).

````text
/goal Every P0 work package in docs/team/lanes/cj.md is merged into origin/main through a pull request; each package's proof command was run in this session against the latest origin/main and passed; tools/lane-check passes; and docs/team/status/cj.md on origin/main lists every package with its PR link and proof result. Not met while any P0 package is unmerged or any proof fails. Also met if `TZ=America/New_York date` shows a time after 20:00 and the status file records what was cut and why.

You are CJ's build agent on CAC, a hackathon project that must be submitted by 20:45 Eastern today. Your lane is `cj`: the widget, embed script, demo site and overlay, in `apps/` only. Three other people are building the other lanes right now, each with their own agent. Work without waiting for me, and never change a file outside your lane.

Setup. Skip any step that is already done.
1. Find the repo. If `git remote get-url origin` in this folder ends in `dell-nvidia-hackathon-2026`, use this folder. Otherwise look for a folder with that name here, in the parent, and in `~`. If there is none, run `gh repo clone Nicola-Bini/dell-nvidia-hackathon-2026` and work inside it.
2. Run `git fetch origin`. If `git show origin/main:AGENTS.md` fails, the scaffold is not merged yet: tell me and stop. If the working tree has uncommitted changes that are not yours, leave them alone and tell me.
3. Check these tools and install what is missing with the system package manager: `git`, `gh auth status`, `node` 22 with `npm`, `uv`. Ask me only for a step that needs my login.
4. Run `make hooks env`, then `make db-up db-check` if your lane uses the database.
5. Read in full, in this order: `AGENTS.md`, `docs/team/OWNERSHIP.md`, `docs/team/lanes/cj.md`, then only the PRD and SCHEMA sections that lane file names.

Then run the work loop in `AGENTS.md` section 5 until the goal is met. In every iteration: check the clock; fetch and read what the other lanes merged; adapt your code and tests to any contract change before starting new work; take the next package; write the failing proof first; build; run the proof, your lane's tests and `tools/lane-check`; update `docs/team/status/cj.md`; open the pull request and merge it yourself. When all P0 packages are merged, re-run every proof against the other lanes' real services, fix what breaks, then tighten and move to P1.

You are on a Pro plan: at most 2 subagents at a time, on the `sonnet` model, and only when a package splits into files that do not overlap. Only you run git; subagents get an exact file list and a proof to make pass.

Build against `fixtures/surfaces/` from the first minute and open the result in a browser at every package. Do not wait for the Serve API.

Decide everything `AGENTS.md` section 8 does not reserve for a person, and write each decision in your status file. If something needs me, say `NEED_INPUT: <question>` once and carry on with the next package that is not blocked.
````
