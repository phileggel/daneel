#!/usr/bin/env python3
"""Cut a release of the project in the working directory, up to its draft: never published.

Use, from the project's checkout, on a fresh `main`:

    python3 <skill>/scripts/release.py --preview      # read-only: the next version and its changelog
    python3 <skill>/scripts/release.py                # cut it
    python3 <skill>/scripts/release.py --draft v1.2.0 # the draft step alone, for a tag already pushed

A release is cut only from `feat` and `fix` commits since the last `v*` tag (a `batch/<date>`
tag never counts): a breaking one moves the major, a `feat` the minor, a `fix` the patch.
Cutting it: `main` is fresh and clean and every workflow run of its head ended green; the
version files and the changelog are written on `chore/release-v<version>`, committed,
pushed; its pull request merges once every check is green; the tag goes on the commit
`main` then holds and is pushed; the draft release gets the changelog section as its notes
— made here, or, when the project has a release workflow, once that workflow's run on the
tag has made it. The owner publishes it. A release whose commit reached `main` but whose tag
GitHub does not hold is not cut again: run again, this script tags that commit and goes on.

Exit: 0 done (or, with --preview, a release is due) · 1 stopped, the message says where and
what to do · 3 nothing to release: no `feat` or `fix` since the last release.

What differs between projects is read from `.claude/daneel.json`, key `run-batch`:
`version_files`, `changelog`, `release_workflow` (the skill's SKILL.md says what each holds).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

MAIN = "main"
CHECKS_TIMEOUT = 3600  # seconds the release pull request may wait for its checks
WORKFLOW_TIMEOUT = 4 * 3600  # seconds the release workflow may take to make the draft
WORKFLOW_APPEARS = 300  # seconds for the workflow's run on the tag to be listed
POLL = 30
sleep = time.sleep  # replaced in tests

# What a project may set in `.claude/daneel.json` under `run-batch`, with its default.
SETTINGS = {
    # The files that carry the version, the first one read for the current version:
    # `package.json`, `package-lock.json`, any other `*.json` with a top-level "version"
    # (`tauri.conf.json`), a `Cargo.toml` (its `[package]` version; its `Cargo.lock` follows).
    "version_files": ["package.json"],
    # The changelog the release writes its section in, and reads its notes from.
    "changelog": "CHANGELOG.md",
    # The workflow a `v*` tag starts, which makes the draft release (its file or name);
    # null: this script makes the draft itself.
    "release_workflow": None,
    # Read by the skill, not here: the recipe run before a release's hand-over.
    "release_check": None,
}

CHANGELOG_INTRO = (
    "# Changelog\n\n"
    "All notable changes to this project will be documented in this file.\n\n"
    "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\n"
    "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
)

COMMIT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<title>.+)$")
RUN_PASSED = {"success", "skipped", "neutral"}


class Stop(Exception):
    """The release stops here; the message says where it stands and what to do."""


# ---------------------------------------------------------------- the project

def project_root() -> Path:
    """The checkout of the working directory: the project released."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()
    return Path(top)


def load_settings(root: Path) -> dict:
    """The defaults, overridden key by key by the project's `.claude/daneel.json`."""
    path = root / ".claude" / "daneel.json"
    own = json.loads(path.read_text(encoding="utf-8")).get("run-batch", {}) if path.exists() else {}
    unknown = set(own) - set(SETTINGS)
    if unknown:
        raise SystemExit(f"release: unknown settings in {path}: {', '.join(sorted(unknown))}")
    settings = {**SETTINGS, **own}
    for name in settings["version_files"]:
        if version_kind(name) is None:
            raise SystemExit(f"release: {name} in run-batch.version_files is no file this script can version")
    return settings


def run(root: Path, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), cwd=root, capture_output=True, text=True, check=False)


def out(root: Path, *command: str) -> str:
    done = run(root, *command)
    if done.returncode != 0:
        raise Stop(f"`{' '.join(command)}` failed: {(done.stderr or done.stdout).strip()}")
    return done.stdout.strip()


# ---------------------------------------------------------------- commits and versions

