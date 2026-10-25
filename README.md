# daneel

The way of working shared by phileggel's projects — folioneer, PatientManager,
SpaceTycoon, DeuterosRE, DungeonMasterRE — served as a Claude Code plugin
marketplace, so a flow change is made once instead of once per repository.

Named after R. Daneel Olivaw, who kept to the Laws for twenty thousand years.

## The goal

A workflow that is **fluid, secure, of quality and fast**. Every rule here is weighed
against all four:

- **Fluid**: a rule costs a run as little as it can. A check the agent runs itself,
  re-tested at the batch end and corrected with the owner in chat, beats a gate that
  stops the run; a rule need not hold perfectly to be worth having.
- **Secure**: what cannot be undone is held firm. A security or data-loss finding is
  always filed; nothing is pushed to `main` or force-pushed by the agent, and a release is published by the owner alone.
- **Quality**: a rule is measured at each batch end, so whether it works is known, not
  assumed.
- **Fast**: a rule that adds steps to every run shows at the batch end what it pays back.

## Plugins

| Plugin | Holds |
| ------ | ----- |
| `flow` | Any project: the batch method (`method.md`), `init`, `plan-batch`, `backlog`, `flow-audit` (`plugins/flow/README.md`) |
| `app` | The addon for folioneer and PatientManager, Tauri + React apps: the loop (`loop.md`), `run-entry`, `run-batch`, `design-proposal`, the document reviewers, the seven stack lanes and `reviewer-guides` with their `protocol.md`, `visual-proof`, `dep-audit` (`plugins/app/README.md`) |

`flow` holds what any project can use. What only those two apps share is `app`, used
beside `flow`; what one project alone runs stays in that project.

## Use

Once per machine:

    claude plugin marketplace add phileggel/daneel
    claude plugin install flow@daneel --scope project
    claude plugin install app@daneel --scope project     # folioneer, PatientManager

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
already lets them run, forked and headless too (`flow-audit` under `claude -p`,
PatientManager, 2026-10-25). Never add a line of the shape
`Bash(python3 *<script>*)` or `Bash(bash *<script>*)`: its leading wildcard also allows
`python3 -c '<anything>' <script>`. The reviewers' scripts (`branch.sh`,
`review-path.sh`) are not measured yet; they are checked the same way the first time a
project's session runs a reviewer.

What differs between projects is the project's own: `.claude/daneel.json` (one key per
piece: `flow-audit`, `plan-batch`, `backlog`, `review`).
Each skill's doc names its keys.

## In CI

A plugin works from a plain checkout of this repository: every file a skill or an
agent reads is reached from its own folder, and every script measures the checkout it
runs in. A CI job checks daneel out beside the project, at a release tag, and its prompt
reads the agent from there:

```yaml
- uses: actions/checkout@v4
  with:
    repository: phileggel/daneel
    ref: app--v0.1.0
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
else. `CHANGELOG.md` says, per plugin and version, what a project must do.

A release is a tag, `<plugin>--v<version>`, made on `main` once the bump is merged:

    claude plugin tag plugins/flow --push

- **Local and headless runs** follow `main`: `claude plugin update flow@daneel` (or the
  marketplace's auto-update) takes the newest version. Claude Code caches a plugin by its
  version, so a change that does not bump it never reaches a project.
- **CI** pins a tag (`ref: app--v0.1.0`) and moves it in a pull request of the project,
  so a reviewer change is reviewed where it lands.

## Status

Version 0.1.0 of both plugins. PatientManager runs `flow` (PatientManager ticket #513)
and moves its copies in PatientManager ticket #538; folioneer follows. A project keeps
its own copies of a piece until its own ticket removes them. A skill
moves here only after its copies are measured in the projects, never designed generic
up front. What a skill still reads from the
project is its own record — its rules, its usage log, its GitHub — never a script or
a doc of the plugin.

The backlog is GitHub issues, filed from `.github/ISSUE_TEMPLATE/`.
`CHANGELOG.md` is what a project must act on when it takes a new version.
