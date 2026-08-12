import sys
import json
import requests
import markdown
import pygments
from pygments.formatters import HtmlFormatter
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QTextEdit, QLineEdit, QPushButton, QComboBox,
    QSlider, QLabel, QSplitter, QFrame, QDialog, QMessageBox,
    QScrollArea, QGroupBox
)

# Dark Theme QSS Stylesheet for Qt 6
QT_QSS = """
QMainWindow, QWidget#centralWidget {
    background-color: #0b0f19;
    color: #f3f4f6;
    font-family: 'Noto Sans TC', 'Source Han Sans TC', 'Microsoft JhengHei', sans-serif;
}

QFrame#sidebar {
    background-color: #060911;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

QFrame#tuningDrawer {
    background-color: #0d1322;
    border-left: 1px solid rgba(255, 255, 255, 0.08);
}

QPushButton {
    background-color: #111827;
    color: #f3f4f6;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1f293d;
    border-color: #06b6d4;
    color: #06b6d4;
}

QPushButton#btnSend {
    background-color: #06b6d4;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#btnSend:hover {
    background-color: #0891b2;
}

QComboBox {
    background-color: #111827;
    color: #f3f4f6;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #06b6d4;
}

QComboBox QAbstractItemView {
    background-color: #111827;
    color: #f3f4f6;
    selection-background-color: #06b6d4;
    selection-color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

QTextBrowser {
    background-color: #0b0f19;
    border: none;
    color: #f3f4f6;
    font-size: 14px;
    line-height: 1.6;
}

QTextEdit#inputPrompt {
    background-color: #111827;
    color: #f3f4f6;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 10px;
    font-size: 14px;
}

QTextEdit#inputPrompt:focus {
    border-color: #06b6d4;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #1f293d;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #06b6d4;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QLabel {
    color: #9ca3af;
}

QLabel#titleLabel {
    color: #f3f4f6;
    font-size: 16px;
    font-weight: 700;
}
"""

# Asynchronous Worker Thread for Streaming AI Responses
class AIStreamWorker(QThread):
    chunk_received = Signal(str)
    error_occurred = Signal(str)
    finished_signal = Signal()

    def __init__(self, settings, messages):
        super().__init__()
        self.settings = settings
        self.messages = messages

    def run(self):
        try:
            provider = self.settings['provider']
            model = self.settings['model']
            baseUrl = self.settings['baseUrl']
            params = self.settings['parameters']

            if provider == 'ollama':
                url = f"{baseUrl}/api/chat"
                formatted = [{"role": "system", "content": params['systemPrompt']}] + self.messages
                payload = {
                    "model": model,
                    "messages": formatted,
                    "stream": True,
                    "options": {
                        "temperature": float(params['temperature']),
                        "top_p": float(params['top_p']),
                        "num_predict": int(params['max_tokens']),
                        "repeat_penalty": float(params['repeat_penalty'])
                    }
                }
                res = requests.post(url, json=payload, stream=True, timeout=30)
                for line in res.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if 'message' in data and 'content' in data['message']:
                            self.chunk_received.emit(data['message']['content'])

            else:  # Remote OpenAI compatible
                url = f"{baseUrl.rstrip('/')}/v1/chat/completions"
                headers = {"Content-Type": "application/json"}
                if self.settings.get('apiKey'):
                    headers["Authorization"] = f"Bearer {self.settings['apiKey']}"

                formatted = [{"role": "system", "content": params['systemPrompt']}] + self.messages
                payload = {
                    "model": model,
                    "messages": formatted,
                    "temperature": float(params['temperature']),
                    "stream": True
                }
                res = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
                for line in res.iter_lines():
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            line_str = line_str[6:]
                        if line_str == '[DONE]':
                            break
                        try:
                            data = json.loads(line_str)
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                self.chunk_received.emit(delta['content'])
                        except:
                            pass

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished_signal.emit()


