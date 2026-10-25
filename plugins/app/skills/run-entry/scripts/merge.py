#!/usr/bin/env python3
"""Rebase the current feature branch onto the target, land it once CI is green, clean up.

Use:  python3 merge.py [-t TARGET]      run from the feature branch, in the checkout
Exit: 0 landed · 1 refused or failed (the reason and the way back are printed)

The merge guard: the branch must be the head of an open pull request whose every check
run is green, and every check named in `required-checks.json` (at the checkout's root)
must be among them. When the rebase moved the tested tree (the target advanced), the
rebased branch is pushed and the merge stops until CI has run on it, unless the rebase
changed record files only (`record_paths`) or nothing at all.

One entry lands as one commit: a fix pushed after the first push is a `fixup!` commit
(`git commit --fixup <sha>`), and the rebase folds it into the commit it names. Folding
rewrites commits and leaves the tree as CI tested it, so the checks stand.

GitHub merges the pull request's tested head; nothing here pushes the target. Squashed
under the folded commit's message when the branch carried `fixup!` commits, rebased
otherwise: the target has a ruleset that accepts only a commit whose checks passed, and
the repository allows rebase and squash merges. The only push is of the task's own
branch, with lease, once its fixups are folded or it is rebased (the method's one
exception to never force-pushing).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

if os.environ.get("NO_COLOR"):
    RED = GREEN = BLUE = NC = ""
else:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"

HERE = Path(__file__).resolve().parent
RERUN = f"python3 {HERE / 'merge.py'}"
WATCH = f"python3 {HERE / 'watch-pr.py'}"

# What a project may set in `.claude/daneel.json` under `run-entry`, with its default.
SETTINGS = {
    # Record files: a move of the target made only of them cannot change what the checks
    # proved, since none is read against the code. An entry ending in `/` is a folder
    # (its `.md` files), any other one a file.
    "record_paths": ["docs/adr/"],
}
# Keys of `run-entry` the skill reads, not this script: known, so not refused.
SKILL_SETTINGS = {"recipes"}


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def fail(msg: str, *recovery_lines: str) -> NoReturn:
    print(f"{RED}❌ {msg}{NC}", file=sys.stderr)
    for line in recovery_lines:
        print(f"{BLUE}   {line}{NC}", file=sys.stderr)
    sys.exit(1)


def root() -> Path:
    return Path(git("rev-parse", "--show-toplevel").stdout.strip())


def settings(top: Path) -> dict:
    """The defaults, overridden key by key by the project's `.claude/daneel.json`."""
    path = top / ".claude" / "daneel.json"
    try:
        own = json.loads(path.read_text(encoding="utf-8")).get("run-entry", {}) if path.exists() else {}
    except (OSError, ValueError) as exc:
        fail(f"Could not read {path}: {exc}")
    unknown = set(own) - set(SETTINGS) - SKILL_SETTINGS
    if unknown:
        fail(f"Unknown run-entry settings in {path}: {', '.join(sorted(unknown))}")
    return {**SETTINGS, **{key: own[key] for key in SETTINGS if key in own}}


def _git_dir() -> Path:
    return Path(git("rev-parse", "--git-dir").stdout.strip())


def _rebase_in_progress() -> bool:
    """True if a rebase was started but not yet finished or aborted."""
    gdir = _git_dir()
    return (gdir / "rebase-merge").is_dir() or (gdir / "rebase-apply").is_dir()


def gh(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["gh", *args], capture_output=True, text=True, check=False, timeout=60)
    except FileNotFoundError:
        fail("gh is not installed — the merge guard cannot read the checks.")
    except subprocess.TimeoutExpired:
        fail(f"gh {args[0]} {args[1]} did not answer within 60 s — is GitHub reachable?")


PASSING = {"success", "skipped", "neutral"}


