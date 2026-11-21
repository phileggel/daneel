---
name: design-proposal
description: Produces the design proposal required before anything the user sees changes — rendered mocks of the target state in light and dark, plus a five-line note, posted on the issue — for an issue or a chat request. Invoked as `/app:design-proposal <id>` (an issue number, or a slug for a chat request). The owner validates; nothing visible is built before.
argument-hint: "[123 | slug]"
allowed-tools:
  - Bash(gh issue view *)
  - Bash(gh issue comment *)
  - Bash(gh issue edit *)
  - Bash(gh repo clone *)
  - Bash(git -C * pull --ff-only)
  - Bash(bash ${CLAUDE_SKILL_DIR}/scripts/publish.sh *)
  - Bash(node ${CLAUDE_SKILL_DIR}/../visual-proof/scripts/visual-proof-capture.mjs *)
  - Bash(npx vite *)
  - Bash(curl *)
  - Bash(rm -f preview.html)
  - Bash(rm -rf src/__preview__)
---

# Skill — `design-proposal`

The loop's design gate (`${CLAUDE_SKILL_DIR}/../../loop.md` § 2).

Setting, optional: `design-proposal.repo` in `.claude/daneel.json`, a repository
(`owner/name`) holding only mocks and notes; without it, `screenshots/design/`.

## Step 1 — Read the task

Load the issue (`gh issue view <id> --json title,body,comments`) or the chat request. From it and
its Done when, list the screens and states that change: one state per distinct thing the
owner must see (the row with the new column, the empty case if it changes).

## Step 2 — Build the target state as a preview

Follow `${CLAUDE_SKILL_DIR}/../visual-proof/SKILL.md` Steps 0 (config) and 3 (write
`preview.html` and `src/__preview__/main.tsx`), with one difference: the preview renders
the **proposed** component tree: the current component copied where the change is
layout-only, or existing `ui/` components for a new surface. For a state of an existing
screen it also renders the **current** component, imported as it is, same sample data,
under the id `state-{state}-current`. Sample data is invented. Never modify the real
component; the preview is disposable.

## Step 3 — Capture

The output folder `{out}`: with `repo`, `{clone}/{id}` in a clone in the scratchpad
(`gh repo clone {repo} {clone}`, or `git -C {clone} pull --ff-only` on an existing one); without,
`screenshots/design`. Then visual-proof Step 4 with that folder.

```bash
node ${CLAUDE_SKILL_DIR}/../visual-proof/scripts/visual-proof-capture.mjs --port {vite_preview_port} --host {vite_preview_host} --name {id} --states {state1,state1-current,state2} --out {out}
```

Produces `{out}/{id}-{light|dark}-{state}.png`, `-current` included. Then `rm -f preview.html` and
`rm -rf src/__preview__`, each its own call, whatever the capture did.

## Step 4 — Write the note

`{out}/{id}.md`, five lines at most: what moves, is added, is removed, stays; one open point.

## Step 5 — Publish, then ask or record

`publish.sh` commits and pushes, never the console-errors file, and prints the sha:

- **With `repo`**: `bash ${CLAUDE_SKILL_DIR}/scripts/publish.sh repo {repo} {clone} {id}`;
  images from `https://github.com/{repo}/blob/<sha>/{id}/<file>?raw=true`.
- **Without**, headless only: `bash ${CLAUDE_SKILL_DIR}/scripts/publish.sh branch {id}`
  (on `design/{id}`, back on `main` after); images from that branch.

The comment is a scratchpad file (the note, then each image; an existing screen's
state is a table row per theme, Current left, Proposed right), posted with
`gh issue comment {id} --body-file <file>`; without an issue, the links go in chat.

- **Chat:** show or point to the images and the note, and ask. On a yes, set the issue's
  Design to `validated` (`gh issue edit`; without an issue, say so in the PR body) and
  continue. On a no, write what the owner wants on the issue and stop.
- **Headless:** `gh issue edit {id} --add-label needs-owner`. The owner validates in the
  thread.

## Rules

1. Real components and tokens only; no drawing tools, no hand-made images.
2. Both themes for every state.
3. The proposal never reaches the project's `main`: the issue holds it.
