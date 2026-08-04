import unittest

from vault_agent.discussion import DiscussionError, discuss, stream_discuss


class FakeProvider:
    def __init__(self):
        self.messages = None
        self.confirmed = None

    def complete(self, messages, confirmed):
        self.messages = messages
        self.confirmed = confirmed
        return "A focused reply"

    def stream(self, messages, confirmed):
        self.messages = messages
        self.confirmed = confirmed
        return iter(["A ", "stream"])


class DiscussionTests(unittest.TestCase):
    def test_sends_a_source_language_policy_with_the_user_message(self):
        provider = FakeProvider()

        result = discuss(provider, "What should I retain?", "en")

        self.assertEqual(result, "A focused reply")
        self.assertTrue(provider.confirmed)
        self.assertIn("source language: en", provider.messages[0]["content"])
        self.assertEqual(provider.messages[1]["content"], "What should I retain?")

    def test_rejects_empty_messages_before_any_provider_call(self):
        with self.assertRaisesRegex(DiscussionError, "empty"):
            discuss(FakeProvider(), "   ", "zh-CN")

    def test_streams_a_discussion_response(self):
        provider = FakeProvider()

        self.assertEqual(list(stream_discuss(provider, "Discuss this", "zh-CN")), ["A ", "stream"])
        self.assertTrue(provider.confirmed)
