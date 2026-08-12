import sys
import json
import os
import requests
import markdown
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QComboBox, QSlider, QDialog, QFormLayout, QSplitter,
    QDoubleSpinBox, QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

CONFIG_DIR = Path.home() / ".config" / "aichat-gui"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_FILE = CONFIG_DIR / "sessions.json"

DEFAULT_CONFIG = {
    "provider": "ollama",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3:latest",
    "openai_url": "https://api.openai.com/v1",
    "openai_key": "",
    "openai_model": "gpt-4o-mini",
    "system_prompt": "You are a helpful, concise AI assistant.",
    "temperature": 0.7,
    "num_ctx": 4096,
    "repeat_penalty": 1.1
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def load_sessions():
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [{"id": "1", "title": "New Chat", "messages": []}]

def save_sessions(sessions):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

def fetch_ollama_models(base_url):
    try:
        url = base_url.rstrip("/") + "/api/tags"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []

# SVG Icon Helper
SVG_ICONS = {
    "send": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>',
    "plus": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#D8DEE9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>',
    "refresh": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>'
}

def svg_to_icon(svg_str, size=24):
    renderer = QSvgRenderer(svg_str.encode("utf-8"))
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(image))

# Stream Worker
class StreamWorker(QThread):
    token_received = Signal(str)
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, cfg, messages):
        super().__init__()
        self.cfg = cfg
        self.messages = messages

    def run(self):
        try:
            provider = self.cfg.get("provider", "ollama")
            system_prompt = self.cfg.get("system_prompt", "")
            temp = float(self.cfg.get("temperature", 0.7))
            num_ctx = int(self.cfg.get("num_ctx", 4096))
            repeat_penalty = float(self.cfg.get("repeat_penalty", 1.1))

            req_messages = []
            if system_prompt:
                req_messages.append({"role": "system", "content": system_prompt})
            req_messages.extend(self.messages)

            if provider == "ollama":
                url = self.cfg.get("ollama_url", "http://localhost:11434").rstrip("/") + "/api/chat"
                model_name = self.cfg.get("ollama_model", "llama3:latest")
                payload = {
                    "model": model_name,
                    "messages": req_messages,
                    "options": {
                        "temperature": temp,
                        "num_ctx": num_ctx,
                        "repeat_penalty": repeat_penalty
                    },
                    "stream": True
                }
                resp = requests.post(url, json=payload, stream=True, timeout=60)
                if resp.status_code == 404:
                    self.error_signal.emit(
                        f"Ollama 未找到模型 '{model_name}' (404 Error)。\n\n"
                        f"💡 請在命令列執行：ollama pull {model_name.split(':')[0]}\n"
                        f"或於上方下拉選單切換其他已下載的模型。"
                    )
                    return
                elif resp.status_code != 200:
                    self.error_signal.emit(f"Ollama API Error ({resp.status_code}): {resp.text}")
                    return

                for line in resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            msg = chunk.get("message", {}).get("content", "")
                            if msg:
                                self.token_received.emit(msg)
                        except Exception:
                            pass
            else:
                url = self.cfg.get("openai_url", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
                headers = {"Content-Type": "application/json"}
                api_key = self.cfg.get("openai_key", "")
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                payload = {
                    "model": self.cfg.get("openai_model", "gpt-4o-mini"),
                    "messages": req_messages,
                    "temperature": temp,
                    "stream": True
                }
                resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
                if resp.status_code == 401:
                    self.error_signal.emit("未提供有效的 API Key (401 Unauthorized)。請在 ⚙️ Settings 填入 Key。")
                    return
                elif resp.status_code == 429:
                    self.error_signal.emit("OpenAI 帳戶額度已用盡 (429 Insufficient Quota)。請更換模式或儲值。")
                    return
                elif resp.status_code != 200:
                    self.error_signal.emit(f"API Error ({resp.status_code}): {resp.text}")
                    return

                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            data = line_str[6:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    self.token_received.emit(delta)
                            except Exception:
                                pass

            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(f"連線失敗: {str(e)}")

# Settings Dialog with Fine-tuning Controls
class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg.copy()
        self.setWindowTitle("⚙️ API 設定與 AI 參數微調 (Settings & Fine-tuning)")
        self.resize(560, 560)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Ollama (Local AI)", "OpenAI / Custom Cloud API"])
        if self.cfg["provider"] == "openai":
            self.provider_combo.setCurrentIndex(1)
        form.addRow("<b>AI Provider:</b>", self.provider_combo)

        # Ollama Fields
        self.ollama_url_input = QLineEdit(self.cfg["ollama_url"])
        form.addRow("Ollama URL:", self.ollama_url_input)

        # OpenAI Fields
        self.openai_url_input = QLineEdit(self.cfg["openai_url"])
        form.addRow("OpenAI Base URL:", self.openai_url_input)

        self.openai_key_input = QLineEdit(self.cfg["openai_key"])
        self.openai_key_input.setEchoMode(QLineEdit.Password)
        self.openai_key_input.setPlaceholderText("sk-proj-...")
        form.addRow("OpenAI API Key:", self.openai_key_input)

        self.openai_model_input = QLineEdit(self.cfg["openai_model"])
        form.addRow("OpenAI Model Name:", self.openai_model_input)

        layout.addLayout(form)

        # Divider & Fine Tuning Parameters
        lbl_tuning = QLabel("<b>🎛️ AI 產生參數微調 (Fine-Tuning Parameters)</b>")
        lbl_tuning.setStyleSheet("color: #00F0FF; font-size: 15px; margin-top: 10px;")
        layout.addWidget(lbl_tuning)

        form_tuning = QFormLayout()

        # Temperature
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 2.0)
        self.spin_temp.setSingleStep(0.1)
        self.spin_temp.setValue(float(self.cfg.get("temperature", 0.7)))
        form_tuning.addRow("溫度 (Temperature [0.0 - 2.0]):", self.spin_temp)

        # Num Ctx
        self.combo_num_ctx = QComboBox()
        self.combo_num_ctx.addItems(["2048", "4096", "8192", "16384", "32768"])
        self.combo_num_ctx.setCurrentText(str(self.cfg.get("num_ctx", 4096)))
        form_tuning.addRow("上下文長度 (Num Ctx):", self.combo_num_ctx)

        # Repeat Penalty
        self.spin_repeat = QDoubleSpinBox()
        self.spin_repeat.setRange(0.5, 2.0)
        self.spin_repeat.setSingleStep(0.1)
        self.spin_repeat.setValue(float(self.cfg.get("repeat_penalty", 1.1)))
        form_tuning.addRow("重複懲罰 (Repeat Penalty [0.5 - 2.0]):", self.spin_repeat)

        # System Prompt
        self.sys_prompt_input = QTextEdit()
        self.sys_prompt_input.setPlainText(self.cfg["system_prompt"])
        self.sys_prompt_input.setMaximumHeight(80)
        form_tuning.addRow("System Prompt (人設):", self.sys_prompt_input)

        layout.addLayout(form_tuning)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 儲存並套用")
        btn_save.setStyleSheet("background-color: #8B5CF6; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px;")
        btn_save.clicked.connect(self.save_and_close)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def save_and_close(self):
        self.cfg["provider"] = "openai" if self.provider_combo.currentIndex() == 1 else "ollama"
        self.cfg["ollama_url"] = self.ollama_url_input.text().strip()
        self.cfg["openai_url"] = self.openai_url_input.text().strip()
        self.cfg["openai_key"] = self.openai_key_input.text().strip()
        self.cfg["openai_model"] = self.openai_model_input.text().strip()
        self.cfg["temperature"] = self.spin_temp.value()
        self.cfg["num_ctx"] = int(self.combo_num_ctx.currentText())
        self.cfg["repeat_penalty"] = self.spin_repeat.value()
        self.cfg["system_prompt"] = self.sys_prompt_input.toPlainText().strip()
        save_config(self.cfg)
        self.accept()

# Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ AI Chatbot Desktop (思源黑體 & SVG Icon 優化版)")
        self.resize(1060, 740)

        self.cfg = load_config()
        self.sessions = load_sessions()
        self.current_session_idx = 0
        self.worker = None

        self.init_ui()
        self.apply_theme_and_font()
        self.load_current_session()
        self.refresh_quick_models()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # Sidebar
        sidebar = QWidget()
        sidebar.setMinimumWidth(240)
        sidebar.setMaximumWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)

        btn_new_chat = QPushButton(" 新對話")
        btn_new_chat.setIcon(svg_to_icon(SVG_ICONS["plus"], 18))
        btn_new_chat.setStyleSheet("background: linear-gradient(135deg, #00F0FF, #00B8D9); color: #000; font-weight: bold; padding: 10px; border-radius: 8px; font-size: 15px;")
        btn_new_chat.clicked.connect(self.create_new_session)
        sidebar_layout.addWidget(btn_new_chat)

        sidebar_layout.addWidget(QLabel("<b>對話歷史紀錄 (SESSIONS)</b>"))

        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self.on_session_clicked)
        sidebar_layout.addWidget(self.session_list)

        btn_settings = QPushButton(" 設定與參數微調")
        btn_settings.setIcon(svg_to_icon(SVG_ICONS["settings"], 18))
        btn_settings.setStyleSheet("background-color: #26293B; color: #E2E8F0; padding: 8px; border-radius: 6px; font-size: 14px;")
        btn_settings.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(btn_settings)

        splitter.addWidget(sidebar)

        # Workspace
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(16, 12, 16, 12)

        # Top Header Model Switcher Bar
        top_bar = QHBoxLayout()
        lbl_model = QLabel("<b>模型選擇 (Model):</b>")
        lbl_model.setStyleSheet("font-size: 15px; color: #00F0FF;")
        top_bar.addWidget(lbl_model)

        self.combo_top_models = QComboBox()
        self.combo_top_models.setMinimumWidth(220)
        self.combo_top_models.currentIndexChanged.connect(self.on_top_model_changed)
        top_bar.addWidget(self.combo_top_models)

        btn_refresh_top = QPushButton()
        btn_refresh_top.setIcon(svg_to_icon(SVG_ICONS["refresh"], 18))
        btn_refresh_top.setToolTip("重新整理本地模型")
        btn_refresh_top.clicked.connect(self.refresh_quick_models)
        top_bar.addWidget(btn_refresh_top)

        top_bar.addStretch()

        self.header_status = QLabel("Ollama API Mode")
        self.header_status.setStyleSheet("color: #94A3B8; font-size: 14px;")
        top_bar.addWidget(self.header_status)

        chat_layout.addLayout(top_bar)

        # Chat Display using QTextBrowser for rich Markdown HTML
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        chat_layout.addWidget(self.chat_display)

        # Input box row
        input_box = QHBoxLayout()
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("輸入訊息... (點擊發送或按 Send 按鈕)")
        self.prompt_input.setMaximumHeight(85)
        input_box.addWidget(self.prompt_input)

        btn_send = QPushButton(" 發送")
        btn_send.setIcon(svg_to_icon(SVG_ICONS["send"], 20))
        btn_send.setStyleSheet("background: linear-gradient(135deg, #8B5CF6, #6D28D9); color: white; font-weight: bold; min-width: 95px; min-height: 55px; border-radius: 8px; font-size: 15px;")
        btn_send.clicked.connect(self.send_message)
        input_box.addWidget(btn_send)

        chat_layout.addLayout(input_box)

        splitter.addWidget(chat_area)
        splitter.setSizes([260, 800])
        main_layout.addWidget(splitter)

    def apply_theme_and_font(self):
        # Set Source Han Sans / Noto Sans TC font
        font = QFont()
        font.setFamilies(["Source Han Sans TC", "Noto Sans TC", "Microsoft JhengHei", "sans-serif"])
        font.setPointSize(11) # Standard comfortable 14-16px equivalent
        QApplication.setFont(font)

        qss = """
        QMainWindow, QWidget {
            background-color: #12131C;
            color: #E2E8F0;
            font-family: 'Source Han Sans TC', 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
            font-size: 15px;
        }
        QListWidget {
            background-color: #1A1C29;
            border: 1px solid #2E334D;
            border-radius: 8px;
        }
        QListWidget::item {
            padding: 10px;
            color: #94A3B8;
            font-size: 14px;
        }
        QListWidget::item:selected {
            background-color: #222538;
            color: #00F0FF;
            font-weight: bold;
        }
        QTextBrowser {
            background-color: #1A1C29;
            border: 1px solid #2E334D;
            border-radius: 8px;
            color: #E2E8F0;
            padding: 12px;
            font-size: 15px;
        }
        QTextEdit {
            background-color: #181926;
            border: 1px solid #2E334D;
            border-radius: 8px;
            color: #E2E8F0;
            font-size: 15px;
            padding: 8px;
        }
        QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
            background-color: #181926;
            border: 1px solid #2E334D;
            padding: 7px;
            border-radius: 6px;
            color: #E2E8F0;
            font-size: 14px;
        }
        """
        self.setStyleSheet(qss)

    def refresh_quick_models(self):
        models = fetch_ollama_models(self.cfg.get("ollama_url", "http://localhost:11434"))
        self.combo_top_models.blockSignals(True)
        self.combo_top_models.clear()
        if models:
            self.combo_top_models.addItems(models)
            if self.cfg["ollama_model"] in models:
                self.combo_top_models.setCurrentText(self.cfg["ollama_model"])
        else:
            self.combo_top_models.addItem(self.cfg.get("ollama_model", "llama3:latest"))
        self.combo_top_models.blockSignals(False)

        provider = self.cfg.get("provider", "ollama").upper()
        self.header_status.setText(f"Backend: {provider}")

    def on_top_model_changed(self, idx):
        model = self.combo_top_models.currentText()
        if model:
            self.cfg["ollama_model"] = model
            save_config(self.cfg)

    def load_current_session(self):
        self.session_list.clear()
        for idx, s in enumerate(self.sessions):
            item = QListWidgetItem(s.get("title", f"Chat {idx+1}"))
            self.session_list.addItem(item)

        self.session_list.setCurrentRow(self.current_session_idx)
        self.render_messages()

    def render_messages(self):
        if self.current_session_idx >= len(self.sessions):
            return

        sess = self.sessions[self.current_session_idx]
        html_output = "<html><head><style>"
        html_output += """
        body { font-family: 'Source Han Sans TC', 'Noto Sans TC', sans-serif; font-size: 15px; color: #E2E8F0; line-height: 1.6; }
        .user-box { background-color: #1E293B; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; color: #00F0FF; }
        .ai-box { background-color: #222538; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; color: #E2E8F0; border-left: 4px solid #8B5CF6; }
        pre { background-color: #0F172A; padding: 10px; border-radius: 6px; font-family: Consolas, monospace; font-size: 14px; overflow-x: auto; }
        code { background-color: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; }
        h1, h2, h3 { color: #00F0FF; margin-top: 12px; margin-bottom: 6px; }
        """
        html_output += "</style></head><body>"

        for m in sess.get("messages", []):
            role = m.get("role", "")
            raw_content = m.get("content", "")

            if role == "user":
                clean_content = raw_content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                html_output += f"<div class='user-box'><b>👤 YOU:</b><br>{clean_content}</div>"
            elif role == "assistant":
                # Render markdown to HTML
                md_html = markdown.markdown(raw_content, extensions=['fenced_code', 'tables', 'nl2br'])
                html_output += f"<div class='ai-box'><b>🤖 ASSISTANT:</b><br>{md_html}</div>"

        html_output += "</body></html>"
        self.chat_display.setHtml(html_output)
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

    def on_session_clicked(self, item):
        self.current_session_idx = self.session_list.row(item)
        self.render_messages()

    def create_new_session(self):
        new_sess = {"id": str(len(self.sessions) + 1), "title": f"Chat {len(self.sessions)+1}", "messages": []}
        self.sessions.insert(0, new_sess)
        self.current_session_idx = 0
        save_sessions(self.sessions)
        self.load_current_session()

    def send_message(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            return

        self.prompt_input.clear()
        sess = self.sessions[self.current_session_idx]
        if not sess["messages"]:
            sess["title"] = prompt[:20] + ("..." if len(prompt) > 20 else "")

        sess["messages"].append({"role": "user", "content": prompt})
        sess["messages"].append({"role": "assistant", "content": ""})

        self.render_messages()

        self.worker = StreamWorker(self.cfg, sess["messages"][:-1])
        self.worker.token_received.connect(self.on_token)
        self.worker.finished_signal.connect(self.on_stream_done)
        self.worker.error_signal.connect(self.on_stream_error)
        self.worker.start()

    def on_token(self, token):
        sess = self.sessions[self.current_session_idx]
        if sess["messages"] and sess["messages"][-1]["role"] == "assistant":
            sess["messages"][-1]["content"] += token
            self.render_messages()

    def on_stream_done(self):
        save_sessions(self.sessions)

    def on_stream_error(self, err_msg):
        QMessageBox.warning(self, "API 連線提示", err_msg)

    def open_settings(self):
        dialog = SettingsDialog(self.cfg, self)
        if dialog.exec():
            self.cfg = load_config()
            self.refresh_quick_models()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
