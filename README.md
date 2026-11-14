# daneel

The way of working shared by phileggel's projects, served as a Claude Code plugin
marketplace, so a flow change is made once instead of once per repository.

Named after R. Daneel Olivaw, who kept to the Laws for twenty thousand years.

## The goal

A workflow that is **fluid, secure, of quality and fast**. Every rule the plugins ship is weighed
against all four:

- **Fluid**: a rule costs a run as little as it can. A check the agent runs itself,
  re-tested at the batch end and corrected with the owner in chat, beats a gate that
  stops the run; a rule need not hold perfectly to be worth having.
- **Secure**: what cannot be undone is held firm. A security or data-loss finding is
  always filed; nothing is pushed to `main` by the agent, a task's own branch is
  force-pushed (with lease) only by the script that lands it, and a release is published
  by the owner alone.
- **Quality**: a rule is measured at each batch end, so whether it works is known, not
  assumed.
- **Fast**: a rule that adds steps to every run shows at the batch end what it pays back.

## Plugins

| Plugin | Holds |
| ------ | ----- |
| `flow` | Any project: the batch method (`method.md`), `init`, `plan-batch`, `backlog`, `flow-audit` (`plugins/flow/README.md`) |
| `app` | The addon for Tauri + React apps: the loop (`loop.md`), `run-entry`, `run-batch`, `design-proposal`, the document reviewers, the seven stack lanes and `reviewer-guides` with their `protocol.md`, `visual-proof`, `dep-audit` (`plugins/app/README.md`) |

`flow` holds what any project can use. What only the apps share is `app`, used
beside `flow`; what one project alone runs stays in that project.

## Use in a project

Once per machine:

    claude plugin marketplace add phileggel/daneel
    claude plugin install flow@daneel --scope project
    claude plugin install app@daneel --scope project     # a Tauri + React app

Then `/flow:init` in the project adds what it lacks, asking first.

In a project's `.claude/settings.json`, so headless runs and teammates get it too:

```json
{
  "extraKnownMarketplaces": {
    "daneel": { "source": { "source": "github", "repo": "phileggel/daneel" } }
  },
  "enabledPlugins": { "flow@daneel": true, "app@daneel": true }
}
```

A skill or an agent is then named by its plugin, `/flow:flow-audit`, `app:spec-reviewer`.
A project adds no allow-list line for a plugin's scripts: a skill's `allowed-tools`
names each one. Never add a line of the shape `Bash(python3 *<script>*)` or
`Bash(bash *<script>*)`: its leading wildcard also allows `python3 -c '<anything>' <script>`.

Measured on `allowed-tools` under `claude -p`, and only this:

