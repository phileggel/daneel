"""Tests for sandbox/snapshot.py: the same history on every build, a push that reaches only
the local `origin`, and an app no run changes. No test talks to a real remote."""

import contextlib
import hashlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "sandbox" / "snapshot.py"
SPEC = importlib.util.spec_from_file_location("snapshot", SCRIPT)
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


def git(folder: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=folder, env=snapshot.clean_env(), capture_output=True, text=True, check=True
    ).stdout.strip()


def app_state() -> str:
    """A digest of every file under the app but what is installed or built there."""
    digest = hashlib.sha256()
    for path in sorted(snapshot.APP.rglob("*")):
        inside = path.relative_to(snapshot.APP)
        if inside.parts[0] in ("node_modules", "target", "dist") or "target" in inside.parts:
            continue
        digest.update(str(inside).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class Restored(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = snapshot.restore(Path(self.temp.name) / "run", packages=False)
        self.work, self.origin = self.folder / "acme", self.folder / "origin.git"

    def tearDown(self):
        self.temp.cleanup()


class TheHistory(Restored):
    def test_two_builds_give_the_same_commit_ids(self):
        again = snapshot.restore(Path(self.temp.name) / "again", packages=False)
        first = git(self.work, "log", "--format=%H")
        self.assertEqual(first, git(again / "acme", "log", "--format=%H"))
        self.assertEqual(len(first.split()), len(snapshot.HISTORY))

    def test_the_ids_do_not_depend_on_the_machine_s_git_identity(self):
        with unittest.mock.patch.dict(os.environ, {
            "GIT_AUTHOR_NAME": "Someone Else", "GIT_COMMITTER_EMAIL": "else@example.com",
            "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+00:00",
        }):
            again = snapshot.restore(Path(self.temp.name) / "again", packages=False)
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), git(again / "acme", "rev-parse", "HEAD"))

    def test_every_commit_has_the_fixed_author_and_date(self):
        logged = git(self.work, "log", "--reverse", "--format=%an <%ae>|%aI|%cI|%s").splitlines()
        expected = [
            f"{snapshot.AUTHOR[0]} <{snapshot.AUTHOR[1]}>|{date}|{date}|{message}"
            for date, message, _ in ((d.replace("+00:00", "Z"), m, p) for d, m, p in snapshot.HISTORY)
        ]
        self.assertEqual(logged, expected)

    def test_the_copy_holds_the_app_s_files_and_no_other(self):
        tracked = git(self.work, "ls-files").splitlines()
        self.assertEqual(sorted(tracked), snapshot.app_files())
        for path in tracked:
            self.assertEqual((self.work / path).read_bytes(), (snapshot.APP / path).read_bytes(), path)
        self.assertFalse([path for path in tracked if path.startswith(("node_modules/", "src-tauri/target/"))])

    def test_the_copy_is_clean_on_main_and_tracks_origin(self):
        self.assertEqual(git(self.work, "status", "--porcelain"), "")
        self.assertEqual(git(self.work, "status", "-sb"), "## main...origin/main")
        self.assertEqual(git(self.origin, "rev-parse", "main"), git(self.work, "rev-parse", "HEAD"))

    def test_a_file_no_prefix_takes_goes_in_the_last_commit(self):
        planned = snapshot.commits(["justfile", "src-tauri/core/src/lib.rs", "src-tauri/build.rs", "new.txt"])
        self.assertEqual([own for _, _, own in planned],
                         [["justfile"], ["src-tauri/core/src/lib.rs"], ["src-tauri/build.rs"], ["new.txt"]])


