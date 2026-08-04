from __future__ import annotations

import re

from .context import ContextCompiler
from .packet import Packet, PacketError, parse_packet
from .session import SessionStore
from .terminology import validate_terms


class DraftError(ValueError):
    pass


def prepare_draft(store: SessionStore, session_id: str, provider) -> Packet:
    session = store.load(session_id)
    if not session.messages:
        raise DraftError("cannot prepare a draft from an empty session")
    latest = session.messages[-1]["content"]
    context = ContextCompiler(store.index).compile(latest)
    instruction = (
        "Create one complete Markdown Conversation Ingest Packet from this discussion. "
        "Return only the packet, with YAML frontmatter and all required Ingest Proposal headings. "
        "Keep source-derived content in the declared source language. Do not create or edit core Wiki objects.\n\n"
        f"VAULT CONTEXT:\n{context.prompt}\n\nSOURCES:\n"
        + "\n".join(
            f"- kind: {source.get('kind', 'unknown')}\n  title: {source.get('title', 'unknown')}\n"
            f"  provenance: {source.get('provenance', 'unknown')}\n"
            f"  content_language: {source.get('content_language', 'unknown')}"
            for source in session.sources
        )
        + "\n\nSESSION:\n"
        + "\n".join(f"{m['role']}: {m['content']}" for m in session.messages)
    )
    store.record_provider_call(session_id, provider)
    raw = provider.complete([{"role": "system", "content": instruction}, {"role": "user", "content": "Prepare the packet now."}], confirmed=True)
    raw = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", raw.strip())
    try:
        packet = parse_packet(raw)
        validate_terms(packet.tags, packet.aliases)
        _validate_source_language(packet, session.sources)
    except (PacketError, ValueError) as error:
        raise DraftError(f"model returned an invalid ingest packet: {error}") from error
    return packet


def _validate_source_language(packet: Packet, sources: list[dict]) -> None:
    """A single packet cannot safely translate or combine known source languages."""
    languages = {str(source["content_language"]) for source in sources if source.get("content_language")}
    if len(languages) > 1:
        raise DraftError("sources use multiple content languages; prepare separate packets per source language")
    if languages and packet.content_language != next(iter(languages)):
        expected = next(iter(languages))
        raise DraftError(f"packet content_language must match the known source language: {expected}")
