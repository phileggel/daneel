"""Tests for the app plugin's scripts — run with `python3 -m unittest discover -s tests`."""

import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/app/scripts"


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def script(repo, name, *args):
    return subprocess.run(
        ["bash", str(SCRIPTS / name), *args], cwd=repo, capture_output=True, text=True
    )


class BranchFilesTest(unittest.TestCase):
    """`files` lists what the branch and the working tree changed, in the project of the
    working directory, narrowed by the lane's own expressions."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = Path(self.folder.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "README.md").write_text("x\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feat/x")
        (self.repo / "src").mkdir()
        (self.repo / "e2e").mkdir()
        (self.repo / "src" / "a.ts").write_text("a\n")
        (self.repo / "e2e" / "b.test.ts").write_text("b\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "work")
        (self.repo / "docs.md").write_text("untracked\n")

    def tearDown(self):
        self.folder.cleanup()

    def files(self, *args):
        result = script(self.repo, "branch.sh", "files", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.split()

    def test_the_branch_and_the_untracked_work_are_listed(self):
        self.assertEqual(self.files(), ["docs.md", "e2e/b.test.ts", "src/a.ts"])

    def test_a_lane_narrows_with_match_and_exclude(self):
        self.assertEqual(self.files("--match", r"\.ts$", "--exclude", "^e2e/"), ["src/a.ts"])

    def test_uncommitted_only_drops_the_branch(self):
        self.assertEqual(self.files("--uncommitted-only"), ["docs.md"])

    def test_an_unknown_filter_is_a_usage_error(self):
        self.assertEqual(script(self.repo, "branch.sh", "files", "--rust").returncode, 2)

    def test_log_takes_no_flags_since_some_write_files(self):
        self.assertEqual(script(self.repo, "branch.sh", "log", "--output=x").returncode, 2)
        self.assertIn("work", script(self.repo, "branch.sh", "log").stdout)


class ReviewPathTest(unittest.TestCase):
    """Each report of a day gets the next number, under the project's `.review/`."""

    def test_the_next_report_number_follows_the_last(self):
        with tempfile.TemporaryDirectory() as folder:
            first = script(folder, "review-path.sh", "reviewer-guides").stdout.strip()
            today = date.today().isoformat()
            self.assertEqual(first, f".review/reviewer-guides-{today}-01.md")
            (Path(folder) / first).write_text("report\n")
            second = script(folder, "review-path.sh", "reviewer-guides").stdout.strip()
            self.assertEqual(second, f".review/reviewer-guides-{today}-02.md")


if __name__ == "__main__":
    unittest.main()
