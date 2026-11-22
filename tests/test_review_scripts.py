"""Tests for the reviewers' scripts — run with `python3 -m unittest discover -s tests`."""

import json
import re
import shutil
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

    def test_the_spec_contract_and_adr_folders_follow_the_project_s_readmes(self):
        self.settings({"review": {"rules": {
            "spec": ["specs/README.md", "docs/glossary.md"], "contract": ["api/contracts/README.md"], "adr": ["decisions/README.md"],
        }}})
        self.assertEqual(self.lanes("specs/orders.md", "api/contracts/orders.md", "decisions/003-x.md"), ["spec", "contract", "adr"])
        # Each kind's README is its conventions, not a document of it; the defaults still fire.
        self.assertEqual(self.lanes("specs/README.md", "api/contracts/README.md"), [])
        self.assertEqual(self.lanes("docs/spec/a.md", "docs/adr/003-x.md"), ["spec", "adr"])

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

    def test_an_unknown_review_key_is_an_error(self):
        self.settings({"review": {"lane": {"infra": ["x"]}}})
        result = script(self.repo, "review-lanes.sh", stdin="x\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("lane", result.stderr)

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


LANES = ["backend", "frontend", "arch", "sql", "infra", "security", "e2e", "spec", "contract", "adr", "guides"]


class SessionPiece(unittest.TestCase):
    """A project's checkout with the plugin checked out inside it, as a CI job has it:
    `.plugin/plugins/app/`, untracked. The base branch is `trunk`; the commit under review
    is checked out detached."""

    BASE_SETTINGS = {"review": {
        "rules": {"backend": ["docs/backend-rules.md"], "spec": ["specs/README.md"]},
        "glossary": "docs/glossary.md",
    }}

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = Path(self.folder.name).resolve() / "project"
        self.repo.mkdir()
        self.tree = self.repo.parent / "tree"
        git(self.repo, "init", "-q", "-b", "trunk")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        self.write("CLAUDE.md", "base rules\n")
        self.write(".claude/daneel.json", json.dumps(self.BASE_SETTINGS))
        self.write(".claude/settings.json", "{}\n")
        self.write("docs/backend-rules.md", "base backend rules\n")
        self.write("docs/glossary.md", "base glossary\n")
        self.write("specs/README.md", "base spec conventions\n")
        self.write("src/a.rs", "fn a() {}\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feat/x")
        self.write("CLAUDE.md", "loosened rules\n")
        self.write(".claude/daneel.json", "{}\n")
        self.write(".claude/skills/x/SKILL.md", "a skill the branch brings\n")
        self.write("docs/backend-rules.md", "loosened backend rules\n")
        self.write("docs/contracts/README.md", "conventions the branch adds\n")
        self.write("src/a.rs", "fn a() { b() }\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "work")
        git(self.repo, "checkout", "-q", "--detach", "feat/x")
        shutil.copytree(SCRIPTS, self.repo / ".plugin/plugins/app/scripts", ignore=shutil.ignore_patterns("__pycache__"))

    def tearDown(self):
        self.folder.cleanup()

    def write(self, path, text):
        file = self.repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")

    def read(self, path):
        return (self.repo / path).read_text(encoding="utf-8")

    def piece(self, name, *args):
        return subprocess.run(
            ["bash", f".plugin/plugins/app/scripts/{name}", *args], cwd=self.repo, capture_output=True, text=True
        )


class ReviewToolsTest(SessionPiece):
    """What a reviewer's session is granted: one line for `--allowedTools`."""

    def tools(self, lane):
        result = self.piece("review-tools.sh", lane)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("\n"), 1)
        entries = re.findall(r'"([^"]*)"', result.stdout)
        self.assertEqual(result.stdout.strip(), " ".join(f'"{entry}"' for entry in entries))
        return entries

    def test_the_report_is_granted_from_the_current_folder_and_from_the_root(self):
        """A session that changed folder before writing still writes its report."""
        tools = self.tools("backend")
        self.assertIn("Edit(.review/**)", tools)
        self.assertIn(f"Edit(/{self.repo}/.review/**)", tools)
        self.assertNotIn("Write", " ".join(tools))

    def test_the_helpers_are_granted_under_both_spellings(self):
        tools = self.tools("backend")
        for helper in ("branch.sh", "review-path.sh"):
            self.assertIn(f"Bash(bash .plugin/plugins/app/scripts/{helper} *)", tools)
            self.assertIn(f"Bash(bash {self.repo}/.plugin/plugins/app/scripts/{helper} *)", tools)

    def test_it_reads_and_runs_no_interpreter(self):
        tools = self.tools("frontend")
        self.assertEqual(tools[:3], ["Read", "Grep", "Glob"])
        commands = [tool[5:-1].split()[0] for tool in tools if tool.startswith("Bash(")]
        self.assertEqual(sorted(set(commands)), ["bash", "git", "grep", "head", "ls", "tail", "wc"])
        granted_bash = [tool for tool in tools if tool.startswith("Bash(bash ")]
        self.assertTrue(all("/scripts/branch.sh *" in tool or "/scripts/review-path.sh *" in tool for tool in granted_bash))
        writers = [tool for tool in tools if re.match(r"Bash\(git (push|commit|checkout|reset|add|rm|fetch|pull|config|clone)", tool)]
        self.assertEqual(writers, [])

    def test_only_the_infra_lane_reaches_the_network_and_only_for_tags(self):
        remote = "Bash(git ls-remote --tags https://github.com/*)"
        self.assertIn(remote, self.tools("infra"))
        for lane in LANES:
            if lane != "infra":
                self.assertNotIn(remote, self.tools(lane), lane)

    def test_an_unknown_lane_or_no_lane_is_a_usage_error(self):
        self.assertEqual(self.piece("review-tools.sh", "rust").returncode, 2)
        self.assertEqual(self.piece("review-tools.sh").returncode, 2)


class ReviewPrepareTest(SessionPiece):
    """What judges a pull request comes from the base branch; the commit under review is
    read from a tree of its own."""

    def prepare(self, base="trunk"):
        return self.piece("review-prepare.sh", base, str(self.tree))

    def test_what_judges_the_pull_request_is_the_base_branch_s(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("CLAUDE.md"), "base rules\n")
        self.assertEqual(json.loads(self.read(".claude/daneel.json")), self.BASE_SETTINGS)
        self.assertEqual(self.read("docs/backend-rules.md"), "base backend rules\n")
        self.assertEqual(self.read("docs/glossary.md"), "base glossary\n")
        self.assertEqual(self.read("specs/README.md"), "base spec conventions\n")
        # What the base branch does not have is no rule yet: a skill, a kind's README.
        self.assertFalse((self.repo / ".claude/skills").exists())
        self.assertFalse((self.repo / "docs/contracts/README.md").exists())
        # The code under review is untouched.
        self.assertEqual(self.read("src/a.rs"), "fn a() { b() }\n")
        self.assertEqual(result.stdout.splitlines(), [
            "from the base branch: CLAUDE.md",
            "from the base branch: .claude",
            "from the base branch: docs/backend-rules.md",
            "from the base branch: specs/README.md",
            "from the base branch: docs/glossary.md",
            "not on the base branch, removed: docs/contracts/README.md",
            "not on the base branch, removed: docs/adr/README.md",
        ])

    def test_the_commit_under_review_is_read_from_its_own_tree(self):
        self.assertEqual(self.prepare().returncode, 0)
        self.assertEqual((self.tree / "CLAUDE.md").read_text(), "loosened rules\n")
        self.assertEqual((self.tree / "docs/backend-rules.md").read_text(), "loosened backend rules\n")
        self.assertEqual((self.tree / "docs/contracts/README.md").read_text(), "conventions the branch adds\n")
        # Its skills and agents never load into the session.
        self.assertFalse((self.tree / ".claude/skills").exists())
        self.assertTrue((self.repo / ".review").is_dir())

    def test_the_branch_helper_measures_from_the_base_and_skips_the_plugin(self):
        self.assertEqual(self.prepare().returncode, 0)
        shown = subprocess.run(["git", "rev-parse", "main", "trunk"], cwd=self.repo, capture_output=True, text=True).stdout.split()
        self.assertEqual(shown[0], shown[1])
        files = self.piece("branch.sh", "files").stdout.split()
        self.assertEqual(files, [".claude/daneel.json", ".claude/skills/x/SKILL.md", "CLAUDE.md",
                                 "docs/backend-rules.md", "docs/contracts/README.md", "src/a.rs"])
        self.assertIn("b()", self.piece("branch.sh", "diff", "src/a.rs").stdout)

    def refused(self, result, words):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(words, result.stderr)
        self.assertEqual(self.read("CLAUDE.md"), "loosened rules\n")
        self.assertFalse((self.repo / ".review").exists())

    def test_a_checkout_with_uncommitted_work_is_refused_and_left_alone(self):
        self.write("src/a.rs", "work in progress\n")
        self.refused(self.prepare(), "uncommitted work")
        self.assertEqual(self.read("src/a.rs"), "work in progress\n")
        self.assertFalse(self.tree.exists())

    def test_a_base_git_does_not_know_is_refused(self):
        self.refused(self.prepare("origin/trunk"), "is not a commit here")

    def test_a_tree_that_exists_or_sits_in_the_checkout_is_refused(self):
        self.refused(self.piece("review-prepare.sh", "trunk", str(self.repo / "tree")), "inside the checkout")
        self.refused(self.piece("review-prepare.sh", "trunk", str(self.repo.parent / "nowhere/tree")), "does not exist")
        self.tree.mkdir()
        self.refused(self.prepare(), "exists already")

    def test_a_checkout_on_main_is_refused(self):
        git(self.repo, "checkout", "-qb", "main")
        self.refused(self.prepare(), "on main")

    def test_settings_that_name_a_path_outside_the_checkout_are_refused(self):
        git(self.repo, "checkout", "-q", "trunk")
        self.write(".claude/daneel.json", json.dumps({"review": {"glossary": "../elsewhere.md"}}))
        git(self.repo, "commit", "-qam", "a path outside")
        git(self.repo, "checkout", "-q", "--detach", "feat/x")
        self.refused(self.prepare(), "could not be read")

    def test_it_takes_a_base_and_a_tree(self):
        self.assertEqual(self.piece("review-prepare.sh", "trunk").returncode, 2)


class ReviewPromptTest(SessionPiece):
    """The instruction a reviewer's session is given."""

    def prompt(self, lane):
        result = self.piece("review-prompt.sh", lane, "/tmp/acme-tree/")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_it_names_the_agent_file_the_plugin_the_tree_and_the_report(self):
        prompt = self.prompt("backend")
        self.assertIn("Read `.plugin/plugins/app/agents/reviewer-backend.md` and follow it exactly, in its default changed-lines mode,", prompt)
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}` in it is `.plugin/plugins/app`", prompt)
        self.assertIn("in `/tmp/acme-tree/`: the branch's tree as pushed", prompt)
        self.assertIn("`bash .plugin/plugins/app/scripts/review-path.sh reviewer-backend` prints", prompt)
        self.assertIn("Post nothing yourself", prompt)

    def test_every_lane_is_given_an_agent_file_that_exists(self):
        agents = SCRIPTS.parent / "agents"
        for lane in LANES:
            name = re.search(r"agents/([\w-]+)\.md", self.prompt(lane)).group(1)
            self.assertTrue((agents / f"{name}.md").exists(), name)
            self.assertIn(f"review-path.sh reviewer-{lane}`", self.prompt(lane))

    def test_a_document_lane_is_pointed_at_its_folder_s_changed_files(self):
        # The folder is the project's, read from the base branch's settings once the
        # checkout is prepared: here the spec README is `specs/README.md`.
        self.assertEqual(self.piece("review-prepare.sh", "trunk", str(self.tree)).returncode, 0)
        self.assertIn("agents/spec-reviewer.md` and follow it exactly, on each file under `specs/` that the pull request changed", self.prompt("spec"))
        self.assertIn("on each file under `docs/contracts/` that the pull request changed, its README aside, one after the other, against its spec", self.prompt("contract"))
        self.assertIn("agents/adr-reviewer.md` and follow it exactly, on each file under `docs/adr/`", self.prompt("adr"))

    def test_a_spec_kept_in_its_own_repository_is_said_to_the_lanes_that_read_it(self):
        """CI has no access to such a spec: the lanes that check against it say so and
        check the rest; the code lanes are told nothing."""
        absent = "keeps its spec in a repository of its own, which is not in this checkout"
        self.assertNotIn(absent, self.prompt("contract"))
        self.write(".claude/daneel.json", json.dumps({"spec-proposal": {"repo": "acme/app-spec"}}))
        for lane in ("spec", "contract", "adr"):
            self.assertIn(absent, self.prompt(lane), lane)
            self.assertIn("report no finding on its absence", self.prompt(lane))
        for lane in ("backend", "frontend", "infra", "guides"):
            self.assertNotIn(absent, self.prompt(lane), lane)

    def test_a_spec_proposal_key_no_piece_reads_is_refused(self):
        self.write(".claude/daneel.json", json.dumps({"spec-proposal": {"repo": "acme/app-spec", "branch": "main"}}))
        result = self.piece("review-prompt.sh", "backend", "/tmp/acme-tree")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown spec-proposal settings", result.stderr)
        self.assertIn("branch", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_an_unknown_lane_or_a_missing_tree_is_a_usage_error(self):
        self.assertEqual(self.piece("review-prompt.sh", "rust", "/tmp/acme-tree").returncode, 2)
        self.assertEqual(self.piece("review-prompt.sh", "backend").returncode, 2)


class TheLanes(unittest.TestCase):
    def test_every_piece_knows_the_same_lanes(self):
        for name in ("review-lanes.sh", "review-tools.sh", "review-prompt.sh"):
            listed = re.search(r"^LANES=\((.*)\)$", (SCRIPTS / name).read_text(encoding="utf-8"), re.MULTILINE).group(1)
            self.assertEqual(listed.split(), LANES, name)


if __name__ == "__main__":
    unittest.main()