def parse_commit(message: str) -> dict:
    """A conventional commit: its type, scope, title line and whether it breaks."""
    subject = message.strip().splitlines()[0] if message.strip() else ""
    match = COMMIT.match(subject)
    if not match:
        return {"type": "other", "scope": None, "title": subject, "breaking": False}
    return {
        "type": match["type"],
        "scope": match["scope"],
        "title": match["title"].strip(),
        "breaking": bool(match["bang"]) or "BREAKING CHANGE" in message,
    }


def releasable(commits: list[dict]) -> list[dict]:
    """What a user notices: the `feat` and `fix` commits, in the order given."""
    return [commit for commit in commits if commit["type"] in ("feat", "fix")]


def next_version(current: str, commits: list[dict]) -> str | None:
    """The semver bump the `feat` and `fix` commits call for; None when there is none."""
    shipped = releasable(commits)
    if not shipped:
        return None
    major, minor, patch = map(int, current.split("."))
    if any(commit["breaking"] for commit in shipped):
        return f"{major + 1}.0.0"
    if any(commit["type"] == "feat" for commit in shipped):
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def changelog_line(commit: dict) -> str:
    """A commit's changelog line: its title, its scope before it when it has one."""
    return f"- [{commit['scope']}] {commit['title']}" if commit["scope"] else f"- {commit['title']}"


def changelog_entry(version: str, day: str, commits: list[dict]) -> str:
    """The changelog section of a release: breaking changes, then Added, then Fixed."""
    shipped = releasable(commits)
    sections = [
        ("⚠️ BREAKING CHANGES", [c for c in shipped if c["breaking"]]),
        ("Added", [c for c in shipped if c["type"] == "feat"]),
        ("Fixed", [c for c in shipped if c["type"] == "fix"]),
    ]
    entry = f"## [{version}] - {day}\n"
    for heading, listed in sections:
        if listed:
            entry += f"\n### {heading}\n\n" + "".join(changelog_line(c) + "\n" for c in listed)
    return entry + "\n"


def changelog_with(existing: str | None, entry: str) -> str:
    """The changelog with the new section above the newest one, under the file's header."""
    if existing is None or not existing.strip():
        return CHANGELOG_INTRO + entry
    newest = re.search(r"^## \[", existing, re.MULTILINE)
    if newest:
        return existing[: newest.start()] + entry + existing[newest.start():]
    return existing.rstrip("\n") + "\n\n" + entry


def notes(changelog: str, version: str) -> str | None:
    """The text under `## [X.Y.Z]`, up to the next version heading; None when absent."""
    version = version.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        return None
    heading = re.search(rf"^## \[{re.escape(version)}\].*$", changelog, re.MULTILINE)
    if not heading:
        return None
    following = re.compile(r"^## \[", re.MULTILINE).search(changelog, heading.end())
    return changelog[heading.end(): following.start() if following else len(changelog)].strip()


# ---------------------------------------------------------------- version files

def version_kind(name: str) -> str | None:
    base = Path(name).name
    if base == "package-lock.json":
        return "lockfile"
    if base == "Cargo.toml":
        return "cargo"
    if base.endswith(".json"):
        return "json"
    return None


def cargo_version(text: str) -> list[re.Match]:
    """The `version = "…"` lines of a Cargo.toml's `[package]` section."""
    section = re.search(r"^\[package\][ \t]*$", text, re.MULTILINE)
    if not section:
        return []
    following = re.compile(r"^\[", re.MULTILINE).search(text, section.end())
    end = following.start() if following else len(text)
    pattern = re.compile(r'^(version\s*=\s*")([^"]+)(")', re.MULTILINE)
    return list(pattern.finditer(text, section.end(), end))


def read_version(name: str, text: str) -> str:
    """The version a file states."""
    if version_kind(name) == "cargo":
        found = cargo_version(text)
        if len(found) != 1:
            raise Stop(f"{name}: [package] version found {len(found)} times, expected once")
        return found[0].group(2)
    data = json.loads(text)
    if "version" not in data:
        raise Stop(f'{name} has no top-level "version"')
    return data["version"]


