# Changelog

What a project must act on when it takes a new version of a plugin.

## flow 0.1.0 — 2026-10-25

The first release, for any project (daneel ticket #13).
- `method.md`: the batch method — who owns what, issues and the Project, the backlog
  (a ceiling that shrinks a backlog over its optional healthy `backlog.target`), budget
  and stop rules, how a batch ends, the flow audit; and what the project provides.
- `/flow:init` adds what a project lacks — Project fields, the flow's labels, issue forms,
  `.claude/daneel.json`, the usage log helpers, a line in `CLAUDE.md` — after asking.
- `/flow:plan-batch`, `/flow:backlog`, `/flow:flow-audit`.

To take it: enable `flow@daneel`, run `/flow:init`, drop the project's own copies; the
project's workflow document keeps only its additions to the method. The agent cuts a
release (its tag and draft); the owner only publishes it, outside the run.

## app 0.1.0 — 2026-10-25

The first release, the addon for folioneer and PatientManager (daneel ticket #13),
converged from both projects' copies.
- `loop.md`: one run, one task; design proposal, harness, reviewers and triage, PR size.
- `/app:run-entry`, `/app:run-batch`, `/app:design-proposal`, `/app:visual-proof`,
  `/app:dep-audit`.
- The reviewers `spec-reviewer`, `contract-reviewer`, `adr-reviewer`, `spec-checker`,
  `reviewer-guides`, and the stack lanes `reviewer-arch`, `-backend`, `-frontend`, `-sql`,
  `-e2e`, `-security`, `-infra`, with `protocol.md`, `branch.sh`, `review-path.sh`.
- `review-lanes.sh`: the lanes a change needs, defaults for a Tauri + React app, the
  project's own paths from `review.lanes`, the guides from `flow-audit.guides`.
- `run-batch`'s `release.py` cuts a release to its draft, never published, and
  `batch-end.sh` tags a batch without one; the closing brief comes last. A project sets
  `run-batch.version_files`, `.changelog`, `.release_workflow`, drops its `release` and
  `batch-end` recipes and its release script, and drops any deny line matching `release.py`.

To take it: enable `app@daneel` beside `flow@daneel`; set `review.rules` (one list of
rules documents per lane) and the optional `run-entry`, `run-batch`, `design-proposal`
keys; move into the project's rules documents what only it checks (its domain, its own
scripts and records); set `review.lanes` for the paths only the project adds to a lane and `flow-audit.guides`
for its guides; `just run-entry` is the one line of `plugins/app/README.md` § Headless
runs, and the review workflow runs the plugin's `review-lanes.sh` with the base branch's
`.claude/daneel.json`; drop the project's copies (`review-lanes.sh`, `run-entry.sh`, their
tests).
