# The batch method

How work moves from a request or an issue to a batch end, for any project that runs
`flow`. The project's own rules document holds what is its alone (its loop, its harness,
its release); where the two disagree on what is here, this file is the rule.

## 1. Who owns what

- **Shared** — the feature and bug issues, each what a user will see; the owner confirms
  its User value and Done when, and approves the batch (§ 2).
- **Owner** — validating a design before anything the user sees changes, where the
  project has a design step.
- **Owner** — publishing a release, outside the agent's run; the agent does everything
  before it (§ 5).
- **Agent** — the task issues: every observation, smell and proposal about the code. The
  owner queues from them.
- **Agent** — the flow issues: the same about the workflow itself (checks, waits, tools,
  the owner's part), audited after each batch (§ 6).
- **Agent** — the task, end to end: tests, code, review, merge. No pull request is
  validated by the owner.
- **Harness** — proving it, mechanically, on every pull request. Nothing merges that the
  harness has not passed.

The owner is not the QA: no issue waits for the owner to check by hand that what was
built works. A Done-when clause the agent cannot run becomes a test of the harness, or,
when that test is larger than the issue, a `task` issue that asks for it, and the issue
closes on what the harness proves. What the owner notices while using the product is
welcome and is no gate.

## 2. Issues and the Project

The backlog is the repository's GitHub issues and its Project, never files in git: no
commit touches it. In prose an issue is "ticket #123", a pull request "PR #123"; a pull
request says `Closes #123`, so its merge closes the issue.

### Filing an issue

- **Four kinds, one label each**: `feature` and `bug`, what a user will see (a `feat`, a
  `fix`); `task`, what a user will not (`refactor`, `chore`, an enabler for a feature);
  `flow`, how the work moves (guides, scripts, recipes, hooks, workflows).
- **From its form** (`.github/ISSUE_TEMPLATE/`), the CLI included: `gh issue create` with
  `--label <kind> --label size:<S|M|L|XL>` and the form's fields as `### <field>`
  sections, then `gh project item-add`. Its title is one plain sentence stating the
  observation, no kind prefix; it carries its evidence (what was seen, where, a figure or
  a pull request), one observation only. Before the agent files one, `/flow:backlog`
  checks it fits (§ 3), and the issue gets the coder's mark.
- **Size** (the `size:` label), by facts, not effort — **S**: one pull request, one
  layer, nothing from the owner; **M**: any other single pull request — several layers,
  a spec, an answer from the owner; **L**: two or three pull requests, or mocks or a spec
  interview with the owner; **XL**: a programme, sliced into sub-issues before it is
  queued. The agent sets it on a task or a flow issue; on a feature or a bug
  `/flow:plan-batch` proposes it and the owner confirms it.
- **What waits on the owner** is a comment on the issue and the `needs-owner` label; the
  owner answers in the thread and the label goes once nothing is open. A feature or bug
  the agent files waits for the owner to confirm its User value; a flow issue waits for
  its Decision. The agent does not change, without asking, what the owner confirmed.
- **A bug is always filed**, even when fixed in the same session: its pull request closes
  it. A chat request that is not a bug needs no issue: the pull request is its record. An
  issue someone else opens is given its label, its form's fields and its size.
- **Fixed, folded, then filed**: a gap in a pull request's own files is fixed in it; one
  in the files of an open issue joins that issue with its evidence, while it stays one
  pull request; else it is filed.
- **A dependency** is GitHub's "blocked by"; the slices of a programme are its
  sub-issues.
- **A gate** an issue carries ("when next touched", "not as a sweep") is honoured, or the
  override is put to the owner — never swept silently. A task the agent files is an
  observation, not a commitment.

### Questions to the owner

- In chat, one question per call (`AskUserQuestion`): what happened, what each option
  changes and costs, the recommended one first; the next waits for its answer. Headless,
  a question is a comment with `needs-owner` and the run moves on.
- **The decision scan** — the questions come before the work: the agent reads the issue
  and the code it names, lists every choice that is the owner's — what a user sees, a
  term, a rule's scope, where a programme stops — and asks each once and at its widest,
  writing the answers into the issue. `/flow:plan-batch` runs it while refining; the run
  asks what is still open before its branch exists.
- **Banked** — a question is asked alone only where the options differ in cost, risk or
  what is seen; a trivial one is the agent's. A choice where one option keeps what a user
  sees today is not asked: it is taken and stated in the pull request. A flow proposal so
  answered is recorded as accepted ("banked" in its Decision) and reported in one line.
- During the work, a question remains right for what the reading could not show — a
  reviewer's finding, a failing machine, a behaviour found in the code: ask, never guess.

### The Project — Status and Batch

- **Status**: Inbox (filed) → Ready → Queued (in the batch) → In progress (its branch
  exists) → In review (a pull request is linked) → Done (closed). GitHub sets the last
  two.
- **Ready**: its form's fields written and its `size:` label set; no `needs-owner`; a
  feature or bug whose Design is none or validated; a flow issue with its Decision.
- **A batch** is the Queued items in row order, their Batch field its date.
  `/flow:plan-batch` proposes it in chat; the owner's yes sets Batch, order and Status,
  and nothing else makes an item Queued. A cut during a batch is the owner's.
- **Sized by its work**, not its number of items: the sum of the proposal's sizes stops
  at what the last batches merged (their `batch-audit` issues), both figures said. About
  a third of it goes to tasks. A programme enters as its first slice.
- **The order**: what the owner asked to have next first; what changes the tools next; a
  dependency before what depends on it; items that touch the same files next to each
  other, so one can be prepared on the other; small fixes a user notices early; what
  needs the owner flagged at the top. Where two disagree, the proposal says so in one
  line.
- **Nothing open is passed over**: every open issue and every open Dependabot pull
  request is on the Project, queued or named as left out with its reason.
- Each queued size is checked against the code before the branch (a feature's or a bug's
  as a question to the owner); one that changes during the work is written before
  closure.

## 3. The backlog ceiling

The open backlog is weighed by size: S 1, M 2, L 4, XL 8, no size 2, a parent with an
open slice 0, a `batch-audit` issue none. The ceiling binds the coding agent alone; it
marks every issue it files (`agent-filed`, or `backlog.coder_mark`).

- The ceiling is the backlog at the last batch end, raised by the owner's issues (every
  one without the coder's mark, and the coder's marked `owner-asked`) and by the waived
  ones (`security`, `data-loss`, or `backlog.waived`), which are always filed.
