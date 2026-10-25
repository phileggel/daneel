# app

The addon for folioneer and PatientManager, two Tauri + React apps: what both run, and a
project of another shape would not. Used with `flow`.

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
| `/app:run-entry` | One task end to end, branch to merge on green; optional `run-entry.lanes`, `run-entry.recipes` |
| `/app:run-batch` | A whole batch: every Queued item through `run-entry`, its end, then `/flow:flow-audit`; optional `run-batch.release_check` |
| `/app:design-proposal` | Mocks of the target state, light and dark, and a note, for the owner to validate; optional `design-proposal.repo` |

`protocol.md` is what every reviewer shares: modes, steps, output, the CI report.
`scripts/branch.sh` and `scripts/review-path.sh` are what the reviewers run, always on
the project of the working directory. The reviewers read the project's own conventions
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
