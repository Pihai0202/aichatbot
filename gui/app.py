import sys
import json
import os
import requests
import markdown
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QComboBox, QDialog, QFormLayout, QSplitter,
    QDoubleSpinBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
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
    "openai_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai_key": "",
    "openai_model": "gemini-2.0-flash",
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
    "sparkle": '<svg viewBox="0 0 24 24" fill="none"><path d="M12 0C12 6.627 6.627 12 0 12C6.627 12 12 17.373 12 24C12 17.373 17.373 12 24 12C17.373 12 12 6.627 12 0Z" fill="#A8C7FA"/></svg>',
    "plus": '<svg viewBox="0 0 24 24" fill="none" stroke="#E3E3E3" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
    "send": '<svg viewBox="0 0 24 24" fill="none" stroke="#A8C7FA" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>',
    "settings": '<svg viewBox="0 0 24 24" fill="none" stroke="#8E918F" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="#C4C7C5" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
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
                    self.error_signal.emit(f"Ollama 未找到模型 '{model_name}' (404 Error)。請在命令列執行 ollama pull {model_name.split(':')[0]}")
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
                url = self.cfg.get("openai_url", "https://generativelanguage.googleapis.com/v1beta/openai/").rstrip("/") + "/chat/completions"
                headers = {"Content-Type": "application/json"}
                api_key = self.cfg.get("openai_key", "")
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                payload = {
                    "model": self.cfg.get("openai_model", "gemini-2.0-flash"),
                    "messages": req_messages,
                    "temperature": temp,
                    "stream": True
                }
                resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
                if resp.status_code == 401:
                    self.error_signal.emit("未提供有效的 API Key (401)。請在 ⚙️ Settings 填入 API Key。")
                    return
                elif resp.status_code == 429:
                    self.error_signal.emit("API 額度已用盡 (429)。請更換 API 密鑰或改用 Ollama。")
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

# Settings Dialog
class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg.copy()
        self.setWindowTitle("⚙️ Gemini 設定與 AI 參數微調")
        self.resize(540, 520)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Ollama (Local AI)", "OpenAI / Gemini / Custom API"])
        if self.cfg["provider"] == "openai":
            self.provider_combo.setCurrentIndex(1)
        form.addRow("<b>AI Provider:</b>", self.provider_combo)

        self.ollama_url_input = QLineEdit(self.cfg["ollama_url"])
        form.addRow("Ollama URL:", self.ollama_url_input)

        self.openai_url_input = QLineEdit(self.cfg["openai_url"])
        form.addRow("Gemini/OpenAI Base URL:", self.openai_url_input)

        self.openai_key_input = QLineEdit(self.cfg["openai_key"])
        self.openai_key_input.setEchoMode(QLineEdit.Password)
        self.openai_key_input.setPlaceholderText("AIzaSy... 或 sk-...")
        form.addRow("API Key:", self.openai_key_input)

        self.openai_model_input = QLineEdit(self.cfg["openai_model"])
        form.addRow("Gemini Model Name:", self.openai_model_input)

        layout.addLayout(form)

        lbl_tuning = QLabel("<b>🎛️ AI 產生參數微調</b>")
        lbl_tuning.setStyleSheet("color: #A8C7FA; font-size: 15px; margin-top: 8px;")
        layout.addWidget(lbl_tuning)

        form_tuning = QFormLayout()
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 2.0)
        self.spin_temp.setValue(float(self.cfg.get("temperature", 0.7)))
        form_tuning.addRow("溫度 (Temperature):", self.spin_temp)

        self.combo_num_ctx = QComboBox()
        self.combo_num_ctx.addItems(["2048", "4096", "8192", "16384"])
        self.combo_num_ctx.setCurrentText(str(self.cfg.get("num_ctx", 4096)))
        form_tuning.addRow("上下文長度 (Num Ctx):", self.combo_num_ctx)

        self.spin_repeat = QDoubleSpinBox()
        self.spin_repeat.setRange(0.5, 2.0)
        self.spin_repeat.setValue(float(self.cfg.get("repeat_penalty", 1.1)))
        form_tuning.addRow("重複懲罰 (Repeat Penalty):", self.spin_repeat)

        self.sys_prompt_input = QTextEdit()
        self.sys_prompt_input.setPlainText(self.cfg["system_prompt"])
        self.sys_prompt_input.setMaximumHeight(70)
        form_tuning.addRow("System Prompt:", self.sys_prompt_input)

        layout.addLayout(form_tuning)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 儲存並套用")
        btn_save.setStyleSheet("background-color: #A8C7FA; color: #000; font-weight: bold; padding: 8px 18px; border-radius: 18px;")
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

