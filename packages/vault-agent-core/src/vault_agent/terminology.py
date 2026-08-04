from __future__ import annotations


class TerminologyError(ValueError):
    """Raised when an alias is used as a parallel tag or link target."""


CANONICAL_TERMS = {
    "大语言模型": "LLM",
    "智能体": "agent",
}


def validate_terms(tags: list[str], aliases: list[str] | None = None) -> None:
    del aliases  # Display aliases are permitted and intentionally not normalized.
    for tag in tags:
        if tag in CANONICAL_TERMS:
            raise TerminologyError(
                f"{tag!r} is a display translation; use canonical term {CANONICAL_TERMS[tag]!r}"
            )
