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
| `/app:visual-proof` | Screenshots of every state of a changed component, light and dark |
| `/app:dep-audit` | npm and Cargo: outdated versions and CVEs, verified on the web |

`protocol.md` is what every reviewer shares: modes, steps, output, the CI report.
`scripts/branch.sh` and `scripts/review-path.sh` are what the reviewers run, always on
the project of the working directory. The reviewers read the project's own conventions
(`docs/spec/README.md`, `docs/contracts/README.md`, `docs/adr/README.md`);
`reviewer-guides` and the protocol read `flow-audit.guides` and the optional
`review.owners`, `review.setup` and `review.glossary` of `.claude/daneel.json`.
The rest of the two apps' shared flow (the stack reviewers, `run-entry`, `run-batch`) comes
here once their two copies converge, each in a ticket of its own.
