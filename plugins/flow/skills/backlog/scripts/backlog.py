#!/usr/bin/env python3
"""The backlog by size against its ceiling: one measure for the coder's check before it
files a ticket, and for the Backlog block of the batch-end audit (`flow-audit.py`).

The ceiling binds the coding agent alone. It marks what it files (`coder_mark`); every
unmarked ticket is the owner's — filed on GitHub, through Cowork or by another session —
and raises the ceiling, as do the coder's tickets the owner approved (`owner-asked`) and
the waived ones (security, data loss, a flaky test). The ceiling is the backlog at the last batch end
plus those, so a backlog over its healthy size can only shrink. A project may set that
healthy size (`target`): at or under it, the agent files up to it. Before the first batch
end only the target holds, and with no target every ticket fits.

Before filing, `match` lists the open issues that name each key of the draft (its paths,
also by folder, its rule IDs, its symbols), read in one call: the agent folds into a hit
that holds the same observation, or files and lists the hits.

Usage, from the project's checkout:
    python3 <plugin>/scripts/backlog.py match src/auth/service.rs ORD-010 place_order
    python3 <plugin>/scripts/backlog.py check M            # does an M fit? exit 1 if not
    python3 <plugin>/scripts/backlog.py check S --waived   # a security, data-loss or flaky-test ticket

What differs between projects is read from `.claude/daneel.json`, key `backlog`
(`SETTINGS` below).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SIZE_WEIGHTS = {"size:S": 1, "size:M": 2, "size:L": 4, "size:XL": 8}
# A ticket with no size counts as an M.
UNSIZED_WEIGHT = 2
OWNER_ASKED = "owner-asked"
# The batch's audit issue is no work.
NOT_WORK = "batch-audit"

SETTINGS = {
    # The label the coding agent puts on every ticket it files.
    "coder_mark": "agent-filed",
    # Labels that are always filed, and raise the ceiling.
    "waived": ["security", "data-loss", "flaky"],
    # The backlog's healthy size, in weight (S 1, M 2, L 4, XL 8); null for none.
    "target": None,
}


def project_root() -> Path:
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()
    return Path(top)


def load_settings(root: Path) -> dict:
    path = root / ".claude" / "daneel.json"
    own = json.loads(path.read_text(encoding="utf-8")).get("backlog", {}) if path.exists() else {}
    unknown = set(own) - set(SETTINGS)
    if unknown:
        raise SystemExit(f"backlog: unknown settings in {path}: {', '.join(sorted(unknown))}")
    return {**SETTINGS, **own}


def parse_moment(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _within(text: str | None, since: datetime, until: datetime) -> bool:
    return text is not None and since < parse_moment(text) <= until


def _open_at(item: dict, moment: datetime) -> bool:
    closed = item.get("closedAt")
    return parse_moment(item["createdAt"]) <= moment and (
        closed is None or parse_moment(closed) > moment
    )


def size_of(issue: dict) -> str:
    sizes = [label for label in issue["labels"] if label in SIZE_WEIGHTS]
    return max(sizes, key=SIZE_WEIGHTS.get).removeprefix("size:") if sizes else "unsized"


def weight(issue: dict) -> int:
    sizes = [SIZE_WEIGHTS[label] for label in issue["labels"] if label in SIZE_WEIGHTS]
    return max(sizes) if sizes else UNSIZED_WEIGHT


def measure_backlog(
    issues: list[dict],
    since: datetime,
    until: datetime,
    coder_mark: str = SETTINGS["coder_mark"],
    waived: tuple[str, ...] = tuple(SETTINGS["waived"]),
    target: int | None = SETTINGS["target"],
) -> dict:
    """The open backlog by size at both ends, the ceiling, and what was added and removed
    in between. A parent weighs nothing while one of its slices is open. Sizes are
    today's labels, not the ones each ticket had then."""
    work = [issue for issue in issues if NOT_WORK not in issue["labels"]]

    def counted(moment: datetime) -> list[dict]:
        return [
            issue
            for issue in work
            if _open_at(issue, moment)
            and not any(_open_at(sub, moment) for sub in issue.get("subIssues", []))
        ]

    def by_size(items: list[dict]) -> dict[str, int]:
        sizes: dict[str, int] = {}
        for issue in items:
            sizes[size_of(issue)] = sizes.get(size_of(issue), 0) + 1
        return dict(sorted(sizes.items()))

    def entry(issue: dict) -> dict:
        return {"number": issue.get("number"), "size": size_of(issue)}

    added = {"coder": [], "owner": [], "waived": []}
    for issue in work:
        if not _within(issue["createdAt"], since, until):
            continue
        labels = issue["labels"]
        if any(label in waived for label in labels):
            added["waived"].append(issue)
        elif coder_mark in labels and OWNER_ASKED not in labels:
            added["coder"].append(issue)
        else:
            added["owner"].append(issue)

    removed = {"done": [], "folded": [], "closed": []}
    for issue in work:
        if _within(issue.get("closedAt"), since, until):
            reason = issue.get("stateReason") or "COMPLETED"
            kind = {"COMPLETED": "done", "DUPLICATE": "folded"}.get(reason, "closed")
            removed[kind].append(issue)

    start, end = counted(since), counted(until)
    at_start, at_end = sum(map(weight, start)), sum(map(weight, end))
    ceiling = at_start + sum(weight(i) for i in added["owner"] + added["waived"])
    if target is not None:
        ceiling = max(ceiling, target)
    return {
        "at_start": at_start,
        "at_end": at_end,
        "ceiling": ceiling,
        "target": target,
        "within_ceiling": at_end <= ceiling,
        "room": ceiling - at_end,
        "tickets": {"start": len(start), "end": len(end)},
        "by_size": {"start": by_size(start), "end": by_size(end)},
        "added": {kind: [entry(i) for i in items] for kind, items in added.items()},
        "removed": {kind: [entry(i) for i in items] for kind, items in removed.items()},
    }


