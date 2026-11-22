"""The rules of `CLAUDE.md` a machine can check, on what a pull request changes and on every
doc. Against BASE_SHA in CI, else against origin/main; with neither, the change rules skip."""

import fnmatch
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INLINE_CODE = re.compile(r"`([^`\n]+)`")
COMMAND = re.compile(r"(git|gh|python3|bash|just|npx|npm|claude) ")
CHAINED = re.compile(r" (&&|\|\|) |; |\$\(")
HEADLESS = [
    "plugins/app/skills/run-entry/SKILL.md",
    "plugins/app/skills/design-proposal/SKILL.md",
    "plugins/app/skills/spec-proposal/SKILL.md",
    "plugins/app/skills/visual-proof/SKILL.md",
    "plugins/app/skills/dep-audit/SKILL.md",
    "plugins/flow/skills/flow-audit/SKILL.md",
]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def base_commit() -> str | None:
    if os.environ.get("BASE_SHA"):
        return os.environ["BASE_SHA"]
    found = git("merge-base", "origin/main", "HEAD")
    return found.stdout.strip() if found.returncode == 0 else None


def version(ref: str, plugin: str) -> str | None:
    shown = git("show", f"{ref}:plugins/{plugin}/.claude-plugin/plugin.json")
    return json.loads(shown.stdout)["version"] if shown.returncode == 0 else None


def changed_plugins(changed: list[str]) -> set[str]:
    return {path.split("/")[1] for path in changed if path.startswith("plugins/")}


def key(number: str) -> tuple[int, ...]:
    return tuple(int(part) for part in number.split("."))


UNRELEASED = "## Unreleased"


def release_fault(plugin: str, before: str | None, now: str, changed: list[str], changelog: str) -> str | None:
    """What a change to a plugin gets wrong about its changelog and its version; None when
    nothing. A version is a coherent set of changes or a batch, released when the owner
    says so: a change adds its line under `## Unreleased`, the changelog's first section,
    and leaves `version` alone; the PR that releases raises `version` (`before` to `now`)
    and names that section `## <plugin> <version> — <date>`. A plugin `before` did not have
    owes its changelog only."""
    if f"plugins/{plugin}/CHANGELOG.md" not in changed:
        return f"plugins/{plugin}/CHANGELOG.md: add the change's line, saying what a project must do"
    if before is None:
        return None
    sections = re.findall(r"^## .*$", changelog, re.MULTILINE)
    first = sections[0] if sections else ""
    if key(now) < key(before):
        return f"plugins/{plugin}: its version went down, {before} to {now}"
    if now == before:
        if first != UNRELEASED:
            return f"plugins/{plugin}/CHANGELOG.md: the line goes under `{UNRELEASED}`, its first section; `version` moves at a release only"
        return None
    if UNRELEASED in sections:
        return f"plugins/{plugin}: `version` moved to {now} and `{UNRELEASED}` is still there: a release names the section"
    if not re.fullmatch(rf"## {re.escape(plugin)} {re.escape(now)} — \d{{4}}-\d{{2}}-\d{{2}}", first):
        return f"plugins/{plugin}/CHANGELOG.md: its first section is not `## {plugin} {now} — <date>`"
    return None


def agent_docs() -> list[Path]:
    return [
        path
        for path in (ROOT / "plugins").rglob("*.md")
        if path.name not in ("README.md", "CHANGELOG.md") and not path.is_symlink()
    ]


def commands(text: str) -> list[tuple[int, str]]:
    """(line, code) for what a doc gives as a command: inline code or a fenced line starting with
    an executable. A rule that names `&&` or `$(...)` is not one."""
    found, fenced = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        for code in [line.strip()] if fenced else INLINE_CODE.findall(line):
            if COMMAND.match(code):
                found.append((number, code))
    return found


