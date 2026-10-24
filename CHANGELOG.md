# Changelog

What a project must act on when it takes a new version of a plugin.

## flow 0.2.0 — unreleased

- `plan-batch`, from folioneer's and PatientManager's copies (90% alike): folioneer's
  version — an Inbox item that changes what a user sees needs its mock before Ready,
  and **Needs you** comes first in the proposal. To take it: set
  `{"plan-batch": {"owner": …, "number": …}}` in `.claude/daneel.json` and drop
  `.claude/skills/plan-batch/`.

## app 0.1.0 — unreleased

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

## flow 0.1.0 — unreleased

- `flow-audit`, from folioneer's and PatientManager's copies (identical), with what it
  used from them: `scripts/flow-audit.py` (PatientManager's figures and folioneer's
  sort of the later CI rounds by cause), `scripts/batch-ends.sh`, and `audit.md`
  (§ 12 of their `docs/workflow.md`).
- To take it: drop `.claude/skills/flow-audit/`, `scripts/flow-audit.py` with its tests
  and the `flow-audit` recipe; § 12 of `docs/workflow.md` points to the plugin; allow
  the plugin's two scripts for headless runs; put the project's own part in
  `.claude/daneel.json` where it differs from the defaults.
