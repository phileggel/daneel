---
name: design-proposal
description: Produces the design proposal required before anything the user sees changes — rendered mocks of the target state in light and dark, plus a five-line note, posted on the issue — for an issue or a chat request. Invoked as `/app:design-proposal <id>` (an issue number, or a short slug for a chat request). The human validates; nothing visible is built before that.
argument-hint: "[123 | slug]"
allowed-tools:
  - Bash(node ${CLAUDE_SKILL_DIR}/../visual-proof/scripts/visual-proof-capture.mjs *)
  - Bash(npx vite *)
  - Bash(curl *)
---

# Skill — `design-proposal`

The proposal is what the human validates instead of the pull request (the loop,
`${CLAUDE_SKILL_DIR}/../../loop.md`, § 2). It shows the target state with the real components
and tokens, so what they approve is what ships.

Setting, optional: `design-proposal.repo` in `.claude/daneel.json`, a repository
(`owner/name`) holding only mocks and notes; without it, `screenshots/design/`.

## Step 1 — Read the task

Load the issue (`gh issue view <id> --comments`) or take the chat request. From it and
its Done when, list the screens and states that change: one state per distinct thing the
human must see (the row with the new column, the dialog with the moved buttons, the
empty case if it changes).

## Step 2 — Build the target state as a preview

Follow `${CLAUDE_SKILL_DIR}/../visual-proof/SKILL.md` Steps 0 (config) and 3 (write
`preview.html` and `src/__preview__/main.tsx`), with one difference: the preview renders
the **proposed** component tree, not the current one. Copy the current component into it
where the change is layout-only, or compose the target from existing `ui/` components for
a new surface. Sample data is invented, never copied from the installed app. Never modify
the real component; the preview is disposable.

## Step 3 — Capture

The output folder `{out}`: with `repo`, `{clone}/{id}` in a clone in the scratchpad
(`gh repo clone {repo} <scratchpad>/design`, or `git pull` an existing one); without,
`screenshots/design`. Then visual-proof Step 4 with that folder: start Vite in the
background, wait until the preview answers, capture, stop Vite.

```bash
node ${CLAUDE_SKILL_DIR}/../visual-proof/scripts/visual-proof-capture.mjs --port {vite_preview_port} --host {vite_preview_host} --name {id} --states {state1,state2} --out {out}
```

Produces `{out}/{id}-{light|dark}-{state}.png`. Delete `preview.html` and
`src/__preview__/` afterwards.

## Step 4 — Write the note

`{out}/{id}.md`, five lines at most: what moves, is added, is removed, stays; one open point.

## Step 5 — Publish, then ask or record

- **With `repo`**: commit the folder in the clone, push it straight to its `main` (no
  pull request, review, CI or hooks), and post the note on the issue with each image inline
  from the pushed commit (`https://raw.githubusercontent.com/{repo}/<sha>/<id>/<file>`);
  a chat request without an issue gets the links in chat.
- **Without**, headless only: commit them on a `design/{id}` branch, push it, and post the
  note on the issue with each image linked from that branch.
- **Chat:** show the images and the note, or point to where they are posted, and ask. On
  a yes, set the issue's Design to `validated` (`gh issue edit`; a chat request has no
  issue: say so in the PR body) and continue the task. On a no, write what the human
  wants on the issue and stop.
- **Headless:** add `needs-owner` to the issue. The human validates in the thread.

## Rules

1. Real components and tokens only; no drawing tools, no hand-made images.
2. Both themes for every state.
3. The proposal never touches production code.
4. The proposal never reaches the project's `main`: the issue holds it.
