"""The ruleset `app` gives a project (`plugins/app/ruleset.json`) holds what `merge.py` and
the method rely on."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULESET = json.loads((ROOT / "plugins/app/ruleset.json").read_text(encoding="utf-8"))
RULES = {rule["type"]: rule.get("parameters", {}) for rule in RULESET["rules"]}


class Ruleset(unittest.TestCase):
    def test_nobody_bypasses_it(self):
        self.assertEqual(RULESET["bypass_actors"], [])
        self.assertEqual(RULESET["enforcement"], "active")

    def test_main_takes_only_a_pull_request_merged_by_rebase_or_squash(self):
        self.assertEqual(sorted(RULES["pull_request"]["allowed_merge_methods"]), ["rebase", "squash"])
        self.assertEqual(RULES["pull_request"]["required_approving_review_count"], 0)

    def test_merge_py_need_not_bring_the_branch_up_to_date(self):
        self.assertIs(RULES["required_status_checks"]["strict_required_status_checks_policy"], False)

    def test_checks_are_those_of_github_actions(self):
        for check in RULES["required_status_checks"]["required_status_checks"]:
            self.assertEqual(check["integration_id"], 15368)

    def test_main_is_neither_deleted_nor_rewritten(self):
        self.assertIn("deletion", RULES)
        self.assertIn("non_fast_forward", RULES)


if __name__ == "__main__":
    unittest.main()
