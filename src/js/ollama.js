import { getIcon } from './icons.js';

export class OllamaManager {
  constructor(baseUrl = 'http://127.0.0.1:11434') {
    this.baseUrl = baseUrl;
    this.isConnected = false;
    this.models = [];
  }

  // Auto-detect local Ollama installation & status
  async checkConnection() {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(3000)
      });

      if (response.ok) {
        const data = await response.json();
        this.isConnected = true;
        this.models = data.models || [];
        return { isConnected: true, models: this.models };
      }
    } catch (err) {
      console.warn('Ollama local ping failed:', err);
    }

    this.isConnected = false;
    this.models = [];
    return { isConnected: false, models: [] };
  }

  // Create installation and setup prompt modal HTML when Ollama is missing
  renderInstallationModal() {
    return `
      <div id="ollama-guide-modal" class="modal-backdrop open">
        <div class="modal-card">
          <div class="modal-header">
            <div class="modal-title" style="color: var(--accent-amber);">
              ${getIcon('alert')} 未偵測到本地 Ollama 服務
            </div>
            <button class="icon-btn" onclick="document.getElementById('ollama-guide-modal').classList.remove('open')">
              ${getIcon('close')}
            </button>
          </div>
          
          <div style="font-size: 0.9rem; line-height: 1.6; color: var(--text-muted);">
            ZeroAI Desk 具備本地 AI 隱私運算功能。若欲使用本地模型 (如 Llama 3.2, Qwen 2.5, DeepSeek R1)，請安裝並啟動 <strong>Ollama</strong>。
          </div>

          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-main);">1. 快速安裝指令 (開啟終端機執行)：</div>
            <div class="cmd-box">
              <span>winget install Ollama.Ollama</span>
              <button class="copy-code-btn" onclick="navigator.clipboard.writeText('winget install Ollama.Ollama'); this.innerText='已複製!';">
                ${getIcon('copy')}
              </button>
            </div>

            <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); margin-top: 6px;">2. 或從官網下載安裝包：</div>
            <a href="https://ollama.com/download" target="_blank" class="new-chat-btn" style="justify-content: center; text-decoration: none; border-style: solid; border-color: var(--primary);">
              ${getIcon('external')} 下載 Ollama (Windows / Mac / Linux)
            </a>
          </div>

          <div style="padding-top: 12px; border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.8rem; color: var(--text-dim);">安裝後請確保 Ollama 已於背景運行</span>
            <button id="btn-recheck-ollama" class="new-chat-btn" style="margin: 0; padding: 8px 16px; background-color: var(--primary); color: white; border: none;">
              ${getIcon('refresh')} 重新偵測連線
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // Pull new model via Ollama API
  async pullModel(modelName, onProgress) {
    try {
      const response = await fetch(`${this.baseUrl}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: modelName, stream: true })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunks = decoder.decode(value, { stream: true }).split('\n');
        for (const chunk of chunks) {
          if (!chunk.trim()) continue;
          try {
            const data = JSON.parse(chunk);
            if (onProgress) onProgress(data);
          } catch (e) {
            // parsing line chunk
          }
        }
      }

      return { success: true };
    } catch (err) {
      console.error('Failed to pull Ollama model:', err);
      return { success: false, error: err.message };
    }
  }
}
