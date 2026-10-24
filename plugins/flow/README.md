# flow

The generic flow core of phileggel's projects: the skills every project runs the
same way, kept once here instead of copied into each repository.

| Skill | What it does |
| ----- | ------------ |
| `/flow:flow-audit` | After a batch ends, judges it from its records alone — `just flow-audit`'s figures, the batch's pull requests and issues — in a forked context, posts the audit on the batch's `batch-audit` issue and files the flow issues it proposes. |

The skill ships its scripts (`scripts/flow-audit.py`, `scripts/batch-ends.sh`) and its
method (`audit.md`, which also says what the project provides and the settings of
`.claude/daneel.json`). See the repository's `README.md` for enabling the plugin.
