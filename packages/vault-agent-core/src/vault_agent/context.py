from __future__ import annotations

from dataclasses import dataclass

from .vault_index import VaultDocument, VaultIndex


@dataclass(frozen=True)
class ContextBundle:
    paths: list[str]
    prompt: str


class ContextCompiler:
    """Compiles an auditable, bounded model context from the local vault index."""

    def __init__(self, index: VaultIndex, max_document_chars: int = 6000, max_catalog_chars: int = 12000):
        self.index = index
        self.max_document_chars = max_document_chars
        self.max_catalog_chars = max_catalog_chars

    def compile(self, query: str) -> ContextBundle:
        governance = self.index.governance_documents()
        related = self.index.search(query)
        seen: set[str] = set()
        documents: list[VaultDocument] = []
        for document in governance + related:
            if document.path not in seen:
                seen.add(document.path)
                documents.append(document)
        sections = []
        for document in documents:
            sections.append(f"<vault-document path=\"{document.path}\">\n{document.content[:self.max_document_chars]}\n</vault-document>")
        relations = [f"{document.path} → " + ", ".join(f"[[{link}]]" for link in document.links) for document in documents if document.links]
        if relations:
            sections.append("<vault-relationships>\n" + "\n".join(relations) + "\n</vault-relationships>")
        profile = self.index.profile()
        profile_lines = ["documents by directory: " + ", ".join(f"{name}: {count}" for name, count in profile["directories"])]
        if profile["tags"]:
            profile_lines.append("frequent tags: " + ", ".join(f"{name}: {count}" for name, count in profile["tags"]))
        if profile["links"]:
            profile_lines.append("frequent concepts: " + ", ".join(f"[[{name}]]: {count}" for name, count in profile["links"]))
        if profile["directories"]:
            sections.append("<vault-profile>\n" + "\n".join(profile_lines) + "\n</vault-profile>")
        catalog_lines: list[str] = []
        used = 0
        for document in self.index.catalog():
            metadata = []
            if document.tags:
                metadata.append("tags: " + ", ".join(document.tags))
            if document.links:
                metadata.append("links: " + ", ".join(f"[[{link}]]" for link in document.links))
            line = f"{document.path} | {document.title}" + (" | " + "; ".join(metadata) if metadata else "")
            if used + len(line) + 1 > self.max_catalog_chars:
                break
            catalog_lines.append(line)
            used += len(line) + 1
        if catalog_lines:
            sections.append("<vault-catalog>\n" + "\n".join(catalog_lines) + "\n</vault-catalog>")
        return ContextBundle(paths=[document.path for document in documents], prompt="\n\n".join(sections))
