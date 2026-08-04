from __future__ import annotations

import argparse
from pathlib import Path

from .staging import stage_packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vault-agent")
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage", help="validate a packet and optionally stage it in Inbox")
    stage.add_argument("--vault", required=True, type=Path)
    stage.add_argument("--packet", required=True, type=Path)
    stage.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "stage":
        result = stage_packet(args.vault, args.packet.read_text(encoding="utf-8"), args.apply)
        status = "staged" if result.written else "preview"
        print(f"{status}: {result.path}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
