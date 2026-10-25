---
name: run-batch
description: Runs a whole batch in chat — every Queued item of the Project through /app:run-entry, one after the other, then the batch's end (a release cut to its draft, or a batch tag), /flow:flow-audit, then the closing brief. Chains the existing skills and decides nothing new. Use when the owner says to run the batch.
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/release.py)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/release.py *)
  - Bash(bash ${CLAUDE_SKILL_DIR}/scripts/batch-end.sh)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh)
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh *)
---

# Skill — `run-batch`

A batch from its Queued items to its closing brief (`flow`'s method, `${CLAUDE_SKILL_DIR}/../../method.md`, § 5; the
loop, `${CLAUDE_SKILL_DIR}/../../loop.md`, § 1 and § 8); this file only puts existing skills
and rules in order. Settings (`.claude/daneel.json`): the Project is `plan-batch.owner` and
`.number`; under `run-batch`, all optional:

- `release_check` — a recipe run before a release's hand-over (`just {release_check}`);
- `version_files` — the files that carry the version, the first read for the current one
  (default `["package.json"]`): `package.json`, `package-lock.json` (its two places), any
  other `*.json` with a top-level `"version"` (`tauri.conf.json`), a `Cargo.toml` (its
  `[package]` version; its `Cargo.lock` follows);
- `changelog` — the file the release writes its section in (default `CHANGELOG.md`);
- `release_workflow` — the workflow a `v*` tag starts, which makes the draft release (its
  file name, `release.yml`); unset, `release.py` makes the draft itself.

## Step 0 — Preconditions

Chat only. `git status --short` is empty and `main` is fresh (`git pull --ff-only`);
otherwise stop and report.

## Step 1 — Read the batch and show it

`gh project item-list {number} --owner {owner} --format json --limit 500`: the items with
Status Queued and the latest Batch date, in row order, and those already Done.
`TaskCreate` one task per remaining item in order, then "Batch end", "Flow audit" and
"Closing brief".
Mark each task `in_progress` when it starts, `completed` once merged; `/app:run-entry`
creates none under it.

## Step 2 — Ask first

For every remaining item, before any of them starts: the decision scan (method § 2), and
`/app:design-proposal` for each that changes what the user sees and is not `validated`.
Put the questions and the mocks to the owner one at a time; write each answer on its
issue. The batch then runs without waiting on the owner.

## Step 3 — Run the items

For each remaining item that is ready, in order: `/app:run-entry #123` (the next may be
prepared while one waits, loop § 7).

Stop, and say where, when `/app:run-entry` stops by its own rules (an open question, the
same gate red three times, the three-hour budget). An item that is not ready is said so
and skipped.

## Step 4 — End the batch

When every item of the batch has been run, skipped or stopped on (method § 5, loop § 1):
the release sweep (loop § Release sweep) and the project's batch-end checks, their
findings folded or filed. Then, on the final `main`:

    python3 ${CLAUDE_SKILL_DIR}/scripts/release.py --preview

- **Exit 0, a `feat` or `fix` is in the batch:** `just {release_check}` when set,
  `/app:dep-audit` (a known vulnerability in what ships blocks the release), then

      python3 ${CLAUDE_SKILL_DIR}/scripts/release.py

  in the background: it lands the version and changelog through a green pull request,
  tags `v<version>` and leaves the draft release; it never publishes. Stopped, it says
  what to do; `--draft v<version>` redoes the draft alone once the tag is pushed.
- **Exit 3, no `feat` or `fix`:** `bash ${CLAUDE_SKILL_DIR}/scripts/batch-end.sh` tags
  the fresh `main` `batch/<UTC date>`.

Then, in both cases, `/flow:flow-audit` once the tag is pushed and, for a release, the
draft made (method § 5).

## Step 5 — The closing brief, last

The last thing the run says: what shipped (each issue with
its pull request), what a user notices (the `feat` and `fix` titles, or "nothing"), what
was filed during the run, what was left — skipped, stopped or not ready — with why, the
dependency audit's verdict, the flow audit's verdict, and for a release "everything is
made but the publishing: <the draft>, <the runs>".

## Rules

1. It chains; it decides nothing. A choice a step does not settle goes to the owner.
2. Never add to or reorder the batch, never publish a release, never skip an item
   silently.
3. One batch per invocation: it ends with the closing brief.
