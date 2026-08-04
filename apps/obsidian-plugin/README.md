# Local Obsidian Debugging

For development, use the repository launcher at `../../scripts/vault-agent`; it runs the tracked Python core without installing anything globally.

Build the plugin from this directory:

```bash
pnpm install
pnpm build
```

For local debugging, link this directory into the target vault as `.obsidian/plugins/vault-agent`, then enable **Vault Agent** in Obsidian Community Plugins. Set **Vault Agent CLI path** to `/Users/seal/Projects/Vault-Agent/scripts/vault-agent`.

Use the pane as a client of the local core:

1. For a book, choose **＋ Book**, add its title, optional author, source language, and your excerpt. This is stored only in the local session; it neither fetches the book nor calls a model. Then send a discussion message when you are ready to share that turn with the configured provider.
2. Select the source language and send a source, excerpt, or question. Replies stream into the conversation and render as Markdown when complete.
3. Choose **Prepare ingest draft** to ask the core for a validated Packet preview.
4. Review it and choose **Confirm stage to Inbox** to let the core write the note. Nothing is written before this confirmation.

Use **History** to reopen a local session. Conversation state is stored by the Core outside the vault, and restoring a session does not make a model call.
Each history item also displays the model last used by that session; the local audit records model, thinking state, reasoning effort, and timestamp but never an API key.

Use **Review** for a local-only summary of Inbox candidates and Claims or Sources missing wikilinks. It does not call a model or change any note.

The displayed model badge comes from `vault-agent provider show`; model keys and provider settings stay outside the plugin and outside the vault.

For public links, the pane first shows a local **Source parsed** status (title, kind, and detected language), then begins the model stream.
For video links it also makes the limitation explicit: media is never downloaded or transcribed, so paste a transcript, excerpt, or your own notes before treating the video's content as evidence.
