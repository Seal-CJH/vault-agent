# Vault Agent

Vault Agent is a local, approval-gated companion for the Vault Template. It separates model assistance from deterministic policy enforcement: models may discuss and draft; only the local core validates and stages Inbox notes.

## Repository layout

- `packages/vault-agent-core`: Python policy core and CLI.
- `apps/obsidian-plugin`: desktop-only Obsidian interaction layer.
- `fixtures`: sanitized test materials only.

## Safe first command

```bash
PYTHONPATH=packages/vault-agent-core/src python3 -m vault_agent.cli stage \
  --vault /path/to/vault --packet /path/to/packet.md
```

Without `--apply`, this prints the proposed Inbox path and writes nothing. `--apply` is required to create a note.

## Model providers

DeepSeek is planned as the first remote provider. API credentials are deliberately not implemented in the plugin and must never be committed. The future `configure-provider` command will use the OS keychain and require an explicit send confirmation for every remote turn.
