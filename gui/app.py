import sys
import json
import os
import requests
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QComboBox, QDialog, QFormLayout, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

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
    "temperature": 0.7
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

# --- Streaming Worker ---
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
                    "options": {"temperature": temp},
                    "stream": True
                }
                resp = requests.post(url, json=payload, stream=True, timeout=60)
                if resp.status_code == 404:
                    self.error_signal.emit(
                        f"Ollama 未找到模型 '{model_name}' (404 Error)。\n\n"
                        f"💡 請確認 Ollama 已啟動，並在命令列執行下列指令下載模型：\n"
                        f"   ollama pull llama3\n"
                        f"或於 ⚙️ Settings 選擇已安裝的模型。"
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
                    self.error_signal.emit(
                        "未提供有效的 API Key (401 Unauthorized)。\n\n"
                        "💡 使用 OpenAI / 雲端 API 模式時，請點擊左下角 ⚙️ Settings，\n"
                        "在 'OpenAI API Key' 欄位填入您的 API Key。"
                    )
                    return
                elif resp.status_code == 429:
                    self.error_signal.emit(
                        "OpenAI 帳戶額度已用盡或無餘額 (429 Insufficient Quota)。\n\n"
                        "💡 解決建議：\n"
                        "1. 免費方案：切換至 Ollama (Local AI) 模式 (先在命令列執行 `ollama pull llama3`)\n"
                        "2. 免費雲端：使用 OpenRouter 免費 API (Base URL 設為 https://openrouter.ai/api/v1)\n"
                        "3. 官方儲值：前往 OpenAI 平台儲值頁面新增點數。"
                    )
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
            self.error_signal.emit(f"連線失敗: {str(e)}\n\n請確認網路或本地 AI 服務 (Ollama) 是否正常啟動。")

# --- Settings Dialog ---
class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg.copy()
        self.setWindowTitle("⚙️ API Provider & Model Settings")
        self.resize(520, 480)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Ollama (Local AI)", "OpenAI / Custom Cloud API"])
        if self.cfg["provider"] == "openai":
            self.provider_combo.setCurrentIndex(1)
        self.provider_combo.currentIndexChanged.connect(self.toggle_provider_fields)
        form.addRow("<b>AI Provider:</b>", self.provider_combo)

        # Ollama Fields
        self.ollama_url_input = QLineEdit(self.cfg["ollama_url"])
        form.addRow("Ollama URL:", self.ollama_url_input)

        ollama_model_layout = QHBoxLayout()
        self.ollama_model_combo = QComboBox()
        self.btn_refresh = QPushButton("🔄 Refresh Local Models")
        self.btn_refresh.clicked.connect(self.refresh_ollama_models)
        ollama_model_layout.addWidget(self.ollama_model_combo, 1)
        ollama_model_layout.addWidget(self.btn_refresh)
        form.addRow("Ollama Model:", ollama_model_layout)

        # OpenAI Fields
        self.openai_url_input = QLineEdit(self.cfg["openai_url"])
        form.addRow("OpenAI Base URL:", self.openai_url_input)

        self.openai_key_input = QLineEdit(self.cfg["openai_key"])
        self.openai_key_input.setEchoMode(QLineEdit.Password)
        self.openai_key_input.setPlaceholderText("sk-proj-...")
        form.addRow("OpenAI API Key:", self.openai_key_input)

        self.openai_model_input = QLineEdit(self.cfg["openai_model"])
        form.addRow("OpenAI Model Name:", self.openai_model_input)

        self.sys_prompt_input = QTextEdit()
        self.sys_prompt_input.setPlainText(self.cfg["system_prompt"])
        self.sys_prompt_input.setMaximumHeight(70)
        form.addRow("System Prompt:", self.sys_prompt_input)

        layout.addLayout(form)

        # Auto fetch models on open
        self.refresh_ollama_models()

        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Save & Apply")
        btn_save.setStyleSheet("background-color: #5F00FF; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        btn_save.clicked.connect(self.save_and_close)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def toggle_provider_fields(self, index):
        is_openai = (index == 1)
        self.openai_url_input.setEnabled(is_openai)
        self.openai_key_input.setEnabled(is_openai)
        self.openai_model_input.setEnabled(is_openai)
        self.ollama_url_input.setEnabled(not is_openai)
        self.ollama_model_combo.setEnabled(not is_openai)
        self.btn_refresh.setEnabled(not is_openai)

    def refresh_ollama_models(self):
        url = self.ollama_url_input.text().strip()
        models = fetch_ollama_models(url)
        self.ollama_model_combo.clear()
        if models:
            self.ollama_model_combo.addItems(models)
            if self.cfg["ollama_model"] in models:
                self.ollama_model_combo.setCurrentText(self.cfg["ollama_model"])
        else:
            self.ollama_model_combo.addItem(f"{self.cfg['ollama_model']} (Not Pulled / Run: ollama pull)")

    def save_and_close(self):
        self.cfg["provider"] = "openai" if self.provider_combo.currentIndex() == 1 else "ollama"
        self.cfg["ollama_url"] = self.ollama_url_input.text().strip()
        if self.ollama_model_combo.currentText():
            self.cfg["ollama_model"] = self.ollama_model_combo.currentText().split(" ")[0]
        self.cfg["openai_url"] = self.openai_url_input.text().strip()
        self.cfg["openai_key"] = self.openai_key_input.text().strip()
        self.cfg["openai_model"] = self.openai_model_input.text().strip()
        self.cfg["system_prompt"] = self.sys_prompt_input.toPlainText().strip()
        save_config(self.cfg)
        self.accept()

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ AI Chat Desktop (Ultra Lightweight)")
        self.resize(1000, 700)

        self.cfg = load_config()
        self.sessions = load_sessions()
        self.current_session_idx = 0
        self.worker = None

        self.init_ui()
        self.apply_dark_theme()
        self.load_current_session()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)

        btn_new_chat = QPushButton("+ New Session")
        btn_new_chat.setStyleSheet("background-color: #00F0FF; color: #000; font-weight: bold; padding: 8px; border-radius: 6px;")
        btn_new_chat.clicked.connect(self.create_new_session)
        sidebar_layout.addWidget(btn_new_chat)

        sidebar_layout.addWidget(QLabel("<b>CONVERSATIONS</b>"))

        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self.on_session_clicked)
        sidebar_layout.addWidget(self.session_list)

        btn_settings = QPushButton("⚙️ Settings & Models")
        btn_settings.setStyleSheet("background-color: #2E3440; color: #D8DEE9; padding: 6px; border-radius: 4px;")
        btn_settings.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(btn_settings)

        splitter.addWidget(sidebar)

        # --- Main Chat Area ---
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(15, 10, 15, 10)

        self.header_label = QLabel()
        self.update_header()
        self.header_label.setStyleSheet("font-size: 14px; color: #88C0D0; padding-bottom: 5px;")
        chat_layout.addWidget(self.header_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        chat_layout.addWidget(self.chat_display)

        input_box = QHBoxLayout()
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Ask AI anything... (Click Send or press Send button)")
        self.prompt_input.setMaximumHeight(80)
        input_box.addWidget(self.prompt_input)

        btn_send = QPushButton("Send 🚀")
        btn_send.setStyleSheet("background-color: #5F00FF; color: white; font-weight: bold; min-width: 80px; min-height: 50px; border-radius: 6px;")
        btn_send.clicked.connect(self.send_message)
        input_box.addWidget(btn_send)

        chat_layout.addLayout(input_box)

        splitter.addWidget(chat_area)
        splitter.setSizes([240, 760])

        main_layout.addWidget(splitter)

    def apply_dark_theme(self):
        qss = """
        QMainWindow, QWidget {
            background-color: #1E1E2E;
            color: #C0CAF5;
        }
        QListWidget {
            background-color: #16161E;
            border: 1px solid #292E42;
            border-radius: 6px;
        }
        QListWidget::item {
            padding: 8px;
            color: #A9B1D6;
        }
        QListWidget::item:selected {
            background-color: #33374C;
            color: #00F0FF;
            font-weight: bold;
        }
        QTextEdit {
            background-color: #1A1B26;
            border: 1px solid #292E42;
            border-radius: 6px;
            color: #C0CAF5;
        }
        QLineEdit, QComboBox {
            background-color: #1A1B26;
            border: 1px solid #292E42;
            padding: 6px;
            border-radius: 4px;
            color: #C0CAF5;
        }
        """
        self.setStyleSheet(qss)

    def update_header(self):
        provider = self.cfg.get("provider", "ollama").upper()
        model = self.cfg.get("ollama_model" if provider == "OLLAMA" else "openai_model", "")
        self.header_label.setText(f"<b>Backend:</b> {provider} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Model:</b> {model}")

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
        html = ""
        for m in sess.get("messages", []):
            role = m.get("role", "")
            content = m.get("content", "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

            if role == "user":
                html += f"""
                <div style='margin-bottom: 12px;'>
                    <b style='color: #00F0FF;'>👤 YOU:</b><br>
                    <div style='background-color: #24283B; padding: 10px; border-radius: 8px; margin-top: 4px; color: #E0E6ED;'>
                        {content}
                    </div>
                </div>
                """
            elif role == "assistant":
                html += f"""
                <div style='margin-bottom: 12px;'>
                    <b style='color: #A000FF;'>🤖 ASSISTANT:</b><br>
                    <div style='background-color: #1F2335; padding: 10px; border-radius: 8px; margin-top: 4px; color: #C0CAF5;'>
                        {content}
                    </div>
                </div>
                """

        self.chat_display.setHtml(html)
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

        # Pre-flight check
        provider = self.cfg.get("provider", "ollama")
        if provider == "openai" and not self.cfg.get("openai_key") and "openai.com" in self.cfg.get("openai_url", ""):
            QMessageBox.warning(
                self, "缺少 API Key",
                "⚠️ 您切換到了 OpenAI / 雲端 API 模式，但尚未填入 API Key！\n\n"
                "請點擊左下角 ⚙️ Settings 填入您的 OpenAI API Key，或切換回 Ollama (Local AI) 模式。"
            )
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
            self.update_header()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
