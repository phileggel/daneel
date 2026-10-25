# The flow audit

After a batch ends (a release or a `batch/<date>` tag), `/flow:flow-audit` audits it once,
as a comment on that batch's `batch-audit` issue: quality first, weighed against speed
and effort. Nothing of it runs during a batch.

- **An auditor of its own** — the skill runs forked, with a fresh context, and judges
  from the figures, the batch's pull requests and the issues filed and closed during it —
  never the session agent's account. What it cannot rebuild from those records is a
  finding; the questions put to the owner are the dated answers in the issue threads.
- **Measures** — `scripts/flow-audit.py` counts every figure beside the batch before:
  the pull requests, the batch's length, CI and its rounds sorted by cause, the open
  issues and Dependabot pull requests, the backlog by size against its ceiling, the usage
  log, dead paths and the guides' length; and reads the records the auditor judges (the
  pull requests with their reviews, the issues with their threads) in a few calls, so the
  auditor reads one document instead of gathering it. A batch end is dated by its
  tag, a release published or not. The auditor counts from the pull requests what
  the reviewers caught, got wrong and left to CI, and reads each generic piece of the
  guide that lists the agent's tools, if the project has one, against its line.
- **Six questions**, asked of every batch: what would have avoided a conflict; where it
  waited, and what would shorten it without costing quality; what can be simplified;
  which script, recipe, skill or agent went unused (keep, fold or remove); where a guide
  was false, contradicted another, or grew without earning it; what was done by hand that
  a tool should do, and which finding belongs to another repository.
- **Hard points** — the three strongest difficulties become `flow` issues with their
  evidence and a proposal; the rest stay in the audit's text. Where nothing should
  change, "keep" is a verdict said in the audit, and no issue is filed.
- **The ceiling** — the open backlog by size (S 1, M 2, L 4, XL 8; no size 2; a parent
  with an open slice 0; `batch-audit` none) at a batch end stays at or under the last
  end's, raised by the owner's tickets (every ticket without the coder's mark, and the
  coder's marked `owner-asked`) and the waived ones (security, data loss). The audit's
  Backlog block states it by size at both ends, the ceiling, what was added (coder,
  owner, waived) and removed (done, folded, closed). A project that holds no ceiling
  reads the figure and judges nothing from it.

A flow issue (the project's `flow` form) carries `Observed` with its evidence — a count,
a duration, a pull request — then a `Proposal` with what it `Costs` and what it protects.
A change that buys speed says what it risks; one that buys safety says what it costs. A
tool nobody used is named, with a verdict: keep, fold or remove. The owner decides each in
its thread; the agent copies the decision, dated, into its Decision field, and it can be
queued. One done, or whose verdict is to keep things as they are, is closed.

## What the project provides

- A git checkout with an `origin` on GitHub, and `gh` signed in to it.
- Batch ends as tags: releases `v*` (published or still a draft) or `batch/<date>` tags, each dated by its tag.
- Pull requests whose CI runs one workflow on every push (`round_workflow`, default
  `Quality`), and a `batch-audit` label.
- Optionally `logs/usage.log` (local, never committed): one line per run of a project
  script or recipe — `time<TAB>tool<TAB>duration<TAB>result`, the result `ok`, `started`
  for a recipe that runs no script, anything else a failure. A script counts as a tool
  when it calls `usage_log.start()` or sources `usage-log.sh`; a recipe when it depends on
  `(_used "<recipe>")`.
- Optionally `.claude/daneel.json`, the project's own part:

  ```json
  {
    "flow-audit": {
      "round_workflow": "Quality",
      "commit_types": ["feat", "fix", "refactor", "chore", "docs", "test", "ci"],
      "guides": ["CLAUDE.md", "docs/workflow.md", ".claude/agents/*.md"],
      "records": ["CHANGELOG.md", "docs/adr/"],
      "path_roots": ["src/", "docs/", "scripts/"]
    }
  }
  ```

  Each key replaces its default (the `SETTINGS` of `scripts/flow-audit.py`); an unknown
  key stops the audit.
