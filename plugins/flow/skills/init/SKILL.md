---
name: init
description: Sets a project up for daneel's flow, adding only what it lacks — the GitHub Project and its fields, the flow's labels, the issue forms, `.claude/daneel.json`, the usage log, a line in CLAUDE.md — after asking the owner about each missing part. Never overwrites. Use when a project adopts the flow, and again when its rules or daneel's version move: a re-run re-aligns it.
disable-model-invocation: true
---

# Skill — `init`

The checklist is `${CLAUDE_SKILL_DIR}/../../method.md` § What the project provides. The
project keeps its own part only.

## Step 1 — Look

From the project's checkout, read without changing anything:

- `.claude/daneel.json`, `CLAUDE.md`, `.github/ISSUE_TEMPLATE/`, `scripts/usage_log.py`;
- `gh repo view --json nameWithOwner`, `gh label list --limit 200 --json name`;
- `gh project list --owner <owner> --format json`; its Project's
  `gh project field-list <number> --owner <owner> --format json`;
- the tags (`git tag -l 'v*' 'batch/*'`) and `.github/workflows/`.

Each checklist item: present, missing, or different (another colour or description). A label the checklist does not name is the project's
own: leave it.

## Step 2 — Ask

One message to the owner, only about what is missing or needs the owner's choice:

- **The Project**: an existing one (which), or a new one.
- **Batch ends**: `v*` releases or `batch/<date>` tags; the workflow run on every push
  (`flow-audit.round_workflow`).
- **Backlog**: its healthy size (`backlog.target`, a weight), or none.
- **Commit types**, where they differ from the default.
- **Personal data**: can an issue hold a user's real data? If so, the forms' checkbox wording.
- **Usage log**: measure the project's scripts, or not.

A default beside each question; one reply; nothing is done before it.

## Step 3 — Add

Only what is missing, never replacing a file, a field or a label:

1. **Project**: `gh project create` if asked; the Status values missing, and a `Batch` text
   field if absent.
2. **Labels**: `gh label create <name> --description <…> --color <…>` for each missing flow
   label; a present one stays.
3. **Issue forms**: each of `${CLAUDE_SKILL_DIR}/templates/ISSUE_TEMPLATE/*.yml` absent from
   `.github/ISSUE_TEMPLATE/`, with `{{project}}` as `<owner>/<number>` and the privacy
   wording; without personal data, the privacy checkbox is left out.
4. **`.claude/daneel.json`**: the keys answered, merged into the file — a key already set
   stays.
5. **Usage log**, if asked: `templates/usage_log.py` and `templates/usage-log.sh` into
   `scripts/` when absent, and `logs/` in `.gitignore`.
6. **CLAUDE.md**: when it does not name the flow, one line: "This project runs daneel's
   flow (`flow@daneel`); its method is the plugin's `method.md`, and this file and the
   project's documents hold only what is this project's own."

Then one pull request on its own branch (`chore: set up daneel's flow`), never on `main`;
its body lists the Project and labels made.

## Report

What was present, what was added, what the owner declined; the record of the run.

## Re-run — a project already set up

Step 1 also reads the pins (`extraKnownMarketplaces.daneel.source.ref` in
`.claude/settings.json`; Grep `--v` under `.github`) and the sections of
`${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md` newer than the pinned version. Step 2 adds three blocks: a `daneel.json` path that no longer exists, a form or label drifted from
the template; a convention the project's docs now state against a default it never
overrode; the "To take it" lines between the pins, one checklist. Step 3 does the
mechanical ones — labels, forms, keys, the pin line — and leaves a change to the
project's rules docs or CI as a proposal.
