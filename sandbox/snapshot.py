#!/usr/bin/env python3
"""A fresh copy of the sandbox's app for one run, with a fixed history and a local `origin`.

Use:  python3 sandbox/snapshot.py restore [FOLDER]   build the copy; prints the folder
      python3 sandbox/snapshot.py discard FOLDER     throw a restored folder away
      (a scenario's branches are added by `sandbox/run.py`, through `restore(branches=...)`)
Exit: 0 done · 1 refused (the reason is printed) · 2 wrong arguments

`restore` writes into FOLDER (a new temporary folder when none is given; it must be empty
or absent):

  FOLDER/acme/        the app on `main`, tracking `origin/main`, clean
  FOLDER/origin.git/  a bare repository, the copy's only remote

The history is HISTORY below: the same commits, dates and authors on every build, so two
builds give the same commit ids for as long as `sandbox/acme/` holds the same files. The
files are those git would track there (`git ls-files`, the app's `.gitignore` applied), so
nothing built is copied. `acme/node_modules` is a copy of the app's installed packages when
they are there (`npm ci` in `sandbox/acme/`): ignored by git, it lets the copy's
`just harness` run with no install, and a run that installs changes its own copy only.

A branch a scenario starts with (a task stopped in review, say) is one more fixed commit on
top of `main`, made of the files of a folder laid over the app's, and pushed to `origin`;
the copy is left on `main`.

Nothing is written under `sandbox/acme/`: a run works on the copy, pushes to
`origin.git`, and `discard` removes both. `discard` refuses a folder `restore` did not make.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parent / "acme"
MARKER = ".acme-snapshot"
AUTHOR = ("Ada Acme", "ada@acme.example")
# Who commits in the copy during a run, so a run needs no git identity of the machine.
RUNNER = ("Acme Agent", "agent@acme.example")

# (date, message, the path prefixes it adds). A file no prefix takes goes in the last commit.
HISTORY = [
    ("2026-01-05T09:00:00+00:00", "chore: the project's settings and recipes",
     [".claude/", ".gitignore", "justfile", "required-checks.json"]),
    ("2026-01-06T10:30:00+00:00", "feat(fees): what a parcel costs, by weight and zone",
     ["src-tauri/core/"]),
    ("2026-01-08T14:15:00+00:00", "feat(fees): the quote command and the window",
     ["src-tauri/"]),
    ("2026-01-12T16:45:00+00:00", "feat(fees): the screen that quotes a parcel", []),
]


def refuse(reason: str) -> SystemExit:
    print(f"snapshot: {reason}", file=sys.stderr)
    return SystemExit(1)


def clean_env(date: str | None = None) -> dict[str, str]:
    """git as it behaves with no configuration of the machine or of a calling hook."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    if date:
        env.update(
            GIT_AUTHOR_NAME=AUTHOR[0], GIT_AUTHOR_EMAIL=AUTHOR[1], GIT_AUTHOR_DATE=date,
            GIT_COMMITTER_NAME=AUTHOR[0], GIT_COMMITTER_EMAIL=AUTHOR[1], GIT_COMMITTER_DATE=date,
        )
    return env


def git(folder: Path, *args: str, date: str | None = None) -> str:
    done = subprocess.run(["git", *args], cwd=folder, env=clean_env(date), capture_output=True, text=True)
    if done.returncode != 0:
        raise refuse(f"git {' '.join(args)} failed in {folder}: {done.stderr.strip()}")
    return done.stdout


def app_files() -> list[str]:
    """The app's files as git would track them, sorted: tracked, or new and not ignored."""
    listed = git(APP, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    return sorted(path for path in listed.split("\0") if path and (APP / path).is_file())


def commits(files: list[str]) -> list[tuple[str, str, list[str]]]:
    """HISTORY with each commit's files: a file goes to the first commit a prefix of which
    it starts with, else to the last."""
    taken: set[str] = set()
    planned = []
    for position, (date, message, prefixes) in enumerate(HISTORY):
        last = position == len(HISTORY) - 1
        own = [f for f in files if f not in taken and (last or any(f.startswith(p) for p in prefixes))]
        taken.update(own)
        if own:
            planned.append((date, message, own))
    return planned


def add_branch(work: Path, name: str, date: str, message: str, files: Path) -> None:
    """One fixed commit on a new branch off `main`: every file under `files`, laid over the
    copy at the same path. Pushed to `origin`; the copy goes back to `main`."""
    laid = sorted(path for path in files.rglob("*") if path.is_file())
    if not laid:
        raise refuse(f"the branch {name} has no file under {files}")
    git(work, "checkout", "-q", "-b", name, "main")
    for path in laid:
        target = work / path.relative_to(files)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    git(work, "add", "--", *[str(path.relative_to(files)) for path in laid])
    git(work, "commit", "-q", "-m", message, date=date)
    git(work, "push", "-q", "-u", "origin", name)
    git(work, "checkout", "-q", "main")


def restore(folder: Path | None = None, packages: bool = True, branches: list[dict] | None = None) -> Path:
    """Builds the copy and its `origin` in `folder`, and returns it; without `packages`, the
    installed packages are left out, for a caller that runs nothing in the copy. `branches`
    are a scenario's: each {"name", "date", "message", "files": a folder}."""
    if folder is None:
        folder = Path(tempfile.mkdtemp(prefix="acme-snapshot-"))
    folder = folder.resolve()
    if folder == APP or APP in folder.parents:
        raise refuse(f"{folder} is inside the app: a copy never lives in what it copies")
    if folder.exists() and any(folder.iterdir()):
        raise refuse(f"{folder} is not empty")
    files = app_files()
    if not files:
        raise refuse(f"no file found in {APP}")
    work, origin = folder / "acme", folder / "origin.git"
    work.mkdir(parents=True)
    (folder / MARKER).write_text("made by sandbox/snapshot.py restore\n", encoding="utf-8")
    git(folder, "init", "-q", "--bare", "-b", "main", str(origin))
    git(work, "init", "-q", "-b", "main")
    for key, value in (("user.name", RUNNER[0]), ("user.email", RUNNER[1]),
                       ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
        git(work, "config", key, value)
    for date, message, own in commits(files):
        for path in own:
            target = work / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(APP / path, target)
        git(work, "add", "--", *own)
        git(work, "commit", "-q", "-m", message, date=date)
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "-u", "origin", "main")
    for branch in branches or []:
        add_branch(work, branch["name"], branch["date"], branch["message"], Path(branch["files"]))
    installed = APP / "node_modules"
    if packages and installed.is_dir():
        shutil.copytree(installed, work / "node_modules", symlinks=True)
    return folder


def discard(folder: Path) -> None:
    folder = folder.resolve()
    if not (folder / MARKER).is_file():
        raise refuse(f"{folder} was not made by restore (no {MARKER}): nothing removed")
    shutil.rmtree(folder)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="snapshot.py", description=__doc__.split("\n")[0])
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("restore").add_argument("folder", nargs="?", type=Path)
    actions.add_parser("discard").add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    if args.action == "restore":
        print(restore(args.folder))
    else:
        discard(args.folder)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
