from __future__ import annotations

import subprocess
from typing import Callable


class CredentialError(RuntimeError):
    pass


def keychain_service(provider: str) -> str:
    if provider != "deepseek":
        raise CredentialError(f"unsupported provider: {provider}")
    return f"vault-agent/{provider}"


def save_key(provider: str, api_key: str, runner: Callable[[list[str]], object] | None = None) -> None:
    if not api_key.strip():
        raise CredentialError("API key cannot be empty")
    command = [
        "security", "add-generic-password", "-U", "-a", "vault-agent", "-s",
        keychain_service(provider), "-w", api_key,
    ]
    if runner is not None:
        runner(command)
        return
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise CredentialError("could not store key in macOS Keychain") from error


def load_key(provider: str) -> str:
    command = ["security", "find-generic-password", "-a", "vault-agent", "-s", keychain_service(provider), "-w"]
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise CredentialError(f"no Keychain credential configured for {provider}") from error
