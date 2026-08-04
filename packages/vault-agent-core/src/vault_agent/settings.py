from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = "deepseek"
    model: str = "deepseek-v4-flash"
    thinking: bool = False
    reasoning_effort: str = "medium"

    def __post_init__(self) -> None:
        if self.provider != "deepseek":
            raise ValueError("only deepseek is currently supported")
        if self.model not in {"deepseek-v4-flash", "deepseek-v4-pro"}:
            raise ValueError("model must be deepseek-v4-flash or deepseek-v4-pro")
        if self.reasoning_effort not in {"low", "medium", "high"}:
            raise ValueError("reasoning_effort must be low, medium, or high")


def default_settings_path() -> Path:
    return Path.home() / "Library" / "Application Support" / "Vault Agent" / "provider.json"


def load_settings(path: Path | None = None) -> ProviderSettings:
    path = path or default_settings_path()
    if not path.exists():
        return ProviderSettings()
    return ProviderSettings(**json.loads(path.read_text(encoding="utf-8")))


def save_settings(path: Path | None, settings: ProviderSettings) -> None:
    path = path or default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
