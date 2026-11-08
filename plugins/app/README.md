# app

The addon for Tauri + React apps: what such apps run, and a project of another shape
would not. Used with `flow`.

| Piece | What it does |
| ----- | ------------ |
| `app:spec-reviewer` | A spec, before its contract: complete, consistent, implementable |
| `app:contract-reviewer` | A contract against its spec: coverage, errors, types |
| `app:adr-reviewer` | ADRs: structure, the gate, status and index |
| `app:spec-checker` | Every rule of a spec implemented and tested |
| `app:reviewer-guides` | The guides lane: what an agent does after reading them |
| `app:reviewer-arch` | Layering across `.rs`, `.ts`, `.tsx`: contexts, flow, gateways, factories, ADR reversals, dead code, English |
| `app:reviewer-backend` | Rust: typed errors, no `unwrap()`, async, repositories, vocabulary, inline tests |
| `app:reviewer-frontend` | React under `src/`: gateway, error pipeline, imports, buckets, ids, a11y, M3 tokens, UX, i18n |
| `app:reviewer-sql` | SQLite migrations: transactions, idempotency, destructive DDL, indexes, types, keys |
| `app:reviewer-e2e` | WebdriverIO scenarios under `e2e/`: selectors, waits, inputs, independence, no mocks, helpers |
| `app:reviewer-security` | Commands, test seams, XSS, storage, secrets, capabilities, cross-layer risks |
| `app:reviewer-infra` | Workflows, Tauri and package config, scripts, hooks, justfile, records, settings |
| `/app:visual-proof` | Screenshots of every state of a changed component, light and dark; `visual-proof.vite_preview_port`, `.vite_preview_host`, `.global_css_import`, `.i18n_import`, optional `.rules` (default `docs/visual-proof-rules.md`), `.frontend_match`, `.frontend_exclude` |
| `/app:dep-audit` | npm and Cargo: outdated versions and CVEs, verified on the web; optional `dep-audit.licence_check`, `.terms_doc` |
| `/app:run-entry` | One task end to end, branch to merge on green; optional `run-entry.recipes`, `.record_paths` |
| `/app:run-batch` | A whole batch: every Queued item through `run-entry`, its end (`release.py` to a draft, or `batch-end.sh`), the closing brief last; optional `run-batch.release_check`, `.version_files`, `.changelog`, `.release_workflow` |
| `/app:design-proposal` | Mocks of the target state, light and dark, and a note, for the owner to validate; optional `design-proposal.repo` |
| `/app:init` | After `/flow:init`: the harness (`required-checks.json`, ruleset, merge settings, deny lines) and which project doc plays each role the reviewers read, asked once, added only where missing; re-run, re-aligns the pins, keys and defaults with the project's docs and this changelog |

`protocol.md` is what every reviewer shares: modes, steps, output, the CI report.
`scripts/branch.sh` and `scripts/review-path.sh` are what the reviewers run, always on
the project of the working directory; `scripts/review-lanes.sh` reads changed paths on
stdin and prints the lanes they need (`--json` for CI), for `run-entry` and the project's
review workflow. The reviewers read the project's own conventions from the docs
`.claude/daneel.json` names: the first path of `review.rules.spec`, `.contract` and `.adr`
is that kind's README (defaults `docs/spec/README.md`, `docs/contracts/README.md`,
`docs/adr/README.md`), whose folder holds the documents and whose text defines their
sections, ID pattern and scopes; the stack lanes read `review.rules.<lane>`;
`reviewer-guides` and the protocol read `flow-audit.guides` and the optional
`review.owners`, `review.setup` and `review.glossary`.

