from vault_agent.packet import PacketError, parse_packet
import unittest


def valid_packet(language: str = "en") -> str:
    return f'''---
type: source
source_type: conversation
source_role: personal
credibility: low
status: captured
captured: 2026-08-04
content_language: {language}
tags:
  - flow/inbox
aliases: []
created: 2026-08-04
updated: 2026-08-04
---

# Conversation: Test capture

## Provenance

- Platform: Test
- Conversation date: 2026-08-04

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


class PacketTests(unittest.TestCase):
    def test_parses_a_valid_packet(self):
        packet = parse_packet(valid_packet())

        self.assertEqual(packet.content_language, "en")
        self.assertEqual(packet.title, "Conversation: Test capture")


    def test_rejects_a_packet_without_content_language(self):
        with self.assertRaisesRegex(PacketError, "content_language"):
            parse_packet(valid_packet().replace("content_language: en\n", ""))
