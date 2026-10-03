# Heartbeat prompts

The model follows one explicit command far better than a long instruction set: a free-form
"do move 1" turn wandered for 79 s and tried hand-built graph changes (all refused); these
prompts take 6 to 9 s. The decisions live in `cac_owner.py` (which gap, which plan), so the
model only runs a command and relays its result. `box/agent_turn.sh <prompt-name>` runs one.

## move1
Move 1. Run exactly this one command: python3 /sandbox/agent/cac_owner.py ask-top-gap
If the JSON has "asked": true, reply with only the value of "message", verbatim. Otherwise
reply "nothing to ask". Do not run anything else.

## move2
Move 2. Run exactly: python3 /sandbox/agent/cac_owner.py propose /sandbox/agent/plans/gift_card.json --topic "gift cards"
If any change was proposed, reply to the owner in two lines: what is waiting in the inbox for
approval, and why (use the count). If none, reply "nothing to propose". Do not run anything else.

## digest
Run exactly: python3 /sandbox/agent/cac_owner.py digest
Reply to the owner in at most three lines: questions today, open gaps, pending changes, new
leads. Counts only. If every count is 0, reply "quiet".
