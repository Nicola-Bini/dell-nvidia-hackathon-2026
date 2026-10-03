# Heartbeat prompts

The model follows one explicit command far better than a long instruction set: a free-form
"do move 1" turn wandered for 79 s and tried hand-built graph changes (all refused); these
prompts take 6 to 9 s. The decisions live in `cac_owner.py` (which gap, which plan), so the
model only runs a command and relays its result. `box/agent_turn.sh <prompt-name>` runs one.

`grow` is the one prompt where the model decides something. It stays on rails the same way:
`next-task` (code) picks one small task from the live graph and hands over everything needed,
the model writes a list of changes, and `apply` (code) orders, de-duplicates and posts them.
The prompt names no business, type or topic. `box/agent_loop.sh` runs it every heartbeat.

## move1
Move 1. Run exactly this one command: python3 /sandbox/agent/cac_owner.py ask-top-gap
If the JSON has "asked": true, reply with only the value of "message", verbatim. Otherwise
reply "nothing to ask". Do not run anything else.

## move2
Move 2. Run exactly: python3 /sandbox/agent/cac_owner.py propose /sandbox/agent/plans/gift_card.json --topic "gift cards"
If any change was proposed, reply to the owner in two lines: what is waiting in the inbox for
approval, and why (use the count). If none, reply "nothing to propose". Do not run anything else.

## grow
Move 3. Step 1: run exactly this one command: python3 /sandbox/agent/cac_owner.py next-task
If the JSON has "task": null, reply "nothing to grow" and stop.
Step 2: do what "how" in that JSON says, using only what that JSON contains. Write your
changes as one JSON list, each change in the form shown in "shapes". Use [] if nothing is
missing.
Step 3: save your list as the file /sandbox/agent/changes.json, then run exactly this one
command: python3 /sandbox/agent/cac_owner.py apply /sandbox/agent/changes.json
Reply to the owner with only the value of "summary" from step 3. Do not run anything else.

## digest
Run exactly: python3 /sandbox/agent/cac_owner.py digest
Reply to the owner in at most three lines: questions today, open gaps, pending changes, new
leads. Counts only. If every count is 0, reply "quiet".
