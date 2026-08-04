from __future__ import annotations


class DiscussionError(ValueError):
    pass


def _messages(message: str, source_language: str) -> list[dict[str, str]]:
    if not message.strip():
        raise DiscussionError("message cannot be empty")
    system = (
        "You are Vault Agent, a discussion assistant for a judgment-centered Obsidian vault. "
        f"The source language: {source_language}. Preserve source-derived content in that language; "
        "do not translate it during ingest. Separate source facts, user judgments, model inferences, "
        "and open questions. Do not claim to write files or change core Wiki objects."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": message}]


def discuss(provider, message: str, source_language: str) -> str:
    return provider.complete(_messages(message, source_language), confirmed=True)


def stream_discuss(provider, message: str, source_language: str):
    return provider.stream(_messages(message, source_language), confirmed=True)
