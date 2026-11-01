"""The ruleset `app` gives a project (`plugins/app/ruleset.json`) holds what GitHub asks of
a ruleset and what `merge.py`, `release.py` and the method rely on."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULESET = json.loads((ROOT / "plugins/app/ruleset.json").read_text(encoding="utf-8"))
RULES = {rule["type"]: rule.get("parameters", {}) for rule in RULESET["rules"]}
SCRIPTS = (
    ROOT / "plugins/app/skills/run-entry/scripts/merge.py",
    ROOT / "plugins/app/skills/run-batch/scripts/release.py",
)


class Ruleset(unittest.TestCase):
    def test_it_covers_the_default_branch_and_nobody_bypasses_it(self):
        self.assertEqual(RULESET["target"], "branch")
        self.assertEqual(RULESET["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"])
        self.assertEqual(RULESET["bypass_actors"], [])
        self.assertEqual(RULESET["enforcement"], "active")
        self.assertTrue(RULESET["name"])

    def test_every_parameter_github_requires_is_there(self):
        self.assertLessEqual(
            {
                "dismiss_stale_reviews_on_push",
                "require_code_owner_review",
                "require_last_push_approval",
                "required_approving_review_count",
                "required_review_thread_resolution",
            },
            set(RULES["pull_request"]),
        )
        self.assertLessEqual(
            {"required_status_checks", "strict_required_status_checks_policy"},
            set(RULES["required_status_checks"]),
        )

    def test_it_allows_every_merge_method_the_scripts_use(self):
        allowed = set(RULES["pull_request"]["allowed_merge_methods"])
        self.assertEqual(allowed, {"rebase", "squash"})
        scripts = "".join(path.read_text(encoding="utf-8") for path in SCRIPTS)
        for method in ("merge", "rebase", "squash"):
            used = f'"--{method}"' in scripts
            self.assertEqual(used, method in allowed, method)

    def test_it_asks_for_no_approval(self):
        self.assertEqual(RULES["pull_request"]["required_approving_review_count"], 0)

    def test_merge_py_need_not_bring_the_branch_up_to_date(self):
        self.assertIs(RULES["required_status_checks"]["strict_required_status_checks_policy"], False)

    def test_it_requires_a_check_of_github_actions(self):
        checks = RULES["required_status_checks"]["required_status_checks"]
        self.assertTrue(checks)
        for check in checks:
            self.assertTrue(check["context"])
            self.assertEqual(check["integration_id"], 15368)

    def test_main_is_neither_deleted_nor_rewritten(self):
        self.assertIn("deletion", RULES)
        self.assertIn("non_fast_forward", RULES)


if __name__ == "__main__":
    unittest.main()
