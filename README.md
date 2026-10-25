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
  always filed; nothing is pushed to `main`, force-pushed or released by the agent.
- **Quality**: a rule is measured at each batch end, so whether it works is known, not
  assumed.
- **Fast**: a rule that adds steps to every run shows at the batch end what it pays back.

## Plugins

One plugin for now, `flow`: working on a project with agents, from planning a batch to
reviewing and auditing it — `plan-batch`, `backlog`, `flow-audit`, and `reviewer-guides`
with its `protocol.md` (`plugins/flow/README.md`). Only what any project can use is
here; what one project's conventions or stack alone can check stays in that project
(ticket #6).

## Use

Once per machine:

    claude plugin marketplace add phileggel/daneel
    claude plugin install flow@daneel --scope project

In a project's `.claude/settings.json`, so headless runs and teammates get it too:

```json
{
  "extraKnownMarketplaces": {
    "daneel": { "source": { "source": "github", "repo": "phileggel/daneel" } }
  },
  "enabledPlugins": { "flow@daneel": true }
}
```

A skill or an agent is then named by its plugin, `/flow:flow-audit`, `flow:reviewer-guides`.
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
    ref: flow--v0.6.0
    path: .daneel
```

```yaml
prompt: |
  Read `.daneel/plugins/flow/agents/reviewer-guides.md` and follow it.
  `${CLAUDE_PLUGIN_ROOT}` in it is `.daneel/plugins/flow`.
```

Read that way the agent file is plain text: Claude Code fills `${CLAUDE_PLUGIN_ROOT}`
only for an installed or `--plugin-dir` plugin, so the prompt says what it stands for.
The workflow's allowed tools name `bash .daneel/plugins/flow/scripts/branch.sh *` and
`bash .daneel/plugins/flow/scripts/review-path.sh *`. A pull request of the project
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
- **CI** pins a tag (`ref: flow--v0.6.0`) and moves it in a pull request of the project,
  so a reviewer change is reviewed where it lands.

## Status

PatientManager runs `flow` (its trial, PatientManager ticket #513, ended 2026-10-25);
folioneer's trial is folioneer/folioneer ticket #589. A project keeps its own copies of a
piece until its own ticket removes them (PatientManager ticket #537). A skill
moves here only after its copies are measured in the projects, never designed generic
up front. What a skill still reads from the
project is its own record — its rules, its usage log, its GitHub — never a script or
a doc of the plugin.

The backlog is GitHub issues, filed from `.github/ISSUE_TEMPLATE/`.
`CHANGELOG.md` is what a project must act on when it takes a new version.
