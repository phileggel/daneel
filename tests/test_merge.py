"""Tests for run-entry's merge.py — one entry lands as one commit — run with `python3 -m unittest discover -s tests`."""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "merge", Path(__file__).resolve().parents[1] / "plugins/app/skills/run-entry/scripts/merge.py"
)
merge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge)

# Git hooks run with GIT_DIR (and GIT_INDEX_FILE, GIT_WORK_TREE…) set, and the
# hooks may run these tests. Every `git` below — the
# helpers here and merge.py's own calls — would then act on the real repository
# instead of the throwaway one. The variables are removed while this module runs.
_SAVED_GIT_ENV: dict[str, str] = {}


def setUpModule():
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        _SAVED_GIT_ENV[key] = os.environ.pop(key)


def tearDownModule():
    os.environ.update(_SAVED_GIT_ENV)


RECORDS = ["docs/adr/", "docs/plan/", "docs/lessons.md"]


class NoRealRepository(unittest.TestCase):
    def test_no_git_variable_reaches_the_tests(self):
        self.assertEqual([k for k in os.environ if k.startswith("GIT_")], [])


class FoldingFixups(unittest.TestCase):
    """A repository with `main` and a checked-out `work` branch, in a temporary folder."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.previous = os.getcwd()
        self.addCleanup(os.chdir, self.previous)
        os.chdir(self.folder.name)
        self.run_git("init", "--quiet", "--initial-branch", "main")
        self.run_git("config", "user.name", "test")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "core.hooksPath", os.devnull)
        self.commit("chore: start", {"README.md": "start\n"})
        self.run_git("checkout", "--quiet", "-b", "work")

    def run_git(self, *args):
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, title, files):
        for name, content in files.items():
            path = Path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.run_git("add", "--all")
        self.run_git("commit", "--quiet", "-m", title)
        return self.run_git("rev-parse", "HEAD")

    def titles(self):
        return self.run_git("log", "--format=%s", "main..work").splitlines()

    def test_a_fixup_is_folded_into_the_commit_it_names_and_the_tree_is_unchanged(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        tested = self.commit("fixup! feat: show the total", {"total.txt": "total, fixed\n"})

        result = merge.rebase_folding_fixups("main")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.titles(), ["feat: show the total"])
        self.assertEqual(Path("total.txt").read_text(encoding="utf-8"), "total, fixed\n")
        self.assertEqual(merge._fold_commits("main", "work"), [])
        self.assertTrue(merge._rebase_left_the_checks_standing(tested, self.run_git("rev-parse", "HEAD"), RECORDS))

    def test_a_fixup_is_folded_when_the_target_moved_too(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        self.commit("fixup! feat: show the total", {"total.txt": "total, fixed\n"})
        self.run_git("checkout", "--quiet", "main")
        self.commit("docs: record a decision", {"docs/adr/009-a-decision.md": "x\n"})
        self.run_git("checkout", "--quiet", "work")

        result = merge.rebase_folding_fixups("main")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.titles(), ["feat: show the total"])
        self.assertTrue(Path("docs/adr/009-a-decision.md").exists())

    def test_a_fixup_that_names_no_commit_is_refused_and_the_branch_goes_back(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        before = self.commit("fixup! feat: something else", {"other.txt": "other\n"})
        self.run_git("checkout", "--quiet", "main")
        self.commit("docs: record a decision", {"docs/adr/009-a-decision.md": "x\n"})
        self.run_git("checkout", "--quiet", "work")
        self.assertEqual(merge.rebase_folding_fixups("main").returncode, 0)
        self.assertNotEqual(self.run_git("rev-parse", "HEAD"), before)

        with self.assertRaises(SystemExit):
            merge.refuse_unfolded_fixups("main", "work", before)

        self.assertEqual(self.run_git("rev-parse", "HEAD"), before)

    def test_a_branch_whose_fixups_were_folded_is_not_refused(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        before = self.commit("fixup! feat: show the total", {"total.txt": "total, fixed\n"})
        merge.rebase_folding_fixups("main")

        merge.refuse_unfolded_fixups("main", "work", before)

        self.assertEqual(self.titles(), ["feat: show the total"])

    def test_squash_and_amend_commits_are_refused_before_the_rebase(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        self.commit("squash! feat: show the total", {"a.txt": "a\n"})
        head = self.commit("amend! feat: show the total", {"b.txt": "b\n"})

        with self.assertRaises(SystemExit):
            merge.refuse_unreadable_folds("main", "work")

        self.assertEqual(self.run_git("rev-parse", "HEAD"), head)

    def test_fixup_commits_alone_pass_the_check_before_the_rebase(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        self.commit("fixup! feat: show the total", {"total.txt": "total, fixed\n"})

        merge.refuse_unreadable_folds("main", "work")

    def test_the_checks_stand_for_record_files_and_fall_for_anything_else(self):
        tested = self.commit("feat: show the total", {"total.txt": "total\n"})
        records = self.commit(
            "docs: record a decision",
            {"docs/adr/001-a-decision.md": "x\n", "docs/lessons.md": "learned\n", "docs/plan/a-plan.md": "x\n"},
        )
        code = self.commit("fix: the total", {"total.txt": "other\n"})

        self.assertTrue(merge._rebase_left_the_checks_standing(tested, tested, RECORDS))
        self.assertTrue(merge._rebase_left_the_checks_standing(tested, records, RECORDS))
        self.assertFalse(merge._rebase_left_the_checks_standing(tested, code, RECORDS))
        # The default names the ADRs alone: a lesson re-runs the checks.
        self.assertFalse(merge._rebase_left_the_checks_standing(tested, records, merge.SETTINGS["record_paths"]))

    def test_a_branch_without_fixups_is_rebased_by_github(self):
        before = self.commit("feat: show the total", {"total.txt": "total\n"})

        self.assertEqual(merge.merge_method("main", before, "work"), ["--rebase"])

    def test_a_branch_whose_fixups_were_folded_is_squashed_under_its_commit(self):
        self.run_git("commit", "--quiet", "--allow-empty", "-m", "feat: show the total", "-m", "Closes #401.")
        before = self.commit("fixup! feat: show the total", {"total.txt": "fixed\n"})
        merge.rebase_folding_fixups("main")

        self.assertEqual(
            merge.merge_method("main", before, "work"),
            [
                "--squash", "--subject", "feat: show the total", "--body", "Closes #401.",
                "--author-email", "test@example.invalid",
            ],
        )

    def test_fixups_folded_into_two_commits_are_refused(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        self.commit("docs: say so", {"docs.md": "docs\n"})
        before = self.commit("fixup! feat: show the total", {"total.txt": "fixed\n"})
        merge.rebase_folding_fixups("main")

        with self.assertRaises(SystemExit):
            merge.merge_method("main", before, "work")

    # GitHub refused the squash, and the folded branch stayed, refused at the next run.
    def test_a_stop_that_pushed_nothing_puts_the_branch_back(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        before = self.commit("fixup! feat: show the total", {"total.txt": "fixed\n"})
        merge.rebase_folding_fixups("main")
        self.assertNotEqual(self.run_git("rev-parse", "HEAD"), before)

        merge.restore_unpushed("work", before)

        self.assertEqual(self.run_git("rev-parse", "HEAD"), before)

    def test_a_branch_the_stop_pushed_stays_as_pushed(self):
        self.commit("feat: show the total", {"total.txt": "total\n"})
        before = self.commit("fixup! feat: show the total", {"total.txt": "fixed\n"})
        merge.rebase_folding_fixups("main")
        folded = self.run_git("rev-parse", "HEAD")
        self.run_git("update-ref", "refs/remotes/origin/work", folded)

        merge.restore_unpushed("work", before)

        self.assertEqual(self.run_git("rev-parse", "HEAD"), folded)


class ChecksGreen(unittest.TestCase):
    """`ensure_checks_green` on a pull request whose head is the commit about to land."""

    REQUIRED = ["PR checks", "Frontend", "Backend"]

    def guard(self, runs):
        with (
            unittest.mock.patch.object(merge, "_open_pull_request", return_value=(7, "abc1234")),
            unittest.mock.patch.object(merge, "_required_checks", return_value=self.REQUIRED),
            unittest.mock.patch.object(merge, "_check_runs", return_value=runs),
            unittest.mock.patch.object(merge, "_reviewer_notes", return_value={}),
        ):
            merge.ensure_checks_green("work", "main", "abc1234", "abc1234", merge.SETTINGS)

    def green(self):
        return {name: ("completed", "success") for name in self.REQUIRED}

    def test_every_required_check_green_lets_the_merge_through(self):
        self.guard(self.green())

    def test_a_missing_required_check_refuses(self):
        runs = self.green()
        del runs["Backend"]
        with self.assertRaises(SystemExit):
            self.guard(runs)

    def test_a_pending_check_refuses(self):
        runs = self.green()
        runs["Backend"] = ("in_progress", "")
        with self.assertRaises(SystemExit):
            self.guard(runs)

    def test_a_failed_optional_check_refuses(self):
        runs = self.green()
        runs["Codec"] = ("completed", "failure")
        with self.assertRaises(SystemExit):
            self.guard(runs)


class DeletingTheRemoteBranch(unittest.TestCase):
    """`delete_remote_branch` against a bare repository standing in for origin."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        root = Path(self.folder.name)
        self.origin = root / "origin.git"
        self.run_git("init", "--quiet", "--bare", str(self.origin))
        os.chdir(root)
        self.run_git("init", "--quiet", "--initial-branch", "main", "work")
        os.chdir(root / "work")
        self.run_git("config", "user.name", "test")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "core.hooksPath", os.devnull)
        self.run_git("remote", "add", "origin", str(self.origin))
        self.run_git("commit", "--quiet", "--allow-empty", "-m", "chore: start")
        self.run_git("push", "--quiet", "origin", "main:main", "main:feature")

    def run_git(self, *args):
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()

    def test_an_existing_branch_is_deleted(self):
        self.assertEqual(merge.delete_remote_branch("feature"), "deleted")

    def test_a_branch_the_remote_already_deleted_is_gone_not_failed(self):
        subprocess.run(["git", "--git-dir", str(self.origin), "branch", "-D", "feature"], check=True, capture_output=True)
        self.assertEqual(merge.delete_remote_branch("feature"), "gone")

    def test_a_refused_delete_that_leaves_the_branch_fails(self):
        hook = self.origin / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'protected' >&2\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(merge.delete_remote_branch("feature"), "failed")