def with_version(name: str, text: str, version: str) -> str:
    """The file's text stating `version`; nothing else moves. A file of another shape stops the
    release rather than be rewritten on a guess."""
    kind = version_kind(name)
    if kind == "cargo":
        found = cargo_version(text)
        if len(found) != 1:
            raise Stop(f"{name}: [package] version found {len(found)} times, expected once")
        return text[: found[0].start(2)] + version + text[found[0].end(2):]
    data = json.loads(text)
    if "version" not in data:
        raise Stop(f'{name} has no top-level "version"')
    old = data["version"]
    data["version"] = version
    if kind == "lockfile":
        top = data.get("packages", {}).get("")
        if not isinstance(top, dict) or "version" not in top:
            raise Stop(f'{name} carries no "version" under packages[""]')
        top["version"] = version
    # The text is edited in place, never re-serialised. Each `"version": "<old>"` is kept
    # only if changing it alone changes a version this release states (a dependency at the
    # same version is left alone, wherever it sits); together they must read as `data`.
    original = json.loads(text)
    pattern = re.compile(r'"version"\s*:\s*"(' + re.escape(str(old)) + r')"')
    kept = []
    for match in pattern.finditer(text):
        one = json.loads(text[: match.start(1)] + version + text[match.end(1):])
        if one != original and _only_release_versions_moved(original, one, kind):
            kept.append(match)
    edited = text
    for match in reversed(kept):
        edited = edited[: match.start(1)] + version + edited[match.end(1):]
    if json.loads(edited) != data:
        raise Stop(f'{name}: its "version" could not be changed without moving anything else')
    return edited


def _only_release_versions_moved(original: dict, moved: dict, kind: str) -> bool:
    """`moved` differs from `original` only in the top-level version or, for a lockfile,
    `packages[""]`'s."""
    a, b = json.loads(json.dumps(original)), json.loads(json.dumps(moved))
    a.pop("version", None)
    b.pop("version", None)
    if kind == "lockfile":
        for side in (a, b):
            top = side.get("packages", {}).get("")
            if isinstance(top, dict):
                top.pop("version", None)
    return a == b


