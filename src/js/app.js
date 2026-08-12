import { icons, getIcon } from './icons.js';
import { renderMarkdown } from './markdown.js';
import { OllamaManager } from './ollama.js';
import { AIEngine } from './api.js';

class ZeroAIDeskApp {
  constructor() {
    this.ollamaManager = new OllamaManager();
    this.aiEngine = new AIEngine();
    
    this.sessions = [];
    this.currentSessionId = null;
    this.isStreaming = false;
    this.abortController = null;
    this.selectedModelValue = '';

    this.initDOMReferences();
    this.initIcons();
    this.loadSavedSessions();
    this.initEventListeners();
    this.initTuningDrawer();
    this.initSettingsModal();
    this.initCustomDropdown();
    
    // Auto-detect Ollama status on startup
    this.checkOllamaStatus();
  }

  initDOMReferences() {
    this.sidebar = document.getElementById('sidebar');
    this.chatHistoryList = document.getElementById('chat-history-list');
    this.messagesContainer = document.getElementById('messages-container');
    this.chatInput = document.getElementById('chat-input');
    this.btnSend = document.getElementById('btn-send');
    this.btnNewChat = document.getElementById('btn-new-chat');
    this.tuningDrawer = document.getElementById('tuning-drawer');
    this.settingsModal = document.getElementById('settings-modal');
    this.ollamaStatusDot = document.getElementById('ollama-status-dot');
    this.ollamaStatusText = document.getElementById('ollama-status-text');
    this.ollamaStatusBadge = document.getElementById('ollama-status-badge');
    this.ollamaModalContainer = document.getElementById('ollama-modal-container');
    
    // Custom Dropdown References
    this.dropdownTrigger = document.getElementById('model-dropdown-trigger');
    this.dropdownMenu = document.getElementById('model-dropdown-menu');
    this.selectedModelText = document.getElementById('selected-model-text');
  }

  initIcons() {
    document.getElementById('brand-icon-slot').innerHTML = getIcon('logo');
    
    document.querySelectorAll('[data-icon]').forEach(el => {
      const iconName = el.getAttribute('data-icon');
      if (icons[iconName]) {
        el.innerHTML = getIcon(iconName);
      }
    });
  }

