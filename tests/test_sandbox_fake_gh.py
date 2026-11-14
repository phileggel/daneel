"""Tests for sandbox/fake_gh.py: a match, a list of answers, the log, and the loud failure on
a command nobody answered. Every call goes through the `gh` that `install` writes, found on
PATH as a workflow finds it."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "sandbox" / "fake_gh.py"

SCENARIO = {
    "gh pr list --state open *": "one-open-pr.json",
    "gh pr list *": "no-pr.json",
    "gh pr checkout *": "ok",
    "gh pr checks *": [{"stdout": "pending.txt", "exit": 8}, "green.txt"],
    "gh pr merge *": {"exit": 1, "stderr": "Pull request is not mergeable\n"},
    "gh issue view 7 *": "missing.json",
}


class FakeGh(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.fixtures = self.folder / "scenario"
        self.fixtures.mkdir()
        self.scenario = self.fixtures / "answers.json"
        self.scenario.write_text(json.dumps(SCENARIO), encoding="utf-8")
        (self.fixtures / "one-open-pr.json").write_text('[{"number": 12, "headRefName": "fix/7-fee"}]\n')
        (self.fixtures / "no-pr.json").write_text("[]\n")
        (self.fixtures / "pending.txt").write_text("harness\tpending\t0\thttps://example.invalid/1\t\n")
        (self.fixtures / "green.txt").write_text("harness\tpass\t41s\thttps://example.invalid/1\t\n")
        self.log = self.folder / "logs" / "gh.jsonl"
        self.bin = self.folder / "bin"
        self.install()

    def tearDown(self):
        self.temp.cleanup()

    def install(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "install", str(self.bin), str(self.scenario), str(self.log)],
            capture_output=True, text=True,
        )

    def gh(self, *args: str) -> subprocess.CompletedProcess:
        """`gh` as a workflow calls it: by name, the fake first on PATH, no variable of ours set."""
        env = {key: value for key, value in os.environ.items() if not key.startswith("FAKE_GH_")}
        env["PATH"] = f"{self.bin}{os.pathsep}{env['PATH']}"
        return subprocess.run(["gh", *args], env=env, capture_output=True, text=True, cwd=self.folder)

    def logged(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_a_command_gets_its_file_as_it_is(self):
        done = self.gh("pr", "list", "--state", "open", "--json", "number,headRefName")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, '[{"number": 12, "headRefName": "fix/7-fee"}]\n')
        self.assertEqual(done.stderr, "")

    def test_the_first_pattern_that_matches_answers(self):
        self.assertEqual(self.gh("pr", "list", "--state", "closed").stdout, "[]\n")

    def test_a_pattern_ending_in_a_star_takes_the_command_alone(self):
        self.assertEqual(self.gh("pr", "list").stdout, "[]\n")

    def test_ok_prints_nothing_and_exits_0(self):
        done = self.gh("pr", "checkout", "12")
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_a_list_gives_the_next_answer_on_each_call_then_the_last(self):
        calls = [self.gh("pr", "checks", "12") for _ in range(3)]
        self.assertEqual([call.returncode for call in calls], [8, 0, 0])
        self.assertIn("pending", calls[0].stdout)
        self.assertIn("pass", calls[1].stdout)
        self.assertEqual(calls[2].stdout, calls[1].stdout)

    def test_the_position_in_a_list_is_per_pattern(self):
        self.gh("pr", "checks", "12")
        self.gh("pr", "list")
        self.gh("pr", "list")
        self.assertEqual(self.gh("pr", "checks", "12").returncode, 0)

    def test_an_answer_can_fail_with_its_own_exit_and_message(self):
        done = self.gh("pr", "merge", "12", "--rebase")
        self.assertEqual((done.returncode, done.stdout), (1, ""))
        self.assertEqual(done.stderr, "Pull request is not mergeable\n")

    def test_every_call_is_logged_in_order(self):
        self.gh("pr", "checkout", "12")
        self.gh("pr", "checks", "12", "--watch")
        self.gh("pr", "checks", "12", "--watch")
        self.assertEqual(self.logged(), [
            {"argv": ["gh", "pr", "checkout", "12"], "command": "gh pr checkout 12",
             "pattern": "gh pr checkout *", "call": 1, "answer": "ok", "exit": 0},
            {"argv": ["gh", "pr", "checks", "12", "--watch"], "command": "gh pr checks 12 --watch",
             "pattern": "gh pr checks *", "call": 1, "answer": {"stdout": "pending.txt", "exit": 8}, "exit": 8},
            {"argv": ["gh", "pr", "checks", "12", "--watch"], "command": "gh pr checks 12 --watch",
             "pattern": "gh pr checks *", "call": 2, "answer": "green.txt", "exit": 0},
        ])

    def test_an_argument_with_spaces_is_logged_whole(self):
        self.gh("pr", "list", "--search", "is:open label:bug")
        self.assertEqual(self.logged()[0]["argv"], ["gh", "pr", "list", "--search", "is:open label:bug"])

    def test_a_command_nobody_answered_fails_loudly_and_is_logged(self):
        done = self.gh("release", "create", "v1.0.0")
        self.assertEqual(done.returncode, 97)
        self.assertEqual(done.stdout, "")
        self.assertIn("fake gh: no answer for: gh release create v1.0.0", done.stderr)
        self.assertEqual(self.logged(), [
            {"argv": ["gh", "release", "create", "v1.0.0"], "command": "gh release create v1.0.0",
             "pattern": None, "call": None, "answer": None, "exit": 97},
        ])

    def test_a_missing_answer_file_fails_loudly_and_is_logged(self):
        done = self.gh("issue", "view", "7", "--json", "title")
        self.assertEqual(done.returncode, 98)
        self.assertIn("missing.json", done.stderr)
        self.assertEqual(self.logged()[0]["exit"], 98)

    def test_a_scenario_that_is_not_json_fails_every_call(self):
        self.scenario.write_text("gh pr list: x\n", encoding="utf-8")
        done = self.gh("pr", "list")
        self.assertEqual(done.returncode, 98)
        self.assertIn("cannot read the scenario", done.stderr)

    def test_an_answer_of_another_shape_is_refused(self):
        self.scenario.write_text(json.dumps({"gh pr list *": {"output": "no-pr.json"}}), encoding="utf-8")
        self.assertEqual(self.gh("pr", "list").returncode, 98)

    def test_it_writes_nothing_in_the_scenario_s_folder(self):
        before = sorted(path.name for path in self.fixtures.iterdir())
        self.gh("pr", "list")
        self.gh("release", "create", "v1.0.0")
        self.assertEqual(sorted(path.name for path in self.fixtures.iterdir()), before)

    def test_install_refuses_to_replace_a_gh(self):
        again = self.install()
        self.assertEqual(again.returncode, 1)
        self.assertIn("already there", again.stderr)

    def test_install_refuses_a_scenario_it_cannot_read(self):
        done = subprocess.run(
            [sys.executable, str(SCRIPT), "install", str(self.folder / "other"), str(self.folder / "none.json"),
             str(self.log)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertFalse((self.folder / "other" / "gh").exists())

    def test_wrong_arguments_exit_2(self):
        done = subprocess.run([sys.executable, str(SCRIPT), "install", str(self.bin)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)

    def test_answer_without_the_installed_gh_says_so(self):
        env = {key: value for key, value in os.environ.items() if not key.startswith("FAKE_GH_")}
        done = subprocess.run([sys.executable, str(SCRIPT), "answer", "pr", "list"], env=env,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 98)
        self.assertIn("FAKE_GH_SCENARIO is not set", done.stderr)


if __name__ == "__main__":
    unittest.main()
