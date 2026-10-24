# app

The flow of the Tauri + React apps — reviewers and skills that read a Rust backend under
`src-tauri/`, a React frontend under `src/`, specs, contracts and ADRs under `docs/`.

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
`scripts/branch.sh` and `scripts/review-path.sh` are what the reviewers run, always
on the project of the working directory. The reviewers read the project's own
conventions (`docs/spec/README.md`, `docs/contracts/README.md`, `docs/adr/README.md`,
`docs/ubiquitous-language.md`). See the repository's `README.md` for enabling it, and
for running a reviewer in CI.
