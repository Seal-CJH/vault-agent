import unittest
from unittest.mock import patch

from vault_agent.sources import _validate_public_url, inspect_source


ARTICLE_HTML = """
<html lang="en"><head>
  <meta property="og:title" content="A useful article">
  <meta name="author" content="Ada Lovelace">
</head><body><nav>Ignore navigation</nav><article>
  <p>First source paragraph.</p><p>Second source paragraph.</p>
</article><script>ignore()</script></body></html>
"""


class SourceInspectionTests(unittest.TestCase):
    def test_extracts_public_article_metadata_and_readable_text(self):
        material = inspect_source(
            kind="article",
            url="https://example.test/article",
            fetch_html=lambda _: ARTICLE_HTML,
        )

        self.assertEqual(material.title, "A useful article")
        self.assertEqual(material.author, "Ada Lovelace")
        self.assertEqual(material.content_language, "en")
        self.assertEqual(material.text, "First source paragraph.\n\nSecond source paragraph.")
        self.assertEqual(material.provenance, "https://example.test/article")

    def test_book_never_fetches_text_and_keeps_only_user_supplied_excerpt(self):
        material = inspect_source(
            kind="book",
            title="The Book",
            author="An Author",
            excerpt="The reader's own supplied excerpt.",
            content_language="en",
            fetch_html=lambda _: self.fail("books must not fetch full text"),
        )

        self.assertEqual(material.title, "The Book")
        self.assertEqual(material.text, "The reader's own supplied excerpt.")
        self.assertEqual(material.provenance, "Book: The Book — An Author")

    def test_requires_public_url_for_an_article(self):
        with self.assertRaisesRegex(ValueError, "http"):
            inspect_source(kind="article", url="file:///private/article")

    def test_fetches_a_public_article_once(self):
        calls = []
        inspect_source(kind="article", url="https://example.test/article", fetch_html=lambda url: calls.append(url) or ARTICLE_HTML)

        self.assertEqual(calls, ["https://example.test/article"])

    def test_uses_html_title_when_open_graph_metadata_is_missing(self):
        material = inspect_source(
            kind="article", url="https://example.test/plain",
            fetch_html=lambda _: "<html><head><title>Plain page title</title></head><body><p>Body.</p></body></html>",
        )

        self.assertEqual(material.title, "Plain page title")

    def test_rejects_local_and_private_addresses_before_fetching(self):
        for url in ("http://localhost/article", "http://127.0.0.1/article", "http://192.168.1.10/article", "http://[::1]/article"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "public"):
                inspect_source(kind="article", url=url, fetch_html=lambda _: self.fail("must not fetch a local URL"))

    def test_rejects_userinfo_in_public_urls(self):
        with self.assertRaisesRegex(ValueError, "public"):
            inspect_source(kind="article", url="https://token@example.test/article", fetch_html=lambda _: self.fail("must not fetch"))

    def test_rejects_hostnames_that_resolve_to_private_addresses(self):
        with patch("vault_agent.sources.socket.getaddrinfo", return_value=[(None, None, None, None, ("10.0.0.8", 443))]):
            with self.assertRaisesRegex(ValueError, "public"):
                _validate_public_url("https://private.example/article", resolve_host=True)
