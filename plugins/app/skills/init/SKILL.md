---
name: init
description: Sets a project up for `app`, after `/flow:init` — the harness (`required-checks.json`, the ruleset, the merge settings, the deny lines) and where the project keeps the rules its reviewers read — adding only what is missing, after asking the owner once. Never overwrites. Use when a project enables `app`, and again when its rules or daneel's version move: a re-run re-aligns it.
disable-model-invocation: true
allowed-tools:
  - Bash(gh repo view --json nameWithOwner,rebaseMergeAllowed,squashMergeAllowed)
  - Bash(gh api repos/{owner}/{repo}/rulesets*)
  - Bash(gh api 'repos/{owner}/{repo}/commits/main/check-runs?per_page=100' *)
  - Bash(gh --version)
  - Bash(git checkout -b chore/take-app)
  - Bash(git add *)
  - Bash(git commit -m *)
  - Bash(git push -u origin HEAD)
  - Bash(gh pr create *)
---

# Skill — `init` (app)

`${CLAUDE_PLUGIN_ROOT}/README.md` § Taking it says what a project needs, in order. The
project keeps its own part only.

## Step 1 — Look

From the checkout, read only:

- `.claude/daneel.json`, `required-checks.json`,
  `.claude/settings.json`'s `permissions.deny`, `CLAUDE.md`, `docs/`;
- `gh repo view --json nameWithOwner,rebaseMergeAllowed,squashMergeAllowed`;
- `gh api repos/{owner}/{repo}/rulesets`, then each one's bypass actors and required checks;
- the check names on `main`: `gh api 'repos/{owner}/{repo}/commits/main/check-runs?per_page=100' --jq '[.check_runs[].name]'`;
- `gh --version`.

Every call reads; no `--method`.

Then, per role, the doc the project's `CLAUDE.md` names, else the default:

| Role | Key | The default, when unset |
| --- | --- | --- |
| spec README | `review.rules.spec`, first path | `docs/spec/README.md` |
| contract README | `review.rules.contract`, first path | `docs/contracts/README.md` |
| ADR README | `review.rules.adr`, first path | `docs/adr/README.md` |
| code and test rules | `review.rules.<lane>` | the lane's own checks |
| glossary | `review.glossary` | none |
| guides | `flow-audit.guides` | `CLAUDE.md`, `.claude/skills/*/SKILL.md`, `.claude/agents/*.md`, `.claude/rules/*.md` |
| owners, setup | `review.owners`, `review.setup` | none |
| visual-proof rules | `visual-proof.rules` | `docs/visual-proof-rules.md` |
| a lane's own folders | `review.lanes.<lane>` | `review-lanes.sh`'s header |
| architecture document (the document reviewers') | none: the rules name it | `ARCHITECTURE.md` |

## Step 2 — Ask

One message: the table, the doc guessed per role or "none → default", and each
harness item missing or divergent — a required check not reporting on `main`, a deny line
absent, a ruleset with a bypass actor or no pull-request rule, a merge method off, `gh`
below 2.50.0. A default beside each line; one reply; nothing is done before it. A blank
role is a conscious default.

## Step 3 — Add

Only what is missing, replacing nothing:

1. **`.claude/daneel.json`**: the roles answered, `review.lanes` included, merged in; a key
   already set stays.
2. **`required-checks.json`**: when absent, the checks named in the reply, each a name CI
   reports.
3. **Deny lines**, for the owner to add to `.claude/settings.json`, which the agent never
   edits: `"Bash(gh release create *)"`, `"Bash(gh release edit *)"`,
   `"Bash(gh api *releases*)"` under `permissions.deny`.
4. **Ruleset**: `${CLAUDE_PLUGIN_ROOT}/ruleset.json` with its example check replaced by
   those of `required-checks.json`, written to a file; the owner runs
   `gh api repos/<owner>/<repo>/rulesets --method POST --input <file>` (none yet) or
   `gh api repos/<owner>/<repo>/rulesets/<id> --method PUT --input <file>` (the one Step 1 found).
5. **Merge settings** off: named for the owner.

Then one pull request, never from `main`: `git checkout -b chore/take-app`, `git add
<path>` per file written, `git commit -m "chore: set up daneel's app"`, `git push -u
origin HEAD`, `gh pr create --body-file <file>`, the body this report.

## Report

Each role with its doc or "default"; each harness item present, added or left to the
owner; what was declined; the record of the run.

## Re-run — a project already set up

Step 1 also reads `DANEEL_REF` in `.github/workflows/review.yml`, the pin in
`.claude/settings.json` and the sections of `${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md` newer
than the pinned version. Step 2 adds three blocks: a key whose doc is gone or no longer
defines what its reader asks; a default the project's docs contradict with no
key set; the "To take it" lines between the pins, one checklist. Step 3 names both pins'
new value for the owner, as the deny lines.
