from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3


GOVERNANCE_PATHS = ("AGENTS.md", "Home.md", "00_Meta/Ingest Workflow.md", "00_Meta/Object Schemas.md", "00_Meta/Tag Registry.md")


@dataclass(frozen=True)
class VaultDocument:
    path: str
    title: str
    content: str
    tags: list[str]
    aliases: list[str]
    links: list[str]


class VaultIndex:
    """A local-only Markdown index. The database never becomes the system of record."""

    def __init__(self, vault_root: Path, database_path: Path):
        self.vault_root = vault_root.resolve()
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        expected = ["path", "title", "content", "tags", "aliases", "links"]
        existing = [row[1] for row in connection.execute("PRAGMA table_info(documents)").fetchall()]
        if existing and existing != expected:
            connection.execute("DROP TABLE documents")
        connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(path UNINDEXED, title, content, tags, aliases, links)")
        return connection

    def rebuild(self) -> int:
        documents = list(self._documents())
        with self._connect() as connection:
            connection.execute("DELETE FROM documents")
            connection.executemany(
                "INSERT INTO documents(path, title, content, tags, aliases, links) VALUES (?, ?, ?, ?, ?, ?)",
                [(d.path, d.title, d.content, " ".join(d.tags), " ".join(d.aliases), " ".join(d.links)) for d in documents],
            )
        return len(documents)

    def search(self, query: str, limit: int = 8) -> list[VaultDocument]:
        terms = re.findall(r"[\w-]+", query, flags=re.UNICODE)
        if not terms:
            return []
        fts_query = " OR ".join(f'"{term}"' for term in terms)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT path, title, content, tags, aliases, links FROM documents WHERE documents MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, limit),
            ).fetchall()
        return [VaultDocument(row[0], row[1], row[2], row[3].split(), row[4].split(), row[5].split()) for row in rows]

    def catalog(self, limit: int = 400) -> list[VaultDocument]:
        """Return lightweight metadata for vault-wide awareness, never note bodies."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT path, title, content, tags, aliases, links FROM documents ORDER BY path LIMIT ?", (limit,)
            ).fetchall()
        return [VaultDocument(row[0], row[1], "", row[3].split(), row[4].split(), row[5].split()) for row in rows]

    def governance_documents(self) -> list[VaultDocument]:
        result: list[VaultDocument] = []
        for relative in GOVERNANCE_PATHS:
            path = self.vault_root / relative
            if path.exists():
                result.append(self._read(path))
        return result

    def _documents(self):
        for path in self.vault_root.rglob("*.md"):
            relative = path.relative_to(self.vault_root)
            if any(part.startswith(".") for part in relative.parts):
                continue
            yield self._read(path)

    def _read(self, path: Path) -> VaultDocument:
        content = path.read_text(encoding="utf-8")
        relative = path.relative_to(self.vault_root).as_posix()
        title = next((match.group(1).strip() for match in re.finditer(r"^#\s+(.+)$", content, re.MULTILINE)), path.stem)
        tags = self._frontmatter_list(content, "tags")
        aliases = self._frontmatter_list(content, "aliases")
        links = [match.group(1).strip() for match in re.finditer(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", content)]
        return VaultDocument(relative, title, content, tags, aliases, links)

    @staticmethod
    def _frontmatter_list(content: str, key: str) -> list[str]:
        match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return []
        lines = match.group(1).splitlines()
        values: list[str] = []
        active = False
        for line in lines:
            if line.startswith(f"{key}:"):
                active = True
                continue
            if active and line.startswith("  - "):
                values.append(line[4:].strip())
                continue
            if active and line and not line.startswith(" "):
                break
        return values