def _gh_json_lines(*args: str) -> list[dict]:
    if not shutil.which("gh"):
        raise SystemExit("backlog: the GitHub command line (gh) is not installed")
    try:
        result = subprocess.run(
            ["gh", *args], check=True, capture_output=True, text=True, timeout=300
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"backlog: gh {' '.join(args[:2])} failed: {error}") from error
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


# `{owner}` and `{repo}` are filled by `gh` from the checkout's remote.
BACKLOG_QUERY = """
query($owner: String!, $repo: String!, $endCursor: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: 100, after: $endCursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number createdAt closedAt stateReason
        labels(first: 20) { nodes { name } }
        subIssues(first: 50) { nodes { createdAt closedAt } }
      }
    }
  }
}
"""


def collect_backlog() -> list[dict]:
    """Every issue with its labels, its close reason and its slices."""
    nodes = _gh_json_lines(
        "api", "graphql", "--paginate", "-f", f"query={BACKLOG_QUERY}",
        "-F", "owner={owner}", "-F", "repo={repo}",
        "--jq", ".data.repository.issues.nodes[]",
    )
    return [
        {
            "number": node["number"],
            "createdAt": node["createdAt"],
            "closedAt": node["closedAt"],
            "stateReason": node.get("stateReason"),
            "labels": [label["name"] for label in node["labels"]["nodes"]],
            "subIssues": node["subIssues"]["nodes"],
        }
        for node in nodes
    ]


def last_batch_end() -> datetime | None:
    """When the last batch ended: its `v*` or `batch/<date>` tag's date; None before the first."""
    made = subprocess.run(
        ["git", "for-each-ref", "--sort=-creatordate", "--count=1",
         "--format=%(creatordate:iso-strict)", "refs/tags/v*", "refs/tags/batch/"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return parse_moment(made) if made else None


def _names(text: str, key: str) -> bool:
    """`key` stands whole in `text`: `ORD-1` is not found in `ORD-10`, nor `order` in
    `place_order`; a folder (`src/orders/`) is found at the head of a longer path."""
    tail = "" if key.endswith("/") else r"(?![\w-])"
    return re.search(r"(?<![\w./-])" + re.escape(key) + tail, text) is not None


def match_keys(keys: list[str], issues: list[dict]) -> dict[str, list[tuple[int, str, bool]]]:
    """For each key of a draft (a path, a rule ID, a symbol), the open issues that name it
    in their title, body or a comment: (number, title, by its folder). A path is also
    matched by its folder (`src/auth/` for `src/auth/service.rs`), and such a hit says so.
    Nothing is folded here: the agent reads each hit."""
    found: dict[str, list[tuple[int, str, bool]]] = {}
    for key in keys:
        folder = key.rsplit("/", 1)[0] + "/" if "/" in key.rstrip("/") and not key.endswith("/") else None
        hits = []
        for issue in sorted(issues, key=lambda i: i["number"]):
            text = "\n".join([issue.get("title") or "", issue.get("body") or ""]
                             + [c.get("body") or "" for c in issue.get("comments") or []])
            if _names(text, key):
                hits.append((issue["number"], issue.get("title") or "", False))
            elif folder and _names(text, folder):
                hits.append((issue["number"], issue.get("title") or "", True))
        found[key] = hits
    return found


def open_issues() -> list[dict]:
    """Every open issue with its title, body and comments, in one call."""
    return _gh_json_lines("issue", "list", "--state", "open", "--limit", "1000",
                          "--json", "number,title,body,comments", "--jq", ".[]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="does a ticket of this size fit under the ceiling")
    check.add_argument("size", choices=["S", "M", "L", "XL"])
    check.add_argument("--waived", action="store_true", help="a security, data-loss or flaky-test ticket")
    match = sub.add_parser("match", help="the open issues naming each key of a draft")
    match.add_argument("keys", nargs="+", help="the draft's paths, rule IDs and symbols")
    args = parser.parse_args(argv)

    if args.command == "match":
        for key, hits in match_keys(args.keys, open_issues()).items():
            named = ", ".join(f"#{n} {title}" + (" (its folder)" if by_folder else "") for n, title, by_folder in hits)
            print(f"{key}: {named or 'none'}")
        return 0

    settings = load_settings(project_root())
    needed = SIZE_WEIGHTS[f"size:{args.size}"]
    now = datetime.now(timezone.utc)
    since = last_batch_end()
    issues = collect_backlog()
    if since is None:
        # Before the first batch end there is nothing to shrink from: only the target holds.
        at_end = sum(weight(i) for i in issues
                     if NOT_WORK not in i["labels"] and _open_at(i, now)
                     and not any(_open_at(s, now) for s in i.get("subIssues", [])))
        target = settings["target"]
        ceiling = target if target is not None else at_end + needed
        block = {"at_end": at_end, "ceiling": ceiling, "room": ceiling - at_end}
    else:
        block = measure_backlog(
            issues, since, now, settings["coder_mark"], tuple(settings["waived"]), settings["target"]
        )
    fits = args.waived or needed <= block["room"]
    print(
        f"backlog {block['at_end']}, ceiling {block['ceiling']}, room {block['room']}: "
        + ("waived, file it" if args.waived else f"an {args.size} ({needed}) "
           + ("fits, file it" if fits else "does not fit: fold it, else drop it if it is not really important, else put it to the owner"))
    )
    return 0 if fits else 1


if __name__ == "__main__":
    sys.exit(main())
