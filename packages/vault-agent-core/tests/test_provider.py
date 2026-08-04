import unittest

from vault_agent.provider import ProviderError, DeepSeekProvider


class ProviderTests(unittest.TestCase):
    def test_refuses_remote_call_without_explicit_confirmation(self):
        provider = DeepSeekProvider(api_key="secret", request=lambda *_: "unexpected")

        with self.assertRaisesRegex(ProviderError, "explicit confirmation"):
            provider.complete([{"role": "user", "content": "hello"}], confirmed=False)

    def test_sends_openai_compatible_request_after_confirmation(self):
        captured = {}

        def request(url, headers, body):
            captured.update(url=url, headers=headers, body=body)
            return '{"choices":[{"message":{"content":"response"}}]}'

        result = DeepSeekProvider(api_key="secret", request=request).complete(
            [{"role": "user", "content": "hello"}], confirmed=True
        )

        self.assertEqual(result, "response")
        self.assertEqual(captured["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
