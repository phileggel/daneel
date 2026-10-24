# daneel

The way of working shared by phileggel's projects — folioneer, PatientManager,
SpaceTycoon, DeuterosRE, DungeonMasterRE — served as a Claude Code plugin
marketplace, so a flow change is made once instead of once per repository.

Named after R. Daneel Olivaw, who kept to the Laws for twenty thousand years.

## Plugins

| Plugin | Holds |
| ------ | ----- |
| `flow` | `flow-audit` — judges a batch from its records alone, with its scripts and its doc |

## Use

Once per machine:

    claude plugin marketplace add phileggel/daneel
    claude plugin install flow@daneel

In a project's `.claude/settings.json`, so headless runs and teammates get it too:

```json
{
  "extraKnownMarketplaces": {
    "daneel": { "source": { "source": "github", "repo": "phileggel/daneel" } }
  },
  "enabledPlugins": { "flow@daneel": true }
}
```

A skill is then called by its plugin name, `/flow:flow-audit`. A headless run has
nobody to approve a command: the project's allow list names the plugin's scripts
(`Bash(python3 *flow-audit/scripts/flow-audit.py*)`, `Bash(bash *flow-audit/scripts/batch-ends.sh*)`).

What differs between projects is the project's `.claude/daneel.json`, read by the
plugin's scripts; each skill's doc names its keys.

## In CI

A plugin works from a plain checkout of this repository: every file a skill or an
agent reads is reached from its own folder, and every script measures the checkout it
runs in. A CI job checks daneel out beside the project, at a release tag, and its prompt
reads the agent from there:

```yaml
- uses: actions/checkout@v4
  with:
    repository: phileggel/daneel
    ref: review--v0.1.0
    path: .daneel
```

The reviewer lanes come here as their own plugin, `review`, so CI pins it apart from
`flow`.

## Versions and releases

Each plugin has its own version, in its `plugin.json`: semver, the middle number moving
when a project must act (a setting renamed, a figure changed), the last for anything
else. `CHANGELOG.md` says, per plugin and version, what a project must do.

A release is a tag, `<plugin>--v<version>`, made on `main` once the bump is merged:

    claude plugin tag plugins/flow --push

- **Local and headless runs** follow `main`: `claude plugin update flow@daneel` (or the
  marketplace's auto-update) takes the newest version. Claude Code caches a plugin by its
  version, so a change that does not bump it never reaches a project.
- **CI** pins a tag (`ref: review--v0.1.0`) and moves it in a pull request of the project,
  so a reviewer change is reviewed where it lands.

## Status

A trial (folioneer/folioneer#589): `flow-audit` alone, the one skill every
project carries, with the scripts and the doc it uses. A skill moves here only after its copies are measured in the
projects, never designed generic up front. What a skill still reads from the
project is its own record — its rules, its usage log, its GitHub — never a script or
a doc of the plugin.

The backlog is GitHub issues, filed from `.github/ISSUE_TEMPLATE/`.
`CHANGELOG.md` is what a project must act on when it takes a new version.
