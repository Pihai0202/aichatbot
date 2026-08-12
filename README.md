# ⚡ Low-Resource AI Chat Suite (TUI & Desktop GUI)

這是一套**低系統資源佔用、反應極速**的 AI 聊天介面工具，包含 **TUI (終端機版)** 與 **Desktop GUI (桌面版)** 雙版本。

支援**本地模型 (Ollama / LM Studio)** 以及 **雲端 API (OpenAI / OpenRouter / DeepSeek / Gemini / 自訂 API Base URL)**。

---

## 🌟 核心功能與優勢

| 功能 / 介面 | TUI 終端機介面 (Go + Bubbletea) | Desktop GUI 桌面介面 (PySide6) |
| :--- | :--- | :--- |
| **記憶體佔用 (RAM)** | **~10 - 15 MB** | **~30 - 50 MB** (遠低於 Electron 的 300MB+) |
| **啟動速度** | 毫秒級瞬間啟動 | 瞬間點開即用 |
| **本地 AI (Ollama)** | 自動連線 `http://localhost:11434` | 支援 `http://localhost:11434` 自動通訊 |
| **雲端 / Custom API** | 支援 OpenAI 相容 API & Key | 支援 OpenAI 相容 API & Key |
| **打字機流式傳輸** | 實時 SSE / Chunk Streaming | 實時 QThread SSE Streaming |
| **對話紀錄持久化** | 自動存至 JSON 檔 | 自動存至 JSON 檔 |

---

## 🚀 快速啟動方式 (Quick Start)

### 1. 一鍵腳本 (Windows Batch)
- 雙擊執行 `c:\AI\run_tui.bat` 啟動 **TUI 終端機版**。
- 雙擊執行 `c:\AI\run_gui.bat` 啟動 **Desktop GUI 桌面版**。

### 2. 命令列手動啟動
```powershell
# 啟動 TUI 終端機版
c:\AI\tui\aichat-tui.exe

# 啟動 Desktop GUI 桌面版
python c:\AI\gui\app.py
```

---

## ⌨️ TUI 快捷鍵說明
- `Tab`: 切換 Focus 焦點 (側邊欄 <-> 對話視窗 <-> 輸入框)
- `Ctrl+N`: 建立新對話 Session
- `Ctrl+S`: 開啟 Settings 與 Local Ollama 模型選擇選單
- `Up / Down` (側邊欄聚焦時): 切換歷史對話紀錄
- `Enter`: 傳送訊息
- `Ctrl+Q` / `Ctrl+C`: 離開程式

---

## 📂 檔案結構說明
```
c:\AI\
├── tui\
│   ├── main.go             # Bubbletea TUI 畫面與鍵盤互動邏輯
│   ├── client.go           # SSE 流式 HTTP API 請求 (Ollama & OpenAI)
│   ├── store.go            # 配置檔與 Session 持久化
│   ├── types.go            # 核心資料結構
│   └── aichat-tui.exe      # 超輕量 10MB 獨立執行檔
├── gui\
│   └── app.py              # PySide6 Qt 原生美觀桌面圖形介面
├── run_tui.bat             # 一鍵啟動 TUI 批次檔
├── run_gui.bat             # 一鍵啟動 GUI 批次檔
└── README.md               # 說明文件
```