class Worktrees(unittest.TestCase):
    LISTING = (
        "worktree /home/me/project\nHEAD 1111\nbranch refs/heads/main\n\n"
        "worktree /home/me/project-docs\nHEAD 2222\nbranch refs/heads/docs/notes\n\n"
        "worktree /home/me/project-detached\nHEAD 3333\ndetached\n"
    )

    # From a worktree, the target is held by the main folder: named, so the
    # refusal can say where to merge from.
    def test_the_folder_holding_the_target_is_found_from_another_worktree(self):
        self.assertEqual(
            merge.worktree_holding("main", self.LISTING, "/home/me/project-docs"),
            "/home/me/project",
        )

    # From the folder that holds the target itself, nothing is in the way.
    def test_the_folder_that_holds_the_target_is_not_in_its_own_way(self):
        self.assertIsNone(merge.worktree_holding("main", self.LISTING, "/home/me/project"))
        self.assertIsNone(merge.worktree_holding("release", self.LISTING, "/home/me/project"))

    # A branch whose name ends like the target is not the target.
    def test_a_branch_named_alike_is_not_the_target(self):
        listing = "worktree /w\nHEAD 1\nbranch refs/heads/not-main\n"
        self.assertIsNone(merge.worktree_holding("main", listing, "/elsewhere"))


