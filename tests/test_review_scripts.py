"""Tests for the reviewers' scripts — run with `python3 -m unittest discover -s tests`."""

import json
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/app/scripts"


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def script(repo, name, *args, stdin=None):
    return subprocess.run(
        ["bash", str(SCRIPTS / name), *args], cwd=repo, capture_output=True, text=True, input=stdin
    )


class BranchFilesTest(unittest.TestCase):
    """`files` lists what the branch and the working tree changed, in the project of the
    working directory, narrowed by the lane's own expressions."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = Path(self.folder.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "README.md").write_text("x\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feat/x")
        (self.repo / "src").mkdir()
        (self.repo / "e2e").mkdir()
        (self.repo / "src" / "a.ts").write_text("a\n")
        (self.repo / "e2e" / "b.test.ts").write_text("b\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "work")
        (self.repo / "docs.md").write_text("untracked\n")

    def tearDown(self):
        self.folder.cleanup()

    def files(self, *args):
        result = script(self.repo, "branch.sh", "files", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.split()

    def test_the_branch_and_the_untracked_work_are_listed(self):
        self.assertEqual(self.files(), ["docs.md", "e2e/b.test.ts", "src/a.ts"])

    def test_a_lane_narrows_with_match_and_exclude(self):
        self.assertEqual(self.files("--match", r"\.ts$", "--exclude", "^e2e/"), ["src/a.ts"])

    def test_uncommitted_only_drops_the_branch(self):
        self.assertEqual(self.files("--uncommitted-only"), ["docs.md"])

    def test_an_unknown_filter_is_a_usage_error(self):
        self.assertEqual(script(self.repo, "branch.sh", "files", "--rust").returncode, 2)

    def test_log_takes_no_flags_since_some_write_files(self):
        self.assertEqual(script(self.repo, "branch.sh", "log", "--output=x").returncode, 2)
        self.assertIn("work", script(self.repo, "branch.sh", "log").stdout)


class ReviewPathTest(unittest.TestCase):
    """Each report of a day gets the next number, under the project's `.review/`."""

    def test_the_next_report_number_follows_the_last(self):
        with tempfile.TemporaryDirectory() as folder:
            first = script(folder, "review-path.sh", "reviewer-guides").stdout.strip()
            today = date.today().isoformat()
            self.assertEqual(first, f".review/reviewer-guides-{today}-01.md")
            (Path(folder) / first).write_text("report\n")
            second = script(folder, "review-path.sh", "reviewer-guides").stdout.strip()
            self.assertEqual(second, f".review/reviewer-guides-{today}-02.md")


class ReviewLanesTest(unittest.TestCase):
    """The lanes a change needs, from its paths: the defaults of a Tauri + React app, and
    the project's own paths from `.claude/daneel.json`."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def settings(self, value):
        (self.repo / ".claude").mkdir(exist_ok=True)
        (self.repo / ".claude" / "daneel.json").write_text(json.dumps(value))

    def lanes(self, *paths, json_out=False):
        result = script(self.repo, "review-lanes.sh", *(["--json"] if json_out else []), stdin="\n".join(paths) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if json_out else result.stdout.split()

    def test_documents_no_reviewer_reads_fire_nothing(self):
        self.assertEqual(self.lanes("README.md", "docs/README.md", "screenshots/a.png"), [])
        self.assertEqual(self.lanes("docs/spec/README.md", "docs/contracts/README.md"), [])

    def test_rust_and_typescript_fire_their_lane_and_arch(self):
        self.assertEqual(self.lanes("src-tauri/src/context/a/domain.rs"), ["backend", "arch"])
        self.assertEqual(self.lanes("src/features/a/gateway.ts"), ["frontend", "arch"])

    def test_an_e2e_scenario_and_a_root_config_are_not_the_frontend(self):
        self.assertEqual(self.lanes("e2e/a/a.test.ts"), ["e2e"])
        self.assertEqual(self.lanes("vite.config.ts"), [])

    def test_the_ipc_boundary_is_security(self):
        self.assertEqual(self.lanes("src-tauri/src/context/a/api.rs"), ["backend", "arch", "security"])
        self.assertEqual(self.lanes("src-tauri/capabilities/default.json"), ["infra", "security"])
        self.assertIn("security", self.lanes("src-tauri/src/core/specta_builder.rs"))

    def test_a_migration_is_sql(self):
        self.assertEqual(self.lanes("src-tauri/migrations/20260927_x.sql"), ["sql"])

    def test_tooling_and_gate_files_are_infra(self):
        for path in (".github/workflows/e2e.yml", "justfile", "scripts/harness.sh", "scripts/capture.mjs",
                     ".githooks/pre-commit", "required-checks.json", ".claude/settings.json"):
            self.assertEqual(self.lanes(path), ["infra"], path)
        self.assertEqual(self.lanes("scripts/tests/test_merge.py"), [])

    def test_specs_contracts_and_adrs_fire_their_reviewers(self):
        self.assertEqual(
            self.lanes("docs/spec/a.md", "docs/contracts/a-contract.md", "docs/adr/003-x.md"),
            ["spec", "contract", "adr"],
        )

    def test_the_guides_are_flow_audit_s(self):
        self.assertEqual(self.lanes("CLAUDE.md"), ["guides"])
        self.assertEqual(self.lanes(".claude/skills/run-entry/SKILL.md"), ["guides"])
        self.assertEqual(self.lanes("docs/workflow.md"), [])
        self.settings({"flow-audit": {"guides": ["docs/workflow.md", "docs/*-rules.md"]}})
        self.assertEqual(self.lanes("docs/workflow.md"), ["guides"])
        self.assertEqual(self.lanes("docs/backend-rules.md"), ["guides"])
        self.assertEqual(self.lanes("CLAUDE.md"), [])

    def test_a_project_adds_its_own_paths_to_a_lane(self):
        self.settings({"review": {"lanes": {
            "infra": ["^tools/[^/]*\\.sh$", "^\\.claude/agents/[^/]*\\.md$"],
            "security": ["^src-tauri/src/auth/"],
        }}})
        self.assertEqual(self.lanes("tools/seed.sh"), ["infra"])
        self.assertEqual(self.lanes(".claude/agents/reviewer-sql.md"), ["infra", "guides"])
        self.assertEqual(self.lanes("src-tauri/src/auth/token.rs"), ["backend", "arch", "security"])
        self.assertEqual(self.lanes("justfile"), ["infra"])

    def test_an_unknown_lane_is_an_error(self):
        self.settings({"review": {"lanes": {"rust": ["x"]}}})
        result = script(self.repo, "review-lanes.sh", stdin="x\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("rust", result.stderr)

    def test_json_names_every_lane_of_the_agents(self):
        out = self.lanes("src-tauri/src/lib.rs", json_out=True)
        self.assertEqual(
            list(out),
            ["backend", "frontend", "arch", "sql", "infra", "security", "e2e", "spec", "contract", "adr", "guides"],
        )
        self.assertEqual([lane for lane, on in out.items() if on], ["backend", "arch"])
        agents = SCRIPTS.parent / "agents"
        for lane in out:
            name = {"spec": "spec-reviewer", "contract": "contract-reviewer", "adr": "adr-reviewer"}.get(lane, f"reviewer-{lane}")
            self.assertTrue((agents / f"{name}.md").exists(), name)


if __name__ == "__main__":
    unittest.main()
