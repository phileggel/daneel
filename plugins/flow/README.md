# flow

Working on any project with agents, from planning a batch to auditing it: kept once here
instead of copied into each repository.

| Piece | What it does |
| ----- | ------------ |
| `/flow:init` | Sets a project up for the flow, adding only what it lacks (Project, labels, issue forms, `.claude/daneel.json`, usage log, a line in CLAUDE.md) after asking the owner. Never overwrites. |
| `/flow:plan-batch` | Shows where the GitHub Project stands and proposes the next batch for the owner to approve in chat; on the yes, sets it on the Project. Needs `plan-batch.owner` and `.number` in `.claude/daneel.json`; `.workflow`, the project's rules document, is optional. |
| `/flow:backlog` | Before the coding agent files a ticket, checks its size fits under the backlog ceiling; the batch-end audit reports the same count. Optional settings `backlog.target` (the healthy size the agent files up to), `backlog.coder_mark` (default `agent-filed`) and `backlog.waived` (default `security`, `data-loss`). |
| `/flow:flow-audit` | After a batch ends, judges it from its records alone — `flow-audit.py`'s figures and records — in a forked context, posts the audit on the batch's `batch-audit` issue and files the flow issues it proposes. |

`method.md` is the batch method the pieces follow, and ends with what the project
provides for them. `flow-audit` ships its scripts (`scripts/flow-audit.py`,
`scripts/batch-ends.sh`) and its method (`audit.md`, which also says what the project provides and the settings of
`.claude/daneel.json`). What one kind of project shares, and others do not, is an addon
beside `flow` (`app`). See the repository's `README.md` for enabling the plugin.
