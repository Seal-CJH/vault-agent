# Architecture

Vault Agent is a local Core with multiple possible interaction clients.

```text
Obsidian / future Feishu bridge / future OpenClaw bridge
                         │ local JSON Lines stdin/stdout
                         ▼
Vault Agent Core
  ├─ local vault index, Vault Profile, and context compiler
  ├─ source inspection and provenance
  ├─ model-provider adapters and confirmation gate
  ├─ Packet validation and terminology checks
  └─ Inbox-only policy gate and local session audit
                         │
                         ▼
Obsidian vault (Markdown system of record)
```

Clients never receive direct write authority. The Core is responsible for every write decision and permits only explicitly applied staging into `01_Inbox/`.

For every turn, the Core rebuilds its local index. The model receives a metadata-only Vault Profile (directory distribution, frequent tags, and linked concepts), governance documents, a bounded catalog, and notes retrieved for the active discussion. It does not receive a blind full-vault dump.

The JSON Lines protocol is deliberately local: it has no HTTP listener. A remote bridge must run beside the Core and should never expose the local protocol directly to the internet.
