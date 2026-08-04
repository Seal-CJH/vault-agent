from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.context import ContextCompiler
from vault_agent.vault_index import VaultIndex


class ContextCompilerTests(unittest.TestCase):
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
