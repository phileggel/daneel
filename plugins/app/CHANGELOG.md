# Changelog — app

What a project must act on when it takes a new version of this plugin.

## app 0.16.0 — 2026-11-28

- With `spec-proposal.repo`, the spec gate opens before a ticket is Ready (`loop.md` § 2).
  `/app:spec-proposal` posts the change's diff on the ticket; on the owner's yes it
  publishes the change and sets the ticket's Spec to `validated`, with the rule IDs and
  the sha. A ticket whose Spec is already `validated` passes the gate at once. Until now
  the change was shown in chat only, and the issue got a comment with the rule IDs.
  Without the key nothing changes. To take it, for a project that sets the key: add the
  `Spec` field of `flow` 0.8.0's forms to its feature and bug forms.
- A spec may be ahead of the code: `/app:run-entry` Step 6 gives `app:spec-checker` and
  `app:contract-reviewer` the rule IDs the ticket's Spec names. Given rule IDs,
  `spec-checker` audits those rules and counts the others, and `contract-reviewer` asks
  no command and no error of a rule outside them. Without rule IDs both do what they did.
  Nothing for a project to do.
- CI reads a spec kept in its own repository. When the project's review workflow checks
  that repository out at the spec folder, with a read-only secret, before
  `review-prepare.sh`, the script copies it beside the files under review and removes its
  `.git`, and `review-prompt.sh` tells the contract and ADR lanes that the spec is ahead
  of the code and that a report quotes at most a sentence of it. Without that checkout
  both scripts do what they did. To take it, for a project that sets `spec-proposal.repo`:
  add the checkout step and its secret to the review workflow (`README.md` § A spec in its
  own repository).
- Wording only: `loop.md` § 7 is "One story per PR, whatever its size".
- `/app:init` ends with a checklist: every line of `README.md` § Taking it, in order, with
  its state — done, added, to do by the project, or the owner's to check or decide. The
  section now lists what the pieces of `app` need beyond the checks and the ruleset: the
  plugins, the harness recipe, the visual-proof keys, the review workflow, where the mocks
  and the spec live, the release keys. `/app:init` still adds the roles' keys and
  `required-checks.json`, lists `design-proposal.repo` among the roles, and builds nothing
  else of the project. Nothing for a project to do.

## app 0.15.0 — 2026-11-28

- `merge.py` finishes a branch whose rebase the agent resolved by hand. A rebase that
  conflicts is still aborted and left to the agent. On the re-run, origin holds the
  commits as they were before that rebase: the script refused them as commits "not in
  local", and its advice (`git pull --rebase`) brought the conflict back, so the only way
  out was a new PR. It now accepts what the local branch once pointed at, and its push
  with lease replaces it. A commit origin holds that the local branch never held still
  refuses the merge. Nothing for a project to do.
- `loop.md` § 7 sets no size for a PR any more: the target of about 400 lines per
  reviewer lane, the split above about 800 and the one PR per layer of a large feature
  are gone. "One story per PR" stays. To take it: remove those figures from any guide of
  the project that restates them.
- `/app:run-entry` Step 8 checks the file of the PR body before the PR exists
  (`grades.py`, exit 1 with each line printed): a (b) line carries the `#NNN` of its
  issue, a (c) line a citation after a dash — a path, `#NNN`, an ADR, a figure or
  `owner`. `loop.md` § 5 gives the form. It reads one local file and calls nothing; the
  grade check of CI findings does not change. Nothing for a project to do.

## app 0.14.0 — 2026-11-22

- `/app:spec-proposal <id>` is the spec gate of 0.13.0 as a skill: it drafts the change to
  the rules, has `app:spec-reviewer` read it, shows the owner the diff and the questions,
  and lands the change only on the yes. `/app:run-entry` Step 1 calls it.
- `spec-proposal.repo` (`owner/name`), optional: the spec lives in a repository of its
  own, which may be private. The spec folder is then a clone of it that git ignores and
  the agent may not edit; an accepted change is pushed to that repository's `main` by the
  skill's `publish.sh`, which refuses the project itself; public text cites a rule by its
  ID; `review-prompt.sh` tells the spec, contract and ADR lanes of CI that the spec is not
  in the checkout (`README.md` § A spec in its own repository).
- Corrects 0.13.0: an accepted spec change is not "the branch's first commit". It goes
  into the task's one commit as it is, since `merge.py` lands one commit per entry and
  refuses a branch that folds into two. Nothing else changes a spec.
