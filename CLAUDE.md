# daneel

A Claude Code plugin marketplace: the flow and the harness phileggel's projects share,
simple and portable. `README.md` says what it holds.

## Two kinds of AI content, never mixed

- **Plugin content** (`plugins/`: skills, agents, method, loop) ships to child projects. It
  is not loaded here and is no rule for developing daneel.
- **Daneel's own** (this file, `.github/review/`, skills in `.claude/skills/`) guides work
  on this repository and never ships.

## What belongs here

- Nothing here knows one project, and nothing names one: not a skill, script, test,
  changelog, manifest or README, and no project's file path, rule ID or ticket ID.
  Examples are invented (`acme`, `src-tauri/src/auth/`). A line that needs a
  project's name belongs in that project.
- A plugin piece comes here extracted from the projects' copies, the differences measured
  and recorded in its pull request, never written generic first.
- The backlog is GitHub issues (`.github/ISSUE_TEMPLATE/`, one form per kind: `feature`, `bug`, `harness`), never files in git.

## How a plugin piece is written

- A plugin ships every script and doc its skills and agents use, and names them through
  `${CLAUDE_SKILL_DIR}` or `${CLAUDE_PLUGIN_ROOT}`, never a bare `scripts/` and never the
  project's checkout. A script measures the checkout it runs in, and works from a plain
  checkout too.
- A plugin never reads another plugin's folder: `app` reads `flow`'s method through its own
  `method.md` link, and names anything else by skill or agent (`/flow:flow-audit`).
- Every command a skill tells the agent to run is written literally, and its
  `allowed-tools` covers it, or the skill says the
  project's own allow list covers it. A skill that can run
  headless never asks: it says what it takes instead.
- One command per shell call: no `&&`, `||`, `;`, `$(...)`, retry loop or `kill`
  pipeline, in a skill as in the recovery lines a script prints.
- What a project's guidelines define (scopes, sections, folders) is read from its docs,
  the piece keeping only its checks and a default; any other per-project difference is a
  key in `.claude/daneel.json`, under the piece's own name, documented in the skill that
  reads it, and listed in its plugin's README and the root README. A script refuses a key
  of its section that no piece reads, and treats a shared file (`required-checks.json`)
  exactly as the other scripts do.
- A script's exit codes read the same in its header and in the skill that acts on them.
- A claim that something was measured says what, when, and covers only that.
- Every doc an agent reads is as concise as it can be: each line is one the agent acts
  on. Each has a word ceiling in `doc-ceilings.json`, lowered with the doc; only the owner
  raises one.

## What the agent never does, and nothing here makes it do

Push a project's `main`; force-push, except the landing script pushing the task's own
branch with lease after folding or rebasing it; publish a release (it cuts the tag and
the draft); bypass a hook (`--no-verify`).

## Checks and releases

- A script that pushes, tags or merges has a test for each of those paths, asserting the
  exact command; no test talks to a real remote.
- Every change to a plugin bumps its `version` in `plugin.json` and adds its
  line to the plugin's `CHANGELOG.md`, saying what a project must do.
- `claude plugin validate .` and `python3 -m unittest discover -s tests` pass before a
  commit. A pull request lands only with `validate` and `review` green. A
  release is `claude plugin tag plugins/<plugin> --push` on `main`.
