# flow

Working on any project with agents, from planning a batch to auditing it: kept once here
instead of copied into each repository.

| Piece | What it does |
| ----- | ------------ |
| `/flow:plan-batch` | Shows where the GitHub Project stands and proposes the next batch for the owner to approve in chat; on the yes, sets it on the Project. Needs `plan-batch.owner`, `.number` and `.workflow` in `.claude/daneel.json`. |
| `/flow:backlog` | Before the coding agent files a ticket, checks its size fits under the backlog ceiling; the batch-end audit reports the same count. Optional settings `backlog.coder_mark` (default `agent-filed`) and `backlog.waived` (default `security`, `data-loss`). |
| `/flow:flow-audit` | After a batch ends, judges it from its records alone — `flow-audit.py`'s figures and records — in a forked context, posts the audit on the batch's `batch-audit` issue and files the flow issues it proposes. |

`flow-audit` ships its scripts (`scripts/flow-audit.py`, `scripts/batch-ends.sh`) and its
method (`audit.md`, which also says what the project provides and the settings of
`.claude/daneel.json`). What one kind of project shares, and others do not, is an addon
beside `flow` (`app`). See the repository's `README.md` for enabling the plugin.
