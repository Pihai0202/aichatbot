# ZeroAI Desk - 極輕量多模型 AI 桌面 (Qt 6 & Web GUI) 與 TUI 雙介面工作站

**ZeroAI Desk** 是一款專為追求高效率與極低系統資源佔用 (&lt; 30MB RAM) 設計的跨平台 AI 桌面視窗 (Qt 6 原生 / Web GUI) 與終端機應用程式。

---

## 🌟 核心特色 (Core Features)

1. **原生 Qt 6 輕量桌面 GUI (PySide6 Qt 6 Native App)**
   - 採用 **C++ Qt 6** 原生 Widget 視窗技術 (`ZeroAI-Desk-Qt.bat` 或 `python qt_app.py`)。
   - 記憶體佔用極低 (**僅 ~28 MB RAM**)，開啟瞬間載入無延遲。

2. **多模型動態切換與 AI 參數微調 (Multi-Model & Parameter Tuning)**
   - 支援隨時無縫切換 **Local Ollama** (Llama 3.2, Qwen 2.5, DeepSeek R1) 與 **遠端 API** (OpenAI, Anthropic Claude, DeepSeek)。
   - 具備滑動式的 **AI 參數微調面板 (Tuning Drawer)**：
     - **溫度 (Temperature)**：0.0 ~ 2.0 (內建「精確 0.2」、「平衡 0.7」、「創意 1.2」快速按鈕)
     - **系統提示詞 (System Prompt)** 編輯器

3. **即時 Markdown 串流渲染 (Real-Time Markdown)**
   - 整合 `markdown` + `pygments` 程式碼高亮與 HTML 樣式渲染。
   - 採用 Qt `QThread` 異步線程處理 SSE 串流，保證 UI 視窗永遠流暢不卡頓。

4. **雙模式支援 (本地 Ollama 自動偵測與遠端 API)**
   - **Ollama 自動探測器**：啟動時探測 `http://127.0.0.1:11434`。
   - **未安裝指引 Modal**：未偵測到 Ollama 時彈出 Qt 對話框提醒 `winget install Ollama.Ollama`。

---

## 🚀 啟動方式 (Quick Start)

### 1. 啟動原生 Qt 6 桌面 GUI (Qt 6 Native App - 推薦極低資源)
雙擊執行資料夾中的 **`ZeroAI-Desk-Qt.bat`** 或是於終端機執行：
```bash
python qt_app.py
# 或
npm run qt
```

### 2. 啟動 Web 視窗桌面 GUI (Electron App)
雙擊執行資料夾中的 **`ZeroAI-Desk-GUI.bat`** 或是執行：
```bash
npm run gui
```

### 3. 啟動極輕量終端機介面 (TUI Terminal Mode)
```bash
npm run tui
```
