from __future__ import annotations

from dataclasses import dataclass
import re


class PacketError(ValueError):
    """Raised when an ingest packet cannot be safely staged."""


@dataclass(frozen=True)
class Packet:
    title: str
    content_language: str
    captured: str
    tags: list[str]
    aliases: list[str]
    raw: str


REQUIRED_FIELDS = {
    "type",
    "source_type",
    "source_role",
    "credibility",
    "status",
    "captured",
    "content_language",
    "created",
    "updated",
}
REQUIRED_SECTIONS = (
    "## Provenance",
    "## Ingest Proposal",
    "### Source Record",
    "### Related Questions",
    "### Claim Updates",
    "### Action Candidates",
    "### Map Updates",
    "### Do Not Promote",
)
LANGUAGE_TAG = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")


def _frontmatter(raw: str) -> tuple[dict[str, str | list[str]], str]:
    if not raw.startswith("---\n"):
        raise PacketError("packet must start with YAML frontmatter")
    end = raw.find("\n---\n", 4)
    if end == -1:
        raise PacketError("packet frontmatter is not closed")
    metadata: dict[str, str | list[str]] = {}
    active_list: str | None = None
    for line in raw[4:end].splitlines():
        if line.startswith("  - ") and active_list:
            metadata.setdefault(active_list, [])
            assert isinstance(metadata[active_list], list)
            metadata[active_list].append(line[4:].strip())
            continue
        active_list = None
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value == "[]":
            metadata[key] = []
            active_list = key
        elif not value:
            metadata[key] = []
            active_list = key
        else:
            metadata[key] = value.strip('"\'')
    return metadata, raw[end + 5 :]


def parse_packet(raw: str) -> Packet:
    metadata, body = _frontmatter(raw)
    missing = sorted(field for field in REQUIRED_FIELDS if not metadata.get(field))
    if missing:
        raise PacketError("missing required frontmatter: " + ", ".join(missing))
    if metadata["type"] != "source":
        raise PacketError("packet type must be source")
    language = str(metadata["content_language"])
    if not LANGUAGE_TAG.fullmatch(language):
        raise PacketError("content_language must be a BCP 47 language tag")
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in body]
    if missing_sections:
        raise PacketError("missing required sections: " + ", ".join(missing_sections))
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if not title_match:
        raise PacketError("packet must contain one H1 title")
    tags = metadata.get("tags", [])
    aliases = metadata.get("aliases", [])
    if not isinstance(tags, list) or not isinstance(aliases, list):
        raise PacketError("tags and aliases must be YAML lists")
    return Packet(title_match.group(1).strip(), language, str(metadata["captured"]), tags, aliases, raw)
