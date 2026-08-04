from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from vault_agent.rpc import handle_request, run_jsonl
from vault_agent.settings import ProviderSettings


class RpcTests(unittest.TestCase):
    def test_starts_a_vault_session_through_json_protocol(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            vault.mkdir()
            with patch("vault_agent.rpc.Path.home", return_value=root):
                events = list(handle_request({"id": "req-1", "method": "session.start", "params": {"vault": str(vault), "source_language": "en"}}))

            self.assertEqual(events[0]["id"], "req-1")
            self.assertEqual(events[0]["type"], "completed")
            self.assertTrue(events[0]["result"]["session_id"])

    def test_refuses_remote_turn_without_explicit_json_confirmation(self):
        with self.assertRaisesRegex(ValueError, "confirm_remote"):
            list(handle_request({"id": "req-2", "method": "session.turn", "params": {"vault": "/tmp/vault", "session_id": "x", "message": "hello"}}))

    def test_emits_jsonl_events_with_request_id(self):
        source = StringIO(json.dumps({"id": "req-3", "method": "provider.show", "params": {}}) + "\n")
        destination = StringIO()
        with patch("vault_agent.rpc.load_settings", return_value=ProviderSettings()):
            run_jsonl(source, destination)

        event = json.loads(destination.getvalue())
        self.assertEqual(event["id"], "req-3")
        self.assertEqual(event["result"]["model"], "deepseek-v4-flash")
