---
name: run-batch
description: Runs a whole batch in chat — every Queued item of the Project through /app:run-entry, one after the other, then the batch's end (a release or a batch tag), then /flow:flow-audit. Chains the existing skills and decides nothing new. Use when the owner says to run the batch.
---

# Skill — `run-batch`

A batch from its Queued items to its audit (`flow`'s method, `method.md`, § 5; the loop,
`${CLAUDE_SKILL_DIR}/../../loop.md`, § 1 and § 8); this file only puts existing skills and
rules in order. Settings (`.claude/daneel.json`): the Project is `plan-batch.owner` and
`.number`; optional `run-batch.release_check`, a recipe run before a release's hand-over.

## Step 0 — Preconditions

Chat only. `git status --short` is empty and `main` is fresh (`git pull --ff-only`);
otherwise stop and report.

## Step 1 — Read the batch and show it

`gh project item-list {number} --owner {owner} --format json --limit 500`: the items with
Status Queued and the latest Batch date, in row order, and those already Done.
`TaskCreate` one task per remaining item in order, then "Closing brief and batch end"
and "Flow audit". Mark each task `in_progress` when it starts, `completed` once merged;
`/app:run-entry` creates none under it.

## Step 2 — Ask first

For every remaining item, before any of them starts: the decision scan (method § 2), and
`/app:design-proposal` for each that changes what the user sees and is not `validated`.
Put the questions and the mocks to the owner one at a time; write each answer on its
issue. The batch then runs without waiting on the owner.

## Step 3 — Run the items

For each remaining item that is ready, in order: `/app:run-entry #123`. While a pull
request waits for its checks, the next task may be prepared on a branch not pushed yet
(loop § 7).

Stop, and say where, when `/app:run-entry` stops by its own rules (an open question, the
same gate red three times, the three-hour budget). An item that is not ready is said so
and skipped.

## Step 4 — Say what the batch achieved, then end it

When every item of the batch has been run, skipped or stopped on, the closing brief of
the batch, before anything else: what shipped (each issue with its pull request), what a
user notices (the `feat` and `fix` titles, or "nothing"), what was filed during the run,
and what was left — skipped, stopped or not ready — with why.

Then end it (method § 5, loop § 1): the release sweep (loop § Release sweep) and the
project's batch-end checks, their findings folded or filed. With a `feat` or `fix`, on
the final `main`: `just {release_check}` when set, `/app:dep-audit`, `just release`, then the hand-over —
everything is made but the publishing: the draft, the dependency audit's verdict, what
was filed and the runs; without, `just batch-end` on a fresh `main`.

## Step 5 — Publish and audit

After a `batch/<date>` tag: `/flow:flow-audit`, once. After a release: the owner
publishes it outside the run, so stop with the hand-over; the next run starts with the
audit (method § 5).

Step 0 of every run: a published release with no audit yet is audited first.

## Rules

1. It chains; it decides nothing. A choice a step does not settle goes to the owner.
2. Never add to or reorder the batch, never publish a release, never skip an item
   silently.
3. One batch per invocation: it ends with the audit.
