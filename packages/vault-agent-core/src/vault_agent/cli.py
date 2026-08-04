from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

from .staging import stage_packet
from .credentials import save_key
from .settings import ProviderSettings, load_settings, save_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vault-agent")
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage", help="validate a packet and optionally stage it in Inbox")
    stage.add_argument("--vault", required=True, type=Path)
    stage.add_argument("--packet", required=True, type=Path)
    stage.add_argument("--apply", action="store_true")
    configure = commands.add_parser("configure-provider", help="store a provider key in macOS Keychain")
    configure.add_argument("provider", choices=["deepseek"])
    configure.add_argument("--model", choices=["deepseek-v4-flash", "deepseek-v4-pro"])
    configure.add_argument("--thinking", choices=["enabled", "disabled"])
    configure.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    provider = commands.add_parser("provider", help="inspect the active non-sensitive provider settings")
    provider.add_argument("action", choices=["show", "set"])
    provider.add_argument("--model", choices=["deepseek-v4-flash", "deepseek-v4-pro"])
    provider.add_argument("--thinking", choices=["enabled", "disabled"])
    provider.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    args = parser.parse_args(argv)
    if args.command == "stage":
        result = stage_packet(args.vault, args.packet.read_text(encoding="utf-8"), args.apply)
        status = "staged" if result.written else "preview"
        print(f"{status}: {result.path}")
        return 0
    if args.command == "configure-provider":
        save_key(args.provider, getpass.getpass(f"{args.provider} API key: "))
        current = load_settings()
        save_settings(None, ProviderSettings(
            provider=args.provider,
            model=args.model or current.model,
            thinking=(args.thinking == "enabled") if args.thinking else current.thinking,
            reasoning_effort=args.reasoning_effort or current.reasoning_effort,
        ))
        print(f"stored {args.provider} credential in macOS Keychain")
        return 0
    if args.command == "provider":
        if args.action == "set":
            current = load_settings()
            save_settings(None, ProviderSettings(
                provider=current.provider,
                model=args.model or current.model,
                thinking=(args.thinking == "enabled") if args.thinking else current.thinking,
                reasoning_effort=args.reasoning_effort or current.reasoning_effort,
            ))
        print(json.dumps(load_settings().__dict__, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
