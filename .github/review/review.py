#!/usr/bin/env python3
"""The `review` check of a daneel pull request.

  review.py prepare <tree> <output>   writes what the reviewer reads, from the pull request,
                                      the issues it closes and the diff in <tree>
  review.py gate <claude-json> <comment>   writes the pull request comment and decides

`gate` exits 0 when the goal is achieved, the change is tested where it can be and no finding
is critical; 1 when one of those fails; 2 when the reviewer gave no usable verdict, which
refuses the merge too.

`prepare` reads PR_NUMBER, BASE_SHA, HEAD_SHA and GITHUB_REPOSITORY. Nothing here runs the
branch's code.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PASSED, REFUSED, NO_VERDICT = 0, 1, 2
CLOSING = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE)
SEVERITIES = (("critical", "🔴 Critical"), ("warning", "🟡 Warning"), ("info", "🔵 Info"))
GOALS = {"achieved", "partial", "not_achieved", "not_stated"}
TESTS = {"proven", "not_testable", "missing"}
COMMENT_LIMIT = 60000


def closing_issues(body: str | None) -> list[int]:
    """The issues a pull request's body closes, in order, each once."""
    return list(dict.fromkeys(int(number) for number in CLOSING.findall(body or "")))


def read_verdict(output: str) -> dict | None:
    """The verdict in `claude -p --output-format json`'s output, or None when it holds none
    that can be trusted: a failed run, or a verdict of the wrong shape."""
    try:
        result = json.loads(output)
    except ValueError:
        return None
    if not isinstance(result, dict) or result.get("is_error"):
        return None
    verdict = result.get("structured_output")
    try:
        known = (
            verdict["goal"]["status"] in GOALS
            and verdict["tests"]["status"] in TESTS
            and all(finding["severity"] in dict(SEVERITIES) for finding in verdict["findings"])
        )
    except (KeyError, TypeError):
        return None
    return verdict if known else None


def refusals(verdict: dict) -> list[str]:
    """Why this verdict refuses the merge. Warnings and info never do."""
    reasons = []
    if verdict["goal"]["status"] != "achieved":
        reasons.append(f"goal: {verdict['goal']['status']}")
    if verdict["tests"]["status"] == "missing":
        reasons.append("tests: missing")
    critical = sum(finding["severity"] == "critical" for finding in verdict["findings"])
    if critical:
        reasons.append(f"{critical} critical")
    return reasons


def render(verdict: dict | None) -> str:
    """The pull request comment."""
    if verdict is None:
        return "## review — ❌ no verdict\n\nThe reviewer gave no usable verdict, so this refuses the merge. See the run's log.\n"
    reasons = refusals(verdict)
    headline = f"❌ refused ({', '.join(reasons)})" if reasons else "✅ passed"
    lines = [
        f"## review — {headline}",
        "",
        f"**Goal — {verdict['goal']['status']}.** {verdict['goal']['stated']}",
        "",
        verdict["goal"]["evidence"],
        "",
        f"**Tests — {verdict['tests']['status']}.** {verdict['tests']['evidence']}",
    ]
    for severity, title in SEVERITIES:
        found = [finding for finding in verdict["findings"] if finding["severity"] == severity]
        if found:
            lines += ["", f"### {title}"]
            lines += [f"- `{f['file']}:{f['line']}` {f['claim']} → {f['fix']}" for f in found]
    return "\n".join(lines)[:COMMENT_LIMIT] + "\n"


def gh_json(path: str) -> dict:
    return json.loads(subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout)


def neutralise(tree: Path) -> None:
    """The branch's tree is read, so nothing in it may be loaded as instructions or settings."""
    for found in list(tree.rglob("CLAUDE.md")):
        found.rename(found.with_name("CLAUDE.md.branch"))
    for found in list(tree.rglob(".claude")):
        if found.is_dir():
            subprocess.run(["rm", "-rf", str(found)], check=True)


def prepare(tree: Path, output: Path) -> int:
    repo, number = os.environ["GITHUB_REPOSITORY"], os.environ["PR_NUMBER"]
    base, head = os.environ["BASE_SHA"], os.environ["HEAD_SHA"]
    pull = gh_json(f"repos/{repo}/pulls/{number}")
    diff = subprocess.run(
        ["git", "-C", str(tree), "diff", f"{base}...{head}"], check=True, capture_output=True, text=True
    ).stdout
    parts = [f"# Pull request #{number}: {pull['title']}", "", pull.get("body") or "(no body)"]
    for issue_number in closing_issues(pull.get("body")):
        issue = gh_json(f"repos/{repo}/issues/{issue_number}")
        parts += ["", f"# Closed issue #{issue_number}: {issue['title']}", "", issue.get("body") or "(no body)"]
    parts += ["", "# Diff", "", "```diff", diff, "```"]
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")
    neutralise(tree)
    return 0


def gate(claude_json: Path, comment: Path) -> int:
    output = claude_json.read_text(encoding="utf-8") if claude_json.exists() else ""
    verdict = read_verdict(output)
    comment.write_text(render(verdict), encoding="utf-8")
    if verdict is None:
        return NO_VERDICT
    return REFUSED if refusals(verdict) else PASSED


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "prepare":
        return prepare(Path(argv[1]), Path(argv[2]))
    if len(argv) == 3 and argv[0] == "gate":
        return gate(Path(argv[1]), Path(argv[2]))
    print(__doc__, file=sys.stderr)
    return NO_VERDICT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
