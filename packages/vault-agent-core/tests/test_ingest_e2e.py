from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.draft import prepare_draft
from vault_agent.session import SessionStore
from vault_agent.sources import SourceMaterial
from vault_agent.staging import stage_packet
from vault_agent.vault_index import VaultIndex


PACKET = '''---
type: source
source_type: article
source_role: primary
credibility: medium
status: captured
captured: 2026-08-04
content_language: en
tags:
  - LLM
  - flow/inbox
aliases:
  - 大语言模型
created: 2026-08-04
updated: 2026-08-04
---

# Source: Knowledge continuity

## Provenance

- URL: https://example.test/article

## Ingest Proposal

### Source Record

- Preserve the source as English evidence.

### Related Questions

- [[Knowledge continuity]]

### Claim Updates

- New Claim: Retrieval makes new evidence easier to connect to existing judgment.

### Action Candidates

- Experiment: Test contextual retrieval during one week of capture.

### Map Updates

- [[agent]]

### Do Not Promote

- The draft does not promote a core Wiki object automatically.
'''

CHINESE_PACKET = '''---
type: source
source_type: article
source_role: primary
credibility: medium
status: captured
captured: 2026-08-05
content_language: zh-CN
tags:
  - LLM
  - flow/inbox
aliases:
  - 大语言模型
created: 2026-08-05
updated: 2026-08-05
---

# Source: 知识连续性

## Provenance

- URL: https://example.test/chinese-article

## Ingest Proposal

### Source Record

- 保留中文来源的原始语义，不翻译为英文。

### Related Questions

- [[知识连续性]]

### Claim Updates

- New Claim: 新材料需要与已有判断建立连接。

### Action Candidates

- Experiment: 用一周时间验证上下文检索是否改善连接质量。

### Map Updates

- [[agent]]

### Do Not Promote

- 不自动写入核心 Wiki 对象。
'''


class DiscussionProvider:
    model = "deepseek-v4-flash"
    thinking = False
    reasoning_effort = "medium"

    def stream(self, messages, confirmed):
        self.messages = messages
        self.confirmed = confirmed
        return iter(["Discussed source."])


class PacketProvider:
    model = "deepseek-v4-flash"
    thinking = False
    reasoning_effort = "medium"

    def complete(self, messages, confirmed):
        self.messages = messages
        self.confirmed = confirmed
        return PACKET


class ChinesePacketProvider(PacketProvider):
    def complete(self, messages, confirmed):
        self.messages = messages
        self.confirmed = confirmed
        return CHINESE_PACKET


class IngestEndToEndTests(unittest.TestCase):
    def test_english_source_discussion_becomes_a_confirmed_inbox_capture(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("# Rules\nUse [[LLM]] and [[agent]] as canonical terms.", encoding="utf-8")
            (root / "03_Wiki").mkdir(parents=True)
            (root / "03_Wiki" / "knowledge-continuity.md").write_text("# Knowledge continuity\nConnect evidence to judgment.", encoding="utf-8")
            index = VaultIndex(root, root / ".state" / "index.sqlite")
            index.rebuild()
            source = SourceMaterial("article", "Knowledge continuity", "Fixture Author", "https://example.test/article", "en", "English source text.")
            store = SessionStore(root / ".state" / "sessions", index, source_inspector=lambda **_: source)
            session = store.create("zh-CN")
            discussion = DiscussionProvider()

            reply = "".join(store.turn(session.id, discussion, "Discuss https://example.test/article"))
            packet = prepare_draft(store, session.id, PacketProvider())
            staged = stage_packet(root, packet.raw, apply=True)

            self.assertEqual(reply, "Discussed source.")
            self.assertIn('language="en"', discussion.messages[0]["content"])
            self.assertTrue(staged.written)
            written = staged.path.read_text(encoding="utf-8")
            self.assertIn("content_language: en", written)
            self.assertIn("  - LLM", written)
            self.assertIn("大语言模型", written)
            self.assertTrue(staged.path.is_relative_to(root / "01_Inbox"))

    def test_chinese_source_discussion_preserves_chinese_in_confirmed_inbox_capture(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("# Rules\nUse [[LLM]] and [[agent]] as canonical terms.", encoding="utf-8")
            (root / "03_Wiki").mkdir(parents=True)
            (root / "03_Wiki" / "knowledge-continuity.md").write_text("# 知识连续性\n连接新的资料与已有判断。", encoding="utf-8")
            index = VaultIndex(root, root / ".state" / "index.sqlite")
            index.rebuild()
            source = SourceMaterial("article", "知识连续性", "测试作者", "https://example.test/chinese-article", "zh-CN", "中文来源原文。")
            store = SessionStore(root / ".state" / "sessions", index, source_inspector=lambda **_: source)
            session = store.create("en")
            discussion = DiscussionProvider()

            reply = "".join(store.turn(session.id, discussion, "讨论 https://example.test/chinese-article"))
            packet = prepare_draft(store, session.id, ChinesePacketProvider())
            staged = stage_packet(root, packet.raw, apply=True)

            self.assertEqual(reply, "Discussed source.")
            self.assertIn('language="zh-CN"', discussion.messages[0]["content"])
            written = staged.path.read_text(encoding="utf-8")
            self.assertIn("content_language: zh-CN", written)
            self.assertIn("保留中文来源的原始语义", written)
            frontmatter = written.split("---", 2)[1]
            tags = frontmatter.split("tags:\n", 1)[1].split("aliases:", 1)[0]
            self.assertIn("  - LLM", tags)
            self.assertNotIn("大语言模型", tags)
            self.assertIn("aliases:\n  - 大语言模型", frontmatter)
