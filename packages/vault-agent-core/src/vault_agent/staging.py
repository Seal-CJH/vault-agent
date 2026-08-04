from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .packet import PacketError, parse_packet
from .policy import target_path, write_packet
from .terminology import validate_terms


@dataclass(frozen=True)
class StageResult:
    path: Path
    written: bool


def stage_packet(vault_root: Path, raw: str, apply: bool = False) -> StageResult:
    packet = parse_packet(raw)
    validate_terms(packet.tags, packet.aliases)
    path = target_path(vault_root, packet.title, packet.captured)
    if not apply:
        return StageResult(path=path, written=False)
    return StageResult(path=write_packet(vault_root, packet.title, packet.captured, raw), written=True)
