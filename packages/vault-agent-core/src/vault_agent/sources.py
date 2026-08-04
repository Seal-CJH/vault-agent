from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SourceMaterial:
    """Normalized, provenance-preserving material supplied to a discussion."""

    kind: str
    title: str
    author: str | None
    provenance: str
    content_language: str | None
    text: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


class _ReadablePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.page_title: list[str] | None = None
        self.author: str | None = None
        self.language: str | None = None
        self._article_depth = 0
        self._body_depth = 0
        self._ignored_depth = 0
        self._paragraph: list[str] | None = None
        self.article_paragraphs: list[str] = []
        self.body_paragraphs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "html":
            self.language = attributes.get("lang") or self.language
        if tag == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            value = attributes.get("content")
            if value and key in {"og:title", "twitter:title"}:
                self.title = value.strip()
            if value and key in {"author", "article:author"}:
                self.author = value.strip()
        if tag == "title":
            self.page_title = []
        if tag in {"script", "style", "nav", "footer", "header", "aside"}:
            self._ignored_depth += 1
        if tag == "body":
            self._body_depth += 1
        if tag == "article":
            self._article_depth += 1
        if tag == "p" and not self._ignored_depth:
            self._paragraph = []

    def handle_endtag(self, tag):
        if tag == "title" and self.page_title is not None:
            title = " ".join("".join(self.page_title).split())
            if title and not self.title:
                self.title = title
            self.page_title = None
        if tag == "p" and self._paragraph is not None:
            paragraph = " ".join("".join(self._paragraph).split())
            if paragraph:
                (self.article_paragraphs if self._article_depth else self.body_paragraphs).append(paragraph)
            self._paragraph = None
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if tag == "body" and self._body_depth:
            self._body_depth -= 1
        if tag in {"script", "style", "nav", "footer", "header", "aside"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data):
        if self.page_title is not None:
            self.page_title.append(data)
        if self._paragraph is not None and not self._ignored_depth:
            self._paragraph.append(data)


def inspect_source(
    *,
    kind: str,
    url: str | None = None,
    title: str | None = None,
    author: str | None = None,
    excerpt: str | None = None,
    content_language: str | None = None,
    fetch_html: Callable[[str], str] | None = None,
) -> SourceMaterial:
    """Inspect public articles; never retrieve protected book text or video media."""
    if kind not in {"article", "video", "book"}:
        raise ValueError("kind must be article, video, or book")
    if kind == "book":
        if not title:
            raise ValueError("book sources require a title")
        return SourceMaterial(
            kind="book", title=title, author=author,
            provenance=f"Book: {title}" + (f" — {author}" if author else ""),
            content_language=content_language, text=(excerpt or "").strip(),
        )
    if not url or urlparse(url).scheme not in {"http", "https"}:
        raise ValueError(f"{kind} sources require a public http(s) URL")
    page = _ReadablePage()
    html = (fetch_html or _fetch_html)(url)
    page.feed(html)
    resolved_title = title or page.title or url
    resolved_author = author or page.author
    resolved_language = content_language or page.language
    if kind == "video":
        return SourceMaterial(
            kind="video", title=resolved_title, author=resolved_author, provenance=url,
            content_language=resolved_language, text=(excerpt or "").strip(),
            warnings=("Video media and transcripts are not downloaded; supply a transcript or excerpt to discuss its content.",),
        )
    paragraphs = page.article_paragraphs or page.body_paragraphs
    return SourceMaterial(
        kind="article", title=resolved_title, author=resolved_author, provenance=url,
        content_language=resolved_language, text="\n\n".join(paragraphs),
    )


def _fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Vault-Agent/0.2 (+local source inspection)"})
    with urlopen(request, timeout=15) as response:  # nosec B310: explicit user-confirmed public URL
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
