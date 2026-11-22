"""The two publish.sh: design-proposal's sends the mocks to the design repository or a
`design/<id>` branch, never the project's `main`, and never with the console-errors file;
spec-proposal's sends an accepted spec change to the spec repository's `main`."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "plugins/app/skills"
SCRIPT = SKILLS / "design-proposal/scripts/publish.sh"
SPEC_SCRIPT = SKILLS / "spec-proposal/scripts/publish.sh"


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def publish(cwd, *args):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)


class Repos(unittest.TestCase):
    """A project and a second repository beside it, each pushing to a local bare one."""

    SECOND = ("design", "https://github.com/acme/design.git")

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.top = Path(folder.name)
        self.project = self.repo("project", "https://github.com/acme/app.git")
        self.clone = self.repo(*self.SECOND)

    def repo(self, name, url):
        """A checkout on `main` whose origin reads as `url` and pushes to a local bare repository."""
        bare = self.top / f"{name}.git"
        git(self.top, "init", "-q", "--bare", "-b", "main", str(bare))
        path = self.top / name
        git(self.top, "init", "-q", "-b", "main", str(path))
        git(path, "config", "user.email", "t@example.com")
        git(path, "config", "user.name", "t")
        git(path, "config", f"url.{bare}.insteadOf", url)
        git(path, "remote", "add", "origin", url)
        git(path, "commit", "-q", "--allow-empty", "-m", "start")
        git(path, "push", "-q", "origin", "main")
        self.bare = getattr(self, "bare", {})
        self.bare[name] = bare
        return path

    def pushed(self, name, ref):
        return git(self.bare[name], "ls-tree", "-r", "--name-only", ref).splitlines()


class Publish(Repos):
    def mocks(self, folder):
        folder.mkdir(parents=True)
        (folder / "ORD-1-light-idle.png").write_bytes(b"png")
        (folder / ".console-errors.json").write_text("[]")

    def test_repo_pushes_the_clone_s_main_without_the_console_errors(self):
        self.mocks(self.clone / "ORD-1")
        result = publish(self.project, "repo", "acme/design", str(self.clone), "ORD-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.pushed("design", "main"), ["ORD-1/ORD-1-light-idle.png"])
        self.assertEqual(result.stdout.strip(), git(self.bare["design"], "rev-parse", "main"))

    def test_repo_refuses_a_clone_of_another_repository(self):
        self.mocks(self.clone / "ORD-1")
        result = publish(self.project, "repo", "acme/other", str(self.clone), "ORD-1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.pushed("design", "main"), [])

    def test_repo_refuses_the_project_itself(self):
        self.mocks(self.project / "ORD-1")
        result = publish(self.project, "repo", "acme/app", str(self.project), "ORD-1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.pushed("project", "main"), [])

    def test_branch_pushes_design_id_and_returns_to_main(self):
        self.mocks(self.project / "screenshots/design")
        result = publish(self.project, "branch", "ORD-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.pushed("project", "design/ORD-1"), ["screenshots/design/ORD-1-light-idle.png"])
        self.assertEqual(self.pushed("project", "main"), [])
        self.assertEqual(git(self.project, "branch", "--show-current"), "main")

    def test_branch_refuses_to_start_off_main(self):
        git(self.project, "switch", "-q", "-c", "feat/ORD-2")
        self.mocks(self.project / "screenshots/design")
        self.assertEqual(publish(self.project, "branch", "ORD-1").returncode, 1)


class SpecPublish(Repos):
    """An accepted spec change reaches the spec repository's `main`, and only there."""

    SECOND = ("spec", "https://github.com/acme/app-spec.git")

    def setUp(self):
        super().setUp()
        (self.clone / "orders.md").write_text("ORD-010 — an order has a customer\n")
        git(self.clone, "add", ".")
        git(self.clone, "commit", "-qm", "the spec so far")
        git(self.clone, "push", "-q", "origin", "main")
        # Every git command the script runs is recorded, then run for real.
        self.calls = self.top / "calls.jsonl"
        shim = self.top / "bin" / "git"
        shim.parent.mkdir()
        shim.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            f"open({str(self.calls)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
            f"os.execv({shutil.which('git')!r}, ['git'] + sys.argv[1:])\n", encoding="utf-8")
        shim.chmod(0o755)

    def change(self):
        (self.clone / "orders.md").write_text("ORD-010 — an order has a customer\nORD-020 — a paid order is never deleted\n")
        (self.clone / "refunds.md").write_text("RFD-010 — a refund names its order\n")

    def publish(self, repo, clone, ident, cwd=None):
        env = dict(os.environ, PATH=f"{self.top / 'bin'}{os.pathsep}{os.environ['PATH']}")
        return subprocess.run(["bash", str(SPEC_SCRIPT), repo, str(clone), ident],
                              cwd=cwd or self.project, capture_output=True, text=True, env=env)

    def commands(self):
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_it_commits_every_change_and_pushes_the_spec_repository_s_main(self):
        self.change()
        result = self.publish("acme/app-spec", self.clone, "12")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.pushed("spec", "main"), ["orders.md", "refunds.md"])
        self.assertEqual(result.stdout.strip(), git(self.bare["spec"], "rev-parse", "main"))
        self.assertEqual(git(self.bare["spec"], "log", "-1", "--format=%s", "main"), "spec: acme/app#12")
        clone = str(self.clone)
        self.assertEqual(self.commands()[-4:], [
            ["-C", clone, "add", "-A"],
            ["-C", clone, "commit", "-q", "-m", "spec: acme/app#12"],
            ["-C", clone, "push", "-q", "origin", "main"],
            ["-C", clone, "rev-parse", "HEAD"],
        ])
        # The project took no commit and no push.
        self.assertEqual(self.pushed("project", "main"), [])
        self.assertEqual(git(self.project, "log", "--format=%s"), "start")

    def test_a_chat_request_s_slug_is_the_commit_s_name(self):
        self.change()
        self.assertEqual(self.publish("acme/app-spec", self.clone, "refund-rules").returncode, 0)
        self.assertEqual(git(self.bare["spec"], "log", "-1", "--format=%s", "main"), "spec: refund-rules")

    def refused(self, result, words):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(words, result.stderr)
        self.assertEqual(self.pushed("spec", "main"), ["orders.md"])
        self.assertEqual(self.pushed("project", "main"), [])
        self.assertEqual([call for call in self.commands() if "push" in call or "commit" in call], [])

    def test_it_refuses_a_clone_of_another_repository(self):
        self.change()
        self.refused(self.publish("acme/other", self.clone, "12"), "is not a clone of acme/other")

    def test_it_refuses_the_project_itself(self):
        (self.project / "orders.md").write_text("a rule\n")
        self.refused(self.publish("acme/app", self.project, "12"), "is the project itself")

    def test_it_refuses_a_clone_that_is_not_on_main(self):
        git(self.clone, "switch", "-q", "-c", "draft")
        self.change()
        self.refused(self.publish("acme/app-spec", self.clone, "12"), "is not on main")

    def test_it_refuses_a_clone_with_nothing_to_publish(self):
        self.refused(self.publish("acme/app-spec", self.clone, "12"), "holds no change")

    def test_it_refuses_a_folder_that_is_no_clone(self):
        (self.top / "plain").mkdir()
        self.refused(self.publish("acme/app-spec", self.top / "plain", "12"), "is not a clone")

    def test_it_takes_a_repository_a_clone_and_an_id(self):
        env_less = subprocess.run(["bash", str(SPEC_SCRIPT), "acme/app-spec", str(self.clone)],
                                  cwd=self.project, capture_output=True, text=True)
        self.assertEqual(env_less.returncode, 2)


if __name__ == "__main__":
    unittest.main()