class EveryPluginChange(unittest.TestCase):
    def setUp(self):
        self.base = base_commit()
        if self.base is None:
            self.skipTest("no base to compare with")
        listed = git("diff", "--name-only", f"{self.base}...HEAD")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.changed = listed.stdout.split()

    def test_it_adds_its_line_and_leaves_the_version_to_a_release(self):
        for plugin in changed_plugins(self.changed):
            changelog = (ROOT / "plugins" / plugin / "CHANGELOG.md").read_text(encoding="utf-8")
            with self.subTest(plugin):
                self.assertIsNone(release_fault(
                    plugin, version(self.base, plugin), version("HEAD", plugin), self.changed, changelog))


class TheReleaseRule(unittest.TestCase):
    """`release_fault`: a version is a set of changes the owner releases, never one PR."""

    CHANGED = ["plugins/app/loop.md", "plugins/app/CHANGELOG.md"]
    WAITING = "# Changelog — app\n\n## Unreleased\n\n- A new line.\n\n## app 0.14.0 — 2026-11-22\n\n- An old one.\n"
    RELEASED = "# Changelog — app\n\n## app 0.15.0 — 2026-11-30\n\n- A new line.\n\n## app 0.14.0 — 2026-11-22\n\n- An old one.\n"

    def fault(self, before, now, changelog, changed=None):
        return release_fault("app", before, now, self.CHANGED if changed is None else changed, changelog)

    def test_a_change_under_unreleased_with_the_version_left_alone_is_right(self):
        self.assertIsNone(self.fault("0.14.0", "0.14.0", self.WAITING))

    def test_a_release_names_its_section_and_raises_the_version(self):
        self.assertIsNone(self.fault("0.14.0", "0.15.0", self.RELEASED))

    def test_a_change_with_no_changelog_line_is_refused(self):
        self.assertIn("CHANGELOG.md", self.fault("0.14.0", "0.14.0", self.WAITING, ["plugins/app/loop.md"]))

    def test_a_change_whose_line_is_not_under_unreleased_is_refused(self):
        tagged = self.RELEASED.replace("0.15.0 — 2026-11-30", "0.14.1 — 2026-11-30")
        self.assertIn("## Unreleased", self.fault("0.14.0", "0.14.0", tagged))
        # `## Unreleased` under a version already named is not the section being prepared.
        below = self.RELEASED + "\n## Unreleased\n\n- A stray line.\n"
        self.assertIn("## Unreleased", self.fault("0.15.0", "0.15.0", below))

    def test_a_version_that_moves_while_unreleased_stays_is_refused(self):
        self.assertIn("names the section", self.fault("0.14.0", "0.15.0", self.WAITING))

    def test_a_release_whose_section_is_missing_or_undated_is_refused(self):
        self.assertIn("## app 0.15.0", self.fault("0.14.0", "0.15.0", self.RELEASED.replace("0.15.0 — 2026-11-30", "0.15.0")))
        self.assertIn("## app 0.16.0", self.fault("0.14.0", "0.16.0", self.RELEASED))

    def test_a_version_never_goes_down(self):
        self.assertIn("went down", self.fault("0.14.0", "0.13.9", self.WAITING))

    def test_a_new_plugin_owes_only_its_changelog(self):
        self.assertIsNone(self.fault(None, "0.1.0", "# Changelog — app\n\n## app 0.1.0 — 2026-11-30\n\n- The first.\n"))
        self.assertIn("CHANGELOG.md", self.fault(None, "0.1.0", "", ["plugins/app/loop.md"]))


class EveryDoc(unittest.TestCase):
    def test_no_command_chains_another(self):
        chained = [
            f"{doc.relative_to(ROOT)}:{number}: {code}"
            for doc in agent_docs()
            for number, code in commands(doc.read_text(encoding="utf-8"))
            if CHAINED.search(code)
        ]
        self.assertEqual(chained, [], "one command per shell call")

    def test_it_sees_a_chained_command_in_code_and_not_in_prose(self):
        doc = "Run `git pull && git push`, never `$(...)` alone.\n```bash\ngh pr view; gh pr merge\n```\n"
        found = [code for _, code in commands(doc) if CHAINED.search(code)]
        self.assertEqual(found, ["git pull && git push", "gh pr view; gh pr merge"])


