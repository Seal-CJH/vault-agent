from __future__ import annotations

from pathlib import Path
import re


class PolicyError(ValueError):
    """Raised when a requested vault write is outside the policy boundary."""


def _slug(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not value:
        raise PolicyError("title must contain at least one Latin letter or number")
    return value[:80]


def target_path(vault_root: Path, title: str, captured: str) -> Path:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", captured):
        raise PolicyError("captured date must use YYYY-MM-DD")
    destination = vault_root / "01_Inbox" / "conversations" / f"{captured}-{_slug(title)}.md"
    if destination.exists():
        raise PolicyError(f"target already exists: {destination}")
    return destination


def write_packet(vault_root: Path, title: str, captured: str, raw: str) -> Path:
    destination = target_path(vault_root, title, captured)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(raw, encoding="utf-8")
    return destination