- **A healthy size** (`backlog.target`, optional): at or under it the agent files up to
  it; over it the ceiling only lets the backlog shrink back. Before the first batch end
  only the target holds; with no target every issue fits.
- An issue that does not fit is folded into an open one, or makes room by closing one it
  supersedes, or — a defect a user meets — is put to the owner in chat. Never filed
  anyway.

## 4. Budget and stop rules

- One task, one run, a budget of wall clock (three hours unless the project's rules say
  otherwise); a wait for a usage limit to reset is not the task's time. Over budget →
  open question "larger than estimated: split?", stop.
- A gate fails → read its log. If the log shows the cause, fix it. If not, the next push
  adds observation and makes the failure cheap to reproduce, never a fix.
- The same gate failing three times on one task → open question, stop.
- A test that fails for a reason the change cannot explain is flaky and is never accepted
  by re-running it: it is skipped in its own pull request and a `task` issue is filed
  with the failure text and the run's link; the fix that re-enables it closes the issue.
  The run continues.
- **Never:** what the project's core rules forbid; nor change the batch without the
  owner's yes; nor push to `main`, force-push, or publish a release (cutting it is the agent's); nor edit
  `.claude/settings.json` (the owner edits it; the agent commits that edit through a
  pull request).

## 5. How a batch ends

Every batch ends alike: the project's batch-end checks, what they find folded or filed
(§ 2), then the release or the batch tag, its flow audit, and last the closing brief — the
last thing the run says, so the owner cannot miss it. A security issue that puts users at
risk is a `fix` instead: a `bug` issue put to the owner, worked before the batch ends,
checked again on what it changed, released.

- **A batch with a `feat` or `fix` is released**: once every pull request of the batch
  has merged and the workflow runs of `main`'s head are green, the agent cuts it: the
  `v*` tag and its draft release, with its notes. Its closing brief says everything is
  made but the publishing, naming the draft and the runs. The owner publishes it later,
  outside the run.
- **Any other batch** the agent closes with a `batch/<date>` tag: it publishes nothing,
  its chores ride in the next release, no fix is picked to fill a changelog.

