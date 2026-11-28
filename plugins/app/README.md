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
| `/app:design-proposal` | Mocks of the target state, light and dark, beside the current one for an existing screen, and a note, for the owner to validate; optional `design-proposal.repo` |
| `/app:spec-proposal` | The spec gate: the change to the rules drafted, read by `app:spec-reviewer`, and its diff shown for the owner to accept, before anything is built; optional `spec-proposal.repo`, a repository of its own for the spec |
| `/app:init` | After `/flow:init`: the harness (`required-checks.json`, ruleset, merge settings, deny lines) and which project doc plays each role the reviewers read, asked once, added only where missing; where the project has none, a private repository for its spec and one for its mocks, if the owner wants them; re-run, re-aligns the pins, keys and defaults with the project's docs and this changelog |

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
the owner.

The machine that runs the agent needs `gh` 2.50.0 or newer, the first with `gh pr checks
--json`, which `release.py` reads; no other command was checked against an older `gh`.

By hand, the same, in this order, since a ruleset refuses a project's own push of `main` and the plugin's
`merge.py` lands only with the pull request (PR) that enables it:

1. One PR, which the owner merges by hand: the plugins enabled;
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
from the base branch, so a PR cannot turn its own reviewers off, and runs
`git diff --name-only "origin/$BASE...HEAD" | bash .daneel/plugins/app/scripts/review-lanes.sh --json`.

### A reviewer's session in CI

Daneel ships no review workflow. It ships what a lane's session needs, versioned with the
reviewers at the same tag, so a project's workflow calls three scripts and restates
nothing. Each runs from the project's checkout, on the commit under review, and its header
says the rest:

| Script | What it gives | Exit |
| --- | --- | --- |
| `review-prepare.sh <base> <tree>` | The checkout made ready: `main` at `<base>` for `branch.sh`; the plugin's folder out of the changed files; the commit under review in `<tree>`, a folder outside the checkout, without its skills and agents; `.review/`; and from `<base>`, `CLAUDE.md`, `.claude/` and every document `review.rules`, `review.glossary`, `review.owners` and `review.setup` name, with the README of each kind `review.rules` leaves out. One that `<base>` does not have is removed. | 0 prepared · 1 refused, nothing changed · 2 usage |
| `review-tools.sh <lane>` | One line for `--allowedTools`: `Read`, `Grep`, `Glob`; the report's folder, granted from the session's folder and from the filesystem root, so a session that changed folder still writes it; the two helpers under both spellings; the reading subcommands of `git`; `grep`, `ls`, `wc`, `head`, `tail`; for `infra`, the tags of an action on github.com. | 0 printed · 2 usage or unknown lane |
| `review-prompt.sh <lane> <tree>` | The instruction: which agent file and on what, what `${CLAUDE_PLUGIN_ROOT}` stands for, what on disk is the base branch's, where the files under review are, where the report goes and how it begins; with `spec-proposal.repo`, the spec, contract and ADR lanes are told that the spec is not in the checkout. | 0 printed · 2 usage, unknown lane, unreadable settings or an unknown `spec-proposal` key |

    bash .daneel/plugins/app/scripts/review-prepare.sh "origin/$BASE" "$RUNNER_TEMP/branch"
    bash .daneel/plugins/app/scripts/review-tools.sh "$LANE"
    bash .daneel/plugins/app/scripts/review-prompt.sh "$LANE" "$RUNNER_TEMP/branch"

`review-prepare.sh` replaces files: it is for a CI checkout, and refuses one with
uncommitted work. The project keeps what is its choice or its budget: the triggers, the
runner, the lanes it runs, the model and its turns, the secret, the checks' names, what it
does with the report. It adds its own entries after the tools line, and its own lines after
the prompt; the session reads the commit under review in `<tree>`, so the workflow gives
it that folder (`--add-dir`).

### One review per PR

