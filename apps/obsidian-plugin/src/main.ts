import { App, ItemView, MarkdownRenderer, Plugin, PluginSettingTab, Setting, WorkspaceLeaf } from "obsidian";
import { ChildProcess, spawn } from "child_process";

const VIEW_TYPE = "vault-agent";
interface VaultAgentSettings { cliPath: string; }
interface SessionSummary { id: string; preview: string; source_language: string; updated_at: string; last_model: string; }
interface SessionRecord { id: string; source_language: string; messages: Array<{ role: string; content: string }>; }
interface ReviewReport { total_notes: number; inbox_notes: string[]; claims_without_links: string[]; sources_without_links: string[]; }
const DEFAULT_SETTINGS: VaultAgentSettings = { cliPath: "/Users/seal/Projects/Vault-Agent/scripts/vault-agent" };

class VaultAgentView extends ItemView {
  private process: ChildProcess | null = null;
  private composer!: HTMLTextAreaElement;
  private sendButton!: HTMLButtonElement;
  private thread!: HTMLElement;
  private modelChip!: HTMLElement;
  private language!: HTMLSelectElement;
  private sessionId: string | null = null;
  constructor(leaf: WorkspaceLeaf, private plugin: VaultAgentPlugin) { super(leaf); }
  getViewType() { return VIEW_TYPE; }
  getDisplayText() { return "Vault Agent"; }
  async onOpen() {
    this.contentEl.empty(); this.contentEl.addClass("vault-agent-shell");
    const header = this.contentEl.createDiv({ cls: "vault-agent-header" });
    header.createEl("strong", { text: "Vault Agent" });
    const review = header.createEl("button", { text: "Review", cls: "vault-agent-quiet" });
    review.onclick = () => void this.showReview();
    const history = header.createEl("button", { text: "History", cls: "vault-agent-quiet" });
    history.onclick = () => void this.showHistory();
    const reset = header.createEl("button", { text: "＋ New", cls: "vault-agent-quiet" });
    reset.onclick = () => { this.thread.empty(); this.sessionId = null; this.composer.value = ""; this.composer.focus(); };
    this.thread = this.contentEl.createDiv({ cls: "vault-agent-thread" });
    this.thread.createDiv({ cls: "vault-agent-empty", text: "Paste a link, excerpt, note, or question to start a source discussion." });
    const composer = this.contentEl.createDiv({ cls: "vault-agent-composer" });
    this.composer = composer.createEl("textarea", { attr: { placeholder: "Discuss this source…" } }); this.composer.rows = 3;
    this.composer.addEventListener("keydown", event => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); void this.send(); } });
    const bar = composer.createDiv({ cls: "vault-agent-composer-bar" });
    this.language = bar.createEl("select"); ["zh-CN", "en"].forEach(value => this.language.createEl("option", { value, text: value }));
    this.modelChip = bar.createSpan({ cls: "vault-agent-model-chip", text: "Checking model…" });
    this.sendButton = bar.createEl("button", { text: "↑ Send", cls: "mod-cta vault-agent-send" });
    this.sendButton.onclick = () => this.process ? this.stop() : void this.send(this.language.value);
    await this.refreshModel();
  }
  async refreshModel() { try { const c = await this.plugin.providerConfig(); this.modelChip.setText(`DeepSeek · ${c.model.replace("deepseek-", "")} · Thinking ${c.thinking ? "on" : "off"}`); } catch { this.modelChip.setText("CLI unavailable — check settings"); } }
  private append(role: string, text = "") { const card = this.thread.createDiv({ cls: `vault-agent-message vault-agent-${role}` }); const meta = card.createDiv({ cls: "vault-agent-message-meta" }); meta.createDiv({ cls: "vault-agent-role", text: role === "user" ? "You" : "Vault Agent" }); const body = card.createDiv({ cls: "vault-agent-body", text }); body.dataset.markdown = text; const copy = meta.createEl("button", { text: "Copy", cls: "vault-agent-copy" }); copy.onclick = async () => { await navigator.clipboard.writeText(body.dataset.markdown ?? body.textContent ?? ""); copy.setText("Copied"); window.setTimeout(() => copy.setText("Copy"), 1200); }; this.thread.scrollTop = this.thread.scrollHeight; return body; }
  private async renderMarkdown(body: HTMLElement) { const markdown = body.dataset.markdown; if (!markdown) return; body.empty(); await MarkdownRenderer.render(this.app, markdown, body, "", this); }
  private async send(language = "zh-CN") {
    const message = this.composer.value.trim(); if (!message || this.process) return;
    this.thread.querySelector(".vault-agent-empty")?.remove(); this.append("user", message); const body = this.append("agent", "Preparing vault context…"); this.composer.value = "";
    this.sendButton.setText("■ Stop"); this.sendButton.addClass("mod-warning");
    try { this.sessionId ??= await this.plugin.startSession(this.vaultPath(), language); } catch (error) { body.setText(`Vault index could not start: ${error instanceof Error ? error.message : String(error)}`); this.stop(); return; }
    this.process = spawn(this.plugin.settings.cliPath, ["rpc"]);
    this.process.stdin?.end(JSON.stringify({ id: `obsidian-${Date.now()}`, method: "session.turn", params: { vault: this.vaultPath(), session_id: this.sessionId, message, confirm_remote: true } }) + "\n");
    let buffer = "";
    this.process.stdout?.on("data", chunk => { buffer += chunk.toString(); const lines = buffer.split("\n"); buffer = lines.pop() ?? ""; lines.filter(Boolean).forEach(line => { try { const event = JSON.parse(line); if (event.type === "error") { body.dataset.markdown = ""; body.setText(`Core error: ${event.message}`); } if (event.type === "source_inspected") { const source = event.source as { kind: string; title: string; provenance: string; content_language?: string }; const status = this.append("agent", `> Source parsed locally: **${source.title}** (${source.kind}, ${source.content_language || "language unknown"})\n> ${source.provenance}`); void this.renderMarkdown(status); body.parentElement && this.thread.appendChild(body.parentElement); } if (event.type === "text_delta") { if (body.textContent === "Preparing vault context…") body.empty(); body.dataset.markdown = (body.dataset.markdown === "Preparing vault context…" ? "" : body.dataset.markdown ?? "") + event.delta; body.appendText(event.delta); this.thread.scrollTop = this.thread.scrollHeight; } } catch { /* protocol errors go to stderr */ } }); });
    this.process.stderr?.on("data", chunk => { const error = `Setup error: ${chunk.toString().trim()}`; body.dataset.markdown = ""; body.setText(error); });
    this.process.on("close", () => { this.process = null; this.sendButton.setText("↑ Send"); this.sendButton.removeClass("mod-warning"); if (body.textContent === "Preparing vault context…") body.setText("No response received."); else { void this.renderMarkdown(body); this.addDraftAction(); } });
    this.process.on("error", error => { body.setText(`CLI could not start: ${error.message}. Check Vault Agent settings.`); });
  }
  private stop() { this.process?.kill("SIGTERM"); this.process = null; this.sendButton.setText("↑ Send"); this.sendButton.removeClass("mod-warning"); }
  private async showHistory() {
    this.thread.empty();
    const panel = this.thread.createDiv({ cls: "vault-agent-history" });
    panel.createEl("div", { text: "Local sessions", cls: "vault-agent-history-title" });
    try {
      const sessions = await this.plugin.listSessions(this.vaultPath());
      if (!sessions.length) { panel.createDiv({ text: "No local sessions yet.", cls: "vault-agent-empty" }); return; }
      sessions.forEach(summary => {
        const item = panel.createEl("button", { cls: "vault-agent-history-item" });
        item.createDiv({ text: summary.preview || "New discussion" });
        item.createEl("small", { text: `${summary.source_language} · ${summary.last_model}` });
        item.onclick = () => void this.restoreSession(summary.id);
      });
    } catch (error) { panel.createDiv({ text: error instanceof Error ? error.message : String(error), cls: "vault-agent-action-error" }); }
  }
  private async showReview() {
    const body = this.append("agent", "Running local vault review…");
    try {
      const report = await this.plugin.reviewVault(this.vaultPath());
      body.dataset.markdown = this.reviewMarkdown(report);
      await this.renderMarkdown(body);
    } catch (error) { body.dataset.markdown = ""; body.setText(error instanceof Error ? error.message : String(error)); }
  }
  private reviewMarkdown(report: ReviewReport): string {
    const list = (items: string[]) => items.length ? items.map(item => `- \`${item}\``).join("\n") : "- None";
    return `## Local Vault Review\n\n- Notes indexed: ${report.total_notes}\n\n### Inbox candidates\n${list(report.inbox_notes)}\n\n### Claims without wikilinks\n${list(report.claims_without_links)}\n\n### Sources without wikilinks\n${list(report.sources_without_links)}\n\n_This report is local and read-only; it does not call a model or edit the vault._`;
  }
  private async restoreSession(sessionId: string) {
    const session = await this.plugin.showSession(this.vaultPath(), sessionId);
    this.sessionId = session.id; this.language.value = session.source_language; this.thread.empty();
    for (const message of session.messages) {
      const body = this.append(message.role === "user" ? "user" : "agent", message.content);
      if (message.role !== "user") await this.renderMarkdown(body);
    }
    this.composer.focus();
  }
  private addDraftAction() {
    if (!this.sessionId) return;
    const actions = this.thread.createDiv({ cls: "vault-agent-actions" });
    const prepare = actions.createEl("button", { text: "Prepare ingest draft", cls: "vault-agent-action-primary" });
    prepare.onclick = async () => {
      prepare.disabled = true; prepare.setText("Preparing draft…");
      try {
        const draft = await this.plugin.prepareDraft(this.vaultPath(), this.sessionId!);
        actions.empty();
        const preview = this.append("agent", draft.packet);
        await this.renderMarkdown(preview);
        const confirm = actions.createEl("button", { text: "Confirm stage to Inbox", cls: "mod-cta vault-agent-action-primary" });
        confirm.onclick = async () => {
          confirm.disabled = true; confirm.setText("Staging…");
          try {
            const result = await this.plugin.stageDraft(this.vaultPath(), this.sessionId!);
            actions.createSpan({ cls: "vault-agent-stage-result", text: `Saved to ${result.path}` });
            confirm.remove();
          } catch (error) { confirm.disabled = false; confirm.setText("Confirm stage to Inbox"); actions.createDiv({ cls: "vault-agent-action-error", text: error instanceof Error ? error.message : String(error) }); }
        };
      } catch (error) { prepare.disabled = false; prepare.setText("Prepare ingest draft"); actions.createDiv({ cls: "vault-agent-action-error", text: error instanceof Error ? error.message : String(error) }); }
    };
  }
  private vaultPath(): string { return (this.app.vault.adapter as unknown as { getBasePath(): string }).getBasePath(); }
}
class VaultAgentSettingTab extends PluginSettingTab { constructor(app: App, private plugin: VaultAgentPlugin) { super(app, plugin); } display() { this.containerEl.empty(); new Setting(this.containerEl).setName("Vault Agent CLI path").setDesc("Absolute path to the local launcher; API keys are never stored here.").addText(text => text.setValue(this.plugin.settings.cliPath).onChange(async value => { this.plugin.settings.cliPath = value || DEFAULT_SETTINGS.cliPath; await this.plugin.saveSettings(); })); } }
export default class VaultAgentPlugin extends Plugin {
  settings: VaultAgentSettings = DEFAULT_SETTINGS;
  async onload() { await this.loadSettings(); this.registerView(VIEW_TYPE, leaf => new VaultAgentView(leaf, this)); this.addRibbonIcon("messages-square", "Open Vault Agent", () => this.activateView()); this.addSettingTab(new VaultAgentSettingTab(this.app, this)); }
  async activateView() { const leaf = this.app.workspace.getRightLeaf(false); if (leaf) await leaf.setViewState({ type: VIEW_TYPE, active: true }); }
  async loadSettings() { this.settings = { ...DEFAULT_SETTINGS, ...(await this.loadData()) }; }
  async saveSettings() { await this.saveData(this.settings); }
  providerConfig(): Promise<{ model: string; thinking: boolean }> { return this.rpcCall("provider.show", {}); }
  async startSession(vault: string, sourceLanguage: string): Promise<string> { return (await this.rpcCall<{ session_id: string }>("session.start", { vault, source_language: sourceLanguage })).session_id; }
  prepareDraft(vault: string, sessionId: string): Promise<{ packet: string; title: string }> { return this.rpcCall("session.draft", { vault, session_id: sessionId, confirm_remote: true }); }
  stageDraft(vault: string, sessionId: string): Promise<{ path: string }> { return this.rpcCall("session.stage", { vault, session_id: sessionId, apply: true }); }
  async listSessions(vault: string): Promise<SessionSummary[]> { return (await this.rpcCall<{ sessions: SessionSummary[] }>("session.list", { vault })).sessions; }
  showSession(vault: string, sessionId: string): Promise<SessionRecord> { return this.rpcCall("session.show", { vault, session_id: sessionId }); }
  reviewVault(vault: string): Promise<ReviewReport> { return this.rpcCall("review.run", { vault }); }
  private rpcCall<T>(method: string, params: Record<string, unknown>): Promise<T> { return new Promise((resolve, reject) => { const child = spawn(this.settings.cliPath, ["rpc"]); let stdout = ""; let stderr = ""; child.stdout?.on("data", chunk => { stdout += chunk.toString(); }); child.stderr?.on("data", chunk => { stderr += chunk.toString(); }); child.on("error", reject); child.on("close", () => { try { const events = stdout.split("\n").filter(Boolean).map(line => JSON.parse(line)); const error = events.find(event => event.type === "error"); if (error) return reject(new Error(error.message)); const completed = events.find(event => event.type === "completed"); if (!completed) return reject(new Error(stderr || "Core returned no completed event.")); resolve(completed.result as T); } catch (error) { reject(error); } }); child.stdin?.end(JSON.stringify({ id: `obsidian-${Date.now()}`, method, params }) + "\n"); }); }
}
