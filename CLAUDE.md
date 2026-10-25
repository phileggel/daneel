# daneel

A Claude Code plugin marketplace: the flow shared by phileggel's projects.
`README.md` says what it holds and how a project enables it. These rules are what a
change here is reviewed against.

## What belongs here

- Nothing here knows one project, and nothing names one: not a skill, script, test,
  changelog, manifest or README, and no project's file path, rule ID or ticket ID.
  Examples are invented (`acme`, `ORD-1`, `src-tauri/src/auth/`). A line that needs a
  project's name belongs in that project, or in a setting the project gives the skill.
- A skill comes here extracted from the projects' copies, with the differences
  between them measured and recorded in its pull request — never written
  generic first.
- The backlog is GitHub issues (`.github/ISSUE_TEMPLATE/`), never files in git.

## How a piece is written

- A plugin ships every script and doc its skills and agents use, and names them through
  `${CLAUDE_SKILL_DIR}` or `${CLAUDE_PLUGIN_ROOT}`, never a bare `scripts/` and never the
  project's checkout. A script measures the checkout it runs in, and works from a plain
  checkout too, as CI uses it.
- A plugin never reads another plugin's folder. `app` depends on `flow`
  (`"dependencies"` in its `plugin.json`) and reads `flow`'s method through its own
  `method.md`, a link the install copies in; anything else across plugins is named by
  skill or agent (`/flow:flow-audit`), never by path.
- Every command a skill tells the agent to run is written literally, and its
  `allowed-tools` covers it — a headless run approves nothing — or the skill says the
  project's own allow list covers it (a project's `just` recipe). A skill that can run
  headless never asks: it says what it takes instead.
- One command per shell call: no `&&`, `||`, `;`, `$(...)`, retry loop or `kill`
  pipeline, in a skill as in the recovery lines a script prints.
- Every per-project difference is a key in `.claude/daneel.json`, under the piece's own
  name, documented in the skill that reads it, and listed in its plugin's README and the
  root README. A script refuses a key of its section that no piece reads, and treats a
  shared file (`required-checks.json`) exactly as the other scripts do.
- A script's exit codes read the same in its header and in the skill that acts on them.
- A claim that something was measured says what, when, and covers only that.

## What the agent never does, and nothing here makes it do

Push a project's `main`; force-push, except the landing script pushing the task's own
branch with lease after it folded or rebased it; publish a release (it cuts the tag and
the draft); bypass a hook (`--no-verify`).

## Checks and releases

- A script that pushes, tags or merges has a test for each of those paths, asserting the
  exact command; no test talks to a real remote.
- Every change to a plugin bumps its `version` in `plugin.json` and adds its
  line to `CHANGELOG.md`, saying what a project must do.
- `claude plugin validate .` and `python3 -m unittest discover -s tests` pass before a
  commit; CI runs both. A release is `claude plugin tag plugins/<plugin> --push` on `main`.
