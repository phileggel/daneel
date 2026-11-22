---
name: spec-proposal
description: The spec gate, required before a task adds or changes a business rule — drafts the spec change, has `app:spec-reviewer` read it and shows the owner the diff; nothing is built before the owner's yes. Invoked as `/app:spec-proposal <id>` (an issue number, or a slug for a chat request). With `spec-proposal.repo` the spec lives in its own repository, and the accepted change is pushed there.
argument-hint: "[123 | slug]"
allowed-tools:
  - Bash(gh issue view *)
  - Bash(gh issue comment *)
  - Bash(gh issue edit *)
  - Bash(gh repo clone *)
  - Bash(git -C * pull --ff-only)
  - Bash(git -C * diff)
  - Bash(git diff *)
  - Bash(git check-ignore *)
  - Bash(bash ${CLAUDE_SKILL_DIR}/scripts/publish.sh *)
---

# Skill — `spec-proposal`

The loop's spec gate (`${CLAUDE_SKILL_DIR}/../../loop.md` § 2).

`{folder}` is the spec folder: that of the first path of `review.rules.spec` in
`.claude/daneel.json` (default `docs/spec`). Its README holds the conventions.

Setting, optional: `spec-proposal.repo`, a repository (`owner/name`) holding the spec and
nothing else. With it, `{folder}` is a clone of that repository, which git ignores and the
agent never edits; without it, `{folder}` is part of the project.

## Step 1 — With `repo`: the spec at hand, and protected

- `{folder}` missing: `gh repo clone {repo} {folder}`; else `git -C {folder} pull --ff-only`.
- `git check-ignore -q {folder}` exits 0, and `.claude/settings.json` denies the folder's
  edits (`"Edit(/{folder}/**)"` under `permissions.deny`). One missing: name it for the
  owner to add, and stop.
- The spec's words are private data (loop § 4): a PR, a commit, an issue or a test name
  cites a rule by its ID, never its text.

## Step 2 — Read the task

`gh issue view <id> --json title,body,comments`, or the chat request. List the rules it
adds or changes. None: say so; the task goes on.

## Step 3 — Draft

In `{draft}`, as the README says: with `repo`, a clone in the scratchpad
(`gh repo clone {repo} {draft}`, or `git -C {draft} pull --ff-only` on an existing one);
without, `{folder}`, on `main`, before any branch.

## Step 4 — Review

`app:spec-reviewer` on each drafted file, given its path in `{draft}`. Fix its 🔴 and run
it again until none is left; what the draft leaves open is a question.

## Step 5 — Ask, then land

The diff is `git -C {draft} diff` with `repo`, `git diff -- {folder}` without.

- **Chat:** show the diff, ask each question alone, then ask for the yes. On a no, write
  what the owner wants on the issue (with `repo`, by rule ID) and stop. On a yes:
  - with `repo`: `bash ${CLAUDE_SKILL_DIR}/scripts/publish.sh {repo} {draft} {id}` commits
    the change, pushes the spec repository's `main` and prints the sha (exit 1: refused,
    the reason printed; say it and stop). Then `git -C {folder} pull --ff-only`, and one
    comment, `gh issue comment {id} --body-file <file>`: the accepted rule IDs and the sha.
  - without: the change stays uncommitted, and goes as it is into the task's commit.
- **Headless:** one comment, `gh issue comment {id} --body-file <file>`: the diff without
  `repo`, the rule IDs with it, the draft left in `{draft}`. Then
  `gh issue edit {id} --add-label needs-owner`; the owner answers in chat.

## Rules

1. No spec changes without the owner's yes to its diff: a rule found missing later comes
   back here.
2. With `repo`, the agent edits `{draft}` only, and the proposal never reaches the issue
   or the project's repository.
