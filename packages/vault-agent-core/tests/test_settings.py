from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vault_agent.settings import ProviderSettings, load_settings, save_settings


class SettingsTests(unittest.TestCase):
    def test_uses_safe_deepseek_defaults_when_no_settings_exist(self):
        with TemporaryDirectory() as directory:
            settings = load_settings(Path(directory) / "provider.json")

            self.assertEqual(settings.model, "deepseek-v4-flash")
            self.assertFalse(settings.thinking)
            self.assertEqual(settings.reasoning_effort, "medium")

    def test_persists_selected_model_and_thinking_options(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "provider.json"
            expected = ProviderSettings("deepseek", "deepseek-v4-pro", True, "high")

            save_settings(path, expected)

            self.assertEqual(load_settings(path), expected)
