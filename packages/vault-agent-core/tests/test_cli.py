from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.cli import main
from test_staging import PACKET


class CliTests(unittest.TestCase):
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