- `/app:init` lists the key among the roles. Its table no longer says who reads the
  architecture document, to keep the doc's length.

To take it: nothing without the key. To move a spec to its own repository (`README.md`
§ A spec in its own repository): create the repository and push the spec folder's files to
its `main`; in the project, remove the folder from git and list it in `.gitignore`; add
`spec-proposal.repo` to `.claude/daneel.json`; the owner adds the deny line on the folder
to `.claude/settings.json`; clone the repository at the folder's path on each computer;
drop a required check of the `spec` lane; move the review workflow to `review-prompt.sh`
(0.12.0), which tells the contract and ADR lanes that the spec is absent.

## app 0.13.0 — 2026-11-22

- A spec changes only as the task's stated intent, accepted by the owner before the branch
  exists, as a design is (`loop.md` § 2, `/app:run-entry` Step 1). The agent drafts the
  change, runs `app:spec-reviewer` on it and shows the owner the diff with its questions;
  on the yes it is the branch's first commit. No later commit of the task touches a spec:
  a rule found missing while implementing, or a finding on the spec, goes back to that
  gate. Before, a new rule went into its spec "in the same commit" as its code, and
  closure updated the spec "if a rule changed".
- Headless, the spec's diff goes to the issue with `needs-owner` and the item stays Queued.
- `/app:run-entry`, wording only, to keep its length: the lane with no verdict loses
  "(by exit code or comment)", which the exit codes above it and the comment's name say.

To take it: a rules document of the project that tells the agent to add a rule to the
spec with its code, or to update the spec at closure, now says the opposite of the loop:
reword it, or drop the line.

## app 0.12.0 — 2026-11-22

- Three scripts give a reviewer's CI session what each project wrote by hand in its review
  workflow, where the copies drifted and two sessions wrote no report
  (`README.md` § A reviewer's session in CI):
  - `review-prepare.sh <base> <tree>` makes the checkout ready: a local `main` at the base
    branch, the plugin's folder out of the changed files, the commit under review in
    `<tree>`, `.review/`, and from the base branch `CLAUDE.md`, `.claude/` and every
    document `review.rules`, `review.glossary`, `review.owners` and `review.setup` name.
    New: the rules documents come from the base branch too, so a PR cannot loosen the
    rules that judge it. It refuses a checkout with uncommitted work.
  - `review-tools.sh <lane>` prints the line for `--allowedTools`. The report's folder is
    granted from the session's folder and from the filesystem root, so a session that
    changed folder still writes its report; the helpers are granted under both spellings.
  - `review-prompt.sh <lane> <tree>` prints the instruction given to the session.
- Daneel still ships no review workflow: the triggers, the runner, the lanes, the model,
  the secret and the checks' names stay the project's.
- `/app:init` lists, among the harness items, a review workflow that does not call the
  three scripts.

To take it: in the review workflow, replace the step that restores files from the base
branch by `review-prepare.sh`, the `--allowedTools` list by `review-tools.sh`'s line and
the prompt by `review-prompt.sh`'s text, then add after each what is the project's own (a
tool its rules documents make a lane run, a line of prompt). A workflow that keeps its own
three still works.

## app 0.11.5 — 2026-11-22

- `merge.py` and `lane-reviewed.py` trust a report or a grade by what the repository lets
  its author do: a permission of `admin` or `write`, asked of GitHub once per account that
  commented. They no longer read the comment's `author_association`, which depends on who
  asks: on an organisation's repository, a member whose membership is private reads as
  `CONTRIBUTOR` to the workflow's token, so `lane-reviewed.py` ignored the owner's grades
  and the lane stayed red. A member or collaborator who may only read is no longer
  trusted. An account whose permission could not be read is named.

To take it: nothing. The workflow's token reads the permission with `contents: read`
alone: probed on 2026-11-22 in a job of daneel's own CI (a user's repository), which read
`admin` for the PR's author and `read` for a stranger. Not probed on an organisation's
repository: there, a lane that stays red after its grades now names the account whose
permission it could not read.

## app 0.11.4 — 2026-11-22

- `merge.py` and `lane-reviewed.py` read every 🔴 and 🟡 of a lane's report: an item under
  a 🔴 or 🟡 heading as before, and now any line carrying the mark, wherever the reviewer
  wrote it (`**B — Rule quality**: 🟡 …`). A finding written that way merged ungraded and
  its lane passed as graded. A heading, or a line that only counts findings, is none. The
  words to quote in a grade start after the mark; the refusal prints them.
