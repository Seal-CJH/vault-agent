# Vault Agent

Vault Agent is a local, approval-gated companion for the Vault Template. It separates model assistance from deterministic policy enforcement: models may discuss and draft; only the local core indexes the vault, validates output, and stages Inbox notes.

## Architecture boundary

The Python core is the authority for vault understanding and writes. It keeps a local full-text index, a compact catalog of paths/tags/wikilinks, and local conversation/draft state outside the vault. Every remote turn receives vault governance, the compact catalog, and only the source notes retrieved for that turn.

Obsidian is a client only: it starts a session, displays streamed discussion, asks the core to prepare a draft, and sends the final explicit staging confirmation. Future clients such as Feishu or OpenClaw use the same core contract; they do not gain independent file-write permission.

## Local client protocol

`vault-agent rpc` is a newline-delimited JSON protocol over stdin/stdout, not a network server. Every request carries an `id`, `method`, and `params`; every response event repeats that id. The Obsidian plugin uses this protocol for settings, sessions, drafts, staging, history, and Review.

```json
{"id":"example-1","method":"session.start","params":{"vault":"/path/to/vault","source_language":"en"}}
```

Read-only methods include `provider.show`, `source.inspect`, `review.run`, `session.list`, and `session.show`. `session.turn` and `session.draft` require `confirm_remote: true`; `session.stage` requires `apply: true`. The protocol is intended for a local child process, so future Feishu/OpenClaw bridges must run beside the Core rather than exposing it as a public port.

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

The command stores the key in macOS Keychain; it never writes the key into the vault, plugin, or Git repository. Provider calls require an explicit confirmation flag in the local core.

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

## Obsidian flow

1. Start a discussion with a source link, excerpt, note, or question. Sending a turn explicitly authorizes that one remote model call.
2. Continue the conversation. The core rebuilds the local index and uses vault rules, catalog metadata, relationships, and retrieved note content on every turn.
3. Click **Prepare ingest draft** when the discussion is ready. This makes a separate, explicit model call that returns a validated Packet preview.
4. Review the complete preview, then click **Confirm stage to Inbox**. Only this action writes a Markdown note, and it is restricted to `01_Inbox/conversations/`.

The plugin’s **History** action asks the Core for local session metadata and restores a selected session without a remote request. Conversation state remains outside the vault; only explicitly confirmed staging creates a vault note.

Use **Review** to run a local, read-only health report. It lists Inbox candidates plus Claims and Sources without wikilinks, while excluding templates. This is the Core capability that future scheduled or remote notification clients will call; it does not contact a model or edit the vault.

The core never directly writes Questions, Claims, Decisions, Experiments, or Reviews. Those remain proposals for the human to promote under the vault’s own governance.

## Source handling

When a user sends a public article URL, the core locally extracts readable page text and records its URL, title, author, and language as provenance. Public video URLs are limited to page metadata: it never downloads media or creates a transcript. Book discussions use only the title, author, and excerpt supplied by the user; the core does not retrieve book text. If a source cannot be inspected, the discussion continues and asks for an excerpt or transcript instead of fabricating content.

Clients receive a `source_inspected` event before the model stream, so they can show what was parsed and which source language was detected. Previously parsed source material remains available across later turns in the same local session.

Source fetching accepts only public HTTP(S) URLs. The Core rejects local/private addresses and credential-bearing URLs, revalidates redirects, and limits a fetched page to 2 MB.
