from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import hashlib

from vault_agent.cli import main
from test_staging import PACKET


class CliTests(unittest.TestCase):
    def test_emits_a_read_only_vault_review(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "01_Inbox").mkdir()
            (root / "01_Inbox" / "capture.md").write_text("# Capture", encoding="utf-8")
            from io import StringIO
            from contextlib import redirect_stdout
            output = StringIO()

            with patch("vault_agent.cli.Path.home", return_value=root), redirect_stdout(output):
                self.assertEqual(main(["review", "--vault", str(root)]), 0)

            self.assertIn('"inbox_notes": ["01_Inbox/capture.md"]', output.getvalue())

    def test_lists_and_loads_sessions_for_a_vault(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            vault.mkdir()
            fingerprint = hashlib.sha256(str(vault.resolve()).encode("utf-8")).hexdigest()[:16]
            state = root / "Library" / "Application Support" / "Vault Agent" / "vaults" / fingerprint / "sessions"
            state.mkdir(parents=True)
            session_id = "local-session"
            (state / f"{session_id}.json").write_text('{"id":"local-session","source_language":"en","messages":[{"role":"user","content":"Resume this"}]}', encoding="utf-8")
            from io import StringIO
            from contextlib import redirect_stdout
            output = StringIO()

            with patch("vault_agent.cli.Path.home", return_value=root), redirect_stdout(output):
                self.assertEqual(main(["session", "list", "--vault", str(vault)]), 0)
                self.assertEqual(main(["session", "show", "--vault", str(vault), "--session-id", session_id]), 0)

            self.assertIn('"preview": "Resume this"', output.getvalue())
            self.assertIn('"id": "local-session"', output.getvalue())

    def test_inspects_a_book_without_provider_or_vault_write(self):
        from io import StringIO
        from contextlib import redirect_stdout

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["source", "inspect", "--kind", "book", "--title", "The Book", "--excerpt", "Reader note.", "--source-language", "en"]), 0)

        self.assertIn('"kind": "book"', output.getvalue())
        self.assertIn('"text": "Reader note."', output.getvalue())

    def test_stage_previews_without_apply(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root / "packet.md"
            packet.write_text(PACKET, encoding="utf-8")

            self.assertEqual(main(["stage", "--vault", str(root), "--packet", str(packet)]), 0)
            self.assertFalse((root / "01_Inbox").exists())
