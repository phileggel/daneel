# Changelog

What a project must act on when it takes a new version of a plugin.

## flow 0.1.0 — unreleased

- `flow-audit`, from folioneer's and PatientManager's copies (identical), with what it
  used from them: `scripts/flow-audit.py` (PatientManager's figures and folioneer's
  sort of the later CI rounds by cause), `scripts/batch-ends.sh`, and `audit.md`
  (§ 12 of their `docs/workflow.md`).
- To take it: drop `.claude/skills/flow-audit/`, `scripts/flow-audit.py` with its tests
  and the `flow-audit` recipe; § 12 of `docs/workflow.md` points to the plugin; allow
  the plugin's two scripts for headless runs; put the project's own part in
  `.claude/daneel.json` where it differs from the defaults.
