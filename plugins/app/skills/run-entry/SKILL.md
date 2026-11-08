---
name: run-entry
description: Runs one task end to end under the loop, to its merge on green. The task is the first ready Queued item of the Project (headless, no argument), an issue the human names (#123), or a plain request typed in chat.
argument-hint: "[#123 | a request]"
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py *)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/watch-pr.py *)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/watch-pr.py)
  - Bash(git status --short)
  - Bash(git branch --show-current)
  - Bash(git pull --ff-only)
  - Bash(git checkout -b *)
  - Bash(git add *)
  - Bash(git commit -m *)
  - Bash(git commit --fixup *)
  - Bash(git push -u origin HEAD)
  - Bash(gh project item-list *)
  - Bash(gh project item-edit *)
  - Bash(gh project field-list *)
  - Bash(gh issue view *)
  - Bash(gh pr list *)
  - Bash(gh pr checkout *)
  - Bash(gh pr create *)
  - Bash(gh run rerun *)
  - Bash(gh run view *)
  - Bash(gh issue comment *)
  - Bash(gh issue edit *)
  - Bash(gh pr comment *)
  - Bash(gh pr edit *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh *)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh *)
---

# Skill — `run-entry`

The rules are the loop
(`${CLAUDE_SKILL_DIR}/../../loop.md`), `flow`'s method (`${CLAUDE_SKILL_DIR}/../../method.md`) and the project's
rules document.

Settings (`.claude/daneel.json`): the Project is `plan-batch.owner` and `.number`; under
`run-entry`, each optional:

- `recipes` — the project's `just` recipes by role: `harness` (default `harness`),
  `push_harness` (default none; `harness` runs once more before the first push).
- `record_paths` — the files whose move of `main` leaves the checks standing (default
  `["docs/adr/"]`; an entry ending in `/` is a folder of `.md` files).

## Step 0 — Preconditions and mode

- `git status --short` is empty, `git branch --show-current` is `main`, and `main` is
  fresh (`git pull --ff-only`). Otherwise stop and report.
- **Headless** (no argument): `gh project item-list {number} --owner {owner} --format json --limit 500`;
  an In progress or In review item without `needs-owner` and with an open pull request
  resumes; else the first Queued item, in row order, that is ready.
- **Chat, named issue** (`#123`): `gh issue view 123 --json title,body,comments`; one with an
  open pull request resumes.
- **Resume**: `gh pr list --state open --json number,headRefName` has its branch
  (`<type>/123-<slug>`); `gh pr checkout <number>`, then Step 8 from the watch, without the scan; a Dependabot pull request does not resume.
- **A Dependabot pull request** (queued or named): loop § Dependabot pull requests, not
  Steps 1 to 10; `python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py` on its branch.
- **Chat, plain request**: no issue is created; its Done when goes in the opening brief.
- **Decision scan and Ready** (method § 2), for an issue, before the branch exists; a flow
  issue's Decision and a task's Observation are its Done when. Chat: each open question
  alone (method § 2), its answer written on the issue.
  Headless: each a comment with `needs-owner`; skip what is not ready, and if nothing is,
  say what blocks each issue and stop. With a spec, loop § 1 step 1's order.

## Step 1 — Design gate

Before any branch exists, and before the item moves: anything the user sees changes and
`Design` is not `validated` — `/app:design-proposal <id>`.

- Chat: nothing is built before the human's yes to the mocks; on a no, stop.
- Headless: the proposal is posted on the issue (loop § 2), its Design set to `needed`;
  the item stays Queued. Back to Step 0 for the next ready item.

## Step 2 — Opening brief, branch, task list

- Opening brief (chat: first message; headless: top of the PR body): **Task** — one line · **Scope** — commit type, layers · **Design** — none / validated
  / needed · **Touching** — the paths.
- `git checkout -b <type>/123-<slug>` (`<type>/<slug>` for a plain request); the item's Status becomes In progress (`gh project item-edit`, ids
  from `gh project field-list {number} --owner {owner} --format json`).
- `TaskCreate` one task per step below (none under `/app:run-batch`).

## Step 3 — Acceptance first

- A new or changed business rule goes into its spec, a changed command into its contract,
  with their reviewer, before the code (their folder's `README.md`).
- Every Done-when clause becomes a failing test, confirmed red, unless no test can prove it (loop § 1, step 3). A clause the agent cannot run: method § 1 (an
  E2E scenario when it needs the real window).

## Step 4 — Implement

Smallest change to green, the right way (loop § 4).

## Step 5 — Harness

`just {harness}` until green, `just {push_harness}` (when set) before the first push (the project's allow list covers both); a gate file is never loosened.

## Step 6 — Reviewers

Exactly the lanes `bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh files | bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh` prints, in
one batch (lane `x` is `app:reviewer-x`; `spec`, `contract`: `app:spec-reviewer`,
`app:contract-reviewer`), and `app:spec-checker` once when the branch touches or names a
spec; every finding graded (loop § 5); again on the fixes before the first push until no 🔴 remains.

## Step 7 — Evidence and commit

`/app:visual-proof` for every changed `.tsx` / `.css`. One commit (the commit rules): `git add <path>`, `git commit -m <title>`.

## Step 8 — Pull request and checks

- Every push: `git push -u origin HEAD`. `gh pr create --body-file <file>`: the body of loop § 1, step 8.
- `python3 ${CLAUDE_SKILL_DIR}/scripts/watch-pr.py` in the background: exit 0 is green, 1 a
  check failed, 2 GitHub unreachable, 3 timed out, 4 not open, 5 GitHub never reached the
  local commit, 6 only lanes the usage limit stopped.
- A red reviewer lane: read its newest comment; grade and apply as loop § 5 says, as a
  `fixup!`; push.
- A lane with no verdict, its comment `no report` or stopped by the CI account's usage
  limit (by exit code or comment): nothing to fix. Re-run that lane alone: `gh run view <run id> --json jobs`
  for its job id, `gh run rerun --job <job id>`, watch again. At the limit, in chat: a wake-up
  at the reset time it names (outside Rule 2), or with none given, ask the owner.
  Headless, at the limit: that time, or that none was given, in a file, then `gh issue
  comment <n> --body-file <file>` and `gh issue edit <n> --add-label needs-owner` (`gh pr`
  for a plain request); leave the PR open, stop.
- Any other red: method § 4 (the log first). Fix with `git commit --fixup <sha>`, push, watch again.
- All green: every lane's newest comment graded in a PR comment (loop § 5).

## Step 9 — Closure

Before the merge:

- **The source docs still match the code** (spec, contract, ADR, architecture doc); the PR body says which, or "docs: none needed".
- What the task met and did not fix is folded or filed as loop § 5 says; a task issue the work resolved is `Closes #NN` too.

A closure commit is a `fixup!`; once its checks are green again:

## Step 10 — Merge

`python3 ${CLAUDE_SKILL_DIR}/scripts/merge.py` lands it; then the closing brief.

## Rules

1. The project's core rules and Step 5 hold, and the batch is never edited (method § 4).
2. Method § 4's wall-clock budget per task; over it, open question and stop.
