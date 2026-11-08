# Changelog — flow

What a project must act on when it takes a new version of this plugin.

## flow 0.5.0 — 2026-11-09

- `/flow:init` re-run on a project already set up re-aligns it: it reads the marketplace pin in `.claude/settings.json` and
  this changelog's sections newer than the pinned version, then asks the owner, in one
  message, about a pointer that no longer exists or no longer says what its reader asks, a
  default the project's docs now contradict without a key, and the "To take it" steps
  between the pins as one checklist; it does the mechanical steps (the pin, labels, forms, keys) in one
  pull request and leaves a change to the project's rules docs or CI as a proposal.

To take it: nothing to change; run `/flow:init` to see the drift from this version on.

## flow 0.4.1 — 2026-11-09

- The changelog is this file, `plugins/flow/CHANGELOG.md`, shipped with the plugin, so a
  skill can read what a project must do between two versions from its own folder.

To take it: nothing to change.

## flow 0.4.0 — 2026-11-08

- `/flow:backlog` Step 2: before filing, `backlog.py match <key> …` lists the open issues
  whose title, body or comments name each key of the draft's Where (a path, also by its
  folder, a rule ID, a symbol), read in one call; the agent folds into a hit that holds the
  same observation, or files and lists the hits.
- `/flow:init`'s `task` form: Where asks for the spec rule IDs and symbols beside the paths.

To take it: in the project's `.github/ISSUE_TEMPLATE/task.yml`, give the Where field the
template's new description; `/flow:init` does not replace a form the project has.

## flow 0.3.0 — 2026-11-08

- A flaky test's issue is always filed: `flaky` joins `security` and `data-loss` as waived
  (`backlog.py`'s default, method § 3 and § 4, the label list, `/flow:backlog`).
- Method § 3: an issue that does not fit, an audit's proposal included, is folded into an
  open one that holds it; else dropped, when it is not really important; else put to the
  owner. Making room by closing one of the agent's own issues is gone. The audit sends each
  proposal through `/flow:backlog`.
- Method § 2, The order: an item with an open pull request comes next after what the owner
  asked for.

To take it: run `/flow:init` to create the `flaky` label. A project that sets
`backlog.waived` adds `flaky` to it.

## flow 0.2.0 — 2026-11-08

- `flow-audit.py`: `later_rounds` gains `rebase_after_a_failed_check`, a round whose round
  before failed and whose commit does not descend from it; `after_a_failed_check` now means
  a commit on top. Each round counts under one key, so the keys still sum to the rounds
  beyond the first.
- `flow-audit.py`: `dangling_paths` is now `{"dead": …, "ignored": …}`: a path git ignores
  (build output) is listed apart from a stale one.
- `flow-audit`'s Step 3: a plugin's script is never in the usage log, so its absence there
  is no data, not no failures.

To take it: an audit comparing `later_rounds` with a batch before 0.2.0 says that
`after_a_failed_check` then also held the rebases after a failed check. A script that reads
`dangling_paths` reads its `dead` key.

## flow 0.1.2 — 2026-11-01

- `method.md` § 2: a fold puts its clause in the target's body and re-labels its size; the
  target stays open until the clause is done, or hands it on. § 3: making room closes only
  one of the agent's own issues, with the reason, never one the owner confirmed.

To take it: nothing to change; the agent follows the new wording.

## flow 0.1.1 — 2026-10-31

- `/flow:init`'s `usage-log.sh` takes its start from Python, not `date +%s.%N`: under BSD
  `date` the usage line was dropped silently.

To take it: a project that already ran `/flow:init` makes the same change in its
`scripts/usage-log.sh`.

## flow 0.1.0 — 2026-10-25

The first release, for any project (daneel ticket #13).
- `method.md`: the batch method — who owns what, issues and the Project, the backlog
  (a ceiling that shrinks a backlog over its optional healthy `backlog.target`), budget
  and stop rules, how a batch ends, the flow audit; and what the project provides.
- `/flow:init` adds what a project lacks — Project fields, the flow's labels, issue forms,
  `.claude/daneel.json`, the usage log helpers, a line in `CLAUDE.md` — after asking.
- `/flow:plan-batch`, `/flow:backlog`, `/flow:flow-audit`.

To take it: enable `flow@daneel`, run `/flow:init`, drop the project's own copies; the
project's workflow document keeps only its additions to the method. The agent cuts a
release (its tag and draft); the owner only publishes it, outside the run.

Earlier versions of `flow` (up to 0.6.0) were withdrawn and their tags removed; 0.1.0 is
lower, so a machine that installed one reinstalls rather than updates:
`claude plugin uninstall flow@daneel`, then `claude plugin install flow@daneel --scope project`.
