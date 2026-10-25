"""Every doc an agent reads stays under its word ceiling (`doc-ceilings.json`): a doc that
grows past it fails CI. A ceiling is lowered when its doc shrinks, raised only by the owner."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CEILINGS = json.loads((ROOT / "doc-ceilings.json").read_text(encoding="utf-8"))["words"]


def agent_docs() -> list[str]:
    """Every `.md` under `plugins/` but the READMEs (written for people) and links to another
    doc, and the root `CLAUDE.md`."""
    found = [
        str(path.relative_to(ROOT))
        for path in (ROOT / "plugins").rglob("*.md")
        if path.name != "README.md" and not path.is_symlink()
    ]
    return sorted(found) + ["CLAUDE.md"]


def words(doc: str) -> int:
    return len((ROOT / doc).read_text(encoding="utf-8").split())


class DocCeilings(unittest.TestCase):
    def test_every_agent_doc_has_a_ceiling_and_every_ceiling_a_doc(self):
        self.assertEqual(sorted(CEILINGS), sorted(agent_docs()))

    def test_no_doc_is_over_its_ceiling(self):
        over = {doc: f"{words(doc)} words, ceiling {CEILINGS[doc]}"
                for doc in agent_docs() if doc in CEILINGS and words(doc) > CEILINGS[doc]}
        self.assertEqual(over, {}, "trim the doc; a ceiling is raised only by the owner")

    def test_a_ceiling_follows_its_doc_down(self):
        slack = {doc: f"{words(doc)} words, ceiling {CEILINGS[doc]}"
                 for doc in agent_docs() if doc in CEILINGS and words(doc) < CEILINGS[doc]}
        self.assertEqual(slack, {}, "lower the ceiling to the doc's count")


if __name__ == "__main__":
    unittest.main()
