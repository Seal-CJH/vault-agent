import unittest

from vault_agent.terminology import TerminologyError, validate_terms


class TerminologyTests(unittest.TestCase):
    def test_rejects_translated_canonical_tag(self):
        with self.assertRaisesRegex(TerminologyError, "LLM"):
            validate_terms(["大语言模型"])

    def test_allows_canonical_terms_and_display_aliases(self):
        validate_terms(["LLM", "agent"], ["大语言模型", "智能体"])