In CI a lane reviews a PR once; a fix is validated by the project's tests, never
by a second review (`loop.md` § 5). Local reviews are run as often as wanted. Daneel ships
no review workflow: the project's asks, in each lane's job, before it starts the reviewer's
session:

    python3 .daneel/plugins/app/scripts/lane-reviewed.py "$PR_NUMBER" <lane>

| Exit | The lane | The job |
| --- | --- | --- |
| 3 | has no report on this PR yet (none, or its newest comment says `no report` or `did not run`) | starts the session |
| 0 | reviewed, every 🔴 and 🟡 graded in a newer comment | passes, no session |
| 1 | reviewed, a 🔴 or 🟡 ungraded (each printed) | fails, no session |
| 2 | the comments could not be read | fails |

A report or a grade counts only from `github-actions[bot]` (the workflow's own token) or
from an account whose permission on the repository is `admin` or `write`; `merge.py` reads
them the same way. Both ask GitHub that permission once per account that commented
(`gh api repos/{owner}/{repo}/collaborators/<login>/permission`), and name an account whose
permission they could not read: its grades then count for nothing. A workflow that posts
its reports as another account gives that account write access.

The step needs a token that reads the PR's comments and an account's permission on the
repository, and no Claude token. The
lane's first run still fails its check on a 🔴; the agent grades every finding in a comment,
then pushes its fix, and the next run passes on exit 0. A lane that first touches the PR
on a later push has no report, so it runs then, once.

## A spec in its own repository

By default a project's spec is a folder of the project (that of the first path of
`review.rules.spec`, default `docs/spec`), and an accepted change goes into the task's
commit. With `spec-proposal.repo` (`owner/name`) the spec lives in a repository of its
own, which the project's owner may keep private:

- The spec folder is a clone of that repository, at the same path, so every reviewer and
  every path a test or a guide names reads as before. The project's `.gitignore` lists
  the folder, and `.claude/settings.json` denies its edits (`"Edit(/docs/spec/**)"` under
  `permissions.deny`, for the default folder). `/app:spec-proposal` checks both each time
  it runs, and updates the clone.
- A change is settled before its ticket is Ready, as a design is (`loop.md` § 2): the
  ticket's Spec field says `needed`, the change is drafted in another clone, in the
  scratchpad, and its diff is posted on the ticket. On the owner's yes, the skill's
  `publish.sh` commits it and pushes the spec repository's `main`, and the ticket's Spec
  becomes `validated`, with the rule IDs and the sha. The script refuses the project
  itself. A ticket that arrives with its Spec already `validated` passes the gate.
- A PR, a commit and a test name cite a rule by its ID, never its words; a ticket shows
  the change it asks for. Where a project's issues are public, so is that diff: the rest
  of the spec is not.
- CI has no access to the spec. The `spec` lane no longer fires in the project, and the
  contract and ADR lanes say that the spec is absent and check the rest (`review-prompt.sh`);
  their checks against the spec, and `app:spec-checker`, run locally.
- What the project's history already published stays there.

For a project with no spec yet, `/app:init` proposes that repository, and one for the
mocks (`design-proposal.repo`). On the owner's yes its `new-repo.sh` creates each, private
and with a README, when it does not exist; for the spec it also clones it at the folder's
path and lists the folder in `.gitignore`. `/app:init` adds the keys; the owner adds the
deny line. The script refuses a folder git tracks.

To move a spec that is already in the project: create the repository and push the folder's files to its `main`;
in the project, remove the folder from git, list it in `.gitignore`, add the key and the
deny line; clone the repository at the folder's path on each computer; drop a required
check of the `spec` lane; add the `Spec` field of `/flow:init`'s forms to the project's
feature and bug forms.

Measured on 2026-11-22, on throwaway projects, with `claude -p --setting-sources project`:
the deny line refused the Write tool in the folder and allowed it beside it; and a
contract lane's session, prepared and prompted by the three scripts with the key set and
no spec folder, wrote its report in 6 turns, said under the headline that the spec was
absent and which checks it could not run, and raised nothing on that absence. The gate
itself was not run end to end: it waits for an owner's yes.

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
