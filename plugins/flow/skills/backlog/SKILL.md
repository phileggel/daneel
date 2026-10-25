---
name: backlog
description: Before the coding agent files a ticket, checks that its size fits under the backlog ceiling, set at the last batch end and raised only by the owner's tickets and the waived ones (security, data loss). Use every time the agent is about to file a ticket.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/backlog.py *)
---

# Backlog ceiling

The ceiling binds the coding agent alone. Tickets the owner files — on GitHub, through
Cowork, by another session — raise it, as do the agent's tickets the owner asked for
(`owner-asked`) and the waived ones.

1. A finding that belongs to the ticket under way is folded into it; nothing is filed.
2. Otherwise run, from the project's checkout:

       python3 ${CLAUDE_SKILL_DIR}/scripts/backlog.py check <S|M|L|XL>            # --waived for security or data loss

3. It fits: file the ticket with the coder's mark (`agent-filed` unless the project's
   `.claude/daneel.json` sets `backlog.coder_mark`) and its `size:` label.
   It does not fit: fold it into an open ticket, or close one it supersedes, or — for
   a defect a user meets — surface it to the owner in chat. Never file it anyway.

The batch end's audit reports the result (`/flow:flow-audit`, its Backlog block).
