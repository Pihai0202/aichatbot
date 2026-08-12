# ⚡ AI Chatbot - 超輕量級 AI 聊天用戶端 (TUI, Desktop GUI & Web Remote)

> 一款**極致低系統資源佔用、瞬間啟動、反應極速**的 AI 聊天介面工具套件。
> 提供 **Go 終端機版 (TUI)**、**PySide6 原生桌面圖形版 (GUI)** 以及 **Web 遠端連線版 (Web UI)** 三重介面！

---

## 🌟 全新升級功能 (New Features)

1. **🎨 視覺美學與字體全面優化**：
   - **思源黑體 (Source Han Sans TC / Noto Sans TC)**：介面與對話文字全局套用思源黑體，預設字體放大至標準舒適的 14~16px。
   - **全向量 SVG Icon**：視窗圖示全面替換為高品質向量 SVG Icon (傳送、設定、刷新、新對話)。
2. **📝 Markdown 高級渲染與語法高亮**：
   - AI 回答自動進行完整 Markdown 渲染（標題 `#`, 粗體 `**`, 列表, 表格, 程式碼塊 ```` ```python ```` 語法高亮）。
3. **🎛️ AI 參數微調 (Fine-Tuning Controls)**：
   - 支援微調 **溫度 (Temperature: 0.0 ~ 2.0)**、**上下文長度 (Num Ctx: 2048 ~ 32768 Tokens)** 與 **重複懲罰 (Repeat Penalty: 0.5 ~ 2.0)**。
4. **⚡ 頂部列快捷模型切換器**：
   - 主介面頂部提供模型下拉選單，無需進入設定選單即可一鍵切換本地 Ollama 模型。
5. **🌐 Web 遠端連線服務 (手機/平板/跨裝置)**：
   - 內建一鍵 Web API 伺服器，自動抓取區域網路 IP 地址，支援同 Wi-Fi 網域下的手機與平板輕鬆存取與對話！

---

## 📊 三大介面對比 (TUI vs Desktop GUI vs Web Remote)

| 特性 / 介面 | ⚡ TUI 終端機介面 | 🖥️ Desktop GUI 桌面介面 | 🌐 Web 遠端網頁介面 |
| :--- | :--- | :--- | :--- |
| **主要技術** | Go 1.24 + Bubbletea | PySide6 (Qt6) + SVG + Markdown | Python Server + HTML5/CSS3/JS |
| **記憶體佔用 (RAM)** | **~10 - 15 MB** | **~30 - 50 MB** | **~20 MB** (伺服器端) |
| **字體與美學** | 霓虹 Terminal 色彩 | **思源黑體 + SVG Icon** | 思源黑體 + Glassmorphism |
| **Markdown 渲染** | Lipgloss 高亮 | 完整 HTML Markdown 渲染 | Marked.js + Highlight.js |
| **跨裝置連線** | ❌ (本地終端機) | ❌ (本地視窗) | **✅ 支援手機/平板/其他電腦** |
| **一鍵啟動腳本** | `run_tui.bat` | `run_gui.bat` | `run_web.bat` |

---

## 🚀 快速開始 (Quick Start)

### 1. 使用一鍵批次檔啟動 (Windows)
- **桌面版 (GUI)**：雙擊開啟 [`run_gui.bat`](file:///c:/AI/run_gui.bat)
- **Web 遠端連線版 (Web UI)**：雙擊開啟 [`run_web.bat`](file:///c:/AI/run_web.bat) (自動開啟 `http://localhost:8000`)
- **終端機版 (TUI)**：雙擊開啟 [`run_tui.bat`](file:///c:/AI/run_tui.bat)

### 2. 使用命令列啟動

```powershell
# 啟動 Desktop GUI 桌面版
python c:\AI\gui\app.py

# 啟動 Web 遠端伺服器 (提供手機/平板連線)
python c:\AI\web\server.py

# 啟動 TUI 終端機版
c:\AI\tui\aichat-tui.exe
```

---

## 📱 手機與平板遠端連線教學

1. 雙擊執行 `run_web.bat` 啟動 Web 伺服器。
2. 命令列視窗會顯示您的區域網路 IP，例如：
   ```
   ============================================================
    [Web Server] AI Chatbot Web Remote Server Started!
    Local Access:    http://localhost:8000
    Remote Wi-Fi IP: http://192.168.1.100:8000
   ============================================================
   ```
3. 讓您的手機或平板連接同一個 Wi-Fi，打開手機瀏覽器輸入 `http://192.168.1.100:8000` 即可在手機上使用您電腦上的本地 Ollama 模型對話！

---

## 🎛️ AI 參數微調說明 (Fine-Tuning)

點擊 **`⚙️ 設定與參數微調`** 面板：
- **溫度 (Temperature)**：`0.0 ~ 2.0`（預設 0.7）。數值越低輸出越確定，越高越有創意。
- **上下文長度 (Num Ctx)**：`2048 ~ 32768 Tokens`（預設 4096）。控制 AI 能記住的歷史對話長度。
- **重複懲罰 (Repeat Penalty)**：`0.5 ~ 2.0`（預設 1.1）。防止 AI 生成重複循環的語句。

---

## 📂 專案目錄結構 (Project Structure)

```
c:\AI\
├── gui/                    # PySide6 桌面 GUI 專案
│   └── app.py              # 思源黑體、SVG Icon、Markdown 渲染桌面介面
├── web/                    # Web 遠端 API 伺服器與網頁端
│   ├── server.py           # 輕量 Web 伺服器 (支援跨裝置 IP 存取)
│   └── static/             # SPA 單頁網頁 (index.html, style.css, app.js)
├── tui/                    # Go Bubbletea TUI 專案
│   ├── main.go / client.go # TUI 核心邏輯與流式 API 引擎
│   └── aichat-tui.exe      # 獨立編譯之 10.3MB 執行檔
├── run_gui.bat             # 一鍵啟動桌面 GUI 版
├── run_web.bat             # 一鍵啟動 Web 遠端網頁版
├── run_tui.bat             # 一鍵啟動 TUI 終端機版
└── README.md               # 專案詳細手冊
```

---

## 📄 授權條款 (License)

MIT License © 2026 [Pihai0202](https://github.com/Pihai0202)
