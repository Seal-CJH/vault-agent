from __future__ import annotations

from dataclasses import dataclass

from .vault_index import VaultDocument, VaultIndex


@dataclass(frozen=True)
class ContextBundle:
    paths: list[str]
    prompt: str


class ContextCompiler:
    """Compiles an auditable, bounded model context from the local vault index."""

    def __init__(self, index: VaultIndex, max_document_chars: int = 6000):
        self.index = index
        self.max_document_chars = max_document_chars

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
        return ContextBundle(paths=[document.path for document in documents], prompt="\n\n".join(sections))
