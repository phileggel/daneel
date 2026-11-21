#!/usr/bin/env python3
"""Has this lane already reviewed this pull request, and is its report answered?

In CI a lane reviews a pull request once (loop § 5). A project's review workflow asks
this before it starts a lane's session, and lets the answer decide the job:

Use:  python3 lane-reviewed.py <pull request number> <lane>
Exit: 0 reviewed, and every 🔴 and 🟡 of its report is graded: the job passes, no session
      1 reviewed, and a 🔴 or 🟡 has no grade newer than the report (each is printed): the
        job fails, no session
      2 the pull request's comments could not be read: the job fails
      3 not reviewed yet: the job runs the lane's session

"Reviewed" is the lane's newest comment (`<!-- review:<lane> -->`) being a report. One
headed `## reviewer-<lane> — no report` or `— did not run …` is none, so the lane runs
again. "Graded" is what `merge.py` asks before a merge: a newer comment line carrying
(a), (b) or (c) and the finding's opening words. A report or a grade counts only from the
repository's own workflow (`github-actions[bot]`) or an account the repository gave access
(its owner, a member, a collaborator): any other account's comment is ignored. Nothing here
reads the code: a fix is validated by the project's tests, never by a second review.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

GRADED, UNGRADED, UNREADABLE, NOT_REVIEWED = 0, 1, 2, 3

_SPEC = importlib.util.spec_from_file_location(
    "merge", Path(__file__).resolve().parent.parent / "skills" / "run-entry" / "scripts" / "merge.py"
)
merge = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(merge)


def when(comment: dict) -> str:
    return comment.get("updated_at") or comment["created_at"]


def report_of(comments: list[dict], lane: str) -> dict | None:
    """The lane's newest trusted comment when it is a report, else None."""
    own = [c for c in sorted(comments, key=when)
           if merge.trusted(c) and c["body"].startswith(f"<!-- review:{lane} -->")]
    if not own or merge.reviewer_heading([own[-1]["body"]], f"reviewer-{lane}"):
        return None
    return own[-1]


def verdict(comments: list[dict], lane: str) -> tuple[int, list[str]]:
    """The exit code, and the lane's ungraded findings when there are some."""
    if report_of(comments, lane) is None:
        return NOT_REVIEWED, []
    ungraded = [words for found, words in merge.ungraded_findings(comments) if found == lane]
    return (UNGRADED if ungraded else GRADED), ungraded


def read_comments(number: str) -> list[dict]:
    result = subprocess.run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}/comments", "--paginate",
         "--jq", merge.COMMENT_FIELDS],
        capture_output=True, text=True, check=False, timeout=60,
    )
    if result.returncode != 0:
        raise OSError((result.stderr or result.stdout).strip() or "gh failed")
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[0].isdigit():
        print("usage: lane-reviewed.py <pull request number> <lane>", file=sys.stderr)
        return UNREADABLE
    number, lane = argv
    try:
        comments = read_comments(number)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"reviewer-{lane}: the comments of PR #{number} could not be read: {error}", file=sys.stderr)
        return UNREADABLE
    code, ungraded = verdict(comments, lane)
    if code == NOT_REVIEWED:
        print(f"reviewer-{lane}: no report on PR #{number} yet: run the lane")
    elif code == GRADED:
        print(f"reviewer-{lane}: reviewed PR #{number} already, every 🔴 and 🟡 graded: no second review")
    else:
        print(f"reviewer-{lane}: reviewed PR #{number} already, {len(ungraded)} finding(s) with no grade newer than the report:")
        for words in ungraded:
            print(f"  {words}")
        print(f"Grade each in one PR comment, one line per finding: (a), (b) or (c) and its words above (loop § 5): gh pr comment {number} --body-file <the grades' file>")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
