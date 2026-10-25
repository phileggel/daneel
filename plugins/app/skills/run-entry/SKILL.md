---
name: run-entry
description: Runs one task end to end under the loop — branch, design gate, acceptance tests, implementation, harness, reviewers, PR, closure, merge on green. The task is the first ready Queued item of the Project (headless, no argument), an issue the human names (#123), or a plain request typed in chat. One task per invocation.
argument-hint: "[#123 | a request]"
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py *)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/watch-pr.py *)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/watch-pr.py)
  - Bash(gh run rerun *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh *)
---

# Skill — `run-entry`

One invocation, one task, through the ceremony to `main`. The rules are the loop
(`${CLAUDE_SKILL_DIR}/../../loop.md`), `flow`'s method (`${CLAUDE_SKILL_DIR}/../../method.md`) and the project's
rules document; this file is the checklist.

Settings (`.claude/daneel.json`): the Project is `plan-batch.owner` and `.number`; under
`run-entry`, each optional:

- `recipes` — the project's `just` recipes by role: `harness` (default `harness`),
  `push_harness` (default none; `harness` runs once more before the first push).
- `record_paths` — the files whose move of `main` leaves the checks standing (default
  `["docs/adr/"]`; an entry ending in `/` is a folder of `.md` files).

`merge.py` lets GitHub merge the tested head and never pushes `main`: the repository
has a ruleset on `main` that takes only a commit whose checks passed, and allows rebase
and squash merges. `merge.py` and `watch-pr.py` read the required checks from `required-checks.json` at the
checkout's root (`{"checks": [...]}`).

## Step 0 — Preconditions and mode

- `git status --short` is empty and `main` is fresh (`git pull --ff-only`). Otherwise
  stop and report; never work on a dirty tree.
- **Headless** (no argument): `gh project item-list {number} --owner {owner} --format json --limit 500`;
  take the first Queued item, in row order, that is ready. Nobody to ask: a
  question becomes a comment on the issue with `needs-owner` (method § 2).
- **Chat, named issue** (`#123`): `gh issue view 123 --comments`.
- **A Dependabot pull request** (queued or named): loop § Dependabot pull requests, not
  Steps 1 to 10 — the diff, each pinned commit, `python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py` on its branch, grade, merge.
- **Chat, plain request**: the request is the task; no issue is created — the PR body
  is its record. Write its Done when into the opening brief.
- **Decision scan**, for an issue, before the branch exists (method § 2). Chat: its
  questions asked then, the answers written on the issue. Headless: each a comment with
  `needs-owner`, and the issue is no longer ready.
- **Ready** as method § 2 defines it; a flow issue's Decision and a task's Observation are their
  Done when. Headless: skip what is not ready; if nothing is, say what blocks each issue
  and stop. Chat: ask each open question alone, with the context to answer it cold, and
  wait for the answer before the next; write the answers on the issue. For an issue with
  a spec: spec draft, `app:spec-reviewer`, then the questions.

## Step 1 — Design gate

Before any branch exists, and before the item moves: anything the user sees changes and
`Design` is not `validated` — `/app:design-proposal <id>`.

- Chat: nothing is built before the human's yes to the mocks; on a no, stop.
- Headless: the proposal is posted on the issue (loop § 2), its Design set to `needed`;
  the item stays Queued, and is ready again once the owner validates. Back to Step 0 for
  the next ready item. Do not implement.

## Step 2 — Opening brief, branch, task list

- Opening brief (chat: first message; headless: top of the PR body): **Task** — the issue
  or request in one line · **Scope** — commit type, layers · **Design** — none / validated
  / needed · **Touching** — the paths.
- `git checkout -b <type>/123-<slug>` (`<type>/<slug>` for a plain request), `<type>` the
  change's commit type; the item's Status becomes In progress (`gh project item-edit`, ids
  from `gh project field-list {number} --owner {owner} --format json`).
- `TaskCreate` one task per step below, each `in_progress` / `completed` (none under `/app:run-batch`).

## Step 3 — Acceptance first

- A new or changed business rule goes into its spec, a changed command into its contract,
  with their reviewer, before the code (their folder's `README.md`).
- Every Done-when clause becomes a failing test (loop § 1, step 3).
- A fault met in production: ask for the input that shows it before designing a fix,
  and reproduce it in a failing test first (loop § 1).
- Run the suites; confirm the new tests are red. A clause the agent cannot run becomes
  a test of the harness — an E2E scenario when it needs the real window — or a `task`
  issue that asks for it (method § 1).

## Step 4 — Implement

Smallest change to green, the right way (loop § 4); Rule 2 holds.

## Step 5 — Harness

`just {harness}` until green, `just {push_harness}` (when set) before the first push: a floor
met with tests, an architecture violation fixed in code — never a gate file loosened.

## Step 6 — Reviewers

Exactly the lanes `bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh files | bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh` prints, in
one batch (lane `x` is `app:reviewer-x`; `spec`, `contract`: `app:spec-reviewer`,
`app:contract-reviewer`), each given the branch, the spec and the vocabulary; every finding
graded (loop § 5); again on the fixes before the first push until no 🔴 remains.

## Step 7 — Evidence and commit

`/app:visual-proof` for every changed `.tsx` / `.css`. One commit (the commit rules).

## Step 8 — Pull request and checks

- Push, `gh pr create --body-file`: the body of loop § 1, step 8.
- `python3 ${CLAUDE_SKILL_DIR}/scripts/watch-pr.py` in the background: exit 0 is green, 1 a
  check failed, 2 GitHub unreachable, 3 timed out, 4 not open, 5 GitHub never reached the
  local commit, 6 only lanes the usage limit stopped.
- A red reviewer lane: read its newest comment; grade and apply as loop § 5 says, as a
  `fixup!`; push.
- A lane stopped by the CI account's usage limit (by exit code or comment): nothing to
  fix. Wait for the reset time it names (a wake-up in chat, a sleep headless; outside
  Rule 4), then `gh run rerun <the run id> --failed` and watch again.
- Any other red: read the log first. If it shows the cause, fix it; if not, the next
  push adds observation and makes the failure cheap, never a fix (method § 4). Fix with
  `git commit --fixup <sha>` (never a new titled commit, never a force-push), push, watch
  again. The same gate red three times: open question, leave the PR open, stop.
- All green: every lane's newest comment graded in a PR comment (loop § 1, step 10).

## Step 9 — Closure

In the same PR, before the merge:

- **The source docs still match the code**: spec, contract, an ADR for a hard technical
  choice, the architecture doc for a new module; the PR body says which, or "docs: none needed".
- A spec touched or named: `app:spec-checker` on it, and what it reports fixed.
- What the task met and did not fix is folded or filed as loop § 5 says (headless too), never
  left in chat; a task issue the work resolved is `Closes #NN` too.

A closure commit is a `fixup!` pushed like any fix; once its checks are green again:

## Step 10 — Merge

`python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py` folds the fixups and lands the pull
request; then the closing brief with the PR number.

## Rules

1. Headless never asks the human; questions are comments on the issue.
2. The project's core rules and Step 5 hold, and the batch is never edited (method § 4).
3. One task per invocation. Stop after Step 10.
4. Method § 4's wall-clock budget per task; over it, open question and stop.