def allowed(skill: str) -> list[str] | None:
    """The patterns of a skill's `allowed-tools`, None when it allows every Bash command."""
    front = skill.split("---")[1]
    if re.search(r"^allowed-tools:.*\bBash\b(?!\()", front, re.MULTILINE):
        return None
    return re.findall(r"Bash\((.*)\)", front)


def covered(code: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(code, p) or fnmatch.fnmatchcase(f"{code} ", p) for p in patterns)


class EverySkillThatCanRunHeadless(unittest.TestCase):
    def test_its_allowed_tools_cover_what_it_tells_the_agent_to_run(self):
        missing = []
        for name in HEADLESS:
            skill = (ROOT / name).read_text(encoding="utf-8")
            patterns = allowed(skill)
            if patterns is None:
                continue
            for number, code in commands(skill):
                if code.startswith("just "):
                    if "allow list" not in skill:
                        missing.append(f"{name}:{number}: {code}: say the project's allow list covers it")
                elif not covered(code, patterns):
                    missing.append(f"{name}:{number}: {code}")
        self.assertEqual(missing, [], "a headless run approves nothing")

    def test_it_reads_a_whole_issue(self):
        """Outside a terminal, `gh issue view --comments` prints the comments and not the body."""
        for name in HEADLESS:
            with self.subTest(name):
                self.assertNotRegex((ROOT / name).read_text(encoding="utf-8"), r"gh issue view \S+ --comments")

    def test_a_pattern_covers_what_it_should_and_no_more(self):
        patterns = ["gh issue edit *", "git push -u origin HEAD"]
        self.assertTrue(covered("gh issue edit", patterns))
        self.assertTrue(covered("gh issue edit 3 --add-label x", patterns))
        self.assertTrue(covered("git push -u origin HEAD", patterns))
        self.assertFalse(covered("git push -u origin main", patterns))
        self.assertFalse(covered("gh issue close 3", patterns))

    def test_it_reads_both_forms_of_allowed_tools(self):
        self.assertIsNone(allowed("---\nallowed-tools: Read, Bash\n---\n"))
        self.assertEqual(allowed("---\nallowed-tools:\n  - Bash(git status)\n---\n"), ["git status"])
        self.assertEqual(allowed("---\nname: x\n---\n"), [])


class EveryFile(unittest.TestCase):
    def test_a_project_s_doc_is_named_only_as_a_default(self):
        """A plugin piece reads a project's rules from the docs the project names; a path
        under `docs/` in an agent doc is only ever the default for when the project says
        nothing, or the example value of a `daneel.json` key, so the paragraph that names
        it says `default` or names `daneel.json`."""
        bare = []
        for doc in agent_docs():
            for paragraph in doc.read_text(encoding="utf-8").split("\n\n"):
                if re.search(r"`[^`\n]*docs/", paragraph) and "default" not in paragraph \
                        and "daneel.json" not in paragraph:
                    bare.append(f"{doc.relative_to(ROOT)}: {paragraph.strip()[:80]}")
        self.assertEqual(bare, [])

    def test_it_names_no_project(self):
        """The names are the repository variable PROJECT_NAMES (comma-separated), since listing
        them here would break the rule."""
        names = [name.strip() for name in os.environ.get("PROJECT_NAMES", "").split(",") if name.strip()]
        if not names:
            self.skipTest("PROJECT_NAMES is not set")
        pattern = re.compile("|".join(re.escape(name) for name in names), re.IGNORECASE)
        found = []
        for path in git("ls-files").stdout.split():
            file = ROOT / path
            if file.is_symlink() or not file.is_file():
                continue
            try:
                text = file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if pattern.search(text):
                found.append(path)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
