# The loop — the apps' method

How a task moves through a Tauri + React app that runs `app` beside `flow`. The batch
around it — ownership, issues, the Project, the backlog, budget and stop rules, the batch
end, the audit — is `flow`'s method, `${CLAUDE_PLUGIN_ROOT}/method.md` (this plugin's link to `flow`'s
own, which `app` depends on). The project's rules
document names what is its own: its harness checks, its rules docs and IDs, where its
mocks live, its release steps.

## 1. One run, one task

A task — a Queued item (`/app:run-entry`, headless), an issue the owner names, or a chat
request (its record is the pull request body) — lands on `main` through a pull request
with every check green, merged by run-entry's `merge.py`.

1. **Pick and brief.** The questions come first (the method's decision scan), with two
   readings the code an issue changes does not show: for an issue that changes what an
   interface can do, the sentences that list what it can do (the strings, the specs, the
   `README.md`) — one that would say less than what is allowed is a question; for every
   record the issue writes, the ADRs that name it — a Done when that stands against one
   is a question. For an issue with a spec the order is: spec draft, `app:spec-reviewer`,
   then the questions, new vocabulary included.
2. **Design gate** (§ 2) for anything the user sees, before any branch exists. Then the
   opening brief states Task, Scope, Design, Touching; the branch is made (the method's
   branch names) and the item moves to In progress.
3. **Acceptance first.** Each Done-when clause becomes a failing test: Rust for logic,
   Vitest for rendering, E2E for what a user does. Test names carry the issue number or
   the spec rule. A new business rule goes into its spec (`docs/spec/`) in the same
   commit; a new or changed command updates its contract (`docs/contracts/`). Confirm red.
   A fault met in production: the input that shows it is asked for before any fix is
   designed — a log says what failed, not why — and a failing test that reproduces it is
   the fix's acceptance test; when the input holds private data, the agent says what it
   needs from it and how little.
4. **Implement** to green, the right way (§ 4).
5. **Self-check:** the scoped recipes while working, then the project's harness recipe
   (`run-entry.recipes.harness`, default `just harness`; § 3). A run is judged by its
   exit code, never by a line picked out of its output.
6. **Self-review:** the reviewer lanes the diff needs (§ 5), again on the fixes until no
   🔴 remains.
7. **Evidence:** `/app:visual-proof` for every changed component.
8. **PR**, opened for the record, not for approval. Body under 20 lines: `Closes #123`,
   the task, each Done-when clause with the test that proves it and where it was seen red
   (or why it could not be), findings that changed something, issues filed, screenshots.
   The commit title is the changelog line.
9. **Closure**, in the same PR before it merges: on an issue that touched a spec,
   `app:spec-checker` runs first and what it finds is fixed; a coverage floor the run
   measured more than a point above rises to half a point under that figure, never down;
   what the task met and did not fix is folded or filed; `ARCHITECTURE.md` if a module
   appeared, the spec if a rule changed.
10. **Merge:** run-entry's `watch-pr.py` waits for the checks; each lane's newest comment,
    green or not, is read and its findings graded (§ 5); then `merge.py` — it refuses
    until every check is green and folds `fixup!` commits, so the task lands as one
    commit. The closing brief says what changed for the user and what the project gained.

**At a batch end**, before the method's release or batch tag: the release sweep
(Conventions); for a release, `/app:dep-audit` on the final `main` once every pull
request of the batch has merged — a known vulnerability in what ships blocks the release —
and the closing brief names its verdict and the runs. `/app:run-batch` then cuts the release
with its `release.py`, which leaves a draft for the owner to publish, or closes any other
batch with its `batch-end.sh`.

## 2. Design proposal

Before any change to what the user sees — a new screen, a moved or added control, a
changed layout or wording pattern — the agent renders mocks of the target state with the
real components and tokens (`/app:design-proposal`): `{id}-{light|dark}-{state}.png` plus
a five-line note (what moves, is added, is removed, stays), posted on the issue; an issue
whose design needs a mock carries `mock`.

- **In chat:** nothing is built until the owner says yes; the yes sets the issue's Design
  to `validated`.
- **Headless:** the issue gets `needs-owner` and the run moves on to the next Queued
  item; the owner validates in the thread.

The mocks show invented data only and never reach `main`: they live where the project's
rules document says, the issue links them, the pull request's visual proofs are the
record.

## 3. The harness

The harness recipe (`just {harness}`, `run-entry.recipes.harness`) runs it locally,
scoped to the layers the branch touched. The same checks are required on every pull
request (`required-checks.json` at the root, which `merge.py`, `watch-pr.py` and
`release.py` all refuse to run without), and CI runs on every push to `main` too:
`release.py` cuts a release only from a `main` whose runs are green. The git hooks run
only fast checks for the same scope. Nothing is run by hand just before a commit or a
push: the hooks do it, and the harness recipe is for wanting CI's answer before pushing. Every app's harness holds at least:

- lint, format, types and build;
- architecture rules, today's debt frozen in `arch-allowlist.json`, which only shrinks;
- unit and integration tests, with coverage for the layers touched;
- coverage floors (`coverage-gates.json`), logic code only, a ratchet never lowered; a
  file leaves the measure only when generated or holding no logic, never to reach a
  number;
- E2E on the real app, every pull request that touches code;
- the reviewers (`review.yml`), one check per lane the diff touches, any 🔴 failing;
- commit hygiene: a conventional title, no trailer;
- dependency advisories (`security-audit.yml`), weekly;
- the merge guard: run-entry's `merge.py` refuses unless the branch heads an open pull
  request with every required check present and green.

Neither `merge.py` nor `release.py` pushes `main`: GitHub merges the tested head, behind
the ruleset on `main`.

The project's rules document lists its own checks beside these.

## 4. The right way to code

- **Logic in Rust, the frontend renders.** A business rule, a validation, an aggregation
  or a derivation is a Rust command with its Rust tests, so every surface follows the
  same rule. The frontend renders, holds ephemeral UI state and maps error codes to
  translations. Logic that lands in the frontend is a harness failure, not a style remark.
- **Gold layouts** for new code (`docs/backend-rules.md`, `docs/frontend-rules.md`, their
  gold rules); bit by bit for existing code (§ 6).
- **Typed errors** on the wire (`docs/error-model.md`); factories and aggregate-root
  methods on domain objects.
- **Stable ids** on every interactive element; text from i18n.
- **Ubiquitous language** in every identifier (`docs/ubiquitous-language.md`).
- **No private data** in logs, commits, fixtures or PR text.
- **Surgical:** touch the file set the task needs; boyscout inside it, never beyond.
- **Read the gold first.** Before changing a pattern that has a named reference, open
  and read it; if it contradicts the design in mind, the gold wins.
- **Check the ADRs before writing "cannot".** Before stating that something cannot be
  done, tested or automated, grep `docs/adr/`: a solved constraint is recorded there.
- **A moved or removed symbol** is searched by its bare name and by every re-export, not
  by its canonical path alone.

## 5. Reviewers and the triage policy

Before the PR, run exactly the lanes this plugin's scripts print:

    bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh files | bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh

and again on every fix before its push, until no 🔴 remains: a file edited in answer
to a finding goes back to its lane, a spec above all.
Once pushed, a fix is a `fixup!` commit pushed as is: CI runs the same lanes on every
push, prompts from a pinned release, and a green CI needs no local run. A local reviewer
gets the branch, the spec and the vocabulary, never a description of the change. Also:
`app:spec-reviewer`, `app:contract-reviewer`, `app:adr-reviewer` when those documents
change; `app:spec-checker` before closing an issue with spec rules; `app:reviewer-guides`
for guides. What every reviewer does is `protocol.md`.

Every finding, local or from CI, is graded before any is applied; one line per finding
that changed something or was rejected goes in the PR body, or a PR comment once pushed:

- **(a)** in scope → fix in the PR.
- **(b)** bigger, or outside the file set → folded or filed, linked from that line.
- **(c)** is never "pre-existing" alone: a rejection cites what overrides the finding —
  a rule, a file, an ADR, a measurement, the owner's decision.
- **(c) one-off** false positive → inline comment `<reviewer> FP: <reason> — see PR #NN`.
- **(c) pattern** → a "not a finding" rule in the reviewer's prompt, same PR.
- **A CI finding the local run missed** → a rule in that reviewer's prompt, same PR.
- **`[DECISION]`** → Conventions.
- **A 🔴 security finding on the agent's own change** is fixed, or put to the owner with
  its options. The agent never clears it with a "not a finding" rule it writes itself.
- **A 🔴 security finding that already exists on `main`**, outside the task: shown to the
  owner with three options — file it as a `task` issue and ship the scoped change (the
  default), widen this pull request, or block. Never deferred silently. A finding the
  pull request introduces blocks.

A CI lane stopped by its usage limit says "did not run (usage limit)" and fails: an
unreviewed pull request does not merge. It is re-run once the limit has reset
(`gh run rerun <run> --failed`).

## 6. Gold for new code, bit by bit for existing

New code follows the golds: the backend layout, the frontend layout and the error model.
Existing code touched by a task is made conformant in the same PR only when all three
hold:

- **Size** — at most about 50 lines of conformance changes.
- **Locality** — inside the files the task already touches.
- **Mechanical** — a rename, an import, a signature or type swap; any design judgement
  (which layer, what name) defers it.

Otherwise the touched code keeps its current standard; a mixed codebase is fine, a
half-migrated file is not. The deciding test is **two stories**: if a reviewer would read
the PR as the task plus a migration, the migration is a separate issue. A spec, contract,
glossary, ADR or `ARCHITECTURE.md` drifting from right code is a `task`.

## 7. PR size and split

One story per pull request. The target is about 400 hand-written lines per reviewer
lane; above about 800 in a lane, split. Generated files, lockfiles, screenshots and spec
documents are not counted, and the total has no limit: a mechanical change that one
check proves is one story whatever its size. Each audit checks the 400 against what CI
found that the local lanes missed. A feature whose backend or frontend exceeds about 20
files or 500 lines ships as one PR per layer, in order: spec, contract, migration,
backend and bindings; then the frontend; then E2E and closure. Each is mergeable alone.

While a pull request waits for its checks, the next task may be prepared on a branch not
pushed yet: its harness and reviewers run there, the reviewers given its last commit
only, and it is rebased onto `main` before its first push — a local rebase, never a
force-push.

## 8. Where the loop runs

The chat session is for filing issues together, design conversations and answering open
questions. The loop runs one task per run and keeps its state in git and the Project.

- **In chat:** `/app:run-entry #123`, or a plain request; `/app:run-batch` for a whole
  batch: the questions first, each remaining item through `/app:run-entry`, the batch's
  end, then the closing brief.
- **Laptop:** `just run-entry` — the first Queued item, headless, under the method's
  budget. A command outside the allow list in `.claude/settings.json` is denied, so the
  run fails instead of waiting. The allow list scopes the flow, it is not a sandbox; what
  is enforced is the harness and the merge guard.
- **Cloud routine** on claude.ai, created disabled; the owner switches it on.

## Conventions

### `[DECISION]` criticals

A reviewer critical tagged `[DECISION]` needs an architectural choice, not a mechanical
fix. It is never fixed unilaterally: it becomes a `needs-owner` question on the issue, or
goes to the owner in chat, and the PR stays open. The choice is recorded before the fix:
a technical one as an ADR (`docs/adr/README.md`), a domain one in the spec or the
glossary.

### Reviewer reports

Locally a reviewer's reply is its report; nothing is written. In CI the reviewer saves
its output under `.review/` (`protocol.md`, The report) and the workflow posts it as the
lane's comment each round. `.review/` is gitignored and safe to delete.

### Dependabot pull requests

The review workflow skips every lane for Dependabot (its runs get no secrets), so its
green reviewer checks are skips, not reviews. It is on the Project as itself and
`/flow:plan-batch` proposes it with the rest. Once queued, the agent reads the diff and
checks each pinned commit against the upstream tag it names; runs run-entry's `merge.py` on its
branch, so the rebase and push are the agent's and CI runs the reviewers for real; grades
that review (a warning is not merged past); and runs `merge.py` again once every check
is green.

### Release sweep

Before a batch ends, run in `release-sweep` mode the lanes this prints:

    git diff --name-only <tag>...HEAD | bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh

`<tag>` the last batch end (`git describe --tags --abbrev=0 --match 'v*' --match 'batch/*'`), plus
`reviewer-security`, which reads the whole command surface; and `app:spec-checker` on
every spec the batch touched. Each lane's `## Files read` goes into the closing brief.
What they find is folded or filed, not fixed in the batch, but for the method's user-risk
case; a finding not critical and older than the batch is filed and reported, not asked
(§ 5 keeps a 🔴 security finding for the owner).

### Shell calls

A headless run has nobody to approve a command, so every shell call is one command the
skill's `allowed-tools` or the project's allow list (`.claude/settings.json`) names:

- no `cd … &&`, no `&&`, `||`, `;` or `$(...)` chain, in a prompt as in a call (the allow
  list matches a literal prefix): `git -C <path>` reaches another directory, a multi-line
  edit goes through `python3 - <<'EOF'`, more logic into a script by name;
- a message or a body goes in a file (`gh pr create --body-file`), never on the command
  line;
- calls that depend on each other run one after another, never in one parallel batch:
  the first failure cancels the rest;
- an empty result is read as a result, not probed again with `echo` or `pwd`;
- a command the deny list refuses is never respelled to get past it;
- a command the list lacks is named to the owner, who adds it; the agent does not.
