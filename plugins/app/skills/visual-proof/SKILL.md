---
name: visual-proof
description: Captures and commits visual proof screenshots for any `.tsx` / `.css` change. Generates a full preview for every component state (idle/loading/results/empty/error) in both light and dark mode, captures with the project's Playwright via the skill's `scripts/visual-proof-capture.mjs`, and reports any console errors found.
allowed-tools:
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh *)
  - Bash(node ${CLAUDE_SKILL_DIR}/scripts/visual-proof-capture.mjs *)
  - Bash(npx vite *)
  - Bash(curl *)
  - Bash(git add screenshots/)
  - Bash(git restore --staged screenshots/.console-errors.json)
  - Bash(git status *)
---

# Skill — `visual-proof`

The steps of the project's `docs/visual-proof-rules.md`, which owns the rules. Every state is captured
in light and dark; the console errors seen during the capture are reported, so the skill
also finds bugs.

Chat, it asks; headless (under `/app:run-entry` with no one to ask), it never does: it
takes what it infers and says so in the report.

## Step 0 — The config

`visual-proof` in `.claude/daneel.json`: `vite_preview_port`, `vite_preview_host`,
`global_css_import`, `i18n_import`, and optionally `frontend_match` and
`frontend_exclude` (extended regular expressions; default `^src/.*\.tsx$` and none).

## Step 1 — The component

`bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh files --match {frontend_match}` (with
`--exclude {frontend_exclude}` when set): one is taken; for
several, chat asks which with `AskUserQuestion`, headless takes each in turn; for none,
chat asks for a component path (bug hunting on an unchanged component), headless stops
and says so. Its name is the file's (`LoginForm.tsx` → `LoginForm`).

## Step 2 — The states

Read the component; infer the states it exposes from its props and logic (loading flags,
error props, empty data, conditional renders). Idle is always one. Chat asks with
`AskUserQuestion`: which states (the inferred ones proposed), whether an interaction needs
a video clip (hover, a modal opening, an animation), and any selector to mask (timestamps,
avatars, random ids). Headless takes every inferred state, no clip, and masks what plainly
varies between runs (a timestamp, a random id).

## Step 3 — The preview

Read the component, `src/bindings.ts` and, when one exists for its domain,
`docs/contracts/{domain}-contract.md`, for realistic data shapes.

The config's paths are from the repository root; from `src/__preview__/main.tsx` strip
the leading `src/` and prefix `../` (`src/i18n/config.ts` → `../i18n/config`).

**`preview.html`** at the repository root:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{ComponentName} — Visual Preview</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/__preview__/main.tsx"></script>
  </body>
</html>
```

**`src/__preview__/main.tsx`**: the real component, the real `i18n_import` (imported for
its side effect, which initialises i18n) and `global_css_import` — no stub. Each state is
rendered with hard-coded realistic data shaped by the contract and the bindings (no
invented type, no `invoke()`; a store is mocked), inside `<div id="state-{name}"
style={{ padding: 24 }}>`: the capture targets that id, never a label or a text. A component using router or context hooks (`useNavigate`, `useLocation`) is wrapped
in its provider with mock values — otherwise it throws and the capture is silently blank.

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import "../ui/global.css"; // global_css_import
import "../i18n/config";
import { LoginForm } from "../features/auth/LoginForm";

if (new URLSearchParams(window.location.search).get("theme") === "dark") {
  document.documentElement.classList.add("dark");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div id="state-idle" style={{ padding: 24 }}>
      <LoginForm isLoading={false} error={null} />
    </div>
    <div id="state-error" style={{ padding: 24 }}>
      <LoginForm isLoading={false} error="Invalid credentials" />
    </div>
  </React.StrictMode>,
);
```

## Step 4 — Capture

`node_modules/playwright` missing means the dependencies are not installed: stop and say
so. Start Vite in the background (`run_in_background: true`), wait until it answers (a
cold start can exceed 3 s; `curl` retries for 30 s), capture (`--mask`, comma-separated,
for the masks), then stop the background Vite task — always, even after a failed capture
(`TaskStop` on it; no `kill` pipeline):

```bash
npx vite --port {vite_preview_port} --host {vite_preview_host}
```

```bash
curl -sf --retry 30 --retry-connrefused --retry-delay 1 -o /dev/null http://{vite_preview_host}:{vite_preview_port}/preview.html
```

```bash
node ${CLAUDE_SKILL_DIR}/scripts/visual-proof-capture.mjs --port {vite_preview_port} --host {vite_preview_host} --name {ComponentName} --states {state1,state2,...}
```

A capture that exited non-zero is reported, and nothing is staged.

## Step 5 — Stage and report

The screenshots are tracked in `screenshots/` (the visual history); the console-errors
file is not:

```bash
git add screenshots/
```

```bash
git restore --staged screenshots/.console-errors.json
```

```bash
git status --short -- screenshots/
```

```
## visual-proof — {ComponentName}

Screenshots staged ({count}):
- screenshots/{ComponentName}-{light|dark}-{state}.png
Video clips ({count}): (when any)

No console errors detected during capture.
  — or —
⚠️  Console errors detected ({count}) — investigate before merging:
  [light] {error text}

⚠️  Before committing — delete the preview files (never committed):
    rm -f preview.html
    rm -rf src/__preview__/
```
