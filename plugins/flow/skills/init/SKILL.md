---
name: init
description: Sets a project up for daneel's flow, adding only what it lacks — the GitHub Project and its fields, the flow's labels, the issue forms, `.claude/daneel.json`, the usage log, a line in CLAUDE.md — after asking the owner about each missing part. Never overwrites. Use once when a project adopts the flow, and again after a flow update that needs something new.
disable-model-invocation: true
---

# Skill — `init`

The flow's method is `${CLAUDE_SKILL_DIR}/../../method.md`; its section "What the project
provides" is the checklist this skill walks. The project keeps its own part only.

## Step 1 — Look

From the project's checkout, read without changing anything:

- `.claude/daneel.json`, `CLAUDE.md`, `.github/ISSUE_TEMPLATE/`, `scripts/usage_log.py`;
- `gh repo view --json nameWithOwner`, `gh label list --limit 200 --json name`;
- `gh project list --owner <owner> --format json`, and for the project's Project, if
  there is one, `gh project field-list <number> --owner <owner> --format json`;
- the tags (`git tag -l 'v*' 'batch/*'`) and `.github/workflows/`.

List, for each item of the checklist: present, missing, or different (a label of another
colour or description is present). A label the checklist does not name is the project's
own (`mvp`, `accessibility`): leave it, never list it as a problem.

## Step 2 — Ask

One message to the owner, only about what is missing or needs the owner's choice:

- **The Project**: use an existing one (which), or create one.
- **Batch ends**: releases (`v*`) or `batch/<date>` tags, and the CI workflow that runs on
  every push (`flow-audit.round_workflow`).
- **Backlog**: its healthy size (`backlog.target`, a weight: S 1, M 2, L 4, XL 8), or none;
  over it, the ceiling makes it shrink.
- **Commit types**, if the project's commit rules differ from the default.
- **Personal data**: does an issue risk holding a user's real data? If so, the forms'
  checkbox wording (title and statement).
- **Usage log**: measure the project's scripts (copy the two helpers into `scripts/`), or not.

Defaults are proposed with each question; the owner answers in one reply. Nothing is done
before the answer.

## Step 3 — Add

Only what is missing, never replacing a file, a field or a label:

1. **Project**: `gh project create` if asked; its Status field gets the method's values that
   are missing, and a `Batch` text field if absent.
2. **Labels**: `gh label create <name> --description <…> --color <…>` for each missing flow
   label (without `--force`: a present one stays as it is).
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

Then one pull request on a branch of its own (`chore: set up daneel's flow`), never on
`main`; the Project and the labels are already on GitHub, and the pull request body lists
them.

## Report

What was present, what was added, what the owner declined. A missing item the owner
declined is not asked again unless the owner runs the skill to change it.
