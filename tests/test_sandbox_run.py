"""Tests for sandbox/run.py and the `resume` scenario. No test calls a model: `claude` is a
stub first on PATH that runs the commands a test gives it, in the copy, as a session would,
and prints a `stream-json` transcript. No test talks to a real remote."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "sandbox"
WATCH = ROOT / "plugins/app/skills/run-entry/scripts/watch-pr.py"
RESUME = SANDBOX / "scenarios" / "resume"

SPEC = importlib.util.spec_from_file_location("sandbox_run", SANDBOX / "run.py")
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)
snapshot, fake_gh = run.snapshot, run.fake_gh

STUB = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
Path = __import__("pathlib").Path
Path(os.environ["STUB_ARGV"]).write_text(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "path": os.environ["PATH"]}))
for command in json.loads(Path(os.environ["STUB_ACTIONS"]).read_text()):
    print(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": command}}]}}), flush=True)
    subprocess.run(["bash", "-c", command], capture_output=True)
result = os.environ.get("STUB_RESULT", "")
if result != "none":
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 7,
                      "duration_ms": 41000, "total_cost_usd": 0.42, "usage": {"output_tokens": 900},
                      "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "git switch x"}}],
                      "result": "Stopped at the usage limit.", **json.loads(result or "{}")}))
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
'''

# What a session that follows `run-entry`'s resume does on this scenario.
RESUMED = [
    "git status --short",
    "gh project item-list 1 --owner acme --format json --limit 500",
    "gh pr list --state open --json number,headRefName",
    "gh pr checkout 17",
    f"python3 {WATCH} --interval 0",
    "gh issue comment 16 --body-file /dev/null",
    "gh issue edit 16 --add-label needs-owner",
]


def app_digest() -> str:
    digest = hashlib.sha256()
    for path in snapshot.app_files():
        digest.update(path.encode() + (snapshot.APP / path).read_bytes())
    return digest.hexdigest()


class StubbedClaude(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        (self.folder / "bin").mkdir()
        stub = self.folder / "bin" / "claude"
        stub.write_text(STUB, encoding="utf-8")
        stub.chmod(0o755)
        self.argv = self.folder / "argv.json"
        self.kept: list[Path] = []

    def tearDown(self):
        for folder in self.kept:
            snapshot.discard(folder)
        self.temp.cleanup()

    def run_scenario(self, actions: list[str], *args: str, **stub: str) -> tuple[int, dict]:
        (self.folder / "actions.json").write_text(json.dumps(actions), encoding="utf-8")
        env = {
            "PATH": f"{self.folder / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "STUB_ACTIONS": str(self.folder / "actions.json"), "STUB_ARGV": str(self.argv),
            **{f"STUB_{key.upper()}": value for key, value in stub.items()},
        }
        report = self.folder / "report.json"
        with unittest.mock.patch.dict(os.environ, env), \
                unittest.mock.patch.object(snapshot.shutil, "copytree"):  # no packages: nothing runs the harness
            code = run.main(["resume", "--report", str(report), *args])
        found = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
        if "kept" in found:
            self.kept.append(Path(found["kept"]))
        return code, found

    def unmet(self, report: dict) -> list[str]:
        return [entry["check"] for entry in report["checks"] if not entry["met"]]


class TheRunner(StubbedClaude):
    def test_a_session_that_resumes_meets_every_expectation(self):
        code, report = self.run_scenario(RESUMED)
        self.assertEqual(self.unmet(report), [])
        self.assertEqual((code, report["finished"], report["met"]), (0, True, report["of"]))
        self.assertGreater(report["of"], 10)

    def test_the_watch_ran_for_real_against_the_fixture(self):
        _, report = self.run_scenario(RESUMED)
        self.assertIn("0 gh pr view --json headRefOid,state", report["gh"])
        self.assertTrue([call for call in report["gh"] if "check-runs?filter=latest" in call and call.startswith("0 ")])
        self.assertTrue([call for call in report["gh"] if "issues/17/comments" in call and call.startswith("0 ")])

    def test_the_report_carries_what_the_session_reported(self):
        _, report = self.run_scenario(RESUMED)
        self.assertEqual((report["cost_usd"], report["turns"], report["session_seconds"]), (0.42, 7, 41))
        self.assertEqual(report["denied"], ["git switch x"])
        self.assertEqual(report["bash"], RESUMED)
        self.assertEqual(report["last_words"], "Stopped at the usage limit.")
        self.assertEqual(report["usage"], {"output_tokens": 900})

    def test_claude_is_started_headless_with_this_checkout_s_plugins_and_no_grant_of_the_machine(self):
        self.run_scenario(RESUMED, "--model", "sonnet", "--max-budget-usd", "1.5")
        started = json.loads(self.argv.read_text(encoding="utf-8"))
        self.assertEqual(started["argv"], [
            "-p", "/app:run-entry",
            "--plugin-dir", str(ROOT / "plugins" / "flow"), "--plugin-dir", str(ROOT / "plugins" / "app"),
            "--permission-mode", "acceptEdits", "--setting-sources", "project", "--strict-mcp-config",
            "--no-session-persistence", "--output-format", "stream-json", "--verbose",
            "--max-budget-usd", "1.5", "--model", "sonnet",
        ])
        self.assertEqual(Path(started["cwd"]).name, "acme")
        self.assertEqual(started["path"].split(os.pathsep)[0], str(Path(started["cwd"]).parent / "bin"))

    def test_a_new_branch_is_seen(self):
        code, report = self.run_scenario([*RESUMED, "git checkout -b fix/16-again"])
        self.assertEqual(code, 1)
        self.assertEqual(self.unmet(report), ["local_branches", "not_ran: git checkout -b "])

    def test_a_command_nobody_answered_is_seen(self):
        code, report = self.run_scenario([*RESUMED, "gh pr view 17 --comments"])
        self.assertEqual((code, self.unmet(report)), (1, ["gh_all_answered"]))
        self.assertIn("97 gh pr view 17 --comments", report["gh"])

    def test_a_scan_before_the_checkout_is_seen(self):
        code, report = self.run_scenario(["gh issue comment 16 --body-file /dev/null", *RESUMED])
        self.assertEqual((code, self.unmet(report)), (1, ["gh_not_before: gh issue comment * before gh pr checkout 17"]))

    def test_a_push_of_main_is_seen(self):
        pushed = ["git commit -q --allow-empty -m x", "git push -q origin main"]
        code, report = self.run_scenario([*RESUMED, *pushed])
        self.assertEqual(code, 1)
        self.assertEqual(self.unmet(report), ["origin_unchanged: main", "not_ran: git push"])

    def test_a_session_that_does_nothing_meets_little(self):
        code, report = self.run_scenario([])
        self.assertEqual(code, 1)
        self.assertEqual(len([name for name in self.unmet(report) if name.startswith("gh_called")]), 5)

    def test_a_session_with_no_result_did_not_finish(self):
        code, report = self.run_scenario(RESUMED, result="none", exit="1")
        self.assertEqual((code, report["finished"]), (2, False))
        self.assertIn("gave no result (claude exited 1)", report["stopped"])

    def test_a_session_stopped_by_its_budget_did_not_finish(self):
        code, report = self.run_scenario(RESUMED, result='{"subtype": "error_max_budget_usd", "is_error": true}')
        self.assertEqual((code, report["stopped"]), (2, "the session ended with error_max_budget_usd"))

    def test_the_folder_is_thrown_away_unless_kept(self):
        _, report = self.run_scenario(RESUMED)
        self.assertNotIn("kept", report)
        self.assertFalse(Path(json.loads(self.argv.read_text(encoding="utf-8"))["cwd"]).exists())
        _, report = self.run_scenario(RESUMED, "--keep")
        kept = Path(report["kept"])
        self.assertTrue((kept / "transcript.jsonl").is_file() and (kept / "gh.jsonl").is_file())

    def test_a_run_leaves_the_app_and_the_scenario_unchanged(self):
        before = app_digest(), sorted(path.name for path in RESUME.rglob("*"))
        self.run_scenario([*RESUMED, "git rm -q -r src", "git commit -q -m gone"])
        self.assertEqual((app_digest(), sorted(path.name for path in RESUME.rglob("*"))), before)


class Refusals(unittest.TestCase):
    def test_a_scenario_that_is_not_there_exits_3(self):
        done = subprocess.run([sys.executable, str(SANDBOX / "run.py"), "no-such-scenario"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 3)
        self.assertIn("cannot read", done.stderr)

    def test_wrong_arguments_exit_3(self):
        done = subprocess.run([sys.executable, str(SANDBOX / "run.py")], capture_output=True, text=True)
        self.assertEqual(done.returncode, 3)

    def test_a_key_nothing_reads_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            for scenario in ({"prompt": "x", "answers": "a.json", "expect": {"gh_caled": []}},
                             {"prompt": "x", "answers": "a.json", "expect": {}, "grade": 1}):
                (Path(temp) / "scenario.json").write_text(json.dumps(scenario), encoding="utf-8")
                with self.assertRaisesRegex(run.Refusal, "keys nothing reads: (gh_caled|grade)"):
                    run.read_scenario(Path(temp))
            (Path(temp) / "scenario.json").write_text('{"prompt": "x"}', encoding="utf-8")
            with self.assertRaisesRegex(run.Refusal, "missing answers, expect"):
                run.read_scenario(Path(temp))


class TheResumeScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenario = run.read_scenario(RESUME)
        cls.answers = json.loads((RESUME / cls.scenario["answers"]).read_text(encoding="utf-8"))
        cls.temp = tempfile.TemporaryDirectory()
        branches = [dict(branch, files=str(RESUME / branch["files"])) for branch in cls.scenario["branches"]]
        cls.folder = snapshot.restore(Path(cls.temp.name) / "run", packages=False, branches=branches)
        cls.work = cls.folder / "acme"
        fake_gh.install(cls.folder / "bin", RESUME / cls.scenario["answers"], cls.folder / "gh.jsonl")
        cls.env = dict(snapshot.clean_env(), PATH=f"{cls.folder / 'bin'}{os.pathsep}{os.environ['PATH']}")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_answer_file_is_there(self):
        for pattern, answer in self.answers.items():
            if answer != "ok":
                self.assertTrue((RESUME / answer).is_file(), f"{pattern}: {answer}")

    def test_the_branch_is_one_fixed_commit_on_main_pushed_and_the_copy_is_on_main(self):
        git = lambda *args: snapshot.git(self.work, *args).strip()  # noqa: E731
        self.assertEqual(git("status", "-sb"), "## main...origin/main")
        self.assertEqual(git("rev-parse", "test/16-presenter-messages~1"), git("rev-parse", "main"))
        self.assertEqual(git("rev-parse", "test/16-presenter-messages"), git("rev-parse", "origin/test/16-presenter-messages"))
        self.assertEqual(git("diff", "--name-only", "main", "test/16-presenter-messages"),
                         "src/features/fees/presenter.test.ts")
        self.assertEqual(git("log", "-1", "--format=%an|%aI|%s", "test/16-presenter-messages"),
                         "Ada Acme|2026-01-14T11:20:00Z|test(fees): each error code has its message")

    def test_the_pull_request_s_head_is_the_branch_s_commit(self):
        """The fixture names a commit id, fixed for as long as the app's files are: when one
        changes, this says which id the answers must carry."""
        head = snapshot.git(self.work, "rev-parse", "test/16-presenter-messages").strip()
        self.assertEqual(json.loads((RESUME / "pr-17-head.json").read_text(encoding="utf-8"))["headRefOid"], head)
        self.assertTrue([pattern for pattern in self.answers if f"commits/{head}/check-runs" in pattern])

    def test_it_is_the_backlog_s_item_in_review(self):
        items = json.loads((SANDBOX / "scenarios/backlog/project-items.json").read_text(encoding="utf-8"))["items"]
        in_review = [item for item in items if item["status"] == "In review"][0]
        self.assertEqual(in_review["content"]["number"], 16)
        prs = json.loads((SANDBOX / "scenarios/backlog/open-prs.json").read_text(encoding="utf-8"))
        self.assertEqual(prs[0]["headRefName"], self.scenario["branches"][0]["name"])
        self.assertEqual(json.loads((RESUME / "pr-17-number.json").read_text(encoding="utf-8"))["number"], prs[0]["number"])

    def test_the_real_watch_reads_the_fixture_as_a_lane_stopped_by_the_usage_limit(self):
        for arguments in ([], ["17"]):
            with self.subTest(arguments):
                done = subprocess.run([sys.executable, str(WATCH), *arguments, "--interval", "0"], cwd=self.work,
                                      env=self.env, capture_output=True, text=True)
                self.assertEqual(done.returncode, 6, done.stdout + done.stderr)
                self.assertIn("USAGE LIMIT: reviewer-frontend resets 11:50am (UTC)", done.stdout)

    def test_the_required_check_of_the_app_is_green_in_the_fixture(self):
        required = json.loads((snapshot.APP / "required-checks.json").read_text(encoding="utf-8"))["checks"]
        runs = [json.loads(line) for line in (RESUME / "check-runs.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual({run_["name"]: run_["conclusion"] for run_ in runs},
                         {**{name: "success" for name in required}, "reviewer-frontend": "failure"})


if __name__ == "__main__":
    unittest.main()