class APush(Restored):
    def test_restore_pushes_main_to_the_local_origin_and_nothing_else(self):
        """The exact pushes of a build: one, of `main`, to the remote it has just pointed at
        the bare repository beside the copy."""
        ran = []
        real = snapshot.git

        def recording(folder, *args, **kwargs):
            ran.append(args)
            return real(folder, *args, **kwargs)

        with unittest.mock.patch.object(snapshot, "git", recording):
            folder = snapshot.restore(Path(self.temp.name) / "watched", packages=False)
        self.assertEqual([args for args in ran if args[0] == "push"], [("push", "-q", "-u", "origin", "main")])
        self.assertEqual([args for args in ran if args[0] == "remote"],
                         [("remote", "add", "origin", str(folder / "origin.git"))])
        self.assertLess(ran.index(("remote", "add", "origin", str(folder / "origin.git"))),
                        ran.index(("push", "-q", "-u", "origin", "main")))

    def test_the_only_remote_is_the_local_origin(self):
        self.assertEqual(git(self.work, "remote"), "origin")
        self.assertEqual(git(self.work, "remote", "get-url", "--all", "origin"), str(self.origin))
        self.assertEqual(git(self.work, "remote", "get-url", "--all", "--push", "origin"), str(self.origin))
        self.assertEqual(git(self.origin, "rev-parse", "--is-bare-repository"), "true")
        self.assertEqual(git(self.origin, "remote"), "")

    def test_a_pushed_branch_lands_in_the_local_origin(self):
        git(self.work, "checkout", "-q", "-b", "feat/x")
        (self.work / "note.txt").write_text("x\n", encoding="utf-8")
        git(self.work, "add", "note.txt")
        git(self.work, "commit", "-q", "-m", "feat: x")
        git(self.work, "push", "-q", "-u", "origin", "HEAD")
        self.assertEqual(git(self.origin, "rev-parse", "feat/x"), git(self.work, "rev-parse", "HEAD"))
        self.assertEqual(git(self.work, "log", "-1", "--format=%an <%ae>"),
                         f"{snapshot.RUNNER[0]} <{snapshot.RUNNER[1]}>")


class TheApp(unittest.TestCase):
    def test_a_run_leaves_it_unchanged(self):
        before = app_state()
        with tempfile.TemporaryDirectory() as temp:
            folder = snapshot.restore(Path(temp) / "run")
            work = folder / "acme"
            (work / "justfile").write_text("broken:\n", encoding="utf-8")
            (work / "src" / "main.tsx").unlink()
            (work / "added.txt").write_text("x\n", encoding="utf-8")
            git(work, "add", "-A")
            git(work, "commit", "-q", "-m", "chore: a run's work")
            git(work, "push", "-q", "origin", "main")
            snapshot.discard(folder)
            self.assertFalse(folder.exists())
        self.assertEqual(app_state(), before)

    def test_the_packages_are_a_copy_git_does_not_see(self):
        """A run that installs or removes a package changes its own copy, never the app's."""
        packages = snapshot.APP / "node_modules"
        if not packages.is_dir():
            self.skipTest("sandbox/acme/node_modules is not installed")
        before = sorted(path.name for path in packages.iterdir())
        with tempfile.TemporaryDirectory() as temp:
            work = snapshot.restore(Path(temp) / "run") / "acme"
            copied = work / "node_modules"
            self.assertFalse(copied.is_symlink())
            self.assertEqual(sorted(path.name for path in copied.iterdir()), before)
            self.assertEqual(git(work, "status", "--porcelain"), "")
            (copied / "installed-by-a-run").mkdir()
            (copied / "vitest" / "package.json").unlink()
        self.assertEqual(sorted(path.name for path in packages.iterdir()), before)
        self.assertTrue((packages / "vitest" / "package.json").is_file())


class Refusals(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_restore_refuses_a_folder_that_is_not_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "kept.txt").write_text("x\n", encoding="utf-8")
            done = self.run_script("restore", temp)
            self.assertEqual(done.returncode, 1)
            self.assertIn("is not empty", done.stderr)
            self.assertEqual([path.name for path in Path(temp).iterdir()], ["kept.txt"])

    def test_restore_refuses_a_folder_inside_the_app(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            snapshot.restore(snapshot.APP / "copy")
        self.assertEqual(stopped.exception.code, 1)
        self.assertFalse((snapshot.APP / "copy").exists())

    def test_discard_refuses_a_folder_restore_did_not_make(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "kept.txt").write_text("x\n", encoding="utf-8")
            done = self.run_script("discard", temp)
            self.assertEqual(done.returncode, 1)
            self.assertIn("nothing removed", done.stderr)
            self.assertTrue((Path(temp) / "kept.txt").exists())

    def test_the_command_line_restores_then_discards(self):
        with tempfile.TemporaryDirectory() as temp:
            done = self.run_script("restore", str(Path(temp) / "run"))
            self.assertEqual(done.returncode, 0, done.stderr)
            folder = Path(done.stdout.strip())
            self.assertTrue((folder / "acme" / "justfile").is_file())
            self.assertEqual(self.run_script("discard", str(folder)).returncode, 0)
            self.assertFalse(folder.exists())

    def test_wrong_arguments_exit_2(self):
        self.assertEqual(self.run_script("rebuild").returncode, 2)


if __name__ == "__main__":
    unittest.main()