- `app:spec-reviewer`, `app:contract-reviewer` and `app:adr-reviewer` write one item per
  finding, its mark first (`- 🟡 ORD-020 — scope missing`), under their categories.
  `app:contract-reviewer` no longer ends with "A 🟡 never blocks": its last line says so.

To take it: nothing. A report already on an open PR whose findings were written inline
now asks for their grades.

## app 0.11.3 — 2026-11-21

- `app:reviewer-arch`, wording only: "For both" names what it covers, the two use-case
  checks above it (a use case importing another, a use case naming a sqlx type).

To take it: nothing.

## app 0.11.2 — 2026-11-21

- Wording only: every doc says `PR` (`flow`'s `method.md` § 1 says what it stands for);
  `loop.md`'s "Dependabot PRs" section is named so where a skill points to it.

To take it: nothing.

## app 0.11.1 — 2026-11-21

- The skills and agents, wording only (`flow`'s `method.md` § 7): `app:adr-reviewer` says
  `the owner` where it said `the user`; `app:contract-reviewer` and `app:spec-checker` say
  in one sentence which document they take; `/app:run-entry` Step 10 says when the merge
  runs; `rules documents` everywhere. No rule changes.

To take it: nothing.

## app 0.11.0 — 2026-11-21

- `app:reviewer-guides`, a new check, plain language (`flow`'s `method.md` § 7): one thing
  under two names in a changed guide is a 🟡; an added sentence that must be read twice
  to act on is a 🔵, with its rewording.

To take it: with `flow` 0.6.0. A 🟡 of the new check is graded like any other.

## app 0.10.1 — 2026-11-21

- Wording only: `loop.md` § 1 lists the two readings of step 1, an exception reads
  `except` (it read `but`), `/app:run-entry` and `/app:design-proposal` say `the owner`
  where they said `the human`, and `protocol.md` says `rules documents`. No rule changes.
- `release.py` prints `Everything is made except the publishing` (it printed `but`).

To take it: nothing.

## app 0.10.0 — 2026-11-21

- `lane-reviewed.py` and `merge.py` read a lane report or a grade only from
  `github-actions[bot]` or from the repository's owner, a member or a collaborator. On a
  public repository any account can comment: one shaped as a clean report, or as grade
  lines, no longer passes a lane or clears a 🔴.
- `/app:design-proposal`: with `repo`, an image is linked as
  `https://github.com/{repo}/blob/<sha>/{id}/<file>?raw=true`, which GitHub serves to a
  viewer with access to a private repository; `raw.githubusercontent.com` answered 404.

To take it: nothing when the review workflow posts its reports with the workflow's own
token. One that posts them as another account makes that account a collaborator.

## app 0.9.0 — 2026-11-15

- `/app:design-proposal`: for a state of an existing screen, the preview also renders the
  current component, and the comment shows it beside the proposed one, one table row per
  theme (`{id}-{light|dark}-{state}-current.png`).
- `/app:run-entry`: a slice split off the item during its run is Queued right after it
  (`flow`'s `method.md` § 2), with `gh project item-add`, `gh project item-edit` and the
  position call of `gh api graphql`, written literally; its `allowed-tools` now cover them
  and `gh project view`.
- `app:reviewer-arch`: a sqlx type in a use case's test module is a finding only when the
  project's backend rules include tests; in the use case itself it is one as before.

To take it: with `flow` 0.5.1. A project whose backend rules forbid sqlx in the tests of
its use cases says so in those rules, or the lane no longer raises it.

## app 0.8.0 — 2026-11-14

- In CI a lane reviews a pull request once. After its report, a later push does not start
  it again: its check passes when every 🔴 and 🟡 of the report is graded, and the
  project's tests alone validate the fix. `scripts/lane-reviewed.py <pull request> <lane>`
  answers for a review workflow: exit 3 not reviewed yet, 0 reviewed and graded, 1 a
  finding ungraded, 2 the comments could not be read (`README.md` § One review per pull
  request). Local reviews are unchanged.
- `loop.md` § 5 and `/app:run-entry` Step 8 say so: every lane's newest comment is graded
  in a pull request comment before the push that applies it. `loop.md` no longer asks for
  a rule in a lane's document for each CI finding the local run missed.

To take it: in the review workflow, each lane's job runs `lane-reviewed.py` before the
reviewer's session, and starts the session on exit 3 only; on 0 the job ends green, on 1 or
2 it fails. Until then every push reviews again, as before.

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