def _required_checks() -> list[str]:
    path = root() / "required-checks.json"
    try:
        return list(json.loads(path.read_text(encoding="utf-8"))["checks"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        fail(f"Could not read {path.name}: {exc}")


def _open_pull_request(branch: str, target: str) -> tuple[int, str]:
    """Number and head sha of the open pull request from `branch` into `target`."""
    result = gh(
        "pr", "list", "--head", branch, "--base", target, "--state", "open",
        "--json", "number,headRefOid", "--limit", "1",
    )
    if result.returncode != 0:
        fail("Could not list pull requests.", (result.stderr or "").strip())
    prs = json.loads(result.stdout or "[]")
    if not prs:
        fail(
            f"No open pull request from {branch} into {target}.",
            "Every change goes through the harness — open one and let it run:",
            f"  git push -u origin {branch}",
            f"  gh pr create --base {target} --body-file <the body's file>",
        )
    return int(prs[0]["number"]), str(prs[0]["headRefOid"])


def _check_runs(sha: str) -> dict[str, tuple[str, str]]:
    """Latest check run per name on `sha`: name -> (status, conclusion).

    A re-run creates a new run with the same name and a higher id; the
    highest id wins whatever order the API lists them in.
    """
    result = gh(
        "api", f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs?filter=latest",
        "--paginate",
        "--jq", '.check_runs[] | [.id, .name, .status, (.conclusion // "")] | @tsv',
    )
    if result.returncode != 0:
        fail(f"Could not read the check runs of {sha[:7]}.", (result.stderr or "").strip())
    latest: dict[str, tuple[int, str, str]] = {}
    for line in result.stdout.splitlines():
        run_id, name, status, conclusion = (line.split("\t") + ["", "", ""])[:4]
        if name not in latest or int(run_id) > latest[name][0]:
            latest[name] = (int(run_id), status, conclusion)
    return {name: (status, conclusion) for name, (_, status, conclusion) in latest.items()}


def record_files_only(files: list[str], record_paths: list[str]) -> bool:
    folders = tuple(p for p in record_paths if p.endswith("/"))
    names = {p for p in record_paths if not p.endswith("/")}
    return all(f in names or (f.endswith(".md") and f.startswith(folders)) for f in files)


def _rebase_left_the_checks_standing(before: str, after: str, record_paths: list[str]) -> bool:
    """True when the tree the checks ran on and the tree about to land are identical, or differ by record files only.

    Comparing the two trees, not the target's history, means a branch stacked
    on commits that have since merged, or one whose `fixup!` commits were just
    folded, is not sent for a re-run: what CI tested is what lands.
    """
    diff = git("diff", "--name-only", before, after, check=False)
    if diff.returncode != 0:
        fail(f"Could not compare {before[:7]} with {after[:7]}.", (diff.stderr or "").strip())
    return record_files_only([f for f in diff.stdout.splitlines() if f], record_paths)


FOLD_PREFIXES = ("fixup! ", "squash! ", "amend! ")


def _fold_commits(target: str, branch: str) -> list[str]:
    """Titles of the commits of `branch` not in `target` that ask to be folded into another."""
    log = git("log", "--format=%s", f"{target}..{branch}", check=False)
    if log.returncode != 0:
        fail(f"Could not list the commits of {branch}.", (log.stderr or "").strip())
    return [title for title in log.stdout.splitlines() if title.startswith(FOLD_PREFIXES)]


def refuse_unreadable_folds(target: str, branch: str) -> None:
    """Stop before the rebase on a `squash!` or `amend!` commit: it would land a message no check has read."""
    unreadable = [t for t in _fold_commits(target, branch) if not t.startswith("fixup! ")]
    if unreadable:
        fail(
            f"`{branch}` carries squash!/amend! commits; only fixup! commits are folded.",
            *(f"  {title}" for title in unreadable),
            "Drop or reword each one (git rebase), carry its change as `git commit --fixup <sha>` instead,",
            "push, let CI run, then re-run.",
        )


def refuse_unfolded_fixups(target: str, branch: str, before: str) -> None:
    """Stop after the rebase on a `fixup!` commit that named no commit of the branch.

    It was not folded, and must not reach the target: its title would become a
    changelog line. The branch goes back to `before`, its head before the rebase.
    """
    unfolded = _fold_commits(target, branch)
    if unfolded:
        # The rebase has just completed, so the tree is clean: this only moves the branch back.
        restored = git("reset", "--hard", before, check=False).returncode == 0
        fail(
            f"`{branch}` carries fixup! commits that name no commit of the branch.",
            *(f"  {title}" for title in unfolded),
            "Branch was restored to its original state (no rewrite)."
            if restored
            else f"Branch is rebased; its original head was {before[:7]}.",
            "Give each the exact title of the commit it fixes (`git commit --fixup <sha>` does), then re-run.",
        )


def restore_unpushed(branch: str, before: str) -> None:
    """After a stop that pushed nothing, put the branch back on `before`, its head before
    the rebase: a rebased branch origin does not hold would be refused at the next run as
    one whose origin is ahead. A branch the stop pushed is left as pushed."""
    head = git("rev-parse", branch).stdout.strip()
    pushed = git("rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}", check=False)
    if head == before or (pushed.returncode == 0 and pushed.stdout.strip() == head):
        return
    if git("reset", "--quiet", "--hard", before, check=False).returncode == 0:
        print(f"{BLUE}ℹ {branch} is back on {before[:7]}, as it was before the rebase.{NC}", file=sys.stderr)
    else:
        print(f"{RED}❌ {branch} is rebased; its original head was {before[:7]} (git reset --hard {before[:7]}).{NC}", file=sys.stderr)


def rebase_folding_fixups(target: str) -> subprocess.CompletedProcess[str]:
    """Rebase the current branch onto `target`, folding each `fixup!` commit into the commit it names."""
    return subprocess.run(
        ["git", "rebase", "--interactive", "--autosquash", target],
        capture_output=True,
        text=True,
        check=False,
        # The todo list git proposes is taken as it is: nobody edits it.
        env={**os.environ, "GIT_SEQUENCE_EDITOR": "true"},
    )


def worktree_holding(branch: str, listing: str, here: str) -> str | None:
    """The path of another worktree that has `branch` checked out, from the output of
    `git worktree list --porcelain`; None when no other worktree holds it."""
    path = ""
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line == f"branch refs/heads/{branch}" and path != here:
            return path
    return None


def reviewer_heading(comments: list[str], check_name: str) -> str | None:
    """What a reviewer lane's sticky comment says of itself: the text after the dash of
    its `## reviewer-<lane> — …` heading ("no report", "did not run (usage limit)"), or
    None when the lane has no comment or its heading carries no such note."""
    lane = check_name.removeprefix("reviewer-")
    marker = f"<!-- review:{lane} -->"
    for body in reversed(comments):
        if not body.startswith(marker):
            continue
        for line in body.splitlines():
            if line.startswith(f"## {check_name} — "):
                note = line.split(" — ", 1)[1].strip()
                # A report's own heading counts files; only a note about the run is told.
                return note if not note[:1].isdigit() else None
        return None
    return None


def _reviewer_notes(number: int, failed: list[str]) -> dict[str, str]:
    """For the reviewer checks that completed without passing, what each one's sticky
    comment says of its run. Best effort: the refusal is the product, the note an aid —
    a slow or failing call gives no note, never another error."""
    lanes = [name for name in failed if name.startswith("reviewer-")]
    if not lanes:
        return {}
    try:
        result = subprocess.run(
            [
                "gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}/comments", "--paginate",
                "--jq", ".[] | .body | @json",
            ],
            capture_output=True, text=True, check=False, timeout=30,
        )
        comments = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}
    notes = {name: reviewer_heading(comments, name) for name in lanes}
    return {name: note for name, note in notes.items() if note}


def ensure_checks_green(branch: str, target: str, before: str, after: str, config: dict) -> tuple[int, str]:
    """Refuse the merge unless CI is green on exactly the commits about to land.

    Returns the pull request's number and its tested head.
    """
    number, head = _open_pull_request(branch, target)
    if after != head:
        standing = before == head and _rebase_left_the_checks_standing(before, after, config["record_paths"])
        # GitHub merges the tested head itself: a rebase that left the checks standing
        # needs no push.
        if not standing:
            push = git("push", "--force-with-lease", "origin", branch, check=False)
            if push.returncode != 0:
                fail(
                    f"Local {branch} ({after[:7]}) is not the head of PR #{number} ({head[:7]}) and the push failed.",
                    (push.stderr or "").strip(),
                )
        if standing:
            print(
                f"{BLUE}ℹ The rebase left the tested tree as it was, record files aside; the checks of {head[:7]} stand.{NC}",
                file=sys.stderr,
            )
        else:
            why = "the rebase moved the commits" if before == head else "the local branch was ahead of the pull request"
            fail(
                f"{branch} pushed as {after[:7]} — {why}.",
                f"CI runs on it now: {WATCH} {number}",
                f"Re-run `{RERUN}` when every check is green.",
            )
    runs = _check_runs(head)
    missing = [name for name in _required_checks() if name not in runs]
    failing = sorted(
        name
        for name, (status, conclusion) in runs.items()
        if status != "completed" or conclusion not in PASSING
    )
    # A reviewer that did not run is told apart from one that found a critical.
    # Only for a check that has finished: a lane still running has a stale comment.
    notes = _reviewer_notes(number, [name for name in failing if runs[name][0] == "completed"])
    not_green = [
        f"{name}: {runs[name][0] if runs[name][0] != 'completed' else runs[name][1]}"
        + (f" — {notes[name]}" if name in notes else "")
        for name in failing
    ]
    if missing or not_green:
        fail(
            f"PR #{number} is not green on {head[:7]}.",
            *(f"  missing: {name}" for name in missing),
            *(f"  {line}" for line in not_green),
            f"Watch: {WATCH} {number} — then re-run `{RERUN}`.",
        )
    print(f"{GREEN}✓ PR #{number}: every check green on {head[:7]}.{NC}", file=sys.stderr)
    return number, head


def merge_method(target: str, before: str, branch: str) -> list[str]:
    """How GitHub lands the pull request, as `gh pr merge` options.

    A branch that carried `fixup!` commits (`before`, its head before the rebase) is
    squashed under the message and author of the commit they were folded into, so the
    entry still lands as one commit; any other branch is rebased, its commits as they are.
    """
    if not _fold_commits(target, before):
        return ["--rebase"]
    log = git("log", "--format=%H", f"{target}..{branch}", check=False)
    folded = log.stdout.split()
    if log.returncode != 0 or len(folded) != 1:
        fail(
            f"`{branch}` folds into {len(folded)} commits; GitHub squashes a pull request into one.",
            "One entry lands as one commit: fold the others into it, push, let CI run, then re-run.",
        )
    subject, body, email = (
        git("log", "-1", f"--format={part}", folded[0]).stdout.strip() for part in ("%s", "%b", "%ae")
    )
    return ["--squash", "--subject", subject, "--body", body, "--author-email", email]


def delete_remote_branch(branch: str) -> str:
    """Delete `origin/<branch>`: "deleted", "gone" (already removed elsewhere) or "failed".

    A failed delete is re-checked against the remote rather than parsed: GitHub
    deletes a merged branch itself (delete_branch_on_merge), and racing it
    rejects the push with a message that varies.
    """
    result = git("push", "--delete", "origin", branch, check=False)
    if result.returncode == 0:
        return "deleted"
    still_there = git("ls-remote", "--exit-code", "--heads", "origin", branch, check=False)
    if still_there.returncode == 2:  # --exit-code: the remote answered and holds no such ref
        return "gone"
    print(f"{RED}❌ Failed to delete origin/{branch}:{NC}", file=sys.stderr)
    for line in (result.stderr or "no stderr").strip().splitlines():
        print(f"{BLUE}   {line}{NC}", file=sys.stderr)
    print(f"{BLUE}   Retry manually once unblocked: git push --delete origin {branch}{NC}", file=sys.stderr)
    return "failed"


def land_by_github(number: int, head: str, target: str, before: str, branch: str) -> None:
    method = merge_method(target, before, branch)
    result = gh("pr", "merge", str(number), *method, "--match-head-commit", head)
    if result.returncode != 0:
        fail(
            f"GitHub refused to merge PR #{number}.",
            (result.stderr or "").strip(),
            f"Inspect: gh pr view {number} (a ruleset that asks the branch to be up to date refuses it) — then re-run `{RERUN}`.",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-t", "--target", default="main", help="Target branch to merge into (default: main).")
    args = parser.parse_args()
    target = args.target
    here = str(root())
    config = settings(Path(here))

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    # Pre-flight 1 — not already on the target.
    if branch == target:
        fail(f"Already on {target} — nothing to merge.", f"Run from a feature branch (not {target}).")

    # Pre-flight 2 — clean working tree (both staged and unstaged).
    if (
        git("diff", "--quiet", check=False).returncode != 0
        or git("diff", "--cached", "--quiet", check=False).returncode != 0
    ):
        fail("Working tree has uncommitted changes.", "Commit or stash them, then re-run.")

    # Pre-flight 3 — no rebase in progress (from a previous interrupted run).
    if _rebase_in_progress():
        fail(
            "A rebase is already in progress in this repo.",
            "Finish or abandon it first:",
            "  git rebase --continue   # after resolving conflicts",
            "  git rebase --abort      # to abandon",
            "Then re-run.",
        )

    # Pre-flight 4 — the target is not checked out in another worktree: the merge checks
    # the target out here, which git refuses when another folder holds it.
    holder = worktree_holding(target, git("worktree", "list", "--porcelain").stdout, here)
    if holder:
        fail(
            f"`{target}` is checked out in {holder}: the merge cannot run from this worktree.",
            "Merge from that folder instead, once it is clean and this worktree is pushed:",
            f"  git worktree remove {shlex.quote(here)}",
            f"  git -C {shlex.quote(holder)} checkout {shlex.quote(branch)}",
            f"  then, from {shlex.quote(holder)}: {RERUN}",
        )

    # Pre-flight 5 — target branch exists locally.
    if git("rev-parse", "--verify", "--quiet", target, check=False).returncode != 0:
        fail(f"Target branch {target} does not exist locally.", f"Create or fetch it: git fetch origin {target}:{target}")

    # Pre-flight 6 — the branch's origin is not ahead of local: the remote branch is
    # deleted at the end, and commits only it holds would vanish silently.
    if git("rev-parse", "--verify", "--quiet", f"origin/{branch}", check=False).returncode == 0:
        if git("fetch", "--quiet", "origin", branch, check=False).returncode != 0:
            fail(
                f"Could not fetch origin/{branch}.",
                "Origin is unreachable or the branch was deleted server-side.",
                f"Investigate: git fetch origin {branch}",
            )
        # Fail closed if the count itself fails.
        ahead = git("rev-list", "--count", f"{branch}..origin/{branch}", check=False)
        if ahead.returncode != 0:
            fail(
                f"Could not compare {branch} with origin/{branch}.",
                f"Investigate: git rev-list --count {branch}..origin/{branch}",
            )
        count = ahead.stdout.strip()
        if count != "0":
            fail(
                f"origin/{branch} has {count} commit(s) not in local {branch}.",
                f"The merge would delete origin/{branch} and lose those commits.",
                f"  git pull --ff-only origin {branch}    # incorporate them",
                f"  git pull --rebase origin {branch}     # if local has also diverged",
                "Then re-run the merge. Discarding them is the owner's call, never the agent's.",
            )

    # Step 1 — sync local target with origin (skip if no remote).
    has_origin_target = git("rev-parse", "--verify", "--quiet", f"origin/{target}", check=False).returncode == 0
    result = git("checkout", target, check=False)
    if result.returncode != 0:
        fail(
            f"Could not checkout `{target}`.",
            f"detail: {result.stderr.strip() or '(no stderr captured)'}",
            "Common causes: untracked files conflict, uncommitted changes. Inspect: git status",
        )
    if has_origin_target:
        if git("pull", "--ff-only", "--quiet", "origin", target, check=False).returncode != 0:
            fail(
                f"Could not fast-forward pull origin/{target}.",
                f"Local {target} has diverged from origin/{target}, or origin is unreachable.",
                f"Investigate: git fetch origin {target}",
                f"  git log {target}..origin/{target}",
            )
    else:
        print(f"{BLUE}ℹ No origin/{target} remote — skipping pull.{NC}", file=sys.stderr)

    # Step 2 — rebase the branch onto the target, folding its fixups. On conflict the
    # rebase is aborted: the branch is never left half-rewritten.
    result = git("checkout", branch, check=False)
    if result.returncode != 0:
        fail(f"Could not checkout `{branch}`.", f"detail: {result.stderr.strip() or '(no stderr captured)'}", "Inspect: git status")
    before = git("rev-parse", branch).stdout.strip()
    refuse_unreadable_folds(target, branch)
    if rebase_folding_fixups(target).returncode != 0:
        abort = git("rebase", "--abort", check=False)
        if abort.returncode != 0:
            fail(
                f"Cannot merge `{branch}` into `{target}`: rebase has conflicts AND `git rebase --abort` failed.",
                f"abort stderr: {abort.stderr.strip() or '(no stderr captured)'}",
                "Branch is mid-rebase. Inspect `git status`, then `git rebase --abort` or `--continue` manually.",
            )
        fail(
            f"Cannot merge `{branch}` into `{target}`: rebase has conflicts.",
            "Branch was restored to its original state (no rewrite).",
            "Resolve manually and re-run:",
            f"  git rebase {target}    # walk through the conflicts",
            "  # ...fix conflicting files, then git add + git rebase --continue",
            f"  {RERUN}",
        )
    refuse_unfolded_fixups(target, branch, before)
    after = git("rev-parse", branch).stdout.strip()

    try:
        # Step 3 — the merge guard: green checks on exactly these commits; then land.
        number, head = ensure_checks_green(branch, target, before, after, config)
        land_by_github(number, head, target, before, branch)
    except BaseException:
        # A stop, an interrupt during the wait, or a git error: the same way back.
        if git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != branch:
            git("checkout", branch, check=False)
        restore_unpushed(branch, before)
        raise

    # Step 4 — bring the local target to what landed.
    result = git("checkout", target, check=False)
    if result.returncode != 0 or git("pull", "--ff-only", "--quiet", "origin", target, check=False).returncode != 0:
        fail(
            f"PR #{number} is merged, but the local `{target}` could not be brought up to date.",
            f"Manually: git checkout {target}",
            "  git pull --ff-only",
            f"  git push --delete origin {branch}",
            f"  git branch -D {branch}",
        )

    # Step 5 — delete the remote branch (GitHub may have deleted it already: benign).
    remote_state = "skipped"  # one of: skipped, deleted, gone, failed
    if has_origin_target and git("rev-parse", "--verify", "--quiet", f"origin/{branch}", check=False).returncode == 0:
        remote_state = delete_remote_branch(branch)

    # Step 6 — delete the local branch. GitHub's commits are not the local ones, so git
    # may not see the branch as merged: it goes when what landed is its tree.
    landed = git("diff", "--quiet", after, target, check=False).returncode == 0
    result = git("branch", "-D" if landed else "-d", branch, check=False)
    if result.returncode != 0 and not landed:
        print(
            f"{BLUE}ℹ PR #{number} is merged; {target} moved since, so the local {branch} is kept: "
            f"git branch -D {branch} once you have checked it.{NC}",
            file=sys.stderr,
        )
    elif result.returncode != 0:
        fail(
            f"Could not delete local branch {branch}.",
            "The branch is merged into target, but git refused the delete —",
            f"most likely a stale upstream config. Inspect: git branch -vv | grep {branch}",
            f"Force-delete if confirmed: git branch -D {branch}",
        )

    parts = ["local"]
    if remote_state == "deleted":
        parts.append("remote")
    elif remote_state == "failed":
        parts.append("remote delete failed — see above")
    print(
        f"{GREEN}✅ {branch} merged into {target} by GitHub (PR #{number}), and deleted ({' + '.join(parts)}).{NC}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
