from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.context import ContextCompiler
from vault_agent.vault_index import VaultIndex


class ContextCompilerTests(unittest.TestCase):
    def test_includes_a_compact_catalog_of_other_vault_notes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "03_Wiki").mkdir(parents=True)
            (root / "03_Wiki" / "decision.md").write_text(
                "---\ntags:\n  - domain/ai\n---\n# Model choice\n\nLinks to [[LLM]].", encoding="utf-8"
            )
            (root / "03_Wiki" / "unrelated.md").write_text("# Reading list\n\nLater material.", encoding="utf-8")
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()

            bundle = ContextCompiler(index).compile("model")

            self.assertIn("<vault-catalog>", bundle.prompt)
            self.assertIn("03_Wiki/unrelated.md | Reading list", bundle.prompt)
            self.assertIn("tags: domain/ai", bundle.prompt)

    def test_includes_a_vault_wide_profile_before_the_catalog(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "01_Inbox").mkdir()
            (root / "03_Wiki" / "Claims").mkdir(parents=True)
            (root / "01_Inbox" / "capture.md").write_text("---\ntags:\n  - flow/inbox\n---\n# Capture\n\nConnect to [[LLM]].", encoding="utf-8")
            (root / "03_Wiki" / "Claims" / "continuity.md").write_text("---\ntags:\n  - domain/ai\n---\n# Continuity\n\nConnect to [[LLM]] and [[agent]].", encoding="utf-8")
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()

            bundle = ContextCompiler(index).compile("new source")

            self.assertIn("<vault-profile>", bundle.prompt)
            self.assertIn("01_Inbox: 1", bundle.prompt)
            self.assertIn("03_Wiki: 1", bundle.prompt)
            self.assertIn("[[LLM]]: 2", bundle.prompt)
            self.assertLess(bundle.prompt.index("<vault-profile>"), bundle.prompt.index("<vault-catalog>"))

    def test_includes_governance_and_related_vault_documents(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00_Meta").mkdir()
            (root / "03_Wiki" / "Claims").mkdir(parents=True)
            (root / "AGENTS.md").write_text("# Rules\n\nPreserve source language.", encoding="utf-8")
            (root / "03_Wiki" / "Claims" / "vault-context.md").write_text("# Vault context\n\nContext keeps new captures connected.", encoding="utf-8")
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()

            bundle = ContextCompiler(index).compile("How should context connect captures?")

            self.assertIn("AGENTS.md", bundle.paths)
            self.assertIn("03_Wiki/Claims/vault-context.md", bundle.paths)
            self.assertIn("Preserve source language.", bundle.prompt)
            self.assertIn("Vault context", bundle.prompt)

    def test_includes_a_relationship_summary_for_retrieved_notes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "03_Wiki").mkdir(parents=True)
            (root / "03_Wiki" / "continuity.md").write_text(
                "# Continuity\n\nConnect to [[LLM]] and [[agent|Agent]].", encoding="utf-8"
            )
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()

            bundle = ContextCompiler(index).compile("continuity")

            self.assertIn("<vault-relationships>", bundle.prompt)
            self.assertIn("03_Wiki/continuity.md → [[LLM]], [[agent]]", bundle.prompt)
