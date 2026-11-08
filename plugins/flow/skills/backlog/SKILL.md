---
name: backlog
description: Before the coding agent files a ticket, finds an open one to fold it into and checks its size fits under the backlog ceiling. Use every time the agent is about to file a ticket.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/backlog.py *)
---

# Backlog ceiling

The ceiling binds the coding agent alone; its rules, `backlog.target` included, are
`${CLAUDE_SKILL_DIR}/../../method.md` § 3.

1. A finding that belongs to the ticket under way is folded into it; nothing is filed.
2. The draft's Where keys (paths, rule IDs, symbols):

       python3 ${CLAUDE_SKILL_DIR}/scripts/backlog.py match <key> [<key> ...]

   Fold into a hit holding the same observation; else the ticket lists the hits.
3. Then:

       python3 ${CLAUDE_SKILL_DIR}/scripts/backlog.py check <S|M|L|XL>            # --waived: security, data loss, flaky

4. It fits: file the ticket with the coder's mark (`agent-filed` unless
   `backlog.coder_mark` is set) and its `size:` label. It does not fit: method § 3.
