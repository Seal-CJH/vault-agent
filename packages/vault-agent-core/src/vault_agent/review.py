from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from .vault_index import VaultIndex


@dataclass(frozen=True)
class ReviewReport:
    total_notes: int
    inbox_notes: list[str]
    claims_without_links: list[str]
    sources_without_links: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def review_vault(index: VaultIndex) -> ReviewReport:
    """Read-only judgment-quality audit; promotion and edits remain human decisions."""
    documents = [document for document in index.all_documents() if not document.path.startswith("00_Meta/Templates/")]
    claims_without_links: list[str] = []
    sources_without_links: list[str] = []
    inbox_notes: list[str] = []
    for document in documents:
        object_type = _object_type(document.content)
        if document.path.startswith("01_Inbox/"):
            inbox_notes.append(document.path)
        if object_type == "claim" and not document.links:
            claims_without_links.append(document.path)
        if object_type == "source" and not document.links:
            sources_without_links.append(document.path)
    return ReviewReport(
        total_notes=len(documents), inbox_notes=inbox_notes,
        claims_without_links=claims_without_links, sources_without_links=sources_without_links,
    )


def _object_type(content: str) -> str | None:
    frontmatter = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
    if not frontmatter:
        return None
    match = re.search(r"^type:\s*([^\s#]+)", frontmatter.group(1), re.MULTILINE)
    return match.group(1).strip() if match else None
