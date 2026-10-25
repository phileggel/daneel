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
| `/app:visual-proof` | Screenshots of every state of a changed component, light and dark |
| `/app:dep-audit` | npm and Cargo: outdated versions and CVEs, verified on the web |
| `/app:run-entry` | One task end to end, branch to merge on green; optional `run-entry.recipes`, `.record_paths` |
| `/app:run-batch` | A whole batch: every Queued item through `run-entry`, its end (`release.py` to a draft, or `batch-end.sh`), the closing brief last; optional `run-batch.release_check`, `.version_files`, `.changelog`, `.release_workflow` |
| `/app:design-proposal` | Mocks of the target state, light and dark, and a note, for the owner to validate; optional `design-proposal.repo` |

`protocol.md` is what every reviewer shares: modes, steps, output, the CI report.
`scripts/branch.sh` and `scripts/review-path.sh` are what the reviewers run, always on
the project of the working directory; `scripts/review-lanes.sh` reads changed paths on
stdin and prints the lanes they need (`--json` for CI), for `run-entry` and the project's
review workflow. The reviewers read the project's own conventions
(`docs/spec/README.md`, `docs/contracts/README.md`, `docs/adr/README.md`);
`reviewer-guides` and the protocol read `flow-audit.guides` and the optional
`review.owners`, `review.setup` and `review.glossary` of `.claude/daneel.json`.

The seven stack lanes hold the checks both apps share; what one project alone checks (its
domain, its own scripts and records, an owner's decision) lives in its rules documents,
which each lane reads from `review.rules`: one list of paths per lane, keyed `arch`,
`backend`, `frontend`, `sql`, `e2e`, `security`, `infra`
(`"backend": ["docs/backend-rules.md", "docs/error-model.md", "docs/test-rules.md"]`). A check
such a document states for the lane is one of the lane's; a lane the key does not list
runs on its own checks alone. The infra lane's documents also name the files and records the
project adds to it, the actions it lets go unpinned and its deny list; the e2e lane's name
the helpers folder; the security lane's say which data the project holds as personal.

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
