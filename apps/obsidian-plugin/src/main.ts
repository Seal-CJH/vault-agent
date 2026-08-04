import { ItemView, Plugin, WorkspaceLeaf } from "obsidian";

const VIEW_TYPE = "vault-agent";

class VaultAgentView extends ItemView {
  constructor(leaf: WorkspaceLeaf) { super(leaf); }
  getViewType() { return VIEW_TYPE; }
  getDisplayText() { return "Vault Agent"; }
  async onOpen() {
    this.contentEl.createEl("h2", { text: "Vault Agent" });
    this.contentEl.createEl("p", { text: "Configure the local CLI before starting a source discussion." });
  }
}

export default class VaultAgentPlugin extends Plugin {
  async onload() {
    this.registerView(VIEW_TYPE, leaf => new VaultAgentView(leaf));
    this.addRibbonIcon("messages-square", "Open Vault Agent", () => this.activateView());
  }
  async activateView() {
    const leaf = this.app.workspace.getRightLeaf(false);
    if (leaf) await leaf.setViewState({ type: VIEW_TYPE, active: true });
  }
}
