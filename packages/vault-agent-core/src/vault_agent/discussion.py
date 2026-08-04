from __future__ import annotations


class DiscussionError(ValueError):
    pass


def discuss(provider, message: str, source_language: str) -> str:
    if not message.strip():
        raise DiscussionError("message cannot be empty")
    system = (
        "You are Vault Agent, a discussion assistant for a judgment-centered Obsidian vault. "
        f"The source language: {source_language}. Preserve source-derived content in that language; "
        "do not translate it during ingest. Separate source facts, user judgments, model inferences, "
        "and open questions. Do not claim to write files or change core Wiki objects."
    )
    return provider.complete(
        [{"role": "system", "content": system}, {"role": "user", "content": message}],
        confirmed=True,
    )
