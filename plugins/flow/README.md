# flow

The generic flow core of phileggel's projects: the skills every project runs the
same way, kept once here instead of copied into each repository.

| Skill | What it does |
| ----- | ------------ |
| `/flow:flow-audit` | After a batch ends, judges it from its records alone — `just flow-audit`'s figures, the batch's pull requests and issues — in a forked context, posts the audit on the batch's `batch-audit` issue and files the flow issues it proposes. |

Setup: the project provides `just batch-ends`, `just flow-audit` and
`docs/workflow.md` § 12, which the skill reads. See the repository's `README.md`
for enabling the plugin.
