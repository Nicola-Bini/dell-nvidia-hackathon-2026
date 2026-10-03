# CAC — rules for every coding agent in this repo

CAC is a local agent a small business owns: it turns the business's site into a knowledge
graph and serves it as interface to visitors and as tools to assistants. Product:
[docs/PRD.md](docs/PRD.md). Contracts: [docs/SCHEMA.md](docs/SCHEMA.md).

**Deadline: submit by 20:45 Eastern, Saturday 3 October 2026. Freeze at 20:00.**
Four people build at once, each with their own agent. These rules are what keep four agents
from colliding. They apply to every agent, whatever tool it runs in.

## 1. Read first

1. This file.
2. [docs/team/OWNERSHIP.md](docs/team/OWNERSHIP.md): who owns which paths, and the seams
   between lanes.
3. Your lane file, `docs/team/lanes/<lane>.md`: your work packages, in order, each with a
   proof command.
4. Only the PRD and SCHEMA sections your lane file names. Do not read `docs/research/`
   unless a decision needs it.

## 2. Lanes

| Lane | Person | Owns | Plan |
|---|---|---|---|
| `blake` | Blake | Database, seed, fixtures, shared package, Serve API, privacy proofs, integration | Max |
| `je` | Je | Owner tools API and owner inbox | Pro |
| `cj` | CJ | Widget, embed script, demo site, overlay | Pro |
| `nico` | Nico | The box, the NemoClaw agent, benchmarks, MCP server | Pro |

