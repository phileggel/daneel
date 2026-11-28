#!/usr/bin/env python3
"""Does every (b) and (c) grade of a PR body carry its source?

Run-entry checks the file of the body before the PR exists (loop § 5): a finding
deferred or rejected with no source is one a CI reviewer raises again.

Use:  python3 grades.py <the PR body's file>
Exit: 0 every (b) and (c) line carries its source
      1 a (b) or (c) line lacks its source (each is printed)
      2 the file could not be read

A grade line is any line carrying (b) or (c). A (b) line carries the `#NNN` of the issue
the finding was folded into or filed as. A (c) line carries, after a dash, what overrides
the finding: a path, `#NNN`, an ADR, a figure or `owner`. Nothing here calls GitHub, and
nothing checks that the source is the right one.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SOURCED, UNSOURCED, UNREADABLE = 0, 1, 2

ISSUE = re.compile(r"#\d+")
DASH = re.compile(r"\s[—–-]\s")
# A figure (an issue's number and most rule IDs carry one), an ADR, the owner, a path.
CITATION = re.compile(r"\d|\bADR\b|\bowner\b|[\w.-]+/[\w./-]+|\b[\w-]{2,}\.[A-Za-z]{1,5}\b", re.IGNORECASE)

NO_ISSUE = "(b) with no #NNN"
NO_CITATION = "(c) with no citation after a dash (a path, #NNN, an ADR, a figure or `owner`)"
SHOWN = 100  # the characters of a refused line that are printed


def unsourced(body: str) -> list[tuple[int, str, str]]:
    """(line number, what it lacks, the line) for each (b) or (c) line without its source."""
    found = []
    for number, line in enumerate(body.splitlines(), 1):
        if "(b)" in line and not ISSUE.search(line):
            found.append((number, NO_ISSUE, line.strip()))
        if "(c)" in line:
            after = DASH.split(line.split("(c)", 1)[1], maxsplit=1)
            if len(after) < 2 or not CITATION.search(after[1]):
                found.append((number, NO_CITATION, line.strip()))
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: grades.py <the PR body's file>", file=sys.stderr)
        return UNREADABLE
    try:
        body = Path(argv[0]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(f"grades: {argv[0]} could not be read: {error}", file=sys.stderr)
        return UNREADABLE
    found = unsourced(body)
    if not found:
        print(f"grades: every (b) and (c) line of {argv[0]} carries its source")
        return SOURCED
    print(f"grades: {len(found)} grade line(s) of {argv[0]} lack their source:")
    for number, lacks, line in found:
        print(f"  line {number}: {lacks}: {line[:SHOWN]}")
    print(f"Give each its source (loop § 5), then: python3 {Path(__file__).resolve()} {argv[0]}")
    return UNSOURCED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
