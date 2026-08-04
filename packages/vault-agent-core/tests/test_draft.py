from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.draft import prepare_draft
from vault_agent.session import SessionStore
from vault_agent.vault_index import VaultIndex


PACKET = '''---
type: source
source_type: conversation
source_role: personal
credibility: low
status: captured
captured: 2026-08-04
content_language: en
tags:
  - flow/inbox
aliases: []
created: 2026-08-04
updated: 2026-08-04
---

# Conversation: Context capture

## Provenance

- Platform: Vault Agent

## Ingest Proposal

### Source Record

- Disposition: Inbox capture

### Related Questions

-

### Claim Updates

- New Claim:

### Action Candidates

- Decision:

### Map Updates

-

### Do Not Promote

-
'''


class FakeProvider:
    def complete(self, messages, confirmed):
        self.messages = messages
        self.confirmed = confirmed
        return PACKET


class DraftTests(unittest.TestCase):
    def test_creates_a_valid_packet_from_a_vault_aware_session(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("# Rules", encoding="utf-8")
            index = VaultIndex(root, root / ".index.sqlite")
            index.rebuild()
            store = SessionStore(root / ".sessions", index)
            session = store.create("en")
            session.messages.append({"role": "user", "content": "Keep this context insight."})
            session.sources.append({"kind": "article", "title": "Source", "provenance": "https://example.test/source", "content_language": "en", "text": "Source text", "author": None, "warnings": []})
            store._save(session)
            provider = FakeProvider()

            draft = prepare_draft(store, session.id, provider)

            self.assertEqual(draft.title, "Conversation: Context capture")
            self.assertTrue(provider.confirmed)
            self.assertIn("Keep this context insight.", provider.messages[0]["content"])
            self.assertIn("https://example.test/source", provider.messages[0]["content"])
            self.assertEqual(len(store.load(session.id).provider_calls), 1)
