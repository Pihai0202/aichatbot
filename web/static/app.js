document.addEventListener("DOMContentLoaded", () => {
  let config = {
    provider: "ollama",
    ollama_url: "http://localhost:11434",
    ollama_model: "llama3:latest",
    openai_url: "https://generativelanguage.googleapis.com/v1beta/openai/",
    openai_key: "",
    openai_model: "gemini-2.0-flash",
    temperature: 0.7,
    num_ctx: 4096,
    repeat_penalty: 1.1,
    system_prompt: "You are a helpful, concise AI assistant."
  };

  let sessions = [
    { id: "1", title: "New Conversation", messages: [] }
  ];
  let activeSessionIdx = 0;

  // DOM Elements
  const sessionListEl = document.getElementById("session-list");
  const messagesContainerEl = document.getElementById("chat-messages");
  const heroWelcomeEl = document.getElementById("hero-welcome");
  const promptInputEl = document.getElementById("prompt-input");
  const btnSendEl = document.getElementById("btn-send");
  const btnNewChatEl = document.getElementById("btn-new-chat");
  const quickModelSelectEl = document.getElementById("quick-model-select");

  // Modal DOM
  const modalEl = document.getElementById("settings-modal");
  const btnOpenSettingsEl = document.getElementById("btn-open-settings");
  const btnCloseModalEl = document.getElementById("btn-close-modal");
  const btnSaveSettingsEl = document.getElementById("btn-save-settings");

  const settingProviderEl = document.getElementById("setting-provider");
  const settingOllamaUrlEl = document.getElementById("setting-ollama-url");
  const settingOpenaiUrlEl = document.getElementById("setting-openai-url");
  const settingOpenaiKeyEl = document.getElementById("setting-openai-key");
  const settingTempEl = document.getElementById("setting-temp");
  const valTempEl = document.getElementById("val-temp");
  const settingNumCtxEl = document.getElementById("setting-num-ctx");
  const settingRepeatEl = document.getElementById("setting-repeat");
  const valRepeatEl = document.getElementById("val-repeat");
  const settingSystemPromptEl = document.getElementById("setting-system-prompt");

  // Load config & sessions from localStorage
  const savedCfg = localStorage.getItem("aichat_cfg");
  if (savedCfg) {
    try { config = { ...config, ...JSON.parse(savedCfg) }; } catch (e) {}
  }
  const savedSess = localStorage.getItem("aichat_sessions");
  if (savedSess) {
    try { sessions = JSON.parse(savedSess); } catch (e) {}
  }

  // Configure Marked markdown
  marked.setOptions({
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    },
    breaks: true
  });

  function saveStorage() {
    localStorage.setItem("aichat_cfg", JSON.stringify(config));
    localStorage.setItem("aichat_sessions", JSON.stringify(sessions));
  }

  function fetchModels() {
    if (config.provider === "openai") {
      quickModelSelectEl.innerHTML = "";
      const opt = document.createElement("option");
      opt.value = config.openai_model || "gemini-2.0-flash";
      opt.textContent = config.openai_model || "gemini-2.0-flash";
      quickModelSelectEl.appendChild(opt);
      return;
    }

    fetch("/api/models?url=" + encodeURIComponent(config.ollama_url))
      .then(res => res.json())
      .then(models => {
        quickModelSelectEl.innerHTML = "";
        if (models && models.length > 0) {
          models.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m;
            if (m === config.ollama_model) opt.selected = true;
            quickModelSelectEl.appendChild(opt);
          });
        } else {
          const opt = document.createElement("option");
          opt.value = config.ollama_model;
          opt.textContent = config.ollama_model + " (Not pulled)";
          quickModelSelectEl.appendChild(opt);
        }
      })
      .catch(() => {});
  }

  function renderSidebar() {
    sessionListEl.innerHTML = "";
    sessions.forEach((s, idx) => {
      const item = document.createElement("div");
      item.className = "session-item" + (idx === activeSessionIdx ? " active" : "");
      item.textContent = s.title || "Chat " + (idx + 1);
      item.addEventListener("click", () => {
        activeSessionIdx = idx;
        renderSidebar();
        renderMessages();
      });
      sessionListEl.appendChild(item);
    });
  }

  function renderMessages() {
    const sess = sessions[activeSessionIdx];
    if (!sess || sess.messages.length === 0) {
      heroWelcomeEl.classList.remove("hidden");
      messagesContainerEl.classList.add("hidden");
      return;
    }

    heroWelcomeEl.classList.add("hidden");
    messagesContainerEl.classList.remove("hidden");
    messagesContainerEl.innerHTML = "";

    sess.messages.forEach(m => {
      const bubble = document.createElement("div");
      bubble.className = "message-bubble " + m.role;

      const avatar = document.createElement("div");
      avatar.className = "message-avatar";
      avatar.textContent = m.role === "user" ? "YY" : "✨";

      const body = document.createElement("div");
      body.className = "message-body";

      if (m.role === "assistant") {
        body.innerHTML = marked.parse(m.content || "...");
      } else {
        body.textContent = m.content;
      }

      bubble.appendChild(avatar);
      bubble.appendChild(body);
      messagesContainerEl.appendChild(bubble);
    });

    messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
  }

  function sendMessage() {
    const text = promptInputEl.value.trim();
    if (!text) return;

    promptInputEl.value = "";
    const sess = sessions[activeSessionIdx];

    if (sess.messages.length === 0) {
      sess.title = text.length > 18 ? text.slice(0, 18) + "..." : text;
      renderSidebar();
    }

    sess.messages.push({ role: "user", content: text });
    sess.messages.push({ role: "assistant", content: "" });
    renderMessages();

    // Fetch SSE Stream
    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        config: config,
        messages: sess.messages.slice(0, -1)
      })
    }).then(response => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      function read() {
        reader.read().then(({ done, value }) => {
          if (done) {
            saveStorage();
            return;
          }
          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");
          lines.forEach(line => {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") return;
              try {
                const parsed = JSON.parse(data);
                if (parsed.token) {
                  sess.messages[sess.messages.length - 1].content += parsed.token;
                  renderMessages();
                } else if (parsed.error) {
                  sess.messages[sess.messages.length - 1].content += "\n\n❌ **Error**: " + parsed.error;
                  renderMessages();
                }
              } catch (e) {}
            }
          });
          read();
        });
      }
      read();
    }).catch(err => {
      sess.messages[sess.messages.length - 1].content = "❌ **Connection Error**: " + err.message;
      renderMessages();
    });
  }

  // Event Listeners
  btnSendEl.addEventListener("click", sendMessage);
  promptInputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnNewChatEl.addEventListener("click", () => {
    sessions.unshift({ id: Date.now().toString(), title: "New Conversation", messages: [] });
    activeSessionIdx = 0;
    saveStorage();
    renderSidebar();
    renderMessages();
  });

  quickModelSelectEl.addEventListener("change", (e) => {
    config.ollama_model = e.target.value;
    saveStorage();
  });

  // Settings Modal Handlers
  btnOpenSettingsEl.addEventListener("click", () => {
    settingProviderEl.value = config.provider;
    settingOllamaUrlEl.value = config.ollama_url;
    settingOpenaiUrlEl.value = config.openai_url;
    settingOpenaiKeyEl.value = config.openai_key;
    settingTempEl.value = config.temperature;
    valTempEl.textContent = config.temperature;
    settingNumCtxEl.value = config.num_ctx;
    settingRepeatEl.value = config.repeat_penalty;
    valRepeatEl.textContent = config.repeat_penalty;
    settingSystemPromptEl.value = config.system_prompt;
    modalEl.classList.remove("hidden");
  });

  btnCloseModalEl.addEventListener("click", () => modalEl.classList.add("hidden"));
  settingTempEl.addEventListener("input", (e) => valTempEl.textContent = e.target.value);
  settingRepeatEl.addEventListener("input", (e) => valRepeatEl.textContent = e.target.value);

  btnSaveSettingsEl.addEventListener("click", () => {
    config.provider = settingProviderEl.value;
    config.ollama_url = settingOllamaUrlEl.value.trim();
    config.openai_url = settingOpenaiUrlEl.value.trim();
    config.openai_key = settingOpenaiKeyEl.value.trim();
    config.temperature = parseFloat(settingTempEl.value);
    config.num_ctx = parseInt(settingNumCtxEl.value);
    config.repeat_penalty = parseFloat(settingRepeatEl.value);
    config.system_prompt = settingSystemPromptEl.value.trim();
    saveStorage();
    modalEl.classList.add("hidden");
    fetchModels();
  });

  // Init
  renderSidebar();
  renderMessages();
  fetchModels();
});