# Main Qt 6 Application Window
class ZeroAIQtWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZeroAI Desk - Qt 6 輕量多模型 AI 工作站")
        self.resize(1180, 780)

        self.settings = {
            'provider': 'ollama',
            'model': 'llama3.2',
            'baseUrl': 'http://127.0.0.1:11434',
            'apiKey': '',
            'parameters': {
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 4096,
                'repeat_penalty': 1.1,
                'systemPrompt': 'You are a helpful, intelligent, and precise AI assistant.'
            }
        }

        self.messages = []
        self.current_response = ""

        self.init_ui()
        self.check_ollama_status()

    def init_ui(self):
        centralWidget = QWidget()
        centralWidget.setObjectName("centralWidget")
        self.setCentralWidget(centralWidget)

        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # Top Navbar
        navbar = QFrame()
        navbar.setFixedHeight(60)
        navbar.setStyleSheet("background-color: #060911; border-bottom: 1px solid rgba(255, 255, 255, 0.08);")
        navLayout = QHBoxLayout(navbar)
        navLayout.setContentsMargins(16, 0, 16, 0)

        titleLabel = QLabel("⚡ ZeroAI Desk (Qt 6 原生架構)")
        titleLabel.setObjectName("titleLabel")
        navLayout.addWidget(titleLabel)

        navLayout.addStretch()

        # Model Selector
        self.modelCombo = QComboBox()
        self.modelCombo.setMinimumWidth(260)
        self.modelCombo.currentIndexChanged.connect(self.on_model_changed)
        navLayout.addWidget(self.modelCombo)

        # Toggle Tuning Drawer Button
        btnToggleTuning = QPushButton("🎛️ AI 參數微調")
        btnToggleTuning.clicked.connect(self.toggle_tuning_drawer)
        navLayout.addWidget(btnToggleTuning)

        mainLayout.addWidget(navbar)

        # Content Splitter (Messages + Tuning Drawer)
        self.bodySplitter = QSplitter(Qt.Horizontal)

        # Chat View Container
        chatContainer = QWidget()
        chatLayout = QVBoxLayout(chatContainer)
        chatLayout.setContentsMargins(20, 20, 20, 20)

        # Markdown Chat Text Browser
        self.chatBrowser = QTextBrowser()
        self.chatBrowser.setOpenExternalLinks(True)
        chatLayout.addWidget(self.chatBrowser)

        # Bottom Input Bar
        inputLayout = QHBoxLayout()
        self.inputPrompt = QTextEdit()
        self.inputPrompt.setObjectName("inputPrompt")
        self.inputPrompt.setFixedHeight(60)
        self.inputPrompt.setPlaceholderText("輸入訊息... (Ctrl+Enter 或點擊送出)")
        inputLayout.addWidget(self.inputPrompt)

        self.btnSend = QPushButton("送出")
        self.btnSend.setObjectName("btnSend")
        self.btnSend.setFixedHeight(60)
        self.btnSend.setFixedWidth(90)
        self.btnSend.clicked.connect(self.send_message)
        inputLayout.addWidget(self.btnSend)

        chatLayout.addLayout(inputLayout)
        self.bodySplitter.addWidget(chatContainer)

        # AI Tuning Drawer (Right Panel)
        self.tuningDrawer = QFrame()
        self.tuningDrawer.setObjectName("tuningDrawer")
        self.tuningDrawer.setFixedWidth(300)
        drawerLayout = QVBoxLayout(self.tuningDrawer)
        drawerLayout.setContentsMargins(16, 16, 16, 16)

        drawerTitle = QLabel("🎛️ AI 參數微調 (Qt 6 Native)")
        drawerTitle.setStyleSheet("font-weight: 700; color: #f3f4f6; font-size: 14px;")
        drawerLayout.addWidget(drawerTitle)

        # Temperature Slider
        lblTempTitle = QLabel("溫度 (Temperature):")
        self.lblTempVal = QLabel("0.7")
        self.lblTempVal.setStyleSheet("color: #06b6d4; font-weight: 700;")
        tempHeader = QHBoxLayout()
        tempHeader.addWidget(lblTempTitle)
        tempHeader.addWidget(self.lblTempVal)
        drawerLayout.addLayout(tempHeader)

        self.sliderTemp = QSlider(Qt.Horizontal)
        self.sliderTemp.setRange(0, 20)
        self.sliderTemp.setValue(7)
        self.sliderTemp.valueChanged.connect(self.on_temp_changed)
        drawerLayout.addWidget(self.sliderTemp)

        # Presets
        presetLayout = QHBoxLayout()
        btnP1 = QPushButton("精確 (0.2)")
        btnP1.clicked.connect(lambda: self.sliderTemp.setValue(2))
        btnP2 = QPushButton("平衡 (0.7)")
        btnP2.clicked.connect(lambda: self.sliderTemp.setValue(7))
        btnP3 = QPushButton("創意 (1.2)")
        btnP3.clicked.connect(lambda: self.sliderTemp.setValue(12))
        presetLayout.addWidget(btnP1)
        presetLayout.addWidget(btnP2)
        presetLayout.addWidget(btnP3)
        drawerLayout.addLayout(presetLayout)

        # System Prompt
        lblSys = QLabel("系統提示詞 (System Prompt):")
        drawerLayout.addWidget(lblSys)
        self.inputSysPrompt = QTextEdit()
        self.inputSysPrompt.setFixedHeight(120)
        self.inputSysPrompt.setPlainText(self.settings['parameters']['systemPrompt'])
        self.inputSysPrompt.textChanged.connect(self.on_sys_prompt_changed)
        drawerLayout.addWidget(self.inputSysPrompt)

        drawerLayout.addStretch()
        self.bodySplitter.addWidget(self.tuningDrawer)

        mainLayout.addWidget(self.bodySplitter)

    def toggle_tuning_drawer(self):
        self.tuningDrawer.setVisible(not self.tuningDrawer.isVisible())

    def on_temp_changed(self, val):
        temp = val / 10.0
        self.lblTempVal.setText(str(temp))
        self.settings['parameters']['temperature'] = temp

    def on_sys_prompt_changed(self):
        self.settings['parameters']['systemPrompt'] = self.inputSysPrompt.toPlainText()

    def check_ollama_status(self):
        self.modelCombo.clear()
        try:
            res = requests.get(f"{self.settings['baseUrl']}/api/tags", timeout=2)
            if res.status_code == 200:
                data = res.json()
                models = data.get('models', [])
                for m in models:
                    self.modelCombo.addItem(f"[Local] {m['name']}", f"ollama:{m['name']}")
        except Exception as e:
            # Show Ollama Setup Prompt Dialog
            QMessageBox.information(
                self,
                "Ollama 本地 AI 提示",
                "未偵測到本地 Ollama 服務。\n欲使用本地模型請開啟終端機執行:\n\n  winget install Ollama.Ollama"
            )

        # Append Remote Models
        self.modelCombo.addItem("[Remote] OpenAI gpt-4o-mini", "openai:gpt-4o-mini")
        self.modelCombo.addItem("[Remote] DeepSeek-V3", "deepseek:deepseek-chat")
        self.modelCombo.addItem("[Remote] DeepSeek-R1 (推理)", "deepseek:deepseek-reasoner")

    def on_model_changed(self, idx):
        data = self.modelCombo.currentData()
        if not data:
            return
        if data.startswith("ollama:"):
            self.settings['provider'] = 'ollama'
            self.settings['model'] = data.replace("ollama:", "")
            self.settings['baseUrl'] = 'http://127.0.0.1:11434'
        elif data.startswith("openai:"):
            self.settings['provider'] = 'openai'
            self.settings['model'] = data.replace("openai:", "")
            self.settings['baseUrl'] = 'https://api.openai.com'
        elif data.startswith("deepseek:"):
            self.settings['provider'] = 'deepseek'
            self.settings['model'] = data.replace("deepseek:", "")
            self.settings['baseUrl'] = 'https://api.deepseek.com'

    def send_message(self):
        text = self.inputPrompt.toPlainText().strip()
        if not text:
            return

        self.messages.append({"role": "user", "content": text})
        self.inputPrompt.clear()
        self.btnSend.setEnabled(False)

        self.current_response = ""
        self.render_chat()

        self.worker = AIStreamWorker(self.settings, self.messages)
        self.worker.chunk_received.connect(self.on_chunk)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_chunk(self, chunk):
        self.current_response += chunk
        self.render_chat()

    def on_error(self, err):
        self.current_response += f"\n\n⚠️ **錯誤**: {err}"
        self.render_chat()

    def on_finished(self):
        if self.current_response:
            self.messages.append({"role": "assistant", "content": self.current_response})
        self.btnSend.setEnabled(True)

    def render_chat(self):
        html = """
        <style>
            body { font-family: 'Noto Sans TC', sans-serif; background-color: #0b0f19; color: #f3f4f6; }
            .user-msg { background-color: #1f293d; padding: 12px 16px; border-radius: 12px; margin: 10px 0; max-width: 85%; align-self: flex-end; }
            .bot-msg { background-color: #111827; padding: 12px 16px; border-radius: 12px; margin: 10px 0; border: 1px solid rgba(255,255,255,0.08); }
            code { background-color: #1a2332; color: #06b6d4; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; }
            pre { background-color: #0d1117; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); overflow-x: auto; }
        </style>
        """

        for msg in self.messages:
            role = msg['role']
            content_md = markdown.markdown(msg['content'], extensions=['extra', 'codehilite'])
            if role == 'user':
                html += f"<div class='user-msg'><b>👤 使用者:</b><br>{content_md}</div>"
            else:
                html += f"<div class='bot-msg'><b>🤖 AI 助理:</b><br>{content_md}</div>"

        if self.current_response:
            resp_md = markdown.markdown(self.current_response, extensions=['extra', 'codehilite'])
            html += f"<div class='bot-msg'><b>🤖 AI 助理 (思考/回應中...):</b><br>{resp_md}</div>"

        self.chatBrowser.setHtml(html)
        self.chatBrowser.moveCursor(QTextCursor.End)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(QT_QSS)
    window = ZeroAIQtWindow()
    window.show()
    sys.exit(app.exec())
