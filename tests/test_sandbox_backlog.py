"""The sandbox app's backlog, `sandbox/scenarios/backlog.json`: each item loads through the
fake `gh`, and the Project lists them in a fixed order with their Status."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SANDBOX = Path(__file__).resolve().parents[1] / "sandbox"
SCENARIOS = SANDBOX / "scenarios"

# Row order is the batch's order: what a headless run reads top down.
ROWS = [
    (16, "In review"),
    (14, "Queued"),
    (12, "Queued"),
    (11, "Queued"),
    (13, "Queued"),
    (15, "Queued"),
]
FORM = {
    "feature": ["### Size", "### User value", "### Done when", "### Design"],
    "bug": ["### Size", "### User value", "### Done when", "### Design"],
    "task": ["### Found by", "### Where", "### Observation", "### Size", "### Waits on the owner"],
}


class TheBacklog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.log = cls.folder / "gh.jsonl"
        subprocess.run(
            [sys.executable, str(SANDBOX / "fake_gh.py"), "install", str(cls.folder / "bin"),
             str(SCENARIOS / "backlog.json"), str(cls.log)], check=True, capture_output=True)
        cls.env = dict(os.environ, PATH=f"{cls.folder / 'bin'}{os.pathsep}{os.environ['PATH']}")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def gh(self, command: str):
        """The command exactly as a skill writes it, answered as JSON."""
        done = subprocess.run(command.split(), env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def items(self) -> list[dict]:
        return self.gh("gh project item-list 1 --owner acme --format json --limit 500")["items"]

    def test_the_project_lists_the_items_in_a_fixed_order_with_their_status(self):
        listed = self.gh("gh project item-list 1 --owner acme --format json --limit 500")
        self.assertEqual([(item["content"]["number"], item["status"]) for item in listed["items"]], ROWS)
        self.assertEqual(listed["totalCount"], len(ROWS))

    def test_each_item_loads_whole_through_the_fake_gh(self):
        for item in self.items():
            number = item["content"]["number"]
            with self.subTest(number):
                issue = self.gh(f"gh issue view {number} --json title,body,comments")
                self.assertEqual(set(issue), {"title", "body", "comments"})
                self.assertEqual(issue["title"], item["title"])
                self.assertEqual(issue["title"], item["content"]["title"])
                self.assertEqual(issue["body"], item["content"]["body"])

    def test_each_item_carries_one_kind_a_size_and_its_form_s_fields(self):
        for item in self.items():
            with self.subTest(item["content"]["number"]):
                kinds = [label for label in item["labels"] if label in FORM]
                self.assertEqual(len(kinds), 1, item["labels"])
                self.assertEqual(len([label for label in item["labels"] if label.startswith("size:")]), 1)
                body = item["content"]["body"]
                found = [body.find(section) for section in FORM[kinds[0]]]
                self.assertNotIn(-1, found, f"a field of the {kinds[0]} form is missing")
                self.assertEqual(found, sorted(found), "the form's order")

    def test_the_backlog_holds_each_case_a_scenario_needs(self):
        by_number = {item["content"]["number"]: item for item in self.items()}
        kinds = {number: next(label for label in item["labels"] if label in FORM) for number, item in by_number.items()}
        self.assertEqual(kinds, {16: "task", 14: "feature", 12: "task", 11: "bug", 13: "feature", 15: "task"})
        # A ready task: no label that stops it, nothing waiting.
        self.assertNotIn("needs-owner", by_number[12]["labels"])
        self.assertIn("### Waits on the owner\n\nNothing.", by_number[12]["content"]["body"])
        # A feature whose Done when a test can prove, its design validated.
        self.assertIn("### Design\n\nvalidated", by_number[13]["content"]["body"])
        self.assertIn("- A fragile parcel costs 2.00 more", by_number[13]["content"]["body"])
        # The only item that waits on the owner, with the question as its last comment.
        self.assertEqual([n for n, item in by_number.items() if "needs-owner" in item["labels"]], [14])
        asked = self.gh("gh issue view 14 --json title,body,comments")["comments"]
        self.assertEqual(asked[-1]["author"]["login"], "acme-agent")
        self.assertTrue(asked[-1]["body"].rstrip().endswith("?"))
        # One blocked by another, which is queued above it.
        self.assertIn("Blocked by #12", by_number[15]["content"]["body"])
        numbers = [number for number, _ in ROWS]
        self.assertLess(numbers.index(12), numbers.index(15))

    def test_the_item_in_review_has_its_open_pull_request_and_branch(self):
        in_review = [item for item in self.items() if item["status"] == "In review"]
        self.assertEqual(len(in_review), 1)
        self.assertEqual(in_review[0]["linked pull requests"], ["https://github.com/acme/acme/pull/17"])
        self.assertEqual(self.gh("gh pr list --state open --json number,headRefName"),
                         [{"headRefName": "test/16-presenter-messages", "number": 17}])
        for item in self.items():
            if item["status"] != "In review":
                self.assertNotIn("linked pull requests", item)

    def test_the_status_field_has_the_six_states_and_a_batch_field(self):
        fields = self.gh("gh project field-list 1 --owner acme --format json")["fields"]
        status = next(field for field in fields if field["name"] == "Status")
        self.assertEqual([option["name"] for option in status["options"]],
                         ["Inbox", "Ready", "Queued", "In progress", "In review", "Done"])
        self.assertIn("Batch", [field["name"] for field in fields])

    def test_what_the_app_s_settings_name_is_what_the_fixtures_answer(self):
        settings = json.loads((SANDBOX / "acme" / ".claude" / "daneel.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["plan-batch"], {"owner": "acme", "number": 1})

    def test_every_answer_is_a_file_that_is_there_and_is_json(self):
        scenario = json.loads((SCENARIOS / "backlog.json").read_text(encoding="utf-8"))
        for pattern, answer in scenario.items():
            with self.subTest(pattern):
                json.loads((SCENARIOS / answer).read_text(encoding="utf-8"))
        answered = {SCENARIOS / answer for answer in scenario.values()}
        self.assertEqual(answered, set((SCENARIOS / "backlog").iterdir()), "an answer file no command returns")

    def test_a_form_of_the_command_the_fixtures_do_not_hold_fails_loudly(self):
        done = subprocess.run("gh issue view 12 --comments".split(), env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 97)

    def test_the_chat_requests_are_one_named_issue_and_two_plain_ones(self):
        requests = {path.name: path.read_text(encoding="utf-8").strip() for path in (SCENARIOS / "requests").iterdir()}
        self.assertEqual(sorted(requests), ["named-issue.txt", "plain-fix.txt", "plain-rename.txt"])
        self.assertEqual(requests["named-issue.txt"], "/app:run-entry #12")
        for name in ("plain-fix.txt", "plain-rename.txt"):
            self.assertRegex(requests[name], r"^/app:run-entry [A-Z].{40,}\.$")
            self.assertNotRegex(requests[name], r"#\d")


if __name__ == "__main__":
    unittest.main()
