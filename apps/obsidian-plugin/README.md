# Local Obsidian Debugging

For development, use the repository launcher at `../../scripts/vault-agent`; it runs the tracked Python core without installing anything globally.

Build the plugin from this directory:

```bash
pnpm install
pnpm build
```

For local debugging, link this directory into the target vault as `.obsidian/plugins/vault-agent`, then enable **Vault Agent** in Obsidian Community Plugins. Set **Vault Agent CLI path** to `/Users/seal/Projects/Vault-Agent/scripts/vault-agent`.

Use the pane as a client of the local core:

1. Select the source language and send a source, excerpt, or question. Replies stream into the conversation and render as Markdown when complete.
2. Choose **Prepare ingest draft** to ask the core for a validated Packet preview.
3. Review it and choose **Confirm stage to Inbox** to let the core write the note. Nothing is written before this confirmation.

The displayed model badge comes from `vault-agent provider show`; model keys and provider settings stay outside the plugin and outside the vault.
