import readline from 'readline';

// Extremely low memory Terminal UI (TUI) for ZeroAI Desk
class ZeroAITUI {
  constructor() {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    this.state = {
      provider: 'ollama',
      model: 'llama3.2',
      baseUrl: 'http://127.0.0.1:11434',
      temperature: 0.7,
      systemPrompt: 'You are a helpful AI assistant.',
      messages: []
    };

    this.isOllamaOnline = false;
  }

  async start() {
    console.clear();
    console.log(`\x1b[36m%s\x1b[0m`, `========================================================`);
    console.log(`\x1b[1m\x1b[35m%s\x1b[0m`, `  ZeroAI Desk - 終端機介面 (TUI Mode) [極低資源模式]`);
    console.log(`\x1b[36m%s\x1b[0m`, `========================================================`);
    console.log(`指令指南:`);
    console.log(`  \x1b[33m/model <name>\x1b[0m  - 切換 AI 模型 (例: /model llama3.2)`);
    console.log(`  \x1b[33m/temp <value>\x1b[0m  - 調整溫度 (例: /temp 0.2)`);
    console.log(`  \x1b[33m/ollama\x1b[0m        - 檢查本地 Ollama 狀態與已安裝模型`);
    console.log(`  \x1b[33m/clear\x1b[0m         - 清除當前對話紀錄`);
    console.log(`  \x1b[33m/exit\x1b[0m          - 離開 TUI\n`);

    await this.checkOllama();
    this.promptUser();
  }

  async checkOllama() {
    try {
      const res = await fetch(`${this.state.baseUrl}/api/tags`, {
        signal: AbortSignal.timeout(2000)
      });
      if (res.ok) {
        const data = await res.json();
        this.isOllamaOnline = true;
        console.log(`\x1b[32m✔ 本地 Ollama 已連線！可用模型: ${data.models.map(m => m.name).join(', ')}\x1b[0m\n`);
        if (data.models.length > 0) {
          this.state.model = data.models[0].name;
        }
        return;
      }
    } catch (e) {}

    this.isOllamaOnline = false;
    console.log(`\x1b[31m✖ 未偵測到本地 Ollama 服務。預設使用遠端 API 模式。\x1b[0m`);
    console.log(`  若欲安裝 Ollama，請執行: \x1b[36mwinget install Ollama.Ollama\x1b[0m\n`);
  }

  promptUser() {
    const statusLine = `[${this.state.provider.toUpperCase()} | ${this.state.model} | Temp:${this.state.temperature}]`;
    this.rl.question(`\x1b[34m${statusLine} 你: \x1b[0m`, async (input) => {
      const text = input.trim();
      if (!text) {
        return this.promptUser();
      }

      if (text.startsWith('/')) {
        await this.handleCommand(text);
        return this.promptUser();
      }

      this.state.messages.push({ role: 'user', content: text });
      process.stdout.write(`\x1b[35mAI 助理: \x1b[0m`);

      await this.streamChatResponse();
      console.log('\n');
      this.promptUser();
    });
  }

  async handleCommand(cmdStr) {
    const parts = cmdStr.split(' ');
    const cmd = parts[0].toLowerCase();
    const arg = parts.slice(1).join(' ');

    if (cmd === '/exit') {
      console.log('再見！');
      process.exit(0);
    } else if (cmd === '/clear') {
      this.state.messages = [];
      console.log('\x1b[33m已清除對話歷史紀錄。\x1b[0m');
    } else if (cmd === '/temp') {
      const val = parseFloat(arg);
      if (!isNaN(val)) {
        this.state.temperature = val;
        console.log(`\x1b[32m溫度已設定為: ${val}\x1b[0m`);
      }
    } else if (cmd === '/model') {
      if (arg) {
        this.state.model = arg;
        console.log(`\x1b[32m模型已切換為: ${arg}\x1b[0m`);
      }
    } else if (cmd === '/ollama') {
      await this.checkOllama();
    } else {
      console.log(`\x1b[31m未知指令: ${cmd}\x1b[0m`);
    }
  }

  async streamChatResponse() {
    try {
      const formattedMessages = [
        { role: 'system', content: this.state.systemPrompt },
        ...this.state.messages
      ];

      const response = await fetch(`${this.state.baseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.state.model,
          messages: formattedMessages,
          stream: true,
          options: { temperature: this.state.temperature }
        })
      });

      if (!response.ok) {
        process.stdout.write(`\x1b[31m[API 錯誤 ${response.status}]\x1b[0m`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const lines = decoder.decode(value, { stream: true }).split('\n');
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const json = JSON.parse(line);
            if (json.message?.content) {
              const chunk = json.message.content;
              fullText += chunk;
              process.stdout.write(chunk);
            }
          } catch (e) {}
        }
      }

      this.state.messages.push({ role: 'assistant', content: fullText });
    } catch (err) {
      process.stdout.write(`\x1b[31m[連線錯誤: ${err.message}]\x1b[0m`);
    }
  }
}

const tui = new ZeroAITUI();
tui.start();
