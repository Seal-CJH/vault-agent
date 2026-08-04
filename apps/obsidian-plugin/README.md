# Local Obsidian Debugging

For development, use the repository launcher at `../../scripts/vault-agent`; it runs the tracked Python core without installing anything globally.

Build the plugin from this directory:

```bash
pnpm install
pnpm build
```

For local debugging, link this directory into the target vault as `.obsidian/plugins/vault-agent`, then enable **Vault Agent** in Obsidian Community Plugins. Set **Vault Agent CLI path** to `/Users/seal/Projects/Vault-Agent/scripts/vault-agent`.
