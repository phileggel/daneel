"""Tests for run-batch's release.py and batch-end.sh — run with `python3 -m unittest discover -s tests`.

No network, no tag or push outside a throwaway repository: git and gh are answered by mocks,
and batch-end.sh runs against a bare repository in a temporary folder.
"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/app/skills/run-batch/scripts"
SPEC = importlib.util.spec_from_file_location("release", SCRIPTS / "release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)

ROOT = Path(".")


def commits(*messages):
    return [release.parse_commit(message) for message in messages]


class Versions(unittest.TestCase):
    def test_only_a_feat_or_a_fix_is_released(self):
        self.assertIsNone(release.next_version("1.2.3", commits("chore: tidy", "docs: say it", "refactor!: rename")))

    def test_a_fix_moves_the_patch_a_feat_the_minor_a_breaking_one_the_major(self):
        self.assertEqual(release.next_version("1.2.3", commits("fix: a", "chore: b")), "1.2.4")
        self.assertEqual(release.next_version("1.2.3", commits("fix: a", "feat: b")), "1.3.0")
        self.assertEqual(release.next_version("1.2.3", commits("feat!: a", "fix: b")), "2.0.0")
        self.assertEqual(release.next_version("1.2.3", commits("fix: a\n\nBREAKING CHANGE: b")), "2.0.0")

    def test_a_title_is_its_first_line_and_a_scope_is_kept(self):
        commit = release.parse_commit("feat(transfer): move a holding\n\nRule TRF-012, backend only.")
        self.assertEqual((commit["type"], commit["scope"], commit["title"]), ("feat", "transfer", "move a holding"))
        self.assertEqual(release.parse_commit("Merge branch x")["type"], "other")


class Changelog(unittest.TestCase):
    def test_the_entry_lists_breaking_then_added_then_fixed_scope_first(self):
        entry = release.changelog_entry("2.0.0", "2026-10-25", commits(
            "feat(transfer): move a holding to another account",
            "fix: removing one line no longer deletes the whole",
            "chore: not a user's",
            "feat!: the export is one file",
        ))
        self.assertEqual(entry, (
            "## [2.0.0] - 2026-10-25\n\n"
            "### ⚠️ BREAKING CHANGES\n\n- the export is one file\n\n"
            "### Added\n\n- [transfer] move a holding to another account\n- the export is one file\n\n"
            "### Fixed\n\n- removing one line no longer deletes the whole\n\n"
        ))

    def test_the_entry_goes_above_the_newest_section_under_the_header(self):
        existing = "# Changelog\n\nIntro.\n\n## [1.0.0] - 2026-10-01\n\n### Fixed\n\n- old\n"
        entry = "## [1.0.1] - 2026-10-25\n\n### Fixed\n\n- new\n\n"
        self.assertEqual(release.changelog_with(existing, entry),
                         "# Changelog\n\nIntro.\n\n" + entry + "## [1.0.0] - 2026-10-01\n\n### Fixed\n\n- old\n")
        self.assertTrue(release.changelog_with(None, entry).startswith("# Changelog\n"))
        self.assertTrue(release.changelog_with(None, entry).endswith(entry))

    def test_the_notes_are_the_section_of_the_version(self):
        text = "# Changelog\n\n## [0.24.0] - d\n\n### Added\n\n- a\n\n## [0.23.0] - d\n\n### Fixed\n\n- b\n"
        self.assertEqual(release.notes(text, "v0.24.0"), "### Added\n\n- a")
        self.assertEqual(release.notes(text, "0.23.0"), "### Fixed\n\n- b")
        self.assertIsNone(release.notes(text, "v0.25.0"))
        self.assertIsNone(release.notes(text, "0.2"), "a prefix of a version is not that version")


class VersionFiles(unittest.TestCase):
    def test_the_lockfile_states_the_version_in_its_two_places_and_nothing_else_moves(self):
        lock = {"name": "app", "version": "0.0.0", "lockfileVersion": 3, "packages": {
            "": {"name": "app", "version": "0.0.0", "dependencies": {"é": "1.0.0"}},
            "node_modules/é": {"version": "1.0.0"},
        }}
        written = release.with_version("package-lock.json", json.dumps(lock, indent=2, ensure_ascii=False) + "\n", "0.4.0")
        lock["version"] = lock["packages"][""]["version"] = "0.4.0"
        self.assertEqual(written, json.dumps(lock, indent=2, ensure_ascii=False) + "\n")

    def test_a_lockfile_of_another_shape_is_not_rewritten(self):
        with self.assertRaises(release.Stop):
            release.with_version("package-lock.json", '{"version": "1.0.0"}', "1.1.0")

    def test_a_json_file_states_its_top_level_version(self):
        text = '{\n  "productName": "App",\n  "version": "1.0.0",\n  "app": {"version": "x"}\n}\n'
        self.assertEqual(json.loads(release.with_version("src-tauri/tauri.conf.json", text, "1.1.0"))["version"], "1.1.0")

    def test_a_json_file_keeps_its_indent(self):
        text = '{\n    "name": "a",\n    "version": "1.0.0"\n}\n'
        self.assertEqual(release.with_version("tauri.conf.json", text, "1.1.0"), text.replace("1.0.0", "1.1.0"))
        self.assertEqual(release.read_version("package.json", '{"version": "3.2.1"}'), "3.2.1")

    def test_cargo_moves_the_package_version_alone(self):
        text = ('[package]\nname = "app"\nauthors = ["me"]\nrust-version = "1.80"\nversion = "1.0.0"\n\n'
                '[dependencies]\nserde = { version = "1.0.0" }\n[dependencies.x]\nversion = "1.0.0"\n')
        written = release.with_version("src-tauri/Cargo.toml", text, "1.1.0")
        self.assertEqual(written, text.replace('version = "1.0.0"\n\n', 'version = "1.1.0"\n\n', 1))
        self.assertEqual(release.read_version("Cargo.toml", text), "1.0.0")
        with self.assertRaises(release.Stop):
            release.with_version("Cargo.toml", '[workspace]\nversion = "1.0.0"\n', "1.1.0")

    def test_an_unknown_file_or_setting_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / ".claude").mkdir()
            settings = Path(folder) / ".claude" / "daneel.json"
            settings.write_text(json.dumps({"run-batch": {"version_files": ["VERSION"]}}))
            with self.assertRaises(SystemExit):
                release.load_settings(Path(folder))
            settings.write_text(json.dumps({"run-batch": {"changelog_path": "x"}}))
            with self.assertRaises(SystemExit):
                release.load_settings(Path(folder))
            settings.write_text(json.dumps({"run-batch": {"changelog": "docs/CHANGES.md", "release_check": "release-check"}}))
            loaded = release.load_settings(Path(folder))
            self.assertEqual((loaded["changelog"], loaded["version_files"]), ("docs/CHANGES.md", ["package.json"]))


def run_record(name, status="completed", conclusion="success", run_id=1):
    return {"name": name, "status": status, "conclusion": conclusion, "id": run_id,
            "html_url": f"https://example.invalid/runs/{run_id}"}


class Runs(unittest.TestCase):
    def test_green_runs_are_no_obstacle(self):
        self.assertEqual(release.runs_in_the_way([run_record("Quality"), run_record("E2E", conclusion="skipped", run_id=2)]), [])

    def test_an_unfinished_or_failed_run_is_named(self):
        obstacles = release.runs_in_the_way([
            run_record("Quality", status="in_progress", conclusion=None), run_record("E2E", conclusion="failure", run_id=2)])
        self.assertEqual(len(obstacles), 2)
        self.assertIn("E2E: failure", obstacles[0])
        self.assertIn("Quality: not finished (in_progress)", obstacles[1])

    def test_the_newest_run_of_a_workflow_counts_and_none_at_all_is_an_obstacle(self):
        self.assertEqual(release.runs_in_the_way([run_record("E2E", conclusion="failure", run_id=2), run_record("E2E", run_id=7)]), [])
        self.assertEqual(len(release.runs_in_the_way([run_record("E2E", run_id=2), run_record("E2E", conclusion="cancelled", run_id=7)])), 1)
        self.assertEqual(len(release.runs_in_the_way([])), 1)

    def test_checks_are_pending_until_listed_and_all_ended(self):
        self.assertEqual(release.checks_verdict([])[0], "pending")
        self.assertEqual(release.checks_verdict([{"bucket": "pass"}, {"bucket": "pending"}])[0], "pending")
        self.assertEqual(release.checks_verdict([{"bucket": "pass"}, {"bucket": "skipping"}])[0], "green")
        self.assertEqual(release.checks_verdict([{"name": "Quality", "bucket": "pass"}], ["Quality", "Review"])[0], "pending")
        self.assertEqual(release.checks_verdict([{"name": "Quality", "bucket": "pass"}], ["Quality"])[0], "green")
        verdict, failed = release.checks_verdict([{"name": "Quality", "bucket": "fail", "link": "l"}, {"bucket": "pending"}])
        self.assertEqual((verdict, len(failed)), ("red", 1))


class GitHub:
    """Answers each command as git and gh would; records them in order."""

    def __init__(self, **answers):
        self.ran, self.answers = [], answers

    def __call__(self, command, **_):
        command = [str(part) for part in command]
        self.ran.append(command)
        for prefix, (code, out) in self.answers.items():
            if " ".join(command).startswith(prefix):
                return subprocess.CompletedProcess(command, code, stdout=out, stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def did(self, *start):
        return any(command[: len(start)] == list(start) for command in self.ran)


def main_head(**more):
    return GitHub(**{
        "git rev-parse --abbrev-ref": (0, "main\n"),
        "git rev-parse": (0, "abc123\n"),
        "gh api": (0, json.dumps({"workflow_runs": [run_record("Quality")]})),
        **more,
    })


class FreshMain(unittest.TestCase):
    def test_a_clean_fresh_main_whose_runs_are_green_passes(self):
        github = main_head()
        with mock.patch.object(release.subprocess, "run", side_effect=github):
            release.fresh_main(ROOT)
        self.assertIn("repos/{owner}/{repo}/actions/runs?head_sha=abc123&per_page=100", github.ran[-1])

    def test_another_branch_a_dirty_tree_or_a_red_run_stops_it(self):
        for answers in (
            {"git rev-parse --abbrev-ref": (0, "fix/x\n")},
            {"git status": (0, " M CHANGELOG.md\n")},
            {"gh api": (0, json.dumps({"workflow_runs": [run_record("Quality", conclusion="failure")]}))},
            {"gh api": (0, "not json")},
            {"gh api": (1, "")},
        ):
            with mock.patch.object(release.subprocess, "run", side_effect=main_head(**answers)):
                with self.assertRaises(release.Stop):
                    release.fresh_main(ROOT)

    def test_a_main_behind_origin_stops_it(self):
        heads = iter(["abc\n", "def\n"])
        def answer(command, **_):
            if command[:2] == ["git", "rev-parse"] and "--abbrev-ref" not in command:
                return subprocess.CompletedProcess(command, 0, stdout=next(heads), stderr="")
            return main_head()(command)
        with mock.patch.object(release.subprocess, "run", side_effect=answer):
            with self.assertRaises(release.Stop):
                release.fresh_main(ROOT)


class ThroughAPullRequest(unittest.TestCase):
    def github(self, checks="pass", landed="chore: release v0.12.0", same_tree=0):
        return GitHub(**{
            "git rev-parse": (0, "abc123\n"),
            "gh pr create": (0, "https://github.com/o/r/pull/42\n"),
            "gh pr checks": (0, json.dumps([{"name": "Quality", "bucket": checks, "link": "l"}])),
            "git log -1": (0, landed + "\n"),
            "git diff --quiet": (same_tree, ""),
        })

    def land(self, github):
        with mock.patch.object(release.subprocess, "run", side_effect=github), contextlib.redirect_stdout(io.StringIO()):
            release.land(ROOT, "0.12.0", ["package.json", "CHANGELOG.md"])

    def test_the_release_lands_through_its_pull_request_then_is_tagged(self):
        github = self.github()
        self.land(github)
        self.assertIn(["gh", "pr", "merge", "42", "--rebase", "--match-head-commit", "abc123"], github.ran)
        steps = [command[:3] for command in github.ran]
        self.assertLess(steps.index(["gh", "pr", "merge"]), steps.index(["git", "tag", "-a"]))
        self.assertIn(["git", "tag", "-a", "v0.12.0", "-m", "Version 0.12.0", "main"], github.ran)
        self.assertIn(["git", "push", "--quiet", "origin", "refs/tags/v0.12.0"], github.ran)
        self.assertFalse(any(c[:2] == ["git", "push"] and "main" in c for c in github.ran), "nothing is pushed to main")
        self.assertFalse(any("--no-verify" in c for c in github.ran), "no hook is bypassed")
        self.assertFalse(github.did("gh", "release"), "landing makes no release")

    def test_a_release_whose_checks_fail_is_neither_merged_nor_tagged(self):
        github = self.github(checks="fail")
        with self.assertRaises(release.Stop):
            self.land(github)
        self.assertFalse(github.did("gh", "pr", "merge"))
        self.assertFalse(github.did("git", "tag"))

    def test_a_main_head_other_than_the_release_commit_is_not_tagged(self):
        for github in (self.github(landed="fix: someone else"), self.github(same_tree=1)):
            with self.assertRaises(release.Stop):
                self.land(github)
            self.assertFalse(github.did("git", "tag"))

    def test_pending_checks_are_waited_for(self):
        answers = iter(["[]", json.dumps([{"bucket": "pending"}]), json.dumps([{"bucket": "pass"}])])
        def answer(command, **_):
            out = next(answers) if command[:3] == ["gh", "pr", "checks"] else ""
            return subprocess.CompletedProcess(command, 0, stdout=out, stderr="")
        with mock.patch.object(release.subprocess, "run", side_effect=answer), \
                mock.patch.object(release, "sleep") as slept:
            release.wait_for_checks(ROOT, "42")
        self.assertEqual(slept.call_count, 2)


class Draft(unittest.TestCase):
    def project(self, folder, workflow=None):
        root = Path(folder)
        (root / "CHANGELOG.md").write_text("# Changelog\n\n## [1.1.0] - d\n\n### Added\n\n- a\n")
        return root, {**release.SETTINGS, "release_workflow": workflow}

    def draft(self, root, settings, github):
        with mock.patch.object(release.subprocess, "run", side_effect=github), \
                mock.patch.object(release, "sleep"), contextlib.redirect_stdout(io.StringIO()) as said:
            release.draft(root, settings, "v1.1.0")
        return said.getvalue()

    def test_without_a_workflow_the_draft_is_made_here_never_published(self):
        with tempfile.TemporaryDirectory() as folder:
            root, settings = self.project(folder)
            github = GitHub(**{"gh release create": (0, "https://github.com/o/r/releases/v1.1.0\n")})
            said = self.draft(root, settings, github)
        create = next(c for c in github.ran if c[:3] == ["gh", "release", "create"])
        self.assertIn("--draft", create)
        self.assertIn("Everything is made but the publishing", said)
        self.assertFalse(any("--draft=false" in c or "publish" in " ".join(c) for c in github.ran))

    def test_with_a_workflow_its_draft_gets_the_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            root, settings = self.project(folder, workflow="release.yml")
            github = GitHub(**{
                "gh run list": (0, json.dumps([{"databaseId": 9, "status": "completed", "conclusion": "success", "url": "u"}])),
                "gh release view": (0, json.dumps({"isDraft": True, "url": "r"})),
            })
            said = self.draft(root, settings, github)
        self.assertIn(["gh", "run", "list", "--workflow", "release.yml", "--branch", "v1.1.0"], [c[:7] for c in github.ran])
        self.assertTrue(github.did("gh", "release", "edit", "v1.1.0", "--notes-file"))
        self.assertFalse(github.did("gh", "release", "create"))
        self.assertIn("run u", said)

    def test_a_failed_workflow_or_a_published_release_stops_it(self):
        failed = [{"databaseId": 9, "status": "completed", "conclusion": "failure", "url": "u"}]
        done = [{"databaseId": 9, "status": "completed", "conclusion": "success", "url": "u"}]
        for github in (
            GitHub(**{"gh run list": (0, json.dumps(failed))}),
            GitHub(**{"gh run list": (0, json.dumps(done)), "gh release view": (0, json.dumps({"isDraft": False}))}),
        ):
            with tempfile.TemporaryDirectory() as folder:
                root, settings = self.project(folder, workflow="release.yml")
                with self.assertRaises(release.Stop):
                    self.draft(root, settings, github)
            self.assertFalse(github.did("gh", "release", "edit"))


class Main(unittest.TestCase):
    def test_nothing_to_release_exits_3_and_changes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "package.json").write_text('{"version": "1.0.0"}')
            github = GitHub(**{"git describe": (0, "v1.0.0\n"), "git log": (0, "chore: a\x00docs: b\x00")})
            with mock.patch.object(release, "project_root", return_value=Path(folder)), \
                    mock.patch.object(release.subprocess, "run", side_effect=github), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(release.main(["--preview"]), 3)
        self.assertIn(["git", "describe", "--tags", "--abbrev=0", "--match", "v*"], github.ran)
        self.assertFalse(github.did("git", "fetch"), "a preview is read-only")

    def test_a_preview_names_the_next_version(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "package.json").write_text('{"version": "1.0.0"}')
            github = GitHub(**{"git describe": (1, ""), "git log": (0, "feat: a\x00")})
            with mock.patch.object(release, "project_root", return_value=Path(folder)), \
                    mock.patch.object(release.subprocess, "run", side_effect=github), \
                    contextlib.redirect_stdout(io.StringIO()) as said:
                self.assertEqual(release.main(["--preview"]), 0)
        self.assertIn("1.0.0 → 1.1.0", said.getvalue())
        self.assertIn(["git", "log", "HEAD", "--format=%B%x00"], github.ran)


class BatchEnd(unittest.TestCase):
    """batch-end.sh against a bare repository in a temporary folder: nothing real is tagged."""

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=self.env)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        base = Path(self.folder.name)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t"}
        self.origin, self.work = base / "origin.git", base / "work"
        self.git(base, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.git(base, "clone", "-q", str(self.origin), str(self.work))
        self.git(self.work, "switch", "-q", "-c", "main")
        self.git(self.work, "commit", "-q", "--allow-empty", "-m", "chore: start")
        self.git(self.work, "push", "-q", "origin", "main")

    def tearDown(self):
        self.folder.cleanup()

    def batch_end(self):
        return subprocess.run(["bash", str(SCRIPTS / "batch-end.sh")], cwd=self.work, capture_output=True, text=True, env=self.env)

    def test_a_fresh_main_is_tagged_once_per_commit(self):
        self.assertEqual(self.batch_end().returncode, 0)
        tags = self.git(self.origin, "tag").stdout.split()
        self.assertEqual(len(tags), 1)
        self.assertTrue(tags[0].startswith("batch/"))
        again = self.batch_end()
        self.assertEqual(again.returncode, 1)
        self.assertIn("already ends a batch", again.stderr)

    def test_a_second_batch_the_same_day_gets_its_own_tag(self):
        self.assertEqual(self.batch_end().returncode, 0)
        self.git(self.work, "commit", "-q", "--allow-empty", "-m", "chore: next")
        self.git(self.work, "push", "-q", "origin", "main")
        self.assertEqual(self.batch_end().returncode, 0)
        tags = sorted(self.git(self.origin, "tag").stdout.split())
        self.assertEqual(len(tags), 2)
        self.assertTrue(tags[1].endswith(".2"))

    def test_a_main_ahead_of_origin_is_not_tagged(self):
        self.git(self.work, "commit", "-q", "--allow-empty", "-m", "chore: local")
        self.assertEqual(self.batch_end().returncode, 1)
        self.assertEqual(self.git(self.origin, "tag").stdout, "")


if __name__ == "__main__":
    unittest.main()
