"""Tests for app's grades.py — every (b) and (c) grade of a PR body carries its source —
run with `python3 -m unittest discover -s tests`. The script reads one local file and
calls nothing."""

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/app/skills/run-entry/scripts/grades.py"
SPEC = importlib.util.spec_from_file_location("grades", SCRIPT)
grades = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(grades)


def lacking(body: str) -> list[tuple[int, str]]:
    return [(number, lacks) for number, lacks, _ in grades.unsourced(body)]


class ADeferredFinding(unittest.TestCase):
    def test_a_b_line_with_its_issue_passes(self):
        self.assertEqual(lacking("- (b) the retry has no ceiling — filed #412\n"), [])

    def test_a_b_line_with_no_issue_is_refused(self):
        self.assertEqual(lacking("- (b) the retry has no ceiling — in the spec's open questions\n"),
                         [(1, grades.NO_ISSUE)])


class ARejectedFinding(unittest.TestCase):
    def test_each_kind_of_citation_after_the_dash_passes(self):
        for source in ("src-tauri/src/auth/session.rs holds it", "decided in #380", "ADR keeps the code only",
                       "measured at 3 ms", "the owner said so", "see glossary.md"):
            with self.subTest(source):
                self.assertEqual(lacking(f"- (c) the error loses its cause — {source}\n"), [])

    def test_a_c_line_that_says_only_older_is_refused(self):
        self.assertEqual(lacking("- (c) older\n"), [(1, grades.NO_CITATION)])
        self.assertEqual(lacking("- (c) the error loses its cause — pre-existing\n"), [(1, grades.NO_CITATION)])

    def test_a_path_in_the_finding_is_not_its_citation(self):
        """The finding names the file it is about: only what follows the dash is the source."""
        self.assertEqual(lacking("- (c) src-tauri/src/auth/session.rs:42 unwraps — older\n"),
                         [(1, grades.NO_CITATION)])

    def test_a_hyphen_between_spaces_is_a_dash(self):
        self.assertEqual(lacking("- (c) the error loses its cause - ADR-009\n"), [])


class ABody(unittest.TestCase):
    def test_only_b_and_c_lines_are_read(self):
        body = "Closes #12\n\n- (a) the amount is an integer of cents now\n- a line of prose\n"
        self.assertEqual(lacking(body), [])

    def test_each_refused_line_is_reported_with_its_number(self):
        body = "Closes #12\n- (b) too big for this PR\n- (a) fixed\n- (c) older\n"
        self.assertEqual(lacking(body), [(2, grades.NO_ISSUE), (4, grades.NO_CITATION)])


class TheExitCode(unittest.TestCase):
    def run_on(self, body: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "body.md"
            file.write_text(body, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = grades.main([str(file)])
        return code, out.getvalue()

    def test_zero_when_every_line_carries_its_source(self):
        code, _ = self.run_on("- (b) the retry has no ceiling — #412\n- (c) a shorter name — the owner keeps it\n")
        self.assertEqual(code, 0)

    def test_one_and_each_line_printed_when_a_source_lacks(self):
        code, out = self.run_on("- (c) older\n")
        self.assertEqual(code, 1)
        self.assertIn("line 1: (c) with no citation after a dash", out)
        self.assertIn("grades.py", out.splitlines()[-1])

    def test_two_when_the_file_cannot_be_read(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(grades.main(["/nonexistent/body.md"]), 2)
            self.assertEqual(grades.main([]), 2)
        self.assertIn("could not be read", err.getvalue())


if __name__ == "__main__":
    unittest.main()
