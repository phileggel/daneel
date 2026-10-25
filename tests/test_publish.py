"""design-proposal's publish.sh: the mocks reach the design repository or a `design/<id>`
branch, never the project's `main`, and never with the console-errors file."""

import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/app/skills/design-proposal/scripts/publish.sh"


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def publish(cwd, *args):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)


class Publish(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.top = Path(folder.name)
        self.project = self.repo("project", "https://github.com/acme/app.git")
        self.clone = self.repo("design", "https://github.com/acme/design.git")

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

    def mocks(self, folder):
        folder.mkdir(parents=True)
        (folder / "ORD-1-light-idle.png").write_bytes(b"png")
        (folder / ".console-errors.json").write_text("[]")

    def pushed(self, name, ref):
        return git(self.bare[name], "ls-tree", "-r", "--name-only", ref).splitlines()

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


if __name__ == "__main__":
    unittest.main()