The seven stack lanes hold the checks both apps share; what one project alone checks (its
domain, its own scripts and records, an owner's decision) lives in its rules documents,
which each lane reads from `review.rules`: one list of paths per lane, keyed `arch`,
`backend`, `frontend`, `sql`, `e2e`, `security`, `infra`, and `spec`, `contract`, `adr`,
whose first path is that kind's README and whose folder its lane watches
(`"backend": ["docs/backend-rules.md", "docs/error-model.md", "docs/test-rules.md"]`). A check
such a document states for the lane is one of the lane's; a lane the key does not list
runs on its own checks alone. The infra lane's documents also name the files and records the
project adds to it, the actions it lets go unpinned and its deny list; the e2e lane's name
the helpers folder; the security lane's say which data the project holds as personal.

## Taking it

`/app:init`, after `/flow:init`, reads the project, asks the owner once about what is
missing or divergent (the harness items below, and which doc plays each role the reviewers
read: `review.rules.<lane>`, `review.rules.spec`, `.contract`, `.adr`, `review.glossary`,
`flow-audit.guides`, `visual-proof.rules`), adds what the agent may, and names the rest for
the owner. By hand, the same:

The machine that runs the agent needs `gh` 2.50.0 or newer, the first with `gh pr checks
--json`, which `release.py` reads; no other command was checked against an older `gh`.

In this order, since a ruleset refuses a project's own push of `main` and the plugin's
`merge.py` lands only with the pull request that enables it:

1. One pull request, which the owner merges by hand: the plugins enabled;
   `required-checks.json` at the root (`{"checks": [...]}`), its names the real job names,
   each job already reporting; and in `.claude/settings.json` the deny lines for publishing
   a release (the plugin's scripts run their own `gh`, which these do not stop):

   ```json
   { "permissions": { "deny": ["Bash(gh release create *)", "Bash(gh release edit *)", "Bash(gh api *releases*)"] } }
   ```

2. In the repository's settings, rebase and squash merges allowed: `merge.py` and
   `release.py` use both.
3. The ruleset, every app's the same: a copy of this plugin's `ruleset.json`, its example
   check replaced by those of `required-checks.json`, under GitHub Actions (app 15368). Nobody
   bypasses it. "Require branches to be up to date" stays off: `merge.py` needs that. The
   owner applies it, or replaces the one the project has:

       gh api repos/<owner>/<repo>/rulesets --method POST --input <copy>
       gh api repos/<owner>/<repo>/rulesets/<id> --method PUT --input <copy>

## Lanes

`review-lanes.sh` fires a lane only on files its reviewer takes, with defaults for a
Tauri + React app (the script's header lists them): `backend` any `.rs`; `frontend`
`src/**/*.ts(x)`; `arch` either; `sql` migrations; `infra` the files `reviewer-infra`
names; `security` `api.rs`, capabilities and `specta_builder.rs`; `e2e`
`e2e/**/*.test.ts`; `spec`, `contract`, `adr` their `docs/` folder; `guides` the
`flow-audit.guides` globs. A project adds its own paths per lane under `review.lanes`
of `.claude/daneel.json`: extended regular expressions on the path from the repository
root, which only add to the defaults (a lane name it does not know is an error):

```json
{ "review": { "lanes": { "infra": ["^tools/[^/]*\\.sh$"], "security": ["^src-tauri/src/auth/"] } } }
```

In CI the workflow checks daneel out (see daneel's `README.md`), takes `.claude/daneel.json`
from the base branch, so a pull request cannot turn its own reviewers off, and runs
`git diff --name-only "origin/$BASE...HEAD" | bash .daneel/plugins/app/scripts/review-lanes.sh --json`.
The workflow should give the reviewers the rules documents (`review.rules`, the READMEs)
from the base branch too, or a pull request can loosen the review that judges it; daneel
ships no step for that, the project's workflow does it.

## Headless runs

`run-entry` with no argument takes the first ready Queued item, so the headless runner is
`claude -p "/app:run-entry"` itself and needs no script: the skill's Step 0 checks the
tree, `main` and the Project. The project's `justfile` adds one run at a time, a budget
and a log:

```just
# One Queued item, headless: one run at a time, a 3-hour budget, logged under logs/run-entry/
run-entry:
    mkdir -p logs/run-entry && flock -n -E 0 logs/run-entry/.lock timeout --signal=INT --kill-after=60 ${RUN_ENTRY_BUDGET:-3h} claude -p "/app:run-entry" --permission-mode acceptEdits --output-format text >> logs/run-entry/$(date -u +%Y%m%dT%H%M%SZ).log 2>&1
```

`flock` and `timeout` are Linux's (util-linux, coreutils). The exit is `claude`'s, 124 at
the budget; a run already holding the lock exits 0. Print mode asks nobody: a command
outside the project's allow list is denied and the run fails instead of waiting.
