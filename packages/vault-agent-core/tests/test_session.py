from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.session import SessionStore
from vault_agent.sources import SourceMaterial
from vault_agent.vault_index import VaultIndex


class FakeProvider:
    def __init__(self): self.messages = None
    def stream(self, messages, confirmed): self.messages = messages; return iter(["reply"])


class SessionTests(unittest.TestCase):
    def test_prepares_new_source_metadata_for_client_events(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()
            material = SourceMaterial("article", "Visible title", "Author", "https://example.test/a", "en", "Body")
            store = SessionStore(root / ".sessions", index, source_inspector=lambda **_: material)
            session = store.create("en")

            sources = store.prepare_sources(session.id, "Read https://example.test/a")

            self.assertEqual(sources, [{"kind": "article", "title": "Visible title", "provenance": "https://example.test/a", "content_language": "en"}])

    def test_keeps_previously_inspected_source_material_available_in_later_turns(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()
            material = SourceMaterial("article", "Source title", "Author", "https://example.test/a", "en", "Persistent source body.")
            store = SessionStore(root / ".sessions", index, source_inspector=lambda **_: material)
            session = store.create("en")
            first = FakeProvider()
            second = FakeProvider()

            "".join(store.turn(session.id, first, "Read https://example.test/a"))
            "".join(store.turn(session.id, second, "How does this connect?"))

            self.assertIn("Persistent source body.", second.messages[0]["content"])

    def test_lists_local_sessions_newest_first_without_reading_the_vault(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()
            store = SessionStore(root / ".state" / "sessions", index)
            first = store.create("en")
            first.messages.append({"role": "user", "content": "First discussion"})
            store._save(first)
            second = store.create("zh-CN")
            second.messages.append({"role": "user", "content": "第二个讨论"})
            store._save(second)

            summaries = store.list()

            self.assertEqual([summary["id"] for summary in summaries], [second.id, first.id])
            self.assertEqual(summaries[0]["preview"], "第二个讨论")
            self.assertEqual(summaries[1]["source_language"], "en")

    def test_attaches_inspected_source_material_to_the_vault_aware_turn(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            index = VaultIndex(root, root / ".vault-agent.sqlite")
            index.rebuild()
            material = SourceMaterial("article", "Source title", "Author", "https://example.test/a", "en", "Source body.")
            store = SessionStore(root / ".sessions", index, source_inspector=lambda **_: material)
            session = store.create("zh-CN")
            provider = FakeProvider()

            "".join(store.turn(session.id, provider, "Discuss https://example.test/a"))

            self.assertIn("<source-material", provider.messages[0]["content"])
            self.assertIn("Source body.", provider.messages[0]["content"])
            self.assertIn("known source-material language over the declared default", provider.messages[0]["content"])
            self.assertEqual(store.load(session.id).sources[0]["provenance"], "https://example.test/a")

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
