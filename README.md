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

DeepSeek is the first remote provider. Configure its credential locally with:

```bash
PYTHONPATH=packages/vault-agent-core/src python3 -m vault_agent.cli configure-provider deepseek
```

The command stores the key in macOS Keychain; it never writes the key into the vault, plugin, or Git repository. Provider calls require an explicit confirmation flag in the local core. The Obsidian panel remains a desktop-only installation skeleton while its discussion workflow is implemented.

### Choose a model

Inspect the active, non-sensitive settings:

```bash
PYTHONPATH=packages/vault-agent-core/src python3 -m vault_agent.cli provider show
```

Switch to DeepSeek Pro with thinking enabled:

```bash
PYTHONPATH=packages/vault-agent-core/src python3 -m vault_agent.cli provider set \
  --model deepseek-v4-pro --thinking enabled --reasoning-effort high
```

Settings are stored separately from the API key at `~/Library/Application Support/Vault Agent/provider.json`. The Obsidian pane calls `vault-agent provider show` and displays the active model, thinking state, and reasoning effort; configure its CLI path in the plugin settings.
