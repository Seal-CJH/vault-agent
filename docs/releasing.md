# Releasing Vault Agent

1. Update the same semantic version in `packages/vault-agent-core/pyproject.toml` and `apps/obsidian-plugin/manifest.json`.
2. Ensure CI is green and review the compatibility matrix.
3. Create and push a signed or annotated tag such as `v0.1.1`.
4. The Release workflow builds a Core wheel/source distribution and an Obsidian plugin zip, then attaches them to the GitHub Release.

The release workflow never packages API keys, local provider settings, session state, or vault content.
