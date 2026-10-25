# Changelog

What a project must act on when it takes a new version of a plugin.

## flow 0.5.0 — 2026-10-25

- `backlog` (ticket #3): `/flow:backlog` checks, before the coding agent files a ticket,
  that its size fits under the ceiling; the same count is `flow-audit`'s Backlog block,
  now with the status by size, what was added (coder, owner, waived) and removed (done,
  folded, closed). The coder's tickets carry a mark (`agent-filed`); every other ticket
  is the owner's and raises the ceiling, as do `security` and `data-loss` ones.
- `flow-audit` and `spec-checker` no longer name a project's documents (ticket #6):
  `flow-audit` reads the project's `guides` setting, `spec-checker` the project's own
  rule numbering.
- To take it: the coding agent's rules say to run `/flow:backlog` before filing, and
  mark what it files `agent-filed` (or set `backlog.coder_mark` and `backlog.waived` in
  `.claude/daneel.json`). Until then every new ticket counts as the owner's.

## flow 0.4.0 — 2026-10-25

- `app` is folded into `flow` (ticket #6): one plugin now holds `plan-batch`,
  `flow-audit`, the reviewers `spec-reviewer`, `contract-reviewer`, `adr-reviewer`,
  `spec-checker` and `reviewer-guides` with `protocol.md`, `branch.sh` and
  `review-path.sh`, and the skills `visual-proof` and `dep-audit`, unchanged
  (`app 0.1.0` below). They are named `flow:…` instead of `app:…`.
- To take it: nothing for a project that enables `flow` only; the new pieces arrive
  beside the project's own copies, which stay in use until the project removes them in
  a ticket of its own. A project that enabled `app@daneel` drops it. A CI job reading
  `.daneel/plugins/app/` reads `.daneel/plugins/flow/` at `ref: flow--v0.4.0`.

## flow 0.3.1 — 2026-10-25

- `flow-audit.py` reads a scoped or breaking pull request title as its type
  (`chore(deps): …` is a `chore`, `feat!: …` a `feat`); a Dependabot pull request
  counted as `other` before. The auditor keeps its working files in the session's
  scratchpad, never `/tmp`. Nothing to do in a project.

## flow 0.3.0 — 2026-10-25

- `flow-audit` is faster: `flow-audit.py` reads the records the auditor judges — the
  window's merged pull requests with their commits, comments and reviews, the issues
  filed, closed or discussed with their threads, the last two `batch-audit` issues, the
  open `flow` issues — into `records` of its JSON, in a few GitHub calls. The auditor
  reads that document instead of fetching each pull request and issue (50 to 100 turns,
  7 to 15 minutes in PatientManager and folioneer, measured 2026-10-25). On
  PatientManager's batch of 2026-10-24 the script took 65 s.
- A release still a draft stops the script at once, and the skill stops with it: it
  never waits on CI, retries or publishes.
- Nothing to do in a project; `logs/flow-audit.json` gains the `records` key.

## flow 0.2.0 — 2026-10-24

- `plan-batch`, from folioneer's and PatientManager's copies (90% alike): folioneer's
  version — an Inbox item that changes what a user sees needs its mock before Ready,
  and **Needs you** comes first in the proposal. To take it: set
  `{"plan-batch": {"owner": …, "number": …}}` in `.claude/daneel.json` and drop
  `.claude/skills/plan-batch/`.

## app 0.1.0 — 2026-10-24

- The reviewers `spec-reviewer`, `contract-reviewer`, `adr-reviewer`, `spec-checker` and
  `reviewer-guides`, from folioneer's copies (PatientManager's 90–97% alike: examples,
  and its spec, contract and ADR reviewers not following the protocol), with neutral
  examples; `protocol.md` merged from both `review-protocol.md` (64% alike); the
  scripts they call, `branch.sh` and `review-path.sh`. `branch.sh files` takes the lane's
  own `--match` / `--exclude` in place of the named stack filters, and `log` takes no
  flags. A release sweep names its tag in the prompt.
- `visual-proof` with `visual-proof-capture.mjs`, which resolves Playwright from the
  project; `.claude/visual-proof.json` gains `frontend_match` / `frontend_exclude`.
- `dep-audit`: the licence gate and the external terms only where the project has
  their files; the toolchain line for a pinned or an unpinned Rust.
- To take it: drop the project's copies of these agents, skills and the two scripts
  where nothing else calls them (`review-lanes.sh` and the stack lanes still call
  `branch.sh` with its named filters: keep the project's copy until those move); point
  the review workflow at `.daneel/plugins/app/agents/` as `README.md` § In CI says.

## flow 0.1.0 — 2026-10-24

- `flow-audit`, from folioneer's and PatientManager's copies (identical), with what it
  used from them: `scripts/flow-audit.py` (PatientManager's figures and folioneer's
  sort of the later CI rounds by cause), `scripts/batch-ends.sh`, and `audit.md`
  (§ 12 of their `docs/workflow.md`).
- To take it: drop `.claude/skills/flow-audit/`, `scripts/flow-audit.py` with its tests
  and the `flow-audit` recipe; § 12 of `docs/workflow.md` points to the plugin; allow
  the plugin's two scripts for headless runs; put the project's own part in
  `.claude/daneel.json` where it differs from the defaults.
