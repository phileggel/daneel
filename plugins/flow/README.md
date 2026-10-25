# flow

Working on a project with agents, from planning a batch to reviewing, proving and
auditing it: kept once here instead of copied into each repository.

| Piece | What it does |
| ----- | ------------ |
| `/flow:plan-batch` | Shows where the GitHub Project stands and proposes the next batch for the owner to approve in chat; on the yes, sets it on the Project. Needs `plan-batch.owner` and `.number` in `.claude/daneel.json`. |
| `/flow:backlog` | Before the coding agent files a ticket, checks its size fits under the backlog ceiling; the batch-end audit reports the same count. Optional settings `backlog.coder_mark` (default `agent-filed`) and `backlog.waived` (default `security`, `data-loss`). |
| `/flow:flow-audit` | After a batch ends, judges it from its records alone — `flow-audit.py`'s figures and records — in a forked context, posts the audit on the batch's `batch-audit` issue and files the flow issues it proposes. |
| `flow:spec-reviewer` | A spec, before its contract: complete, consistent, implementable |
| `flow:contract-reviewer` | A contract against its spec: coverage, errors, types |
| `flow:adr-reviewer` | ADRs: structure, the gate, status and index |
| `flow:spec-checker` | Every rule of a spec implemented and tested |
| `flow:reviewer-guides` | The guides lane: what an agent does after reading them |
| `/flow:visual-proof` | Screenshots of every state of a changed component, light and dark |
| `/flow:dep-audit` | npm and Cargo: outdated versions and CVEs, verified on the web |

`flow-audit` ships its scripts (`scripts/flow-audit.py`, `scripts/batch-ends.sh`) and its
method (`audit.md`, which also says what the project provides and the settings of
`.claude/daneel.json`). `protocol.md` is what every reviewer shares: modes, steps,
output, the CI report; `scripts/branch.sh` and `scripts/review-path.sh` are what the
reviewers run, always on the project of the working directory. The reviewers read the
project's own conventions (`docs/spec/README.md`, `docs/contracts/README.md`,
`docs/adr/README.md`, `docs/ubiquitous-language.md`). See the repository's `README.md`
for enabling the plugin, and for running a reviewer in CI.
