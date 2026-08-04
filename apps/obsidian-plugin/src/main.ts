import { App, ItemView, Plugin, PluginSettingTab, Setting, WorkspaceLeaf } from "obsidian";
import { execFile } from "child_process";

const VIEW_TYPE = "vault-agent";

interface VaultAgentSettings { cliPath: string; }
const DEFAULT_SETTINGS: VaultAgentSettings = { cliPath: "vault-agent" };

class VaultAgentView extends ItemView {
  constructor(leaf: WorkspaceLeaf, private plugin: VaultAgentPlugin) { super(leaf); }
  getViewType() { return VIEW_TYPE; }
  getDisplayText() { return "Vault Agent"; }
  async onOpen() {
    this.contentEl.createEl("h2", { text: "Vault Agent" });
    const status = this.contentEl.createEl("p", { text: "Reading local provider configuration…" });
    try {
      const config = await this.plugin.providerConfig();
      status.setText(`DeepSeek · ${config.model} · thinking ${config.thinking ? "enabled" : "disabled"} · ${config.reasoning_effort}`);
    } catch {
      status.setText("Local CLI is not configured. Set its path in Vault Agent settings.");
    }
  }
}

class VaultAgentSettingTab extends PluginSettingTab {
  constructor(app: App, private plugin: VaultAgentPlugin) { super(app, plugin); }
  display() {
    this.containerEl.empty();
    new Setting(this.containerEl)
      .setName("Vault Agent CLI path")
      .setDesc("The installed vault-agent executable. No API key is stored by Obsidian.")
      .addText(text => text.setValue(this.plugin.settings.cliPath).onChange(async value => {
        this.plugin.settings.cliPath = value || DEFAULT_SETTINGS.cliPath;
        await this.plugin.saveSettings();
      }));
  }
}

export default class VaultAgentPlugin extends Plugin {
  settings: VaultAgentSettings = DEFAULT_SETTINGS;
  async onload() {
    await this.loadSettings();
    this.registerView(VIEW_TYPE, leaf => new VaultAgentView(leaf, this));
    this.addRibbonIcon("messages-square", "Open Vault Agent", () => this.activateView());
    this.addSettingTab(new VaultAgentSettingTab(this.app, this));
  }
  async activateView() {
    const leaf = this.app.workspace.getRightLeaf(false);
    if (leaf) await leaf.setViewState({ type: VIEW_TYPE, active: true });
  }
  async loadSettings() { this.settings = { ...DEFAULT_SETTINGS, ...(await this.loadData()) }; }
  async saveSettings() { await this.saveData(this.settings); }
  providerConfig(): Promise<{ model: string; thinking: boolean; reasoning_effort: string }> {
    return new Promise((resolve, reject) => execFile(this.settings.cliPath, ["provider", "show"], (error, stdout) => {
      if (error) return reject(error);
      try { resolve(JSON.parse(stdout)); } catch (parseError) { reject(parseError); }
    }));
  }
}
