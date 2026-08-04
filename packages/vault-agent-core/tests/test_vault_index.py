from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.vault_index import VaultIndex


class VaultIndexTests(unittest.TestCase):
    def test_indexes_markdown_and_finds_related_content(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00_Meta").mkdir()
            (root / "03_Wiki" / "Claims").mkdir(parents=True)
            (root / "00_Meta" / "Ingest Workflow.md").write_text("# Ingest Workflow\n\nPreserve evidence.", encoding="utf-8")
            (root / "03_Wiki" / "Claims" / "agent-memory.md").write_text(
                "---\ntype: claim\ntags:\n  - domain/ai\naliases:\n  - Agent memory\n---\n# Agent memory\n\nLocal retrieval improves knowledge continuity.", encoding="utf-8"
            )
            (root / ".obsidian").mkdir()
            (root / ".obsidian" / "hidden.md").write_text("must not index", encoding="utf-8")
            index = VaultIndex(root, root / ".vault-agent.sqlite")

            indexed = index.rebuild()
            results = index.search("knowledge continuity")

            self.assertEqual(indexed, 2)
            self.assertEqual(results[0].path, "03_Wiki/Claims/agent-memory.md")
            self.assertEqual(results[0].title, "Agent memory")
            self.assertEqual(results[0].tags, ["domain/ai"])

    def test_extracts_wikilinks_and_makes_them_searchable(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "03_Wiki").mkdir(parents=True)
            (root / "03_Wiki" / "connected.md").write_text(
                "# Connected\n\nSupports [[LLM]] and [[agent|Agent]].\n", encoding="utf-8"
            )
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()

            document = index.search("LLM")[0]

            self.assertEqual(document.links, ["LLM", "agent"])

    def test_returns_always_on_governance_documents(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00_Meta").mkdir()
            (root / "AGENTS.md").write_text("# Rules", encoding="utf-8")
            (root / "Home.md").write_text("# Home", encoding="utf-8")
            (root / "00_Meta" / "Ingest Workflow.md").write_text("# Workflow", encoding="utf-8")
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()

            paths = [document.path for document in index.governance_documents()]

            self.assertEqual(paths, ["AGENTS.md", "Home.md", "00_Meta/Ingest Workflow.md"])