  initCustomDropdown() {
    this.dropdownTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      this.dropdownMenu.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!this.dropdownMenu.contains(e.target) && !this.dropdownTrigger.contains(e.target)) {
        this.dropdownMenu.classList.remove('open');
      }
    });
  }

  // Load chat sessions from local storage
  loadSavedSessions() {
    const saved = localStorage.getItem('zero_ai_sessions');
    if (saved) {
      try {
        this.sessions = JSON.parse(saved);
      } catch (e) {
        this.sessions = [];
      }
    }

    if (this.sessions.length === 0) {
      this.createNewSession();
    } else {
      this.currentSessionId = this.sessions[0].id;
      this.renderSidebarHistory();
      this.renderMessages();
    }
  }

  saveSessions() {
    localStorage.setItem('zero_ai_sessions', JSON.stringify(this.sessions));
  }

  createNewSession() {
    const newSession = {
      id: 'session_' + Date.now(),
      title: '新對話 ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      createdAt: new Date().toISOString(),
      messages: []
    };

    this.sessions.unshift(newSession);
    this.currentSessionId = newSession.id;
    this.saveSessions();
    this.renderSidebarHistory();
    this.renderMessages();
  }

  getCurrentSession() {
    return this.sessions.find(s => s.id === this.currentSessionId) || this.sessions[0];
  }

  renderSidebarHistory() {
    this.chatHistoryList.innerHTML = '';
    this.sessions.forEach(session => {
      const item = document.createElement('div');
      item.className = `history-item ${session.id === this.currentSessionId ? 'active' : ''}`;
      item.innerHTML = `
        <span class="history-title">${session.title}</span>
        <button class="history-delete" title="刪除對話" data-id="${session.id}">
          ${getIcon('trash')}
        </button>
      `;

      item.addEventListener('click', (e) => {
        if (e.target.closest('.history-delete')) return;
        this.currentSessionId = session.id;
        this.renderSidebarHistory();
        this.renderMessages();
      });

      const btnDelete = item.querySelector('.history-delete');
      btnDelete.addEventListener('click', (e) => {
        e.stopPropagation();
        this.deleteSession(session.id);
      });

      this.chatHistoryList.appendChild(item);
    });
  }

  deleteSession(sessionId) {
    this.sessions = this.sessions.filter(s => s.id !== sessionId);
    if (this.sessions.length === 0) {
      this.createNewSession();
    } else {
      if (this.currentSessionId === sessionId) {
        this.currentSessionId = this.sessions[0].id;
      }
      this.saveSessions();
      this.renderSidebarHistory();
      this.renderMessages();
    }
  }

  renderMessages() {
    const session = this.getCurrentSession();
    this.messagesContainer.innerHTML = '';

    if (!session.messages || session.messages.length === 0) {
      this.messagesContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); gap: 16px; text-align: center; margin-top: 60px;">
          <div style="width: 56px; height: 56px; border-radius: 16px; background: linear-gradient(135deg, var(--primary), var(--accent-purple)); display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 0 20px var(--primary-glow);">
            ${getIcon('logo')}
          </div>
          <h2 style="font-weight: 600; color: var(--text-main);">ZeroAI Desk 工作站</h2>
          <p style="max-width: 480px; font-size: 0.9rem; line-height: 1.6; color: var(--text-muted);">
            系統資源佔用極低 (&lt; 40MB RAM)。支援本地 <strong>Ollama</strong> 與遠端 <strong>OpenAI / DeepSeek / Claude</strong> 等多模型隨時切換與即時 Markdown 串流渲染。
          </p>
        </div>
      `;
      return;
    }

    session.messages.forEach(msg => {
      this.appendMessageBubble(msg.role, msg.content, false);
    });

    this.scrollToBottom();
  }

  appendMessageBubble(role, content, animate = true) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper';

    const isUser = role === 'user';
    const avatarClass = isUser ? 'user' : 'bot';
    const avatarIcon = isUser ? getIcon('user') : getIcon('bot');
    const senderName = isUser ? '使用者' : 'AI 助理';

    wrapper.innerHTML = `
      <div class="avatar ${avatarClass}">${avatarIcon}</div>
      <div class="message-body">
        <div class="message-header">
          <span class="sender-name">${senderName}</span>
        </div>
        <div class="message-content">${renderMarkdown(content)}</div>
      </div>
    `;

    this.messagesContainer.appendChild(wrapper);
    if (animate) this.scrollToBottom();
    return wrapper.querySelector('.message-content');
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  // Detect local Ollama and render high-end custom dropdown menu
  async checkOllamaStatus() {
    this.ollamaStatusDot.className = 'status-dot checking';
    this.ollamaStatusText.innerText = '探測 Ollama 中...';

    const res = await this.ollamaManager.checkConnection();

    this.dropdownMenu.innerHTML = '';
    const availableModelList = [];

    if (res.isConnected) {
      this.ollamaStatusDot.className = 'status-dot connected';
      this.ollamaStatusText.innerText = `Ollama 已連線 (${res.models.length} 個模型)`;

      if (res.models.length > 0) {
        const headerLocal = document.createElement('div');
        headerLocal.className = 'dropdown-group-header';
        headerLocal.innerHTML = `${getIcon('sparkles')} <span>本地 Ollama 模型</span>`;
        this.dropdownMenu.appendChild(headerLocal);

        res.models.forEach(m => {
          availableModelList.push({
            id: `ollama:${m.name}`,
            label: m.name,
            tag: 'Local',
            tagClass: 'local'
          });
        });
      }
    } else {
      this.ollamaStatusDot.className = 'status-dot disconnected';
      this.ollamaStatusText.innerText = 'Ollama 未運行 (點擊安裝)';
    }

    // Append Remote API Models
    const headerRemote = document.createElement('div');
    headerRemote.className = 'dropdown-group-header';
    headerRemote.innerHTML = `${getIcon('cloud')} <span>遠端 API 模型</span>`;
    this.dropdownMenu.appendChild(headerRemote);

    const remoteModels = [
      { id: 'openai:gpt-4o-mini', label: 'OpenAI gpt-4o-mini', tag: 'Remote', tagClass: 'remote' },
      { id: 'openai:gpt-4o', label: 'OpenAI gpt-4o', tag: 'Remote', tagClass: 'remote' },
      { id: 'deepseek:deepseek-chat', label: 'DeepSeek-V3', tag: 'Remote', tagClass: 'remote' },
      { id: 'deepseek:deepseek-reasoner', label: 'DeepSeek-R1 (推理模型)', tag: 'Remote', tagClass: 'remote' },
      { id: 'anthropic:claude-3-5-sonnet-20241022', label: 'Anthropic Claude 3.5 Sonnet', tag: 'Remote', tagClass: 'remote' }
    ];

    remoteModels.forEach(rm => availableModelList.push(rm));

    // Render items into dropdown
    availableModelList.forEach((mItem, index) => {
      const itemEl = document.createElement('div');
      itemEl.className = `dropdown-item ${this.selectedModelValue === mItem.id || (!this.selectedModelValue && index === 0) ? 'active' : ''}`;
      itemEl.innerHTML = `
        <span style="font-weight: 500;">${mItem.label}</span>
        <span class="model-tag ${mItem.tagClass}">${mItem.tag}</span>
      `;

      itemEl.addEventListener('click', () => {
        this.selectModel(mItem);
        this.dropdownMenu.classList.remove('open');
      });

      this.dropdownMenu.appendChild(itemEl);
    });

    // Default selection
    if (!this.selectedModelValue && availableModelList.length > 0) {
      this.selectModel(availableModelList[0]);
    }
  }

  selectModel(modelItem) {
    this.selectedModelValue = modelItem.id;
    this.selectedModelText.innerText = `[${modelItem.tag}] ${modelItem.label}`;

    // Highlight active item in menu
    this.dropdownMenu.querySelectorAll('.dropdown-item').forEach(el => {
      if (el.innerText.includes(modelItem.label)) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    const val = modelItem.id;
    if (val.startsWith('ollama:')) {
      const modelName = val.replace('ollama:', '');
      this.aiEngine.updateSettings({
        provider: 'ollama',
        model: modelName,
        baseUrl: 'http://127.0.0.1:11434'
      });
    } else if (val.startsWith('openai:')) {
      const modelName = val.replace('openai:', '');
      this.aiEngine.updateSettings({
        provider: 'openai',
        model: modelName,
        baseUrl: 'https://api.openai.com'
      });
    } else if (val.startsWith('deepseek:')) {
      const modelName = val.replace('deepseek:', '');
      this.aiEngine.updateSettings({
        provider: 'deepseek',
        model: modelName,
        baseUrl: 'https://api.deepseek.com'
      });
    } else if (val.startsWith('anthropic:')) {
      const modelName = val.replace('anthropic:', '');
      this.aiEngine.updateSettings({
        provider: 'anthropic',
        model: modelName
      });
    }
  }

  // Handle message sending & streaming
  async sendMessage() {
    const text = this.chatInput.value.trim();
    if (!text || this.isStreaming) return;

    const session = this.getCurrentSession();
    
    // Auto title update for first message
    if (session.messages.length === 0) {
      session.title = text.slice(0, 20) + (text.length > 20 ? '...' : '');
      this.renderSidebarHistory();
    }

    session.messages.push({ role: 'user', content: text });
    this.saveSessions();

    if (session.messages.length === 1) {
      this.renderMessages();
    } else {
      this.appendMessageBubble('user', text);
    }

    this.chatInput.value = '';
    this.chatInput.style.height = 'auto';

    // Prepare assistant response bubble
    const responseContentEl = this.appendMessageBubble('assistant', '');
    this.isStreaming = true;
    this.btnSend.disabled = true;

    this.abortController = new AbortController();
    let streamedResponseText = '';

    await this.aiEngine.streamChat(
      session.messages,
      (chunk) => {
        streamedResponseText += chunk;
        responseContentEl.innerHTML = renderMarkdown(streamedResponseText, { isStreaming: true });
        this.scrollToBottom();
      },
      (err) => {
        streamedResponseText += `\n\n> ⚠️ **錯誤通知**：${err.message}`;
        responseContentEl.innerHTML = renderMarkdown(streamedResponseText);
      },
      this.abortController.signal
    );

    session.messages.push({ role: 'assistant', content: streamedResponseText });
    this.saveSessions();

    this.isStreaming = false;
    this.btnSend.disabled = false;
  }

  initEventListeners() {
    // Send button & textarea keydown
    this.btnSend.addEventListener('click', () => this.sendMessage());
    
    this.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Auto expand textarea
    this.chatInput.addEventListener('input', () => {
      this.chatInput.style.height = 'auto';
      this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 200) + 'px';
    });

    // New chat button
    this.btnNewChat.addEventListener('click', () => this.createNewSession());

    // Sidebar toggles
    document.getElementById('btn-toggle-sidebar').addEventListener('click', () => {
      this.sidebar.classList.add('collapsed');
      document.getElementById('btn-expand-sidebar').style.display = 'flex';
    });

    document.getElementById('btn-expand-sidebar').addEventListener('click', () => {
      this.sidebar.classList.remove('collapsed');
      document.getElementById('btn-expand-sidebar').style.display = 'none';
    });

    // Ollama badge click -> open guide modal if disconnected or refresh status
    this.ollamaStatusBadge.addEventListener('click', () => {
      if (!this.ollamaManager.isConnected) {
        this.ollamaModalContainer.innerHTML = this.ollamaManager.renderInstallationModal();
        
        const btnRecheck = document.getElementById('btn-recheck-ollama');
        if (btnRecheck) {
          btnRecheck.addEventListener('click', async () => {
            await this.checkOllamaStatus();
            if (this.ollamaManager.isConnected) {
              const modal = document.getElementById('ollama-guide-modal');
              if (modal) modal.classList.remove('open');
            }
          });
        }
      } else {
        this.checkOllamaStatus();
      }
    });

    // Export Chat History
    document.getElementById('btn-export-chat').addEventListener('click', () => {
      const session = this.getCurrentSession();
      let mdContent = `# ${session.title}\n\n`;
      session.messages.forEach(m => {
        mdContent += `### ${m.role === 'user' ? 'User' : 'Assistant'}\n${m.content}\n\n---\n\n`;
      });

      const blob = new Blob([mdContent], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${session.title.replace(/[^\w\s\u4e00-\u9fa5]/gi, '_')}.md`;
      a.click();
    });
  }

  // Initialize AI Fine-Tuning Parameter Drawer
  initTuningDrawer() {
    const btnToggle = document.getElementById('btn-toggle-tuning');
    const btnClose = document.getElementById('btn-close-tuning');

    btnToggle.addEventListener('click', () => this.tuningDrawer.classList.toggle('open'));
    btnClose.addEventListener('click', () => this.tuningDrawer.classList.remove('open'));

    // Bind parameter sliders
    const bindSlider = (id, valId, paramKey) => {
      const slider = document.getElementById(id);
      const valDisplay = document.getElementById(valId);
      slider.addEventListener('input', () => {
        valDisplay.innerText = slider.value;
        const updateObj = { parameters: {} };
        updateObj.parameters[paramKey] = slider.value;
        this.aiEngine.updateSettings(updateObj);
      });
    };

    bindSlider('slider-temperature', 'val-temperature', 'temperature');
    bindSlider('slider-topp', 'val-topp', 'top_p');
    bindSlider('slider-maxtokens', 'val-maxtokens', 'max_tokens');
    bindSlider('slider-repeatpenalty', 'val-repeatpenalty', 'repeat_penalty');

    // System prompt input
    const systemPromptInput = document.getElementById('input-system-prompt');
    systemPromptInput.addEventListener('input', () => {
      this.aiEngine.updateSettings({
        parameters: { systemPrompt: systemPromptInput.value }
      });
    });

    // Preset helper attached to window
    window.setParamPreset = (paramKey, value) => {
      if (paramKey === 'temperature') {
        document.getElementById('slider-temperature').value = value;
        document.getElementById('val-temperature').innerText = value;
        this.aiEngine.updateSettings({ parameters: { temperature: value } });
      }
    };

    window.setSystemPreset = (type) => {
      let prompt = '';
      if (type === 'code') {
        prompt = 'You are an expert senior software engineer. Write efficient, clean, type-safe, and well-documented code with detailed explanations.';
      } else if (type === 'translate') {
        prompt = 'You are a professional multi-lingual translator. Translate the text accurately while maintaining context, tone, and formatting.';
      } else if (type === 'concise') {
        prompt = 'You are a concise analytical assistant. Provide clear, direct, bullet-pointed answers without fluff.';
      }

      systemPromptInput.value = prompt;
      this.aiEngine.updateSettings({ parameters: { systemPrompt: prompt } });
    };
  }

  // Initialize Remote API Settings Modal
  initSettingsModal() {
    const btnOpen = document.getElementById('btn-open-settings');
    const btnClose = document.getElementById('btn-close-settings');
    const btnSave = document.getElementById('btn-save-settings');

    btnOpen.addEventListener('click', () => this.settingsModal.classList.add('open'));
    btnClose.addEventListener('click', () => this.settingsModal.classList.remove('open'));

    btnSave.addEventListener('click', () => {
      const provider = document.getElementById('settings-provider-select').value;
      const baseUrl = document.getElementById('settings-base-url').value.trim();
      const apiKey = document.getElementById('settings-api-key').value.trim();

      const updateObj = { provider };
      if (baseUrl) updateObj.baseUrl = baseUrl;
      if (apiKey) updateObj.apiKey = apiKey;

      this.aiEngine.updateSettings(updateObj);
      this.settingsModal.classList.remove('open');
      alert('API 設定已更新成功！');
    });
  }
}

// Instantiate app on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.app = new ZeroAIDeskApp();
});
