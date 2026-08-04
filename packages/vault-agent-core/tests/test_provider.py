import unittest
import json

from vault_agent.provider import ProviderError, DeepSeekProvider, provider_from_settings
from vault_agent.settings import ProviderSettings


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

    def test_builds_provider_from_saved_model_options(self):
        provider = provider_from_settings(
            "secret", ProviderSettings("deepseek", "deepseek-v4-pro", True, "high")
        )

        self.assertEqual(provider.model, "deepseek-v4-pro")
        self.assertTrue(provider.thinking)
        self.assertEqual(provider.reasoning_effort, "high")

    def test_sends_thinking_parameters_only_when_enabled(self):
        bodies = []

        def request(_, __, body):
            bodies.append(json.loads(body))
            return '{"choices":[{"message":{"content":"response"}}]}'

        DeepSeekProvider(api_key="secret", model="deepseek-v4-pro", thinking=True, reasoning_effort="high", request=request).complete([], confirmed=True)
        DeepSeekProvider(api_key="secret", thinking=False, request=request).complete([], confirmed=True)

        self.assertEqual(bodies[0]["model"], "deepseek-v4-pro")
        self.assertEqual(bodies[0]["thinking"], {"type": "enabled"})
        self.assertEqual(bodies[0]["reasoning_effort"], "high")
        self.assertNotIn("thinking", bodies[1])

    def test_streams_text_deltas_after_explicit_confirmation(self):
        def stream_request(*_):
            return iter([
                'data: {"choices":[{"delta":{"content":"Hello"}}]}',
                'data: {"choices":[{"delta":{"content":" world"}}]}',
                "data: [DONE]",
            ])

        provider = DeepSeekProvider(api_key="secret", stream_request=stream_request)

        self.assertEqual(
            list(provider.stream([{"role": "user", "content": "hello"}], confirmed=True)),
            ["Hello", " world"],
        )
