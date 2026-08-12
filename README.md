# ⚡ AI Chatbot - 超輕量級 AI 聊天用戶端 (TUI & Desktop GUI)

> 一款**極致低系統資源佔用、瞬間啟動、反應極速**的 AI 聊天介面工具組。
> 提供 **Go 終端機版 (TUI)** 與 **PySide6 原生桌面圖形版 (GUI)** 雙介面，支援 **Ollama 本地 AI 模型** 與 **雲端 OpenAI 相容 API**。

---

## 🌟 核心特點 (Key Features)

- **⚡ 極致輕量與低資源佔用**：
  - **TUI (Go + Bubbletea)**：記憶體佔用僅 **~10 - 15 MB RAM**，編譯為單一 10MB 獨立執行檔，無外部依賴。
  - **Desktop GUI (PySide6)**：記憶體佔用僅 **~30 - 50 MB RAM**，遠低於傳統 Electron / Webview 應用 (300MB+)。
- **🤖 雙核心 API 相容 (Local & Cloud)**：
  - **本地 AI (Local AI)**：原生支援 [Ollama](https://ollama.com/) (`http://localhost:11434`)、LM Studio (`http://localhost:1234`)，保護個人數據隱私，完全免費。
  - **雲端 AI (Cloud APIs)**：支援 OpenAI、OpenRouter、DeepSeek、Groq、Gemini 等任何 OpenAI-compatible REST API。
- **💬 打字機流式傳輸 (Real-time Streaming)**：
  - 支援 SSE / HTTP Chunk 流式輸出，邊生成邊即時顯示打字效果，反應零延遲。
- **📁 對話歷史與持久化 (Session Management)**：
  - 自動建立多對話分頁、歷史紀錄存取與自動儲存，離線也可瀏覽對話。

---

## 📊 雙版本介面對比 (TUI vs Desktop GUI)

| 特性 / 介面 | ⚡ TUI 終端機介面 | 🖥️ Desktop GUI 桌面介面 |
| :--- | :--- | :--- |
| **主要技術** | Go 1.24 + Bubbletea + Lipgloss | Python 3.14 + PySide6 (Qt6) |
| **記憶體佔用 (RAM)** | **~10 - 15 MB** | **~30 - 50 MB** |
| **啟動速度** | 毫秒級 (Instant) | 瞬間點開即用 |
| **操作方式** | 全鍵盤快捷鍵極速流動 | 滑鼠點擊 + 鍵盤操作 |
| **適用場景** | 開發者、Hacker 風格、SSH / 低配機器 | 一般日常使用、習慣視窗桌面操作者 |
| **一鍵啟動腳本** | `run_tui.bat` | `run_gui.bat` |

---

## 🚀 快速開始 (Quick Start)

### 1. 使用一鍵批次檔啟動 (Windows)
雙擊專案目錄下的 `.bat` 檔即可直接運行：
- **桌面版 (GUI)**：雙擊開啟 [`run_gui.bat`](file:///c:/AI/run_gui.bat)
- **終端機版 (TUI)**：雙擊開啟 [`run_tui.bat`](file:///c:/AI/run_tui.bat)

### 2. 使用命令列啟動

```powershell
# 啟動 Desktop GUI 桌面版
python c:\AI\gui\app.py

# 啟動 TUI 終端機版
c:\AI\tui\aichat-tui.exe
```

---

## 📖 詳細使用指南 (Usage Guide)

### 🖥️ 一、 Desktop GUI 桌面圖形版使用手冊

#### 1. 對話操作
- **發送訊息**：在下方文字框輸入您的問題後，點擊 **`Send 🚀`** 按鈕或按下 `Ctrl + Enter` 發送。
- **建立新對話**：點擊左上角的 **`+ New Session`** 按鈕即可開啟空白對話。
- **切換歷史對話**：點擊左側對話列表中的任何歷史項目，即可隨時查看與續寫過去的對話。

#### 2. API 設定與模型切換 (Settings)
點擊左下角 **`⚙️ Settings & Models`** 進入設定面板：
- **使用本地 AI (Ollama)**：
  1. **Provider** 選擇 `Ollama (Local)`。
  2. **Ollama URL** 保持預設 `http://localhost:11434`。
  3. **Ollama Model** 輸入您本地已下載的模型名稱（例如 `llama3:latest` 或 `qwen2:latest`）。
- **使用雲端 API (OpenAI / OpenRouter / DeepSeek)**：
  1. **Provider** 選擇 `OpenAI / Custom API`。
  2. **OpenAI Base URL** 輸入 API 端點（例如 OpenRouter 輸入 `https://openrouter.ai/api/v1`）。
  3. **OpenAI API Key** 填入您的授權密鑰。
  4. **OpenAI Model** 輸入模型代號（如 `gpt-4o-mini` 或 `deepseek-chat`）。
  5. **System Prompt** 設定系統人設（如：*「你是一個專業的程式設計助手」*）。

---

### ⚡ 二、 TUI 終端機版使用手冊

TUI 版本完全針對鍵盤流設計，操作說明如下：

#### 1. 鍵盤快捷鍵 (Keybindings)

| 快捷鍵 | 功能說明 |
| :--- | :--- |
| **`Tab`** | 在 **對話歷史選單 (Sessions)** ↔ **對話內容 (Viewport)** ↔ **文字輸入框 (Input)** 之間切換焦點 |
| **`Ctrl + N`** | 快速建立新的對話 Session |
| **`Ctrl + S`** | 開啟 **Settings & Model Selector** 選單彈窗 |
| **`Enter`** | (焦點在輸入框時) 發送對話訊息 |
| **`Shift + Enter`** | (焦點在輸入框時) 文字換行 |
| **`Up / Down`** | (焦點在側邊欄時) 切換歷史對話項目 |
| **`Ctrl + Q` / `Ctrl + C`** | 離開程式 |

#### 2. 設定選單 (Ctrl + S)
在 TUI 介面中按下 `Ctrl + S` 會跳出設定彈窗：
- 按 **`1`** 鍵：切換為 **Ollama 本地 API** 模式。
- 按 **`2`** 鍵：切換為 **OpenAI 雲端 API** 模式。
- 按 **`Up / Down (方向鍵)`**：滾動選擇自動偵測到的 Ollama 本地模型清單。
- 按 **`Esc`**：關閉彈窗並返回對話。

---

## 🦙 本地模型 (Ollama) 配置教學

若您希望在無網路環境下完全免費使用 AI，推薦使用 **Ollama**：

1. **安裝 Ollama**：至 [Ollama 官網](https://ollama.com/) 下載並安裝。
2. **下載 AI 模型**：打開您的 PowerShell / Terminal，執行：
   ```bash
   # 下載 Meta 輕量模型
   ollama run llama3

   # 或下載 阿里 Qwen2 中文模型
   ollama run qwen2
   ```
3. **開始使用**：啟動本軟體即可自動連接連線對話！

---

## 📂 專案目錄結構 (Project Structure)

```
c:\AI\
├── tui/                    # Go Bubbletea TUI 專案
│   ├── main.go             # TUI 介面佈局與鍵盤事件處理
│   ├── client.go           # HTTP SSE 流式 API 引擎 (Ollama & OpenAI)
│   ├── store.go            # 本地 JSON 配置檔與對話歷史持久化
│   ├── types.go            # 核心資料結構型別
│   ├── go.mod              # Go 模組設定
│   └── aichat-tui.exe      # 編譯完成之超輕量獨立執行檔 (10.3MB)
├── gui/                    # PySide6 桌面 GUI 專案
│   └── app.py              # Qt6 桌面介面主程式與多執行緒流式引擎
├── run_tui.bat             # 一鍵啟動 TUI 終端機版
├── run_gui.bat             # 一鍵啟動 Desktop GUI 桌面版
├── .gitignore              # Git 忽略檔案設定
└── README.md               # 專案詳細使用手冊
```

---

## 🛠️ 開發與編譯 (Build Guide)

### 重新編譯 TUI 執行檔 (Go)
```powershell
cd c:\AI\tui
C:\go\bin\go.exe build -o aichat-tui.exe .
```

### 執行 GUI 桌面版 (Python)
```powershell
python -m pip install PySide6 requests
python c:\AI\gui\app.py
```

---

## 📄 授權條款 (License)

MIT License © 2026 [Pihai0202](https://github.com/Pihai0202)