**The one rule: change only files in your lane.** Exact paths are in `tools/lanes.conf`;
`tools/lane-check` enforces them and runs on every push. Everything else is read-only to
you, including `docs/SCHEMA.md`, `fixtures/` and `demo/` (Blake's). If you need a change
outside your lane, file a request (section 6) and keep working behind a shim in your lane.

## 3. Git protocol

Lanes own disjoint paths, so branches that pass `tools/lane-check` cannot conflict.

```bash
git fetch origin
git switch -c <lane>/wp<N>-<slug> origin/main     # always cut from fresh origin/main
# ...work, small Conventional Commits, staged by path: git add <your lane paths>
tools/lane-check                                   # must pass
<the work package's proof command>                 # must pass
git fetch origin && git rebase origin/main         # picks up other lanes; no conflicts
git push -u origin HEAD
gh pr create --base main --title "<lane>: wp<N> <what>" \
  --body "Business impact: <one line>. Proof: <command> -> <result>"
gh pr merge --squash --delete-branch
```

- Merge your own PR as soon as lane-check and the proof pass. No review wait. Lane
  ownership is the review.
- Ship small and often: a PR whenever a proof goes green or another lane is waiting on
  you, and at least once an hour. Unmerged work is invisible to the other three.
- Start every new branch from `origin/main`, never from an old branch (PRs are squashed).
- Never push to `main`, never force-push, never touch another lane's branch, never use
  `git add -A` or `git add .` at the repo root.
- If a rebase or merge reports a conflict, someone crossed a lane. Do not resolve it by
  editing their file: take `origin/main`'s version of anything outside your lane, keep
  yours inside it, and file a request.
- Only the main agent runs git. Subagents never commit, push or switch branches.

## 4. Engineering rules

- Stack is fixed by SCHEMA section 2: Python 3.12, FastAPI, psycopg 3 with raw SQL (no
  ORM); Vite, React, TypeScript; Node 22. Use `uv` for Python.
- Each lane keeps its own dependency manifest and lockfile inside its own directory.
  There is no root workspace and no shared lockfile.
- Python layering: routes -> services -> domain -> infra. Business logic stays out of
  routes.
- Red, then green: write the failing test or proof first, then the smallest change that
  passes it. Never delete, weaken or skip a test to get green.
- Limits: functions at most 100 lines, cyclomatic complexity at most 8, at most 5
  positional parameters, lines at most 100 characters. Warnings in files you touch are
  defects.
- No cloud model client anywhere in the code. Models are reached only through
  `LLM_BASE_URL` and `EMBED_BASE_URL`, which must be local.
- Privacy invariants (PRD section 10) are not negotiable: the Serve API connects only as
  `cac_serve`; raw visitor text and lead payloads never reach logs, the agent, or any
  public response; only the owner credential can approve, revert or verify.
- Never commit `.env` or a real secret. Never print secrets.
- There is no cloud deployment. Everything runs on the Dell box; laptops are for
  development.
- In this repo the lane file takes the place of per-feature spec and proof documents: do
  not create `docs/features/` or a shared status file.

## 5. The work loop

Repeat until your goal is met. Do not wait for a human between iterations.

1. **Clock.** Run `TZ=America/New_York date`. Apply the gates and cut lines in your lane
   file. After 20:00, stop building: only fixes that a rehearsal exposed.
2. **Sync.** `git fetch origin`. Read what landed since your last sync:
   `git log --oneline <last-synced-sha>..origin/main`, and
   `git diff --stat <last-synced-sha> origin/main -- docs/SCHEMA.md fixtures demo docs/team packages`.
   Read any `docs/team/requests/*-to-<lane>-*` you have not handled, and the status file
   of any lane you depend on.
3. **Adapt.** If a contract, fixture or seam changed, update your code and tests to match
   before starting anything new. If the real thing behind one of your shims has landed,
   switch to it and delete the shim. If a request is addressed to you, do it now or record
   why not in your status file.
4. **Pick.** Take the first work package in your lane file that is not done and that the
   clock still allows.
5. **Build.** Red, then green. Split across subagents only as section 7 allows.
6. **Verify.** Run the package's proof, your lane's whole test suite, and
   `tools/lane-check`. Fix failures now; three failed attempts on the same failure means
   step back and change approach, not retry.
7. **Ship.** Update `docs/team/status/<lane>.md` in the same branch, then PR and merge
   (section 3).
8. **Improve.** When every P0 package is merged, re-run all your proofs against the latest
   `origin/main` with the neighbouring lanes' real services in place of your mocks. Fix
   what breaks, then measure and tighten (latency, error states, demo script), then start
   P1 packages.

When something needs a person (section 8), write one `NEED_INPUT: <question>` line to the
user and in your status file, then continue with the next package that is not blocked.

## 6. Requests across lanes

To ask another lane for something, add a new file in your own PR:
`docs/team/requests/<your-lane>-to-<their-lane>-<nn>-<slug>.md`, stating what you need,
why, by when, and the exact contract change you propose. Only you edit that file. The
owner answers by shipping the change and noting it under "Requests handled" in their
status file. Until then, code against the contract you proposed behind a shim in your own
lane. A change to `docs/SCHEMA.md`, `fixtures/` or `demo/` is always a request to `blake`.

## 7. Subagents

- Use them when a package splits into parts that touch different files. Give each one its
  exact file list (inside your lane, no overlap between subagents), the contract sections
  to read, and the proof it must make pass.
- Pro plans (`je`, `cj`, `nico`): at most 2 at a time, on a cheaper model (`sonnet`;
  `haiku` for searches). Max plan (`blake`): up to 5 at a time.
- Verify what a subagent returns by running the proof yourself before you commit it.

## 8. What needs a human

Ask only for these; decide everything else yourself and note the decision in your status
file: questions for the organizers (PRD section 18), logins and consent screens
(`gh auth login`, NemoClaw installer prompts, the tunnel, adding the Claude connector),
physical access to the box, anything that deletes data you did not create, and the final
BuilderBase submission.

## 9. Status file

`docs/team/status/<lane>.md`, updated in every PR: one row per work package (state, PR
link, proof command and result), then "Measured numbers", "Decisions", "Requests handled",
"Blocked on". Other lanes read it to learn what they can rely on.