class ReviewerNotes(unittest.TestCase):
    # A reviewer that did not run says so in its sticky comment's heading; the
    # refusal repeats it, so a red check is not read as a finding.
    def test_a_reviewer_that_did_not_run_is_told_apart_from_a_finding(self):
        comments = [
            "<!-- e2e-screenshots -->\n## E2E screenshots — success\n",
            "<!-- review:arch -->\n## reviewer-arch — did not run (usage limit)\n\nRe-run…",
            "<!-- review:infra -->\n## reviewer-infra — no report\n\nThe reviewer produced…",
            "<!-- review:backend -->\n## reviewer-backend — 3 files reviewed\n\n🔴 1 critical",
        ]
        self.assertEqual(
            merge.reviewer_heading(comments, "reviewer-arch"),
            "did not run (usage limit)",
        )
        self.assertEqual(
            merge.reviewer_heading(comments, "reviewer-infra"), "no report"
        )
        # A real report's heading is not a note about the run: nothing is added.
        self.assertIsNone(merge.reviewer_heading(comments, "reviewer-backend"))
        # A lane with no comment yet.
        self.assertIsNone(merge.reviewer_heading(comments, "reviewer-sql"))

    # A lane writes one comment per round: the newest one is read.
    def test_the_newest_round_s_comment_is_the_one_read(self):
        comments = [
            "<!-- review:arch -->\n## reviewer-arch — no report\n",
            "<!-- review:arch -->\n## reviewer-arch — 2 files reviewed\n",
        ]
        self.assertIsNone(merge.reviewer_heading(comments, "reviewer-arch"))
        self.assertEqual(merge.reviewer_heading(comments[::-1], "reviewer-arch"), "no report")


class Settings(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def write(self, data):
        (self.root / ".claude").mkdir(exist_ok=True)
        (self.root / ".claude" / "daneel.json").write_text(json.dumps(data), encoding="utf-8")

    def test_a_project_without_the_file_takes_the_defaults(self):
        self.assertEqual(merge.settings(self.root), merge.SETTINGS)

    def test_a_project_sets_its_own_keys_and_the_others_are_left_to_their_skills(self):
        self.write({"run-entry": {"record_paths": ["docs/"], "lanes": "bash x.sh"}, "flow-audit": {"x": 1}})
        self.assertEqual(merge.settings(self.root), {"record_paths": ["docs/"]})


if __name__ == "__main__":
    unittest.main()
