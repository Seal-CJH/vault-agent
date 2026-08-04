from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.staging import stage_packet


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

# Conversation: Safe capture

## Provenance

- Platform: Test

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


class StagingTests(unittest.TestCase):
    def test_preview_does_not_write_to_the_vault(self):
        with TemporaryDirectory() as directory:
            result = stage_packet(Path(directory), PACKET, apply=False)

            self.assertFalse(result.written)
            self.assertFalse(result.path.exists())

    def test_apply_writes_only_to_inbox(self):
        with TemporaryDirectory() as directory:
            result = stage_packet(Path(directory), PACKET, apply=True)

            self.assertTrue(result.written)
            self.assertEqual(result.path.parent, Path(directory) / "01_Inbox" / "conversations")
            self.assertEqual(result.path.read_text(encoding="utf-8"), PACKET)
