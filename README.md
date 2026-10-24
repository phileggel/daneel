# daneel

The way of working shared by phileggel's projects — folioneer, PatientManager,
SpaceTycoon, DeuterosRE, DungeonMasterRE — served as a Claude Code plugin
marketplace, so a flow change is made once instead of once per repository.

Named after R. Daneel Olivaw, who kept to the Laws for twenty thousand years.

## Plugins

| Plugin | Holds |
| ------ | ----- |
| `flow` | `flow-audit` — judges a batch from its records alone |

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

A skill is then called by its plugin name, `/flow:flow-audit`.

## Status

A trial (folioneer/folioneer#589): `flow-audit` alone, the one skill every
project carries. A skill moves here only after its copies are measured in the
projects, never designed generic up front. What a skill still reads from the
project — `just flow-audit`, `docs/workflow.md` — stays in the project until
the trial says how a plugin ships it.

The backlog is GitHub issues, filed from `.github/ISSUE_TEMPLATE/`.
`CHANGELOG.md` is what a project must act on when it takes a new version.
