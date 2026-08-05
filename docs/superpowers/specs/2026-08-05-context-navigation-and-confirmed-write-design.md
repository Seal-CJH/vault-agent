# Context Navigation and Confirmed Write Design

## Goal

Make Vault Agent's Obsidian conversation usable as a knowledge-navigation and confirmed-capture workflow. A user must be able to open the local notes and tags that informed a response, then explicitly stage the validated capture without relying on model prose to perform a file write.

## Scope

- Add a Core event that exposes the provider-eligible vault documents retrieved for a discussion turn.
- Render those documents and their canonical tags as clickable Obsidian controls.
- Require model prose to cite retrieved notes with Obsidian wikilinks when it recommends them.
- Replace ambiguous natural-language write expectations with a client-side confirmation state: a prepared Packet can be staged by the visible confirmation control or an exact composer command.
- Return a clickable Inbox note after a successful stage.

Out of scope: web search, direct model writes to core Wiki objects, automatic promotion beyond Inbox, and any exposure of `ai_sharing: local-only` notes.

## Architecture

### Core retrieval event

`SessionStore.turn` compiles the vault context once, then exposes the same provider-eligible retrieved document metadata through a `session.context` JSONL event before provider streaming begins. Each reference contains only `path`, `title`, canonical `tags`, and canonical `links`.

The event never includes document body text. `ContextCompiler` is the authority for eligibility, so `local-only` notes are absent from the provider prompt and the event.

The discussion system instruction states that when referring to supplied vault documents, the model must use exact `[[path|title]]` syntax, and use canonical `#tag` syntax for tags. This is advisory presentation guidance; client-side references remain the reliable navigation surface.

### Obsidian navigation

The plugin renders a compact **Related vault context** card before the streamed answer. Note controls call Obsidian's internal link opening API with the Core-supplied relative path. Tag controls open an Obsidian search URI for the exact canonical tag. These controls are produced only from `session.context`, not parsed from arbitrary model output.

MarkdownRenderer continues to render model wikilinks in the response body, which makes correct inline citations clickable as well.

### Confirmed capture state machine

```text
discussion complete
  → no draft
  → user requests Prepare ingest draft
  → packet preview
  → draft ready
  → explicit stage action or exact “确认录入” command
  → Core session.stage(apply=true)
  → staged state with clickable Inbox note
```

The exact confirmation command is only intercepted while a validated draft is present. It is never sent to the model. The visible confirmation control remains available for discoverability and accessibility.

Core remains the only file-writing authority. Staging writes only `01_Inbox/conversations/`; Questions, Claims, Decisions, Experiments, Reviews, and Maps remain proposals.

## Failure handling

- If no context is retrieved, show no context card rather than an empty placeholder.
- If a referenced note no longer exists when clicked, display an inline plugin error and keep the conversation intact.
- If a draft cannot be prepared, retain the discussion and restore the draft action.
- If staging fails, preserve the preview and restore the confirmation action. Never imply that a file was written.
- If a user enters `确认录入` before a draft exists, treat it as ordinary conversation text; do not stage or silently suppress it.

## Tests

- Core JSONL test: `session.context` precedes text deltas and contains only provider-eligible metadata.
- Core privacy test: a `local-only` note cannot appear in the context event.
- Plugin build/type check: navigation and confirmation state compile.
- Core staging tests: stage stays Inbox-only and requires `apply: true`.
- Manual Obsidian acceptance: open a retrieved note, search a canonical tag, prepare a draft, stage via visible action, stage via exact confirmation command, and open the returned Inbox note.

## Compatibility

The change is additive to the JSONL protocol. Existing clients may ignore `session.context`; the Obsidian plugin uses it when present. No Vault schema change is required.