# Gemini Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini AI Chatbot")
        self.resize(1120, 760)

        self.cfg = load_config()
        self.sessions = load_sessions()
        self.current_session_idx = 0
        self.worker = None

        self.init_ui()
        self.apply_gemini_theme()
        self.load_current_session()
        self.refresh_quick_models()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # --- Gemini Left Sidebar ---
        sidebar = QWidget()
        sidebar.setMinimumWidth(250)
        sidebar.setMaximumWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(10)

        # Brand Logo Row
        brand_row = QHBoxLayout()
        lbl_sparkle = QLabel()
        lbl_sparkle.setPixmap(svg_to_icon(SVG_ICONS["sparkle"], 26).pixmap(26, 26))
        brand_row.addWidget(lbl_sparkle)

        lbl_brand = QLabel("Gemini")
        lbl_brand.setStyleSheet("font-size: 20px; font-weight: 500; color: #E3E3E3;")
        brand_row.addWidget(lbl_brand)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)

        # Mode Tabs
        tabs_box = QHBoxLayout()
        btn_tab1 = QPushButton("即時通訊")
        btn_tab1.setStyleSheet("background-color: #28292A; color: #E3E3E3; border-radius: 14px; padding: 5px 10px; font-size: 13px;")
        btn_tab2 = QPushButton("Spark BETA")
        btn_tab2.setStyleSheet("background: none; color: #8E918F; border-radius: 14px; padding: 5px 10px; font-size: 13px;")
        tabs_box.addWidget(btn_tab1)
        tabs_box.addWidget(btn_tab2)
        sidebar_layout.addLayout(tabs_box)

        # Nav Items
        btn_new_chat = QPushButton(" 新對話")
        btn_new_chat.setIcon(svg_to_icon(SVG_ICONS["plus"], 18))
        btn_new_chat.setStyleSheet("background-color: rgba(255,255,255,0.06); color: #C4C7C5; padding: 9px; border-radius: 18px; font-size: 14px; text-align: left;")
        btn_new_chat.clicked.connect(self.create_new_session)
        sidebar_layout.addWidget(btn_new_chat)

        sidebar_layout.addWidget(QLabel("<span style='color: #8E918F; font-size: 12px;'>近期對話</span>"))

        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self.on_session_clicked)
        sidebar_layout.addWidget(self.session_list)

        # User Profile Footer
        footer_layout = QHBoxLayout()
        lbl_avatar = QLabel("YY")
        lbl_avatar.setStyleSheet("background-color: #2D5B88; color: white; border-radius: 16px; padding: 6px; font-weight: bold; font-size: 13px;")
        footer_layout.addWidget(lbl_avatar)

        lbl_user = QLabel("<b>YY C</b><br><span style='color: #8E918F; font-size: 11px;'>Pro</span>")
        footer_layout.addWidget(lbl_user)
        footer_layout.addStretch()

        btn_settings = QPushButton()
        btn_settings.setIcon(svg_to_icon(SVG_ICONS["settings"], 20))
        btn_settings.setStyleSheet("background: none; border: none; padding: 6px;")
        btn_settings.clicked.connect(self.open_settings)
        footer_layout.addWidget(btn_settings)

        sidebar_layout.addLayout(footer_layout)
        splitter.addWidget(sidebar)

        # --- Main Workspace ---
        workspace = QWidget()
        ws_layout = QVBoxLayout(workspace)
        ws_layout.setContentsMargins(0, 0, 0, 0)

        # Hero Welcome Greeting Label
        self.lbl_hero = QLabel("YY ，趕快開始吧！")
        self.lbl_hero.setAlignment(Qt.AlignCenter)
        self.lbl_hero.setStyleSheet("font-size: 34px; font-weight: 500; color: #E3E3E3; padding: 40px 0;")
        ws_layout.addWidget(self.lbl_hero)

        # Chat TextBrowser Container (Centered max-width 840px)
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setVisible(False)
        ws_layout.addWidget(self.chat_display, 1)

        # Floating Pill Input Capsule Box
        pill_box = QHBoxLayout()
        pill_box.setContentsMargins(40, 10, 40, 20)

        capsule_frame = QFrame()
        capsule_frame.setStyleSheet("background-color: #1E1F20; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 28px; padding: 4px 12px;")
        capsule_layout = QHBoxLayout(capsule_frame)

        btn_add = QPushButton("+")
        btn_add.setStyleSheet("background: none; border: none; color: #C4C7C5; font-size: 20px; font-weight: bold;")
        capsule_layout.addWidget(btn_add)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("問問 Gemini...")
        self.prompt_input.setStyleSheet("background: none; border: none; color: #E3E3E3; font-size: 16px; padding: 8px;")
        self.prompt_input.returnPressed.connect(self.send_message)
        capsule_layout.addWidget(self.prompt_input, 1)

        # Model Selector Dropdown inside Capsule
        self.combo_top_models = QComboBox()
        self.combo_top_models.setStyleSheet("background-color: rgba(255,255,255,0.06); color: #A8C7FA; border-radius: 14px; padding: 4px 10px; font-size: 13px;")
        self.combo_top_models.currentIndexChanged.connect(self.on_top_model_changed)
        capsule_layout.addWidget(self.combo_top_models)

        btn_send = QPushButton()
        btn_send.setIcon(svg_to_icon(SVG_ICONS["send"], 22))
        btn_send.setStyleSheet("background: none; border: none; padding: 4px;")
        btn_send.clicked.connect(self.send_message)
        capsule_layout.addWidget(btn_send)

        pill_box.addWidget(capsule_frame)
        ws_layout.addLayout(pill_box)

        splitter.addWidget(workspace)
        splitter.setSizes([260, 860])
        main_layout.addWidget(splitter)

    def apply_gemini_theme(self):
        font = QFont()
        font.setFamilies(["Source Han Sans TC", "Noto Sans TC", "Microsoft JhengHei", "sans-serif"])
        font.setPointSize(11)
        QApplication.setFont(font)

        qss = """
        QMainWindow, QWidget {
            background-color: #131314;
            color: #E3E3E3;
            font-family: 'Source Han Sans TC', 'Noto Sans TC', sans-serif;
        }
        QListWidget {
            background-color: #1E1F20;
            border: none;
            border-radius: 14px;
        }
        QListWidget::item {
            padding: 8px 12px;
            color: #C4C7C5;
            border-radius: 16px;
        }
        QListWidget::item:selected {
            background-color: #004A77;
            color: #A8C7FA;
            font-weight: 500;
        }
        QTextBrowser {
            background-color: #131314;
            border: none;
            color: #E3E3E3;
            padding: 20px 60px;
            font-size: 16px;
        }
        """
        self.setStyleSheet(qss)

    def refresh_quick_models(self):
        if self.cfg.get("provider") == "openai":
            self.combo_top_models.clear()
            self.combo_top_models.addItem(self.cfg.get("openai_model", "gemini-2.0-flash"))
            return

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

    def on_top_model_changed(self, idx):
        model = self.combo_top_models.currentText()
        if model and self.cfg.get("provider") == "ollama":
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
        if not sess.get("messages"):
            self.lbl_hero.setVisible(True)
            self.chat_display.setVisible(False)
            return

        self.lbl_hero.setVisible(False)
        self.chat_display.setVisible(True)

        html_output = "<html><head><style>"
        html_output += """
        body { font-family: 'Source Han Sans TC', sans-serif; font-size: 16px; color: #E3E3E3; line-height: 1.6; }
        .user-box { background-color: #1E293B; border-radius: 12px; padding: 12px 16px; margin-bottom: 16px; color: #A8C7FA; }
        .ai-box { background-color: #1E1F20; border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; color: #E3E3E3; border: 1px solid rgba(255,255,255,0.05); }
        pre { background-color: #0F172A; padding: 12px; border-radius: 8px; font-family: Consolas, monospace; font-size: 14px; }
        code { background-color: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; }
        h1, h2, h3 { color: #A8C7FA; margin-top: 12px; margin-bottom: 6px; }
        """
        html_output += "</style></head><body>"

        for m in sess.get("messages", []):
            role = m.get("role", "")
            raw_content = m.get("content", "")

            if role == "user":
                clean_content = raw_content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                html_output += f"<div class='user-box'><b>YY:</b><br>{clean_content}</div>"
            elif role == "assistant":
                md_html = markdown.markdown(raw_content, extensions=['fenced_code', 'tables', 'nl2br'])
                html_output += f"<div class='ai-box'><b>✨ Gemini:</b><br>{md_html}</div>"

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
        prompt = self.prompt_input.text().strip()
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
