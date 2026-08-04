from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Iterable, TextIO

from .credentials import load_key
from .draft import prepare_draft
from .provider import provider_from_settings
from .review import review_vault
from .session import SessionStore
from .settings import load_settings
from .sources import inspect_source
from .staging import stage_packet
from .vault_index import VaultIndex


def handle_request(request: dict) -> Iterable[dict]:
    """Handle one local JSON-RPC-like request without opening a network listener."""
    request_id = request.get("id")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("request id must be a non-empty string")
    method = request.get("method")
    params = request.get("params", {})
    if not isinstance(method, str) or not isinstance(params, dict):
        raise ValueError("request requires method and object params")
    if method == "provider.show":
        yield _completed(request_id, asdict(load_settings()))
        return
    if method == "source.inspect":
        material = inspect_source(
            kind=_required(params, "kind"), url=params.get("url"), title=params.get("title"),
            author=params.get("author"), excerpt=params.get("excerpt"), content_language=params.get("source_language"),
        )
        yield _completed(request_id, asdict(material))
        return
    if method in {"session.turn", "session.draft"}:
        _require_remote_confirmation(params)
    vault, store = _store(_required(params, "vault"))
    if method == "review.run":
        yield _completed(request_id, review_vault(store.index).to_dict())
        return
    if method == "session.start":
        source_language = _required(params, "source_language")
        yield _completed(request_id, {"session_id": store.create(source_language).id, "indexed": True})
        return
    if method == "session.list":
        yield _completed(request_id, {"sessions": store.list(int(params.get("limit", 30)))})
        return
    session_id = _required(params, "session_id")
    if method == "session.show":
        yield _completed(request_id, asdict(store.load(session_id)))
        return
    if method == "session.stage":
        if params.get("apply") is not True:
            raise ValueError("session.stage requires apply: true")
        result = stage_packet(vault, store.load_draft(session_id), apply=True)
        yield _completed(request_id, {"path": str(result.path), "written": result.written})
        return
    if method == "session.draft":
        provider = provider_from_settings(load_key("deepseek"), load_settings())
        packet = prepare_draft(store, session_id, provider)
        store.save_draft(session_id, packet.raw)
        yield _completed(request_id, {"packet": packet.raw, "title": packet.title})
        return
    if method == "session.turn":
        message = _required(params, "message")
        provider = provider_from_settings(load_key("deepseek"), load_settings())
        for source in store.prepare_sources(session_id, message):
            yield {"id": request_id, "type": "source_inspected", "source": source}
        yield {"id": request_id, "type": "started", "session_id": session_id}
        for delta in store.turn(session_id, provider, message):
            yield {"id": request_id, "type": "text_delta", "delta": delta}
        yield _completed(request_id, {})
        return
    raise ValueError(f"unsupported method: {method}")


def run_jsonl(source: TextIO, destination: TextIO) -> None:
    """Serve newline-delimited requests via stdin/stdout; intended for local child processes."""
    for line in source:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            for event in handle_request(request):
                destination.write(json.dumps(event, ensure_ascii=False) + "\n")
                destination.flush()
        except Exception as error:
            request_id = request.get("id") if "request" in locals() and isinstance(request, dict) else None
            destination.write(json.dumps({"id": request_id, "type": "error", "message": str(error)}, ensure_ascii=False) + "\n")
            destination.flush()


def _store(vault_value: str) -> tuple[Path, SessionStore]:
    vault = Path(vault_value).expanduser().resolve()
    if not vault.is_dir():
        raise ValueError("vault must be an existing directory")
    fingerprint = hashlib.sha256(str(vault).encode("utf-8")).hexdigest()[:16]
    state = Path.home() / "Library" / "Application Support" / "Vault Agent" / "vaults" / fingerprint
    index = VaultIndex(vault, state / "index.sqlite")
    index.rebuild()
    return vault, SessionStore(state / "sessions", index)


def _required(params: dict, key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


def _require_remote_confirmation(params: dict) -> None:
    if params.get("confirm_remote") is not True:
        raise ValueError("remote model calls require confirm_remote: true")


def _completed(request_id: str, result: dict) -> dict:
    return {"id": request_id, "type": "completed", "result": result}
