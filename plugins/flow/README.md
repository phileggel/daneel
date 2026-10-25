# flow

Working on a project with agents, from planning a batch to reviewing, proving and
auditing it: kept once here instead of copied into each repository.

| Piece | What it does |
| ----- | ------------ |
| `/flow:plan-batch` | Shows where the GitHub Project stands and proposes the next batch for the owner to approve in chat; on the yes, sets it on the Project. Needs `plan-batch.owner` and `.number` in `.claude/daneel.json`. |
| `/flow:backlog` | Before the coding agent files a ticket, checks its size fits under the backlog ceiling; the batch-end audit reports the same count. Optional settings `backlog.coder_mark` (default `agent-filed`) and `backlog.waived` (default `security`, `data-loss`). |
| `/flow:flow-audit` | After a batch ends, judges it from its records alone — `flow-audit.py`'s figures and records — in a forked context, posts the audit on the batch's `batch-audit` issue and files the flow issues it proposes. |
| `flow:reviewer-guides` | The guides lane: what an agent does after reading them |

`flow-audit` ships its scripts (`scripts/flow-audit.py`, `scripts/batch-ends.sh`) and its
method (`audit.md`, which also says what the project provides and the settings of
`.claude/daneel.json`). `protocol.md` is what the reviewer shares: modes, steps,
output, the CI report; `scripts/branch.sh` and `scripts/review-path.sh` are what it
runs, always on the project of the working directory. `reviewer-guides` reads the
project's documents from `.claude/daneel.json`: `flow-audit.guides`, and under `review`
the optional `owners`, `setup` and `glossary`.

What only one project's conventions or stack can check stays in that project: its spec,
contract and ADR reviewers, its visual proof, its dependency audit (ticket #6). See the repository's `README.md`
for enabling the plugin, and for running a reviewer in CI.