A batch is named by its dates, never by a version number, and ends at its tag — the `v*`
tag the agent cuts or `batch/<date>` — never at the release's publication.
`/flow:flow-audit` audits the range it closes at once after that tag, before the closing
brief; publishing is the owner's alone and nothing waits on it.

## 6. The flow audit

After a batch ends, `/flow:flow-audit` audits it once, forked, from its records alone, as
a comment on that batch's `batch-audit` issue; nothing of it runs during a batch. Its
method is `skills/flow-audit/audit.md`: the figures beside the batch before, the six
questions, the three hard points filed as `flow` issues, the backlog against its
ceiling.

A flow issue carries `Observed` with its evidence — a count, a duration, a pull request —
then a `Proposal` with what it `Costs` and what it protects. A change that buys speed
says what it risks; one that buys safety says what it costs. The owner decides each in
its thread, or has banked it (§ 2); the agent copies the decision, dated, into its
Decision field, and it can be queued. One done, or whose verdict is to keep things as
they are, is closed.

## 7. Conventions

- **Tools the flow needs** are added for good — a script with its tests, a recipe —
  never rewritten in a session's scratch folder. Each is judged again at the audit that
  follows a batch: keep, fold or remove.
- **The usage log** (optional): `logs/usage.log`, local, never committed, one line per
  run of a project script or recipe, emptied once its figures are in the batch's audit
  (its format: `audit.md`, What the project provides). Nothing is logged in CI. Skills
  and agents are counted from the session's transcript.
- **Branches** `<type>/123-slug`, the issue's number leading the slug, or `<type>/slug`,
  off a fresh `main`; `<type>` is the conventional commit type the change will carry.
- **The ceremony**: a task lands on `main` only through a pull request whose checks are
  all green; a docs or flow change too.

## What the project provides

The checklist `/flow:init` sets up.

- **A repository** on GitHub, a checkout with `origin`, and `gh` signed in with the
  `project` scope.
- **Labels the flow defines and relies on**:
  - `feature`, `bug`, `task`, `flow` — the four kinds (§ 2), one per issue;
  - `size:S`, `size:M`, `size:L`, `size:XL` — the size (§ 2), weighed by the ceiling;
  - `needs-owner` — a question is open for the owner;
  - `batch-audit` — the issue that holds a batch's audit, no work;
  - `agent-filed` — the coding agent filed it (`backlog.coder_mark` renames it);
  - `owner-asked` — the agent filed it because the owner asked, so it raises the ceiling;
  - `security`, `data-loss` — always filed, raises the ceiling (`backlog.waived`
    replaces the list).

  Any other label (a roadmap stage, a priority, a design marker) is the project's own:
  the flow pieces never require nor remove it; `/flow:plan-batch` may show it.
- **A GitHub Project** with the fields **Status** — single select `Inbox`, `Ready`,
  `Queued`, `In progress`, `In review`, `Done`, its workflows setting In review on a
  linked pull request and Done on close — and **Batch**, holding the batch's date.
- **Issue forms** in `.github/ISSUE_TEMPLATE/`, each adding its kind's label and the
  Project, blank issues off: `feature` and `bug` (Size, User value, Done when, Design:
  none, needed or validated); `task` (Found by, Where, Observation, Size, Waits on the
  owner); `flow` (Size, Observed, Proposal, Costs, Decision). A form may add the
  project's own field, such as a no-private-data checkbox.
- **Tags** for batch ends: releases `v*` (cut by the agent, published by the owner) and `batch/<date>`
  annotated tags.
- **A CI workflow** that runs on every push of a pull request (`Quality` unless
  `flow-audit.round_workflow` names another): its runs count the CI rounds.
- **Optionally `logs/usage.log`**, gitignored (§ 7).
- **`.claude/daneel.json`**, the project's own part, one key per piece:
  - `plan-batch.owner`, `plan-batch.number` — the Project's owner and number, and
    optionally `plan-batch.workflow` — the project's rules document, its additions to this method;
  - `backlog.coder_mark`, `backlog.waived`, `backlog.target` — optional (§ 3);
  - `flow-audit.round_workflow`, `.commit_types`, `.guides`, `.records`, `.path_roots` —
    optional, each replacing its default (`audit.md`).
