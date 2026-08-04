from pathlib import Path
import unittest

from vault_agent.policy import PolicyError, target_path


class PolicyTests(unittest.TestCase):
    def test_creates_a_dated_inbox_conversation_path(self):
        tmp_path = Path(self._testMethodName)
        self.assertEqual(
            target_path(tmp_path, "A useful conversation", "2026-08-04"),
            tmp_path / "01_Inbox" / "conversations" / "2026-08-04-a-useful-conversation.md",
        )

    def test_rejects_existing_target(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "01_Inbox" / "conversations"
            destination.mkdir(parents=True)
            (destination / "2026-08-04-a-useful-conversation.md").write_text("existing")
            with self.assertRaisesRegex(PolicyError, "already exists"):
                target_path(Path(directory), "A useful conversation", "2026-08-04")
