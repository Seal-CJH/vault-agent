from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.review import review_vault
from vault_agent.vault_index import VaultIndex


class VaultReviewTests(unittest.TestCase):
    def test_reports_inbox_and_unlinked_long_term_objects(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "01_Inbox").mkdir()
            (root / "03_Wiki").mkdir(parents=True)
            (root / "01_Inbox" / "capture.md").write_text("# Capture", encoding="utf-8")
            (root / "03_Wiki" / "lonely-claim.md").write_text("---\ntype: claim\n---\n# Lonely claim", encoding="utf-8")
            (root / "03_Wiki" / "linked-source.md").write_text("---\ntype: source\n---\n# Linked source\n\n[[Lonely claim]]", encoding="utf-8")
            (root / "03_Wiki" / "lonely-source.md").write_text("---\ntype: source\n---\n# Lonely source", encoding="utf-8")
            (root / "00_Meta" / "Templates").mkdir(parents=True)
            (root / "00_Meta" / "Templates" / "Claim.md").write_text("---\ntype: claim\n---\n# Template", encoding="utf-8")
            index = VaultIndex(root, root / ".state" / "index.sqlite")
            index.rebuild()

            report = review_vault(index)

            self.assertEqual(report.total_notes, 4)
            self.assertEqual(report.inbox_notes, ["01_Inbox/capture.md"])
            self.assertEqual(report.claims_without_links, ["03_Wiki/lonely-claim.md"])
            self.assertEqual(report.sources_without_links, ["03_Wiki/lonely-source.md"])
