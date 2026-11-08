# Changelog — app

What a project must act on when it takes a new version of this plugin.

## app 0.7.0 — 2026-11-09

- `/app:init` re-run on a project already set up re-aligns it: it reads `DANEEL_REF` in the review workflow and the marketplace pin and
  this changelog's sections newer than the pinned version, then asks the owner, in one
  message, about a pointer that no longer exists or no longer says what its reader asks, a
  default the project's docs now contradict without a key, and the "To take it" steps
  between the pins as one checklist; it does the mechanical steps (keys) and names the pin lines for the owner in one
  pull request and leaves a change to the project's rules docs or CI as a proposal.

To take it: nothing to change; run `/app:init` to see the drift from this version on.

## app 0.6.1 — 2026-11-09

- The changelog is this file, `plugins/app/CHANGELOG.md`, shipped with the plugin, so a
  skill can read what a project must do between two versions from its own folder.

To take it: nothing to change.

## app 0.6.0 — 2026-11-08

- `/app:init`: after `/flow:init`, sets a project up for `app`. It reads the harness
  (`required-checks.json`, the ruleset's bypass actors and required checks, the merge
  settings, the deny lines, `gh --version`) and guesses which project doc plays each role
  the reviewers read (the spec, contract and ADR READMEs, the code rules per lane, the
  glossary, the guides, the visual-proof rules), asks the owner once about what is missing
  or divergent with a default beside each line, adds only what is missing (`daneel.json`
  keys, `required-checks.json`), and names for the owner what the agent may not touch (the
  deny lines, the ruleset, the merge settings). `README.md` § Taking it points to it.

To take it: nothing to change. A project already set up may run it to see which roles run
on defaults.

## app 0.5.0 — 2026-11-08

- The document reviewers (`spec-reviewer`, `contract-reviewer`, `adr-reviewer`),
  `spec-checker`, `reviewer-arch`, `visual-proof` and the loop take a project's conventions
  from the project's docs: the spec, contract and ADR READMEs are the first path of
  `review.rules.spec`, `.contract` and `.adr` (defaults `docs/spec/README.md`, `docs/contracts/README.md`,
  `docs/adr/README.md`), and define their folder, sections, ID pattern and structure; the
  code rules are `review.rules`; the glossary `review.glossary`; the visual-proof rules
  `visual-proof.rules` (default `docs/visual-proof-rules.md`); `review-lanes.sh` fires the
  spec, contract and ADR lanes on that README's folder. Loop § 4 says the code rules
  win over it where they disagree. Every `docs/` path left in an agent doc is a default.

To take it: move the pin to `app--v0.5.0`. Where the defaults hold, no key to set; a
project whose docs live elsewhere sets `review.rules.spec`, `.contract`, `.adr` or
`visual-proof.rules`. The project's review workflow should give the reviewers the rules
documents from the base branch, as it does `daneel.json` (`plugins/app/README.md` § Lanes).

## app 0.4.5 — 2026-11-08

- Loop § 1 step 3 and `run-entry` Step 3: a Done-when clause becomes a failing test in the
  layers the project's test rules ask for (Rust for logic, E2E for what a user does), no
  longer "Vitest for rendering" whatever the project's rules; a clause no test can prove,
  such as a guide's wording, is closed by its diff, and the PR body says why it was not
  seen red.

To take it: nothing to change; a project's test rules say where a frontend test is wanted.

## app 0.4.4 — 2026-11-08

- `app:spec-checker` runs once per entry, with the lanes, when the code of a branch that
  touches or names a spec is finished, before the first push (`run-entry` Step 6, loop § 5);
  no longer at closure, after the push, and no longer in the release sweep. A headless
  `run-entry` now runs it; before, it did not name it.
- Loop § Release sweep: items the owner adds after the sweep get a second one before the
  batch ends, on what merged since the commit the first read up to.

To take it: nothing to change; the agent follows the new wording.

## app 0.4.3 — 2026-11-08

- `protocol.md` § The report: in CI a reply without the written report file is no report,
  and the lane fails. Rule 7: in CI each shell call is one command, never chained; Grep and
  Read search and read files.

To take it: nothing to change. A review workflow that sends a session back while it has no
report file (a `Stop` hook) catches what this wording does not.

## app 0.4.2 — 2026-11-08

- `spec-reviewer` and `spec-checker` take the scopes a rule may carry and whether a spec
  has a `## UX Draft` from the project's `docs/spec/README.md`, not from their prompt. Where
  the README says nothing: `frontend`, `backend`, `frontend + backend`, and a UX Draft, as
  before. With no frontend scope allowed, a screen clause in a spec is a 🔴.

To take it: nothing to change. A project whose specs hold business rules only says so in
`docs/spec/README.md`.

## app 0.4.1 — 2026-11-08

- `merge.py` refuses while a 🔴 or 🟡 in a reviewer lane's newest comment (headed
  `<!-- review:<lane> -->`) has no line in a newer comment carrying (a), (b) or (c) and the
  finding's first 40 characters; it prints each such finding. 🔵 and ℹ️ need no grade.
- `loop.md` § 5: a CI 🔴 or 🟡's grading line quotes its opening words.

To take it: nothing to change; the agent grades as `merge.py` prints. A lane comment that
does not start with `<!-- review:<lane> -->` is not read, as before.

## app 0.4.0 — 2026-11-08

- `release.py` stops at once, naming the error, when `gh pr checks --json` fails; before, an
  older `gh` without that flag read as checks never ending, and a release waited an hour on
  green checks. A pull request with no checks reported yet is still waited for.
- The plugin needs `gh` 2.50.0 or newer (`plugins/app/README.md` § Taking it).

To take it: `gh --version` on the machine that runs the agent; below 2.50.0, upgrade `gh`.
Then move the pin to `app--v0.4.0`.

## app 0.3.1 — 2026-11-01

- `loop.md` § 5: an issue on daneel, as daneel's issues are no longer labelled `flow`.

To take it: nothing to change; the agent follows the new wording.

## app 0.3.0 — 2026-11-01

- `run-entry` Step 0: a task stopped with its pull request open resumes at Step 8's watch on
  its branch: an issue named in chat, or headless an In progress or In review item without
  `needs-owner`, ahead of any Queued item.
- `run-entry`'s `allowed-tools` cover the `git` and `gh` commands it names; the first push and
  every later one is the literal `git push -u origin HEAD`.
- `run-entry` and `design-proposal` read an issue with `--json title,body,comments`: outside a
  terminal, `gh issue view --comments` prints the comments and not the body.

To take it: move the pin to `app--v0.3.0`. A project's allow list need not name these
commands for `run-entry`, but its `just` recipes stay there. `git commit -m *` also matches
a command with `--no-verify`, so add a deny line for it if the hooks must hold headless. A
headless run in a second checkout could resume the same item; run one at a time per project.

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

## app 0.1.1 — 2026-10-31

- `watch-pr.py` no longer crashes on every run (a `NameError` reading `required-checks.json`).
  `run-entry` could not wait for a pull request's checks on 0.1.0.
- `release.py` run after a release commit landed untagged tags that commit and makes the
  draft; on 0.1.0 it bumped the version again and wrote a second changelog section.

To take it: move the project's pin (`ref:` in CI, and the marketplace's, if set) to
`app--v0.1.1`. A project that kept its own `watch-pr.py` for this crash can drop it.

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
