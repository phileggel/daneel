"""Tests for app's new-repo.sh — /app:init gives a project's spec or its mocks a repository
of their own — run with `python3 -m unittest discover -s tests`. `gh` is a stub first on
PATH that records its arguments; no test talks to GitHub."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/app/skills/init/scripts/new-repo.sh"

# `repo view` succeeds once the marker exists; `repo create` makes it; `repo clone` leaves
# a checkout on `main` whose origin is the repository asked for.
GH = """#!/usr/bin/env bash
echo "$*" >> "$GH_LOG"
case "$1 $2" in
"repo view") [ -e "$GH_EXISTS" ] ;;
"repo create") touch "$GH_EXISTS" ;;
"repo clone")
    git init -q -b "${GH_BRANCH:-main}" "$4"
    git -C "$4" remote add origin "https://github.com/$3.git" ;;
esac
"""


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


class NewRepo(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.top = Path(folder.name)
        self.project = self.top / "app"
        git(self.top, "init", "-q", "-b", "main", str(self.project))
        git(self.project, "config", "user.email", "t@example.com")
        git(self.project, "config", "user.name", "t")
        git(self.project, "remote", "add", "origin", "https://github.com/acme/app.git")
        bin_folder = self.top / "bin"
        bin_folder.mkdir()
        (bin_folder / "gh").write_text(GH, encoding="utf-8")
        (bin_folder / "gh").chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{bin_folder}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(self.top / "gh.log"),
            "GH_EXISTS": str(self.top / "exists"),
        }

    def run_script(self, *args, **env):
        return subprocess.run(["bash", str(SCRIPT), *args], cwd=self.project, capture_output=True, text=True,
                              env={**self.env, **env})

    def gh_calls(self):
        log = Path(self.env["GH_LOG"])
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def ignored(self):
        file = self.project / ".gitignore"
        return file.read_text(encoding="utf-8").splitlines() if file.exists() else []

    def refused(self, result, words):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(words, result.stderr)


class ASpecRepository(NewRepo):
    def test_it_is_created_private_cloned_at_the_folder_and_ignored(self):
        result = self.run_script("spec", "acme/app-spec", "docs/spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), [
            "repo view acme/app-spec --json name",
            "repo create acme/app-spec --private --add-readme",
            "repo clone acme/app-spec docs/spec",
        ])
        self.assertTrue((self.project / "docs/spec/.git").is_dir())
        self.assertEqual(self.ignored(), ["/docs/spec/"])
        self.assertEqual(git(self.project, "status", "--porcelain"), "?? .gitignore")
        self.assertIn('to add to .claude/daneel.json: "spec-proposal": {"repo": "acme/app-spec"}', result.stdout)
        self.assertIn('for the owner, under permissions.deny in .claude/settings.json: "Edit(/docs/spec/**)"', result.stdout)

    def test_a_second_run_creates_clones_and_writes_nothing(self):
        self.run_script("spec", "acme/app-spec", "docs/spec")
        Path(self.env["GH_LOG"]).unlink()
        result = self.run_script("spec", "acme/app-spec", "docs/spec/")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), ["repo view acme/app-spec --json name"])
        self.assertEqual(self.ignored(), ["/docs/spec/"])
        for step in ("the repository acme/app-spec", "the clone at docs/spec", "docs/spec in .gitignore"):
            self.assertIn(f"present: {step}", result.stdout)

    def test_the_ignore_line_is_added_after_a_last_line_with_no_newline(self):
        (self.project / ".gitignore").write_text("node_modules", encoding="utf-8")
        self.run_script("spec", "acme/app-spec", "docs/spec")
        self.assertEqual(self.ignored(), ["node_modules", "/docs/spec/"])

    def test_a_folder_git_tracks_is_refused_before_any_repository_is_created(self):
        (self.project / "docs/spec").mkdir(parents=True)
        (self.project / "docs/spec/orders.md").write_text("rules\n", encoding="utf-8")
        git(self.project, "add", ".")
        git(self.project, "commit", "-qm", "a spec in the project")
        self.refused(self.run_script("spec", "acme/app-spec", "docs/spec"), "git tracks docs/spec")
        self.assertEqual(self.gh_calls(), [])

    def test_a_folder_that_is_not_a_clone_of_the_repository_is_refused(self):
        (self.project / "docs/spec").mkdir(parents=True)
        self.refused(self.run_script("spec", "acme/app-spec", "docs/spec"), "is not a clone of acme/app-spec")
        git(self.project, "init", "-q", "-b", "main", "docs/spec")
        git(self.project / "docs/spec", "remote", "add", "origin", "https://github.com/acme/other.git")
        self.refused(self.run_script("spec", "acme/app-spec", "docs/spec"), "is not a clone of acme/app-spec")
        self.assertEqual(self.gh_calls(), [])

    def test_a_folder_outside_the_project_is_refused(self):
        for folder in ("/tmp/spec", "../spec"):
            with self.subTest(folder):
                self.refused(self.run_script("spec", "acme/app-spec", folder), "is not a folder of the project")
        self.assertEqual(self.gh_calls(), [])

    def test_a_clone_that_is_not_on_main_is_refused(self):
        result = self.run_script("spec", "acme/app-spec", "docs/spec", GH_BRANCH="trunk")
        self.refused(result, "a spec is published to main")
        self.assertEqual(self.ignored(), [])


class ADesignRepository(NewRepo):
    def test_it_is_created_private_and_nothing_else(self):
        result = self.run_script("design", "acme/app-design")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), [
            "repo view acme/app-design --json name",
            "repo create acme/app-design --private --add-readme",
        ])
        self.assertEqual(git(self.project, "status", "--porcelain"), "")
        self.assertIn('to add to .claude/daneel.json: "design-proposal": {"repo": "acme/app-design"}', result.stdout)

    def test_one_that_exists_is_left_as_it_is(self):
        Path(self.env["GH_EXISTS"]).touch()
        result = self.run_script("design", "acme/app-design")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), ["repo view acme/app-design --json name"])
        self.assertIn("present: the repository acme/app-design", result.stdout)


class WhatItRefuses(NewRepo):
    def test_the_project_itself(self):
        self.refused(self.run_script("design", "acme/app"), "acme/app is the project itself")
        self.refused(self.run_script("spec", "acme/app", "docs/spec"), "acme/app is the project itself")
        self.assertEqual(self.gh_calls(), [])

    def test_a_name_that_is_not_owner_and_name(self):
        self.refused(self.run_script("design", "app-design"), "is not <owner/name>")
        self.assertEqual(self.gh_calls(), [])

    def test_a_wrong_use_is_exit_2(self):
        for args in ((), ("spec", "acme/app-spec"), ("design",), ("design", "acme/app-design", "extra"), ("mocks", "acme/x")):
            with self.subTest(args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage: new-repo.sh", result.stderr)
        self.assertEqual(self.gh_calls(), [])


if __name__ == "__main__":
    unittest.main()
