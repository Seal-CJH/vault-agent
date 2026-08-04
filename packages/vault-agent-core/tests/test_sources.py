import unittest

from vault_agent.sources import inspect_source


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