def read_file(path: Path) -> tuple[str, bool]:
    """The file's text with `\n` line ends, and whether it was written with `\r\n`."""
    with open(path, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write_file(path: Path, text: str, crlf: bool) -> None:
    """`text` written back with the line ends the file had."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\n", "\r\n") if crlf else text)


def write_versions(root: Path, settings: dict, version: str) -> list[str]:
    """Every version file states `version`; each `Cargo.lock` follows its `Cargo.toml`.
    The paths written, for the release commit."""
    written = []
    for name in settings["version_files"]:
        path = root / name
        text, crlf = read_file(path)
        write_file(path, with_version(name, text, version), crlf)
        written.append(name)
        if version_kind(name) == "cargo":
            metadata = json.loads(out(path.parent, "cargo", "metadata", "--format-version", "1"))
            lock = Path(metadata.get("workspace_root") or path.parent) / "Cargo.lock"
            if lock.exists():
                relative = str(lock.resolve().relative_to(root.resolve()))
                if relative not in written:
                    written.append(relative)
    return written


# ---------------------------------------------------------------- GitHub

def runs_in_the_way(runs: list[dict]) -> list[str]:
    """What stops a release of a commit, from the workflow runs GitHub lists for it: no run
    at all, one that has not ended, one that did not pass. The newest run of each workflow
    counts. One line per obstacle; empty when every workflow ended green."""
    newest: dict[str, dict] = {}
    for item in runs:
        name = item.get("name") or ""
        if name not in newest or item.get("id", 0) > newest[name].get("id", 0):
            newest[name] = item
    if not newest:
        return ["no workflow run is listed for this commit yet"]
    obstacles = []
    for name in sorted(newest):
        item = newest[name]
        where = item.get("html_url") or f"run {item.get('id')}"
        if item.get("status") != "completed":
            obstacles.append(f"{name}: not finished ({item.get('status')}) — {where}")
        elif item.get("conclusion") not in RUN_PASSED:
            obstacles.append(f"{name}: {item.get('conclusion')} — {where}")
    return obstacles


def required_checks(root: Path) -> list[str]:
    """The checks `required-checks.json` at the checkout's root names (`{"checks": [...]}`),
    as `merge.py` and `watch-pr.py` read them: a missing or unreadable file stops the
    release, as it stops them."""
    path = root / "required-checks.json"
    try:
        checks = json.loads(path.read_text(encoding="utf-8"))["checks"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Stop(f"required-checks.json cannot be read: {exc}")
    if not isinstance(checks, list) or not checks or not all(isinstance(c, str) and c for c in checks):
        raise Stop('required-checks.json: "checks" must be a non-empty list of check names')
    return checks


def checks_verdict(checks: list[dict], required: list[str] = ()) -> tuple[str, list[str]]:
    """A pull request's checks (`gh pr checks --json name,bucket,link`): pending while none
    is listed, one runs, or a `required` one is not listed yet; red with the failed ones
    named; else green."""
    if not checks:
        return "pending", []
    failed = [f"{c.get('name')}: {c.get('bucket')} — {c.get('link')}" for c in checks
              if c.get("bucket") in ("fail", "cancel")]
    if failed:
        return "red", failed
    if any(c.get("bucket") == "pending" for c in checks):
        return "pending", []
    if set(required) - {c.get("name") for c in checks}:
        return "pending", []
    return "green", []


def wait_for_checks(root: Path, number: str) -> None:
    required = required_checks(root)
    waited = 0
    while True:
        listed = run(root, "gh", "pr", "checks", number, "--json", "name,bucket,link")
        try:
            checks = json.loads(listed.stdout) if listed.stdout.strip() else []
        except json.JSONDecodeError:
            checks = []
        verdict, failed = checks_verdict(checks, required)
        if verdict == "green":
            return
        if verdict == "red":
            raise Stop(f"the checks of pull request #{number} failed: " + "; ".join(failed))
        if waited >= CHECKS_TIMEOUT:
            raise Stop(f"the checks of pull request #{number} did not end within {CHECKS_TIMEOUT // 60} minutes")
        sleep(POLL)
        waited += POLL


# ---------------------------------------------------------------- the release

def fresh_main(root: Path) -> None:
    """A release starts from `main` as GitHub holds it, clean, its runs all green."""
    branch = out(root, "git", "rev-parse", "--abbrev-ref", "HEAD")
    if branch != MAIN:
        raise Stop(f'the branch is "{branch}", not {MAIN}: a release is cut from {MAIN}')
    if run(root, "git", "fetch", "--quiet", "origin", MAIN, "--tags").returncode != 0:
        raise Stop(f"origin/{MAIN} cannot be fetched")
    if out(root, "git", "rev-parse", "HEAD") != out(root, "git", "rev-parse", f"origin/{MAIN}"):
        raise Stop(f"{MAIN} is not origin/{MAIN}: git pull --ff-only, then release")
    if out(root, "git", "status", "--porcelain"):
        raise Stop("the working tree has uncommitted changes: commit or drop them first")
    sha = out(root, "git", "rev-parse", "HEAD")
    try:
        listed = out(root, "gh", "api", f"repos/{{owner}}/{{repo}}/actions/runs?head_sha={sha}&per_page=100")
        runs = json.loads(listed).get("workflow_runs", [])
    except json.JSONDecodeError as error:
        raise Stop(f"the workflow runs of {sha[:7]} cannot be read: {error}") from error
    obstacles = runs_in_the_way(runs)
    if obstacles:
        raise Stop(f"the workflow runs of {sha[:7]} have not all ended green: " + "; ".join(obstacles))


def last_release(root: Path) -> str | None:
    done = run(root, "git", "describe", "--tags", "--abbrev=0", "--match", "v*")
    return done.stdout.strip() if done.returncode == 0 else None


def commits_since(root: Path, tag: str | None) -> list[dict]:
    listed = out(root, "git", "log", f"{tag}..HEAD" if tag else "HEAD", "--format=%B%x00")
    return [parse_commit(entry) for entry in listed.split("\x00") if entry.strip()]


def plan(root: Path, settings: dict) -> tuple[str, str | None, str, list[dict]]:
    """The current version, the next one (None: nothing to release), the last tag, the commits."""
    first = settings["version_files"][0]
    current = read_version(first, (root / first).read_text(encoding="utf-8"))
    tag = last_release(root)
    commits = commits_since(root, tag)
    return current, next_version(current, commits), tag or "none", commits


def land(root: Path, version: str, files: list[str]) -> None:
    """The release commit reaches `main` through its pull request, merged once green; the
    tag goes on the commit `main` then holds. Nothing is pushed to `main`."""
    tag, branch = f"v{version}", f"chore/release-v{version}"
    title = f"chore: release {tag}"
    out(root, "git", "switch", "--quiet", "-c", branch)
    out(root, "git", "add", "--", *files)
    out(root, "git", "commit", "--quiet", "-m", title)
    commit = out(root, "git", "rev-parse", "HEAD")
    out(root, "git", "push", "--quiet", "-u", "origin", branch)
    url = out(root, "gh", "pr", "create", "--base", MAIN, "--head", branch, "--title", title,
              "--body", f"The version and the changelog of {tag}.")
    number = url.rstrip("/").rsplit("/", 1)[-1]
    print(f"release: pull request #{number} opened, waiting for its checks")
    wait_for_checks(root, number)
    out(root, "gh", "pr", "merge", number, "--rebase", "--match-head-commit", commit)
    out(root, "git", "switch", "--quiet", MAIN)
    out(root, "git", "pull", "--quiet", "--ff-only", "origin", MAIN)
    landed = out(root, "git", "log", "-1", "--format=%s", MAIN)
    if landed != title or run(root, "git", "diff", "--quiet", commit, MAIN).returncode != 0:
        raise Stop(f"pull request #{number} merged, but {MAIN}'s head is not the release commit: nothing is tagged; "
                   f"run release.py again to tag the release commit")
    out(root, "git", "tag", "-a", tag, "-m", f"Version {version}", MAIN)
    out(root, "git", "push", "--quiet", "origin", f"refs/tags/{tag}")
    run(root, "git", "branch", "-D", branch)
    print(f"release: {tag} tagged on {MAIN} and pushed")


def untagged_release(root: Path, settings: dict) -> tuple[str, str] | None:
    """(version, commit) when the version the files state landed on `main` as its release
    commit but GitHub holds no tag for it; None otherwise."""
    first = settings["version_files"][0]
    version = read_version(first, (root / first).read_text(encoding="utf-8"))
    title = "^chore: release v" + version.replace(".", "\\.") + "$"
    commit = out(root, "git", "log", "-1", "--format=%H", "--grep", title)
    if not commit:
        return None
    pushed = run(root, "git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/v{version}")
    if pushed.returncode == 0:
        return None
    if pushed.returncode != 2:
        raise Stop(f"the tags of origin cannot be read: {(pushed.stderr or pushed.stdout).strip()}")
    return version, commit


def tag_landed(root: Path, version: str, commit: str) -> None:
    """The tag goes on the landed release commit and is pushed; one left here by a failed
    push is kept if it is on that commit."""
    tag = f"v{version}"
    local = run(root, "git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    if local.returncode != 0:
        out(root, "git", "tag", "-a", tag, "-m", f"Version {version}", commit)
    elif local.stdout.strip() != commit:
        raise Stop(f"the local tag {tag} is not on the release commit {commit[:7]}: see where it came from, then delete it")
    out(root, "git", "push", "--quiet", "origin", f"refs/tags/{tag}")
    print(f"release: {tag} tagged on the release commit {commit[:7]} and pushed")


def workflow_run(root: Path, workflow: str, tag: str) -> dict:
    """The release workflow's run on the tag, once it has ended."""
    waited = 0
    while True:
        listed = run(root, "gh", "run", "list", "--workflow", workflow, "--branch", tag,
                     "--json", "databaseId,status,conclusion,url", "--limit", "5")
        try:
            runs = json.loads(listed.stdout) if listed.stdout.strip() else []
        except json.JSONDecodeError:
            runs = []
        if runs:
            newest = max(runs, key=lambda item: item.get("databaseId", 0))
            if newest.get("status") == "completed":
                return newest
        elif waited >= WORKFLOW_APPEARS:
            raise Stop(f"no run of {workflow} is listed for {tag}")
        if waited >= WORKFLOW_TIMEOUT:
            raise Stop(f"{workflow} on {tag} has not ended: when it has, release.py --draft {tag}")
        sleep(POLL)
        waited += POLL


def draft(root: Path, settings: dict, tag: str) -> None:
    """The draft release of `tag`, its notes the changelog's section. Never published."""
    text = notes((root / settings["changelog"]).read_text(encoding="utf-8"), tag)
    if not text:
        raise Stop(f"{settings['changelog']} has no section for {tag}")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as file:
        file.write(text + "\n")
    try:
        url, ran = _draft(root, settings["release_workflow"], tag, file.name)
    finally:
        Path(file.name).unlink(missing_ok=True)
    print(f"Everything is made but the publishing: the draft {url}{ran}")


def _draft(root: Path, workflow: str | None, tag: str, notes_file: str) -> tuple[str, str]:
    ran = ""
    if workflow:
        finished = workflow_run(root, workflow, tag)
        ran = f"; run {finished.get('url')}"
        if finished.get("conclusion") != "success":
            raise Stop(f"{workflow} on {tag} ended {finished.get('conclusion')}{ran}: "
                       f"fix or re-run it, then release.py --draft {tag}")
        state = json.loads(out(root, "gh", "release", "view", tag, "--json", "isDraft,url"))
        if not state.get("isDraft"):
            raise Stop(f"the release {tag} is not a draft: it was published outside this script")
        out(root, "gh", "release", "edit", tag, "--notes-file", notes_file)
        return state.get("url"), ran
    url = out(root, "gh", "release", "create", tag, "--draft", "--verify-tag",
              "--title", tag, "--notes-file", notes_file)
    return url, ran


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Cut a release up to its draft; never publish it.")
    parser.add_argument("--preview", action="store_true", help="read-only: the next version and its changelog")
    parser.add_argument("--draft", metavar="TAG", help="the draft step alone, for a tag already pushed")
    args = parser.parse_args(argv)
    root = project_root()
    settings = load_settings(root)
    try:
        if args.draft:
            draft(root, settings, args.draft)
            return 0
        if not args.preview:
            fresh_main(root)
        landed = untagged_release(root, settings)
        if landed:
            print(f"release: v{landed[0]} is on {MAIN} ({landed[1][:7]}) but not tagged: this release finishes it")
            if not args.preview:
                tag_landed(root, *landed)
                draft(root, settings, f"v{landed[0]}")
            return 0
        current, version, tag, commits = plan(root, settings)
        if version is None:
            print(f"release: no feat or fix since {tag}: nothing to release; end the batch with batch-end.sh")
            return 3
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = changelog_entry(version, day, commits)
        print(f"release: {current} → {version} (since {tag})\n\n{entry.rstrip()}\n")
        if args.preview:
            return 0
        if run(root, "git", "rev-parse", "--verify", "--quiet", f"refs/tags/v{version}").returncode == 0:
            raise Stop(f"the tag v{version} already exists")
        if run(root, "git", "rev-parse", "--verify", "--quiet", f"refs/heads/chore/release-v{version}").returncode == 0:
            raise Stop(f"chore/release-v{version} is left from an earlier attempt: see where its pull request "
                       f"stands (gh pr list --head chore/release-v{version} --state all), then delete the branch")
        files = write_versions(root, settings, version)
        changelog = root / settings["changelog"]
        existing, crlf = read_file(changelog) if changelog.exists() else (None, False)
        write_file(changelog, changelog_with(existing, entry), crlf)
        land(root, version, [*files, settings["changelog"]])
        draft(root, settings, f"v{version}")
        return 0
    except Stop as stop:
        print(f"release: stopped: {stop}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
