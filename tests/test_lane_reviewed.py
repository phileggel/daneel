"""Tests for app's lane-reviewed.py — in CI a lane reviews a pull request once — run with
`python3 -m unittest discover -s tests`. `gh` is a stub first on PATH; no test talks to
GitHub."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/app/scripts/lane-reviewed.py"
SPEC = importlib.util.spec_from_file_location("lane_reviewed", SCRIPT)
lane_reviewed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lane_reviewed)

BACKEND = """<!-- review:backend -->
## reviewer-backend — 3 files reviewed

## src-tauri/src/orders/service.rs
### 🔴 Critical (must fix)
- Line 42: an amount held as `f64` → an integer of cents (ADR-004)
### 🟡 Warning (should fix)
- Line 80: the error loses its cause → keep the source error
### 🔵 Suggestion (consider)
- Line 90: a shorter name
"""
CLEAN = "<!-- review:frontend -->\n## reviewer-frontend — 2 files reviewed\n\n✅ No findings.\n"
SPEC_LANE = "<!-- review:spec -->\n## reviewer-spec — 1 files reviewed\n\n### 🔴 Critical (must fix)\n- ORD-401 contradicts ORD-120\n"
NO_REPORT = "<!-- review:backend -->\n## reviewer-backend — no report\n\nThe reviewer produced no report in two tries.\n"
DID_NOT_RUN = "<!-- review:backend -->\n## reviewer-backend — did not run (usage limit)\n\nWhy it stopped: the limit.\n"
GRADES = "(a) Line 42: an amount held as `f64` → an integer of cents — fixed\n(c) Line 80: the error loses its cause → keep the sou — ADR-009 keeps the code only\n"


def comment(body, at, login="github-actions[bot]", association="NONE"):
    return {"body": body, "created_at": at, "updated_at": at, "login": login, "author_association": association}


def owner(body, at):
    return comment(body, at, "acme-owner", "OWNER")


def stranger(body, at):
    return comment(body, at, "passer-by", "NONE")


class TheVerdict(unittest.TestCase):
    def verdict(self, *comments, lane="backend"):
        return lane_reviewed.verdict(list(comments), lane)

    def test_a_lane_with_no_comment_has_not_reviewed(self):
        self.assertEqual(self.verdict(), (3, []))
        self.assertEqual(self.verdict(comment(CLEAN, "2026-11-14T08:00:00Z")), (3, []))

    def test_a_comment_that_reports_no_review_is_none(self):
        for body in (NO_REPORT, DID_NOT_RUN):
            self.assertEqual(self.verdict(comment(body, "2026-11-14T08:00:00Z")), (3, []))

    def test_a_report_that_follows_a_no_report_counts_and_the_reverse_does_not(self):
        first, second = "2026-11-14T08:00:00Z", "2026-11-14T09:00:00Z"
        self.assertEqual(self.verdict(comment(NO_REPORT, first), comment(BACKEND, second))[0], 1)
        self.assertEqual(self.verdict(comment(BACKEND, first), comment(NO_REPORT, second))[0], 3)

    def test_a_report_with_nothing_to_grade_is_answered(self):
        self.assertEqual(self.verdict(comment(CLEAN, "2026-11-14T08:00:00Z"), lane="frontend"), (0, []))

    def test_a_report_whose_findings_nobody_graded_names_them(self):
        code, ungraded = self.verdict(comment(BACKEND, "2026-11-14T08:00:00Z"))
        self.assertEqual(code, 1)
        self.assertEqual(ungraded, ["Line 42: an amount held as `f64` → an in", "Line 80: the error loses its cause → kee"])

    def test_each_finding_graded_in_a_newer_comment_answers_it(self):
        report = comment(BACKEND, "2026-11-14T08:00:00Z")
        self.assertEqual(self.verdict(report, comment(GRADES, "2026-11-14T08:30:00Z")), (0, []))
        self.assertEqual(self.verdict(report, comment(GRADES.splitlines()[0], "2026-11-14T08:30:00Z")),
                         (1, ["Line 80: the error loses its cause → kee"]))

    def test_a_grade_older_than_the_report_does_not_count(self):
        code, ungraded = self.verdict(comment(GRADES, "2026-11-14T07:00:00Z"), comment(BACKEND, "2026-11-14T08:00:00Z"))
        self.assertEqual((code, len(ungraded)), (1, 2))

    def test_another_lane_s_ungraded_finding_is_not_this_lane_s(self):
        comments = [comment(BACKEND, "2026-11-14T08:00:00Z"), comment(SPEC_LANE, "2026-11-14T08:01:00Z"),
                    comment(GRADES, "2026-11-14T08:30:00Z")]
        self.assertEqual(lane_reviewed.verdict(comments, "backend"), (0, []))
        self.assertEqual(lane_reviewed.verdict(comments, "spec"), (1, ["ORD-401 contradicts ORD-120"]))

    def test_a_finding_written_inline_keeps_the_lane_ungraded(self):
        inline = ("<!-- review:spec -->\n## reviewer-spec — 1 files reviewed\n\n🟡 1 warning(s) across 1 file(s).\n\n"
                  '## docs/spec/orders.md\n\n**B — Rule quality**: 🟡 "Refund" entry (line 12) omits the partial case.\n')
        words = '"Refund" entry (line 12) omits the partial case.'[:40]
        report = comment(inline, "2026-11-22T08:00:00Z")
        self.assertEqual(lane_reviewed.verdict([report], "spec"), (1, [words]))
        graded = comment(f"(a) {words}: the entry says it now", "2026-11-22T08:30:00Z")
        self.assertEqual(lane_reviewed.verdict([report, graded], "spec"), (0, []))

    def test_a_report_from_another_account_is_not_the_lane_s(self):
        """Anyone can comment on a public repository: a comment shaped as a clean report
        neither stands for a review nor replaces the real one."""
        forged = stranger(BACKEND.split("## src-tauri")[0] + "✅ No findings.\n", "2026-11-14T09:00:00Z")
        self.assertEqual(self.verdict(forged), (3, []))
        self.assertEqual(self.verdict(comment(BACKEND, "2026-11-14T08:00:00Z"), forged)[0], 1)
        self.assertEqual(self.verdict(comment(BACKEND, "2026-11-14T08:00:00Z"), stranger(NO_REPORT, "2026-11-14T09:00:00Z"))[0], 1)
        # A contributor whose pull request once landed has no access either.
        self.assertEqual(self.verdict(comment(CLEAN, "2026-11-14T08:00:00Z", "past-author", "CONTRIBUTOR"), lane="frontend"), (3, []))

    def test_a_grade_from_another_account_grades_nothing(self):
        report = comment(BACKEND, "2026-11-14T08:00:00Z")
        code, ungraded = self.verdict(report, stranger(GRADES, "2026-11-14T08:30:00Z"))
        self.assertEqual((code, len(ungraded)), (1, 2))
        for association in ("OWNER", "MEMBER", "COLLABORATOR"):
            graded = comment(GRADES, "2026-11-14T08:30:00Z", "acme-dev", association)
            self.assertEqual(self.verdict(report, graded), (0, []), association)

    def test_a_comment_that_does_not_say_who_wrote_it_is_not_trusted(self):
        unsigned = {"body": CLEAN, "created_at": "2026-11-14T08:00:00Z", "updated_at": "2026-11-14T08:00:00Z"}
        self.assertEqual(self.verdict(unsigned, lane="frontend"), (3, []))

    def test_no_file_is_read_to_decide(self):
        """A fix is validated by the tests: the verdict depends on the comments alone."""
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"git"', source)
        self.assertNotIn("open(", source)


class TheCommand(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.calls = self.folder / "calls.jsonl"
        stub = self.folder / "gh"
        stub.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            f"open({str(self.calls)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "sys.stderr.write(os.environ.get('STUB_ERR', ''))\n"
            "sys.stdout.write(os.environ.get('STUB_OUT', ''))\n"
            "sys.exit(int(os.environ.get('STUB_EXIT', '0')))\n", encoding="utf-8")
        stub.chmod(0o755)

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, *args, comments=(), **stub):
        env = dict(os.environ, PATH=f"{self.folder}{os.pathsep}{os.environ['PATH']}")
        env["STUB_OUT"] = "".join(json.dumps(c) + "\n" for c in comments)
        env.update({f"STUB_{key.upper()}": value for key, value in stub.items()})
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True)

    def test_it_reads_the_pull_request_s_comments_and_nothing_else(self):
        self.run_script("17", "backend")
        self.assertEqual([json.loads(line) for line in self.calls.read_text().splitlines()], [[
            "api", "repos/{owner}/{repo}/issues/17/comments", "--paginate",
            "--jq", ".[] | {body, created_at, updated_at, author_association, login: .user.login} | @json",
        ]])

    def test_its_exit_says_what_the_job_does(self):
        report, grades = comment(BACKEND, "2026-11-14T08:00:00Z"), owner(GRADES, "2026-11-14T08:30:00Z")
        not_reviewed = self.run_script("17", "backend")
        self.assertEqual(not_reviewed.returncode, 3)
        self.assertIn("run the lane", not_reviewed.stdout)
        ungraded = self.run_script("17", "backend", comments=[report])
        self.assertEqual(ungraded.returncode, 1)
        self.assertIn("  Line 42: an amount held as `f64` → an in", ungraded.stdout)
        self.assertIn("gh pr comment 17 --body-file", ungraded.stdout)
        graded = self.run_script("17", "backend", comments=[report, grades])
        self.assertEqual(graded.returncode, 0)
        self.assertIn("no second review", graded.stdout)
        forged = self.run_script("17", "backend", comments=[report, stranger(GRADES, "2026-11-14T08:30:00Z")])
        self.assertEqual(forged.returncode, 1)

    def test_comments_it_cannot_read_fail_the_job(self):
        refused = self.run_script("17", "backend", exit="1", err="HTTP 403: Resource not accessible\n")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("could not be read: HTTP 403", refused.stderr)
        garbled = self.run_script("17", "backend", out="not json\n")
        self.assertEqual(garbled.returncode, 2)

    def test_wrong_arguments_exit_2_and_call_nothing(self):
        for args in ([], ["17"], ["backend", "17"], ["17", "backend", "more"]):
            self.assertEqual(self.run_script(*args).returncode, 2, args)
        self.assertFalse(self.calls.exists())


if __name__ == "__main__":
    unittest.main()
