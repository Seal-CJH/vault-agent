from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.session import SessionStore
from vault_agent.vault_index import VaultIndex


class FakeProvider:
    def __init__(self): self.messages = None
    def stream(self, messages, confirmed): self.messages = messages; return iter(["reply"])


class SessionTests(unittest.TestCase):
    def test_persists_a_draft_outside_the_vault(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()
            store = SessionStore(root / ".state" / "sessions", index)
            session = store.create("en")

            stored = store.save_draft(session.id, "# Proposed packet")

            self.assertEqual(store.load_draft(session.id), "# Proposed packet")
            self.assertEqual(stored, root / ".state" / "drafts" / f"{session.id}.md")
            self.assertFalse((root / "01_Inbox").exists())

    def test_persists_history_and_compiles_vault_context_for_each_turn(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("# Vault rules\nKeep links consistent.", encoding="utf-8")
            (root / "03_Wiki" / "Claims").mkdir(parents=True)
            (root / "03_Wiki" / "Claims" / "continuity.md").write_text("# Continuity\nNew knowledge should connect to existing claims.", encoding="utf-8")
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()
            store = SessionStore(root / ".sessions", index)
            session = store.create("zh-CN")
            provider = FakeProvider()

            reply = "".join(store.turn(session.id, provider, "How should I connect this?"))
            restored = store.load(session.id)

            self.assertEqual(reply, "reply")
            self.assertEqual(len(restored.messages), 2)
            self.assertIn("Vault rules", provider.messages[0]["content"])
            self.assertIn("Continuity", provider.messages[0]["content"])
            self.assertEqual(provider.messages[-1]["content"], "How should I connect this?")
