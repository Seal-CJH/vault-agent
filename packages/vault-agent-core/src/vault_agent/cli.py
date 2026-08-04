from __future__ import annotations

import argparse
from dataclasses import asdict
import getpass
import json
import hashlib
from pathlib import Path

from .staging import stage_packet
from .credentials import save_key
from .settings import ProviderSettings, load_settings, save_settings
from .credentials import load_key
from .provider import provider_from_settings
from .discussion import discuss, stream_discuss
from .session import SessionStore
from .vault_index import VaultIndex
from .draft import prepare_draft
from .sources import inspect_source
from .review import review_vault


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
    discussion = commands.add_parser("discuss", help="send one explicitly confirmed discussion turn to the configured provider")
    discussion.add_argument("--message", required=True)
    discussion.add_argument("--source-language", required=True)
    discussion.add_argument("--confirm", action="store_true", help="explicitly authorizes this remote send")
    discussion.add_argument("--stream", action="store_true", help="emit newline-delimited streaming events")
    source = commands.add_parser("source", help="inspect user-authorized source material locally")
    source.add_argument("action", choices=["inspect"])
    source.add_argument("--kind", required=True, choices=["article", "video", "book"])
    source.add_argument("--url")
    source.add_argument("--title")
    source.add_argument("--author")
    source.add_argument("--excerpt")
    source.add_argument("--source-language")
    review = commands.add_parser("review", help="run a read-only vault health review")
    review.add_argument("--vault", required=True, type=Path)
    session = commands.add_parser("session", help="manage local vault-aware discussion sessions")
    session.add_argument("action", choices=["start", "turn", "draft", "stage", "list", "show"])
    session.add_argument("--vault", required=True, type=Path)
    session.add_argument("--source-language", choices=["zh-CN", "en"])
    session.add_argument("--session-id")
    session.add_argument("--message")
    session.add_argument("--confirm", action="store_true")
    session.add_argument("--apply", action="store_true")
    session.add_argument("--limit", type=int, default=30)
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
    if args.command == "discuss":
        if not args.confirm:
            parser.error("discuss requires --confirm before content is sent remotely")
        settings = load_settings()
        agent = provider_from_settings(load_key("deepseek"), settings)
        if args.stream:
            print(json.dumps({"type": "started", **settings.__dict__}, ensure_ascii=False), flush=True)
            for delta in stream_discuss(agent, args.message, args.source_language):
                print(json.dumps({"type": "text_delta", "delta": delta}, ensure_ascii=False), flush=True)
            print(json.dumps({"type": "completed"}), flush=True)
            return 0
        reply = discuss(agent, args.message, args.source_language)
        print(json.dumps({"reply": reply}, ensure_ascii=False))
        return 0
    if args.command == "source":
        material = inspect_source(
            kind=args.kind, url=args.url, title=args.title, author=args.author,
            excerpt=args.excerpt, content_language=args.source_language,
        )
        print(json.dumps(asdict(material), ensure_ascii=False))
        return 0
    if args.command == "review":
        if not args.vault.is_dir():
            parser.error("--vault must be an existing vault directory")
        fingerprint = hashlib.sha256(str(args.vault.resolve()).encode("utf-8")).hexdigest()[:16]
        state = Path.home() / "Library" / "Application Support" / "Vault Agent" / "vaults" / fingerprint
        index = VaultIndex(args.vault, state / "index.sqlite")
        index.rebuild()
        print(json.dumps(review_vault(index).to_dict(), ensure_ascii=False))
        return 0
    if args.command == "session":
        if not args.vault.is_dir():
            parser.error("--vault must be an existing vault directory")
        fingerprint = hashlib.sha256(str(args.vault.resolve()).encode("utf-8")).hexdigest()[:16]
        state = Path.home() / "Library" / "Application Support" / "Vault Agent" / "vaults" / fingerprint
        index = VaultIndex(args.vault, state / "index.sqlite")
        index.rebuild()
        store = SessionStore(state / "sessions", index)
        if args.action == "list":
            print(json.dumps({"sessions": store.list(args.limit)}, ensure_ascii=False))
            return 0
        if args.action == "show":
            if not args.session_id:
                parser.error("session show requires --session-id")
            print(json.dumps(asdict(store.load(args.session_id)), ensure_ascii=False))
            return 0
        if args.action == "start":
            if not args.source_language:
                parser.error("session start requires --source-language")
            created = store.create(args.source_language)
            print(json.dumps({"session_id": created.id, "indexed": True}))
            return 0
        if args.action == "draft":
            if not args.session_id or not args.confirm:
                parser.error("session draft requires --session-id and --confirm")
            packet = prepare_draft(store, args.session_id, provider_from_settings(load_key("deepseek"), load_settings()))
            store.save_draft(args.session_id, packet.raw)
            print(json.dumps({"type": "draft", "packet": packet.raw, "title": packet.title}, ensure_ascii=False))
            return 0
        if args.action == "stage":
            if not args.session_id or not args.apply:
                parser.error("session stage requires --session-id and --apply")
            result = stage_packet(args.vault, store.load_draft(args.session_id), apply=True)
            print(json.dumps({"type": "staged", "path": str(result.path)}, ensure_ascii=False))
            return 0
        if not args.session_id or not args.message or not args.confirm:
            parser.error("session turn requires --session-id, --message, and --confirm")
        agent = provider_from_settings(load_key("deepseek"), load_settings())
        for source in store.prepare_sources(args.session_id, args.message):
            print(json.dumps({"type": "source_inspected", "source": source}, ensure_ascii=False), flush=True)
        print(json.dumps({"type": "started", "session_id": args.session_id}), flush=True)
        for delta in store.turn(args.session_id, agent, args.message):
            print(json.dumps({"type": "text_delta", "delta": delta}, ensure_ascii=False), flush=True)
        print(json.dumps({"type": "completed"}), flush=True)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
