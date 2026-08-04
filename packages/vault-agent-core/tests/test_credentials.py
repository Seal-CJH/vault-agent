import unittest

from vault_agent.credentials import keychain_service, save_key


class CredentialTests(unittest.TestCase):
    def test_saves_deepseek_key_in_named_keychain_service(self):
        command = []
        save_key("deepseek", "secret", command.append)

        self.assertEqual(keychain_service("deepseek"), "vault-agent/deepseek")
        self.assertEqual(command[0][:6], ["security", "add-generic-password", "-U", "-a", "vault-agent", "-s"])
        self.assertNotIn("secret", " ".join(command[0][:-1]))