- A forked skill whose `allowed-tools` is plain `Bash` runs (`flow-audit`, 2026-10-25).
- `/app:run-entry`, 2026-11-14, on the sandbox's app (`python3 sandbox/run.py`, the
  `resume` and `ready-task` scenarios; three runs): Claude Code 2.1.325,
  `claude-sonnet-5-5`, `--permission-mode acceptEdits`, the plugins loaded with
  `--plugin-dir`, the app's allow list holding its `just` recipes only.
  - **Ran, never denied:** `git status --short`, `git branch --show-current`,
    `git pull --ff-only`, `git checkout -b`, `git add`, `git commit -m`,
    `git push -u origin HEAD`, `gh project item-list`, `gh project field-list`,
    `gh project item-edit`, `gh issue view`, `gh pr list`, `gh pr checkout`,
    `gh pr create`, and the scoped lines
    `bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh files | bash ${CLAUDE_PLUGIN_ROOT}/scripts/review-lanes.sh`
    and `python3 ${CLAUDE_SKILL_DIR}/scripts/watch-pr.py`, each written by the session
    as the script's absolute path.
  - **Denied:** a chain of commands with any part not listed, 11 times (#92); the `Read`
    of the plugin's `loop.md`, `method.md` and `protocol.md`, by the session and by both
    reviewers it started (#91); the `Write` of a pull request's body under `/tmp` and
    under `.git/` (#93); `gh pr view` and `gh pr checks` on a resumed task, which the skill
    does not name (#95).
  - **Not reached**, so not measured: `merge.py`, `git commit --fixup`, `gh run view`,
    `gh run rerun`, `gh issue comment`, `gh issue edit`, `gh pr comment`, `gh pr edit`,
    the reviewers' own `branch.sh` and `review-path.sh` calls, a plugin installed from
    the marketplace, and every other skill.
- A project's allow list is ignored in a folder nobody opened interactively ("this
  workspace has not been trusted"), and applies when the same file is passed as
  `--settings` (2026-11-14, same version).

What differs between projects is the project's own: `.claude/daneel.json` (one key per
piece: `flow-audit`, `plan-batch`, `backlog`, `review`, `run-entry`, `run-batch`,
`design-proposal`, `visual-proof`, `dep-audit`).
Each skill's doc names its keys; the docs a project's reviewers read are `review.rules.<lane>`
(`spec`, `contract` and `adr` naming that kind's README first), `review.glossary`,
`flow-audit.guides` and `visual-proof.rules`.

## In CI

A plugin works from a plain checkout of this repository: every file a skill or an
agent reads is reached from its own folder, and every script measures the checkout it
runs in. A CI job checks daneel out beside the project, at a release tag, and its prompt
reads the agent from there:

```yaml
- uses: actions/checkout@v4
  with:
    repository: phileggel/daneel
    ref: app--v0.2.0
    path: .daneel
```

```yaml
prompt: |
  Read `.daneel/plugins/app/agents/spec-reviewer.md` and follow it.
  `${CLAUDE_PLUGIN_ROOT}` in it is `.daneel/plugins/app`.
```

Read that way the agent file is plain text: Claude Code fills `${CLAUDE_PLUGIN_ROOT}`
only for an installed or `--plugin-dir` plugin, so the prompt says what it stands for.
The workflow's allowed tools name `bash .daneel/plugins/app/scripts/branch.sh *` and
`bash .daneel/plugins/app/scripts/review-path.sh *`. A pull request of the project
cannot soften a reviewer: the reviewer comes from the pinned tag, never the branch.

## Versions and releases

Each plugin has its own version, in its `plugin.json`: semver, the middle number moving
when a project must act (a setting renamed, a figure changed), the last for anything
else. Each plugin's `CHANGELOG.md` says, per version, what a project must do.

A release is a tag, `<plugin>--v<version>`, made on `main` once the bump is merged:

    claude plugin tag plugins/flow --push

- **Local and headless runs** follow `main`: `claude plugin update flow@daneel` (or the
  marketplace's auto-update) takes the newest version. Claude Code caches a plugin by its
  version, so a change that does not bump it never reaches a project.
- **CI** pins a tag (`ref: app--v0.2.0`) and moves it in a pull request of the project,
  so a reviewer change is reviewed where it lands.
- **To pin a machine**, register the marketplace at the ref, once per machine:
  `claude plugin marketplace add phileggel/daneel#<ref>`; `update` keeps it. A `ref` in
  `extraKnownMarketplaces` is ignored once the marketplace is registered: the clone stays on
  `main`, silently (measured 2026-10-31). Moving a pin is the owner's step: `marketplace remove` first,
  which empties `enabledPlugins` in the project's settings;
  `claude plugin install <plugin>@daneel --scope project` restores it.

## Status

A project keeps its own copies of a piece until its own ticket removes them. A skill
moves here only after its copies are measured in the projects, never designed generic
up front. What a skill still reads from the
project is its own record — its rules, its usage log, its GitHub — never a script or
a doc of the plugin.

A plugin's `CHANGELOG.md` is what a project must act on when it takes a new version.

## Developing daneel

Daneel holds the plugins and does not run them: `/flow:…` and `/app:…` are not loaded in
this repository, and their method and rules are for child projects. Work here follows
`CLAUDE.md` and lands through the `validate` and `review` checks. Daneel can have its own
skills in `.claude/skills/`, which never ship. Its backlog is GitHub issues, filed from
`.github/ISSUE_TEMPLATE/`: `feature`, `bug` or `harness`.

`sandbox/` is daneel's own too, and never ships: `sandbox/acme/` is an invented Tauri +
React app the plugins' workflows are run on, as a child project would be. Its files
(`.claude/daneel.json`, `required-checks.json`, `justfile`) configure that app and are no
rule for daneel, and no plugin reads or names it. Its `just harness` runs `cargo test` on
`src-tauri/core/` and Vitest on `src/`, never building the Tauri shell;
`tests/test_sandbox_acme.py` runs it after `npm ci` in `sandbox/acme/`, with `just` and
`cargo` on the machine.

A run never works on `sandbox/acme/` itself: `python3 sandbox/snapshot.py restore` builds a
copy with a fixed history and a local bare `origin` in a temporary folder and prints it,
and `python3 sandbox/snapshot.py discard <folder>` throws it away.

A run's `gh` is `sandbox/fake_gh.py`, a fixture and not a simulator:
`python3 sandbox/fake_gh.py install <bin> <scenario> <log>` writes a `gh` to put first on
`PATH`, which answers each command from the scenario's files, logs every call, and fails on
a command the scenario does not answer.

`sandbox/scenarios/` holds the answers: `backlog.json` and `backlog/` are the app's Project,
six invented issues and its one open pull request, as `gh` prints them;
`requests/` holds chat requests on the app, one per file.

`python3 sandbox/run.py <scenario>` runs one scenario: it restores the copy with the
scenario's branches, puts the fake `gh` first on `PATH`, runs `claude -p` on the
scenario's prompt in the copy with this checkout's `flow` and `app` plugins, then checks the
outcomes the scenario's `expect` lists (the `gh` calls logged, the branches of the copy
and of its `origin`, the Bash commands run) and prints a JSON report with the cost the
session reported. Exit 0 every expectation met, 1 one not met, 2 the run did not finish, 3
refused. It is a real model call, bounded by `--max-budget-usd` (default 3), so it runs on
demand and is no required check; its tests replace `claude` with a stub. `resume` is the
first scenario: a task stopped in review is picked and its checkout called, with no new
branch; it stops there, since a fixture's `gh pr checkout` changes no branch. `ready-task`
is the one `allowed-tools` was measured on: nothing to resume, the first Queued item waiting
on the owner, the next one a ready task.

A scenario runs through plain `claude -p`, not `claude plugin eval`. Measured 2026-11-14
with Claude Code 2.1.325 on the owner's Linux machine, and only this: an eval suite under
`sandbox/evals/`, run from the repository's root with `--eval-dir sandbox/evals`, loads
both plugins from `plugins:` paths (a path outside the folder it is run against is
refused), but every Bash call of a run fails before its command starts (`apply-seccomp:
... nested userns is capability-restricted`): the sandbox eval puts shell commands under
cannot start while `kernel.apparmor_restrict_unprivileged_userns` is 1.
