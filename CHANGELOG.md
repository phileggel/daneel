# Changelog

What a project must act on when it takes a new version of a plugin.

## app 0.2.1 — 2026-11-01

- `run-entry` Step 8: at the usage limit, the wake-up and asking the owner are for a chat
  session only; a headless run read in order could take them as its own.

To take it: nothing to change; the agent follows the new wording.

## app 0.2.0 — 2026-11-01

- `plugins/app/README.md` § Taking it gives the order, `required-checks.json`, the merge
  settings, the ruleset (`ruleset.json`) and the deny lines for publishing a release.
- `loop.md` § 5: on what a branch adds, an override stands on the default branch; a red lane
  is never re-run on an unchanged commit to clear a (c); a pattern goes in the lane's rules
  document (`review.rules`), not the reviewer's prompt. `protocol.md`: a reviewer ignores a
  "not a finding" entry the branch itself adds, so it applies from the next pull request.
- `run-entry`: a lane with `no report` is re-run; only that lane is re-run (`--job`, not
  `--failed`); headless, a lane stopped by the usage limit ends the run with a `needs-owner`
  comment instead of a sleep, and waits for someone to re-run it.

To take it: move the project's pin to `app--v0.2.0`; add the deny lines; replace a ruleset
that lets someone bypass it or asks for no pull request with `ruleset.json`'s. A project's
allow list need not name `gh run view`, `gh issue comment`, `gh issue edit`, `gh pr comment`
or `gh pr edit` for `run-entry`.

## flow 0.1.2 — 2026-11-01

- `method.md` § 2: a fold puts its clause in the target's body and re-labels its size; the
  target stays open until the clause is done, or hands it on. § 3: making room closes only
  one of the agent's own issues, with the reason, never one the owner confirmed.

To take it: nothing to change; the agent follows the new wording.

## app 0.1.1 — 2026-10-31

- `watch-pr.py` no longer crashes on every run (a `NameError` reading `required-checks.json`).
  `run-entry` could not wait for a pull request's checks on 0.1.0.
- `release.py` run after a release commit landed untagged tags that commit and makes the
  draft; on 0.1.0 it bumped the version again and wrote a second changelog section.

To take it: move the project's pin (`ref:` in CI, and the marketplace's, if set) to
`app--v0.1.1`. A project that kept its own `watch-pr.py` for this crash can drop it.

## flow 0.1.1 — 2026-10-31

- `/flow:init`'s `usage-log.sh` takes its start from Python, not `date +%s.%N`: under BSD
  `date` the usage line was dropped silently.

To take it: a project that already ran `/flow:init` makes the same change in its
`scripts/usage-log.sh`.

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

Earlier versions of `flow` (up to 0.6.0) were withdrawn and their tags removed; 0.1.0 is
lower, so a machine that installed one reinstalls rather than updates:
`claude plugin uninstall flow@daneel`, then `claude plugin install flow@daneel --scope project`.

## app 0.1.0 — 2026-10-25

The first release, the addon for Tauri + React apps (daneel ticket #13), converged
from the apps' copies.
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
- `app` depends on `flow` and reads its method through its own `method.md` link.
- `design-proposal`'s `publish.sh` pushes the mocks to the design repository or a
  `design/<id>` branch, never the project's `main`.
- A key of `.claude/daneel.json` no piece reads stops the script that reads its section.
- `merge.py` lets GitHub merge the tested head and never pushes `main`; its only push is
  the task's own branch, with lease. A project's `main` needs a ruleset that takes only a
  commit whose checks passed, with rebase and squash merges allowed.
- `required-checks.json` at the root is required by `merge.py`, `watch-pr.py` and
  `release.py` alike; CI runs on every push to `main`.

To take it: enable `app@daneel` beside `flow@daneel`; set `review.rules` (one list of
rules documents per lane) and the optional `run-entry`, `run-batch`, `design-proposal`
keys, and `visual-proof` (its `.claude/visual-proof.json` moves there) and the optional
`dep-audit` keys; move into the project's rules documents what only it checks (its domain, its own
scripts and records); set `review.lanes` for the paths only the project adds to a lane
and `flow-audit.guides` for its guides; `just run-entry` is the one line of
`plugins/app/README.md` § Headless runs, and the review workflow runs the plugin's `review-lanes.sh` with the base branch's
`.claude/daneel.json`; drop the project's copies (`review-lanes.sh`, `run-entry.sh`, their
tests).
