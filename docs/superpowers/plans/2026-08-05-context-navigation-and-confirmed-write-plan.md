# Context Navigation and Confirmed Write Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add navigable local context and an explicit Inbox confirmation flow.

**Architecture:** Core emits metadata, plugin renders it, Core writes Inbox only.

**Tech Stack:** Python, TypeScript, Obsidian API, JSON Lines, unittest.

## Task 1: Context metadata

- [ ] Add `references` to `ContextBundle`.
- [ ] Filter references using the existing provider-eligible document list.
- [ ] Test that `local-only` notes are absent.

Implementation detail: extend `ContextBundle` in `packages/vault-agent-core/src/vault_agent/context.py` to include `references: list[dict[str, object]]`. Build each item from the existing deduplicated `documents` collection with `path`, `title`, `tags`, and `links`. The collection already contains only provider-eligible governance and retrieval results, so do not issue a second index query. In `test_context.py`, create one public note and one `ai_sharing: local-only` note with unique title, tag, link, and body; assert the public object is the only reference and no private string occurs in either prompt or references. Run `PYTHONPATH=packages/vault-agent-core/src:packages/vault-agent-core/tests /usr/bin/python3 -m unittest packages/vault-agent-core/tests/test_context.py -q`; it must fail before the property exists and pass after implementation. Commit Core and test together as `Expose eligible vault context references`.

## Task 2: JSONL event

- [ ] Add `SessionStore.context_references(message)`.
- [ ] Emit `session.context` after source parsing and before text deltas.
- [ ] Test JSONL event order.

Implementation detail: add `SessionStore.context_references(message)` in `session.py`; it returns `ContextCompiler(self.index).compile(message).references`. In `rpc.py`, emit `{"id": request_id, "type": "session.context", "references": store.context_references(message)}` after `source_inspected` and before `started` or `text_delta`. Do not include document bodies. Update the session system instruction to require exact `[[relative/path|title]]` citations for supplied vault documents and canonical tags only when supplied by context; it must also state not to invent file-write results. In `test_rpc.py`, assert `session.context` occurs before the first `text_delta` and contains the expected public path. Run context, RPC, and session tests before committing as `Emit vault context references for clients`.

## Task 3: Obsidian navigation

- [ ] Render Core references in a Related vault context card.
- [ ] Open note paths with the Obsidian workspace API.
- [ ] Open canonical tags through an Obsidian search URI.
- [ ] Build and type-check the plugin.

Implementation detail: define `VaultReference` in `main.ts`. Handle `session.context` alongside `source_inspected`; render a compact card only when references are nonempty. For each note, use `app.metadataCache.getFirstLinkpathDest(path, "")` and `app.workspace.getLeaf(false).openFile(file)`; show an inline error if the file was removed. Deduplicate tags from the received references and open the exact tag search via `obsidian://search?query=tag%3A<encoded-tag>`. Add only `vault-agent-context-card`, `vault-agent-context-title`, `vault-agent-context-note`, and `vault-agent-context-tag` styles. Preserve MarkdownRenderer for inline model wikilinks. Build with the repository's esbuild command and `tsc --noEmit`, then commit as `Add clickable vault context references`.

## Task 4: Confirmed write state

- [ ] Track a prepared draft in the plugin.
- [ ] Stage through a visible confirmation control or exact `确认录入` command.
- [ ] Show a clickable Inbox result only after Core staging succeeds.
- [ ] Build and type-check the plugin.

Implementation detail: add `draftReady` to the view. Once `Prepare ingest draft` returns a valid Packet preview, set it true and retain a visible **Confirm write to Inbox** button. In `send`, intercept only an exact composer value of `确认录入` while `draftReady` is true; clear the composer and call the same `stageCurrentDraft` helper as the button. Before a draft exists, send that phrase to the model normally. `stageCurrentDraft` calls existing `session.stage(apply=true)`, clears readiness only after success, and renders a clickable relative Inbox path. On error it keeps readiness and the visible control. Reset readiness when starting a new session or successful stage. Commit after build as `Stage prepared drafts through explicit confirmation`.

## Task 5: Verification

- [ ] Document the additive event and exact confirmation command.
- [ ] Run all Core tests and plugin build.
- [ ] Manually verify note links, tag links, local-only exclusion, command staging, button staging, and no-draft command behavior.

Document `session.context` as an additive metadata-only event in `README.md`. Document card navigation and the exact confirmation phrase in the plugin README. Run the complete unittest discovery command and plugin build/type check. In Obsidian verify two eligible notes open from a card, canonical tag search opens, a `local-only` fixture is absent, both command and visible button stage a Packet to Inbox and return an openable link, and `确认录入` without a ready draft writes nothing. Commit documentation, push, and wait for green Core, plugin, and secret-scan CI.
