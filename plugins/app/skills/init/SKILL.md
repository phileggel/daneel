---
name: init
description: Sets a project up for `app`, after `/flow:init` — the harness (`required-checks.json`, the ruleset, the merge settings, the deny lines) and where the project keeps the rules its reviewers read — adding only what is missing, after asking the owner once. Never overwrites. Use when a project enables `app`, and again when its rules move.
disable-model-invocation: true
allowed-tools:
  - Bash(gh repo view *)
  - Bash(gh api repos/*)
  - Bash(gh --version)
  - Bash(git checkout -b chore/take-app)
  - Bash(git add *)
  - Bash(git commit -m *)
  - Bash(git push -u origin HEAD)
  - Bash(gh pr create *)
---

# Skill — `init` (app)

`${CLAUDE_PLUGIN_ROOT}/README.md` § Taking it says what a project needs and in which
order; the keys are each piece's. The project keeps its own part only.

## Step 1 — Look

From the project's checkout, read without changing anything:

- `.claude/daneel.json` (`review`, `visual-proof`, `flow-audit.guides`), `required-checks.json`,
  `.claude/settings.json`'s `permissions.deny`, `CLAUDE.md`, `docs/`;
- `gh repo view --json nameWithOwner,rebaseMergeAllowed,squashMergeAllowed`;
- `gh api repos/{owner}/{repo}/rulesets`, then each ruleset's bypass actors and required checks;
- the names CI reports on `main`: `gh api 'repos/{owner}/{repo}/commits/main/check-runs?per_page=100' --jq '[.check_runs[].name]'`;
- `gh --version`.

Then, for each role below, the doc the project's `CLAUDE.md` names for it, else the
default:

| Role | Key | The default, when unset |
| --- | --- | --- |
| spec README (format, sections, IDs, scopes) | `review.rules.spec`, first path | `docs/spec/README.md` |
| contract README | `review.rules.contract`, first path | `docs/contracts/README.md` |
| ADR README (the gate, status values) | `review.rules.adr`, first path | `docs/adr/README.md` |
| code and test rules, per lane | `review.rules.<lane>` | the lane's own checks alone |
| glossary | `review.glossary` | none |
| guides the agent reads | `flow-audit.guides` | `CLAUDE.md`, `.claude/**` |
| owners and setup documents | `review.owners`, `review.setup` | none |
| visual-proof rules | `visual-proof.rules` | `docs/visual-proof-rules.md` |
| a lane's own folders | `review.lanes.<lane>` | the plugin's folders, `review-lanes.sh`'s header |
| architecture document (read by the spec, contract and ADR reviewers, `spec-checker`) | none: the rules name it | `ARCHITECTURE.md` |

## Step 2 — Ask

One message to the owner: the table with the doc guessed for each role, or "none →
default", and each harness item missing or divergent — a required check not reporting on
`main`, a deny line absent, a ruleset with a bypass actor or no pull request rule, a merge
method off, a `gh` below 2.50.0. A default beside each line. The owner corrects lines in
one reply; nothing is done before it. A role left blank is a conscious default, and the
report says so.

## Step 3 — Add

Only what is missing, never replacing a file, a key or a setting:

1. **`.claude/daneel.json`**: the roles answered, `review.lanes` included, merged in; a key
   already set stays.
2. **`required-checks.json`**: when absent, the required checks named in the reply, each a
   name CI reports.
3. **Deny lines**, proposed for the owner to add to `.claude/settings.json`, which the agent
   never edits: `"Bash(gh release create *)"`, `"Bash(gh release edit *)"`,
   `"Bash(gh api *releases*)"` under `permissions.deny`.
4. **Ruleset**: `${CLAUDE_PLUGIN_ROOT}/ruleset.json` with its example check replaced by
   those of `required-checks.json`, written to a file, and the line for the owner to run:
   `gh api repos/<owner>/<repo>/rulesets --method POST --input <file>` when the project has
   none, `gh api repos/<owner>/<repo>/rulesets/<id> --method PUT --input <file>` to replace
   the one Step 1 found.
5. **Merge settings** off: the setting named, for the owner.

Then one pull request, never from `main`: `git checkout -b chore/take-app`, `git add
<path>` for each file written, `git commit -m "chore: set up daneel's app"`, `git push -u
origin HEAD`, `gh pr create --body-file <file>`, the body this report.

## Report

Each role with its doc or "default"; each harness item present, added or left to the
owner; what the owner declined. The report is the record of the run.
