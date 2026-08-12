#include "MainWindow.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFrame>
#include <QSplitter>
#include <QMessageBox>
#include <QTextCursor>
#include <QRegularExpression>
#include <QDateTime>
#include <QIcon>
#include <QSize>
#include <QDebug>

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
    , m_ollamaClient(new OllamaClient(this))
    , m_baseUrl("http://127.0.0.1:11434")
    , m_temperature(0.7)
    , m_topP(0.9)
    , m_maxTokens(4096)
    , m_repeatPenalty(1.1)
    , m_systemPrompt("You are a helpful, intelligent, and precise AI assistant.")
    , m_isGenerating(false)
{
    initUI();
    setupStyles();

    connect(m_ollamaClient, &OllamaClient::modelsReceived, this, &MainWindow::onModelsReceived);
    connect(m_ollamaClient, &OllamaClient::chunkReceived, this, &MainWindow::onChunkReceived);
    connect(m_ollamaClient, &OllamaClient::errorOccurred, this, &MainWindow::onErrorOccurred);
    connect(m_ollamaClient, &OllamaClient::finished, this, &MainWindow::onGenerationFinished);

    onRefreshModels();
}

MainWindow::~MainWindow() {}

void MainWindow::initUI() {
    setWindowTitle("ZeroAI Local Studio - Qt 6 (C++ Native)");
    setWindowIcon(QIcon("assets/icons/logo.svg"));
    resize(1240, 800);

    QWidget* centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);

    QVBoxLayout* mainLayout = new QVBoxLayout(centralWidget);
    mainLayout->setContentsMargins(0, 0, 0, 0);
    mainLayout->setSpacing(0);

    // ==========================================
    // 1. TOP NAVBAR
    // ==========================================
    QFrame* navbar = new QFrame(this);
    navbar->setFixedHeight(62);
    navbar->setObjectName("navbar");

    QHBoxLayout* navLayout = new QHBoxLayout(navbar);
    navLayout->setContentsMargins(18, 0, 18, 0);

    // App Logo + Title
    QLabel* logoIcon = new QLabel(navbar);
    logoIcon->setPixmap(QIcon("assets/icons/logo.svg").pixmap(24, 24));
    navLayout->addWidget(logoIcon);

    QLabel* logoLabel = new QLabel("ZeroAI Local Studio", navbar);
    logoLabel->setObjectName("logoLabel");
    navLayout->addWidget(logoLabel);

    m_statusBadge = new QLabel("已連線", navbar);
    m_statusBadge->setObjectName("statusBadge");
    navLayout->addWidget(m_statusBadge);

    navLayout->addStretch();

    // Model selection dropdown
    QLabel* lblModel = new QLabel("模型 (Model):", navbar);
    lblModel->setStyleSheet("color: #9ca3af; font-size: 13px; font-weight: 500;");
    navLayout->addWidget(lblModel);

    m_modelCombo = new QComboBox(navbar);
    m_modelCombo->setMinimumWidth(260);
    connect(m_modelCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this, &MainWindow::onModelChanged);
    navLayout->addWidget(m_modelCombo);

    m_btnRefreshModels = new QPushButton(" 重新整理", navbar);
    m_btnRefreshModels->setIcon(QIcon("assets/icons/refresh.svg"));
    m_btnRefreshModels->setIconSize(QSize(16, 16));
    connect(m_btnRefreshModels, &QPushButton::clicked, this, &MainWindow::onRefreshModels);
    navLayout->addWidget(m_btnRefreshModels);

    m_btnToggleDrawer = new QPushButton(" AI 參數微調", navbar);
    m_btnToggleDrawer->setIcon(QIcon("assets/icons/tuning.svg"));
    m_btnToggleDrawer->setIconSize(QSize(16, 16));
    connect(m_btnToggleDrawer, &QPushButton::clicked, this, &MainWindow::onToggleTuningDrawer);
    navLayout->addWidget(m_btnToggleDrawer);

    mainLayout->addWidget(navbar);

    // ==========================================
    // 2. MAIN BODY SPLITTER (Sidebar + Chat + Tuning Panel)
    // ==========================================
    QSplitter* bodySplitter = new QSplitter(Qt::Horizontal, centralWidget);

    // ------------------------------------------
    // LEFT SIDEBAR (Chat History)
    // ------------------------------------------
    QFrame* sidebar = new QFrame(bodySplitter);
    sidebar->setFixedWidth(240);
    sidebar->setObjectName("sidebar");

    QVBoxLayout* sidebarLayout = new QVBoxLayout(sidebar);
    sidebarLayout->setContentsMargins(12, 16, 12, 16);

    m_btnNewChat = new QPushButton(" 開啟新對話", sidebar);
    m_btnNewChat->setObjectName("btnNewChat");
    m_btnNewChat->setIcon(QIcon("assets/icons/plus.svg"));
    m_btnNewChat->setIconSize(QSize(16, 16));
    connect(m_btnNewChat, &QPushButton::clicked, this, &MainWindow::onNewChat);
    sidebarLayout->addWidget(m_btnNewChat);

    QLabel* lblHistory = new QLabel("歷史紀錄", sidebar);
    lblHistory->setStyleSheet("color: #6b7280; font-weight: 600; font-size: 12px; margin-top: 10px;");
    sidebarLayout->addWidget(lblHistory);

    m_chatHistoryList = new QListWidget(sidebar);
    m_chatHistoryList->setObjectName("chatHistoryList");
    
    QListWidgetItem* sessionItem = new QListWidgetItem(QIcon("assets/icons/chat.svg"), "對話 Session #1");
    m_chatHistoryList->addItem(sessionItem);
    sidebarLayout->addWidget(m_chatHistoryList);

    QPushButton* btnClear = new QPushButton(" 清空歷史", sidebar);
    btnClear->setIcon(QIcon("assets/icons/trash.svg"));
    btnClear->setIconSize(QSize(16, 16));
    btnClear->setStyleSheet("background: transparent; color: #ef4444; border: 1px solid #374151; font-weight: 500;");
    connect(btnClear, &QPushButton::clicked, this, &MainWindow::onClearHistory);
    sidebarLayout->addWidget(btnClear);

    bodySplitter->addWidget(sidebar);

    // ------------------------------------------
    // CENTRAL CHAT CONTAINER
    // ------------------------------------------
    QWidget* chatContainer = new QWidget(bodySplitter);
    QVBoxLayout* chatLayout = new QVBoxLayout(chatContainer);
    chatLayout->setContentsMargins(20, 20, 20, 20);

    m_chatBrowser = new QTextBrowser(chatContainer);
    m_chatBrowser->setObjectName("chatBrowser");
    m_chatBrowser->setOpenExternalLinks(true);
    chatLayout->addWidget(m_chatBrowser);

    // Input Bar
    QHBoxLayout* inputLayout = new QHBoxLayout();
    m_inputPrompt = new QTextEdit(chatContainer);
    m_inputPrompt->setObjectName("inputPrompt");
    m_inputPrompt->setFixedHeight(64);
    m_inputPrompt->setPlaceholderText("輸入對話內容... (點擊送出或按 Enter)");
    inputLayout->addWidget(m_inputPrompt);

    m_btnSend = new QPushButton(" 送出", chatContainer);
    m_btnSend->setObjectName("btnSend");
    m_btnSend->setIcon(QIcon("assets/icons/send.svg"));
    m_btnSend->setIconSize(QSize(16, 16));
    m_btnSend->setFixedHeight(64);
    m_btnSend->setFixedWidth(96);
    connect(m_btnSend, &QPushButton::clicked, this, &MainWindow::onSendMessage);
    inputLayout->addWidget(m_btnSend);

    m_btnStop = new QPushButton(" 停止", chatContainer);
    m_btnStop->setObjectName("btnStop");
    m_btnStop->setIcon(QIcon("assets/icons/stop.svg"));
    m_btnStop->setIconSize(QSize(16, 16));
    m_btnStop->setFixedHeight(64);
    m_btnStop->setFixedWidth(96);
    m_btnStop->setVisible(false);
    connect(m_btnStop, &QPushButton::clicked, this, &MainWindow::onStopGeneration);
    inputLayout->addWidget(m_btnStop);

    chatLayout->addLayout(inputLayout);
    bodySplitter->addWidget(chatContainer);

    // ------------------------------------------
    // RIGHT AI TUNING DRAWER
    // ------------------------------------------
    m_tuningDrawer = new QFrame(bodySplitter);
    m_tuningDrawer->setFixedWidth(300);
    m_tuningDrawer->setObjectName("tuningDrawer");

    QVBoxLayout* drawerLayout = new QVBoxLayout(m_tuningDrawer);
    drawerLayout->setContentsMargins(16, 16, 16, 16);

    QHBoxLayout* drawerHeader = new QHBoxLayout();
    QLabel* drawerIcon = new QLabel(m_tuningDrawer);
    drawerIcon->setPixmap(QIcon("assets/icons/tuning.svg").pixmap(18, 18));
    drawerHeader->addWidget(drawerIcon);

    QLabel* drawerTitle = new QLabel("AI 參數設定 (Tuning)", m_tuningDrawer);
    drawerTitle->setStyleSheet("font-weight: 700; color: #f3f4f6; font-size: 15px;");
    drawerHeader->addWidget(drawerTitle);
    drawerHeader->addStretch();
    drawerLayout->addLayout(drawerHeader);

    // Server Base URL
    QLabel* lblBaseUrl = new QLabel("Ollama API URL:", m_tuningDrawer);
    lblBaseUrl->setStyleSheet("margin-top: 8px; font-weight: 500;");
    drawerLayout->addWidget(lblBaseUrl);
    m_inputBaseUrl = new QLineEdit(m_baseUrl, m_tuningDrawer);
    m_inputBaseUrl->setObjectName("inputBaseUrl");
    connect(m_inputBaseUrl, &QLineEdit::editingFinished, [this]() {
        m_baseUrl = m_inputBaseUrl->text().trimmed();
        onRefreshModels();
    });
    drawerLayout->addWidget(m_inputBaseUrl);

    // Temperature Slider
    QHBoxLayout* tempHeader = new QHBoxLayout();
    QLabel* lblTempTitle = new QLabel("溫度 (Temperature):", m_tuningDrawer);
    lblTempTitle->setStyleSheet("font-weight: 500;");
    m_lblTempVal = new QLabel("0.7", m_tuningDrawer);
    m_lblTempVal->setStyleSheet("color: #06b6d4; font-weight: 700;");
    tempHeader->addWidget(lblTempTitle);
    tempHeader->addWidget(m_lblTempVal);
    drawerLayout->addLayout(tempHeader);

    m_sliderTemp = new QSlider(Qt::Horizontal, m_tuningDrawer);
    m_sliderTemp->setRange(0, 20);
    m_sliderTemp->setValue(7);
    connect(m_sliderTemp, &QSlider::valueChanged, this, &MainWindow::onTempSliderChanged);
    drawerLayout->addWidget(m_sliderTemp);

    // Temperature Quick Presets
    QHBoxLayout* presetLayout = new QHBoxLayout();
    QPushButton* btnP1 = new QPushButton("精確 (0.2)", m_tuningDrawer);
    connect(btnP1, &QPushButton::clicked, [this]() { m_sliderTemp->setValue(2); });
    QPushButton* btnP2 = new QPushButton("平衡 (0.7)", m_tuningDrawer);
    connect(btnP2, &QPushButton::clicked, [this]() { m_sliderTemp->setValue(7); });
    QPushButton* btnP3 = new QPushButton("創意 (1.2)", m_tuningDrawer);
    connect(btnP3, &QPushButton::clicked, [this]() { m_sliderTemp->setValue(12); });
    presetLayout->addWidget(btnP1);
    presetLayout->addWidget(btnP2);
    presetLayout->addWidget(btnP3);
    drawerLayout->addLayout(presetLayout);

    // System Prompt Editor
    QLabel* lblSysPrompt = new QLabel("系統提示詞 (System Prompt):", m_tuningDrawer);
    lblSysPrompt->setStyleSheet("margin-top: 12px; font-weight: 500;");
    drawerLayout->addWidget(lblSysPrompt);

    m_inputSystemPrompt = new QTextEdit(m_tuningDrawer);
    m_inputSystemPrompt->setFixedHeight(120);
    m_inputSystemPrompt->setPlainText(m_systemPrompt);
    connect(m_inputSystemPrompt, &QTextEdit::textChanged, [this]() {
        m_systemPrompt = m_inputSystemPrompt->toPlainText();
    });
    drawerLayout->addWidget(m_inputSystemPrompt);

    drawerLayout->addStretch();
    bodySplitter->addWidget(m_tuningDrawer);

    mainLayout->addWidget(bodySplitter);

    renderChat();
}

void MainWindow::setupStyles() {
    QString qss = R"(
        QMainWindow {
            background-color: #0b0f19;
            color: #f3f4f6;
            font-family: 'Source Han Sans TC', 'Source Han Sans TW', 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
        }
        QFrame#navbar {
            background-color: #060911;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        QLabel#logoLabel {
            color: #ffffff;
            font-size: 17px;
            font-weight: 700;
            margin-left: 6px;
        }
        QLabel#statusBadge {
            background-color: rgba(6, 182, 212, 0.15);
            color: #06b6d4;
            border: 1px solid rgba(6, 182, 212, 0.3);
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }
        QFrame#sidebar {
            background-color: #060911;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        QPushButton#btnNewChat {
            background-color: #06b6d4;
            color: #ffffff;
            font-weight: 600;
            border-radius: 8px;
            padding: 10px;
        }
        QPushButton#btnNewChat:hover {
            background-color: #0891b2;
        }
        QListWidget#chatHistoryList {
            background-color: transparent;
            border: none;
            color: #d1d5db;
            font-weight: 500;
        }
        QListWidget#chatHistoryList::item {
            padding: 10px;
            border-radius: 6px;
        }
        QListWidget#chatHistoryList::item:hover {
            background-color: #1f293d;
        }
        QListWidget#chatHistoryList::item:selected {
            background-color: #06b6d4;
            color: #ffffff;
        }
        QFrame#tuningDrawer {
            background-color: #0d1322;
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }
        QTextBrowser#chatBrowser {
            background-color: #0b0f19;
            border: none;
            color: #f3f4f6;
            font-size: 14px;
            font-family: 'Source Han Sans TC', 'Noto Sans TC', sans-serif;
        }
        QTextEdit#inputPrompt {
            background-color: #111827;
            color: #f3f4f6;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 8px;
            font-size: 14px;
            font-family: 'Source Han Sans TC', 'Noto Sans TC', sans-serif;
        }
        QTextEdit#inputPrompt:focus {
            border-color: #06b6d4;
        }
        QLineEdit#inputBaseUrl {
            background-color: #111827;
            color: #f3f4f6;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 6px;
            padding: 6px;
        }
        QPushButton {
            background-color: #111827;
            color: #f3f4f6;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 13px;
            font-family: 'Source Han Sans TC', 'Noto Sans TC', sans-serif;
        }
        QPushButton:hover {
            background-color: #1f293d;
            border-color: #06b6d4;
            color: #06b6d4;
        }
        QPushButton#btnSend {
            background-color: #06b6d4;
            color: #ffffff;
            font-weight: 700;
            border: none;
        }
        QPushButton#btnSend:hover {
            background-color: #0891b2;
        }
        QPushButton#btnStop {
            background-color: #ef4444;
            color: #ffffff;
            font-weight: 700;
            border: none;
        }
        QPushButton#btnStop:hover {
            background-color: #dc2626;
        }
        QComboBox {
            background-color: #111827;
            color: #f3f4f6;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 6px 10px;
            font-family: 'Source Han Sans TC', 'Noto Sans TC', sans-serif;
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
            font-family: 'Source Han Sans TC', 'Noto Sans TC', sans-serif;
        }
    )";
    setStyleSheet(qss);
}

void MainWindow::onRefreshModels() {
    m_modelCombo->clear();
    m_modelCombo->addItem(QIcon("assets/icons/refresh.svg"), "載入模型中...");
    m_ollamaClient->fetchModels(m_baseUrl);
}

void MainWindow::onModelsReceived(const QStringList& models) {
    m_modelCombo->clear();
    if (models.isEmpty()) {
        m_statusBadge->setText("未連線");
        m_statusBadge->setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);");
        m_modelCombo->addItem(QIcon("assets/icons/disconnected.svg"), "[未偵測到 Ollama 服務或模型]");
    } else {
        m_statusBadge->setText("已連線 (" + QString::number(models.size()) + " 個模型)");
        m_statusBadge->setStyleSheet("background-color: rgba(6, 182, 212, 0.15); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3);");
        for (const QString& m : models) {
            m_modelCombo->addItem(QIcon("assets/icons/model.svg"), m, m);
        }
    }
}

void MainWindow::onModelChanged(int index) {
    if (index >= 0) {
        m_selectedModel = m_modelCombo->itemData(index).toString();
    }
}

void MainWindow::onSendMessage() {
    QString text = m_inputPrompt->toPlainText().trimmed();
    if (text.isEmpty() || m_isGenerating) return;

    ChatMessage userMsg;
    userMsg.role = "user";
    userMsg.content = text;
    m_messages.append(userMsg);

    m_inputPrompt->clear();
    m_currentAssistantResponse.clear();
    m_isGenerating = true;

    m_btnSend->setVisible(false);
    m_btnStop->setVisible(true);

    renderChat();

    // Prepare JSON messages
    QJsonArray msgArray;

    // Add System Prompt
    if (!m_systemPrompt.isEmpty()) {
        QJsonObject sysObj;
        sysObj["role"] = "system";
        sysObj["content"] = m_systemPrompt;
        msgArray.append(sysObj);
    }

    for (const ChatMessage& msg : m_messages) {
        QJsonObject obj;
        obj["role"] = msg.role;
        obj["content"] = msg.content;
        msgArray.append(obj);
    }

    QJsonObject params;
    params["temperature"] = m_temperature;
    params["top_p"] = m_topP;
    params["max_tokens"] = m_maxTokens;
    params["repeat_penalty"] = m_repeatPenalty;

    m_ollamaClient->sendChatRequest(m_baseUrl, m_selectedModel, msgArray, params);
}

void MainWindow::onStopGeneration() {
    m_ollamaClient->cancelRequest();
}

void MainWindow::onChunkReceived(const QString& chunk) {
    m_currentAssistantResponse += chunk;
    renderChat();
}

void MainWindow::onErrorOccurred(const QString& errorMsg) {
    m_currentAssistantResponse += "\n\n⚠️ **錯誤**: " + errorMsg;
    renderChat();
}

void MainWindow::onGenerationFinished() {
    if (!m_currentAssistantResponse.isEmpty()) {
        ChatMessage botMsg;
        botMsg.role = "assistant";
        botMsg.content = m_currentAssistantResponse;
        m_messages.append(botMsg);
        m_currentAssistantResponse.clear();
    }

    m_isGenerating = false;
    m_btnSend->setVisible(true);
    m_btnStop->setVisible(false);
    renderChat();
}

void MainWindow::onTempSliderChanged(int value) {
    m_temperature = value / 10.0;
    m_lblTempVal->setText(QString::number(m_temperature, 'f', 1));
}

void MainWindow::onToggleTuningDrawer() {
    m_tuningDrawer->setVisible(!m_tuningDrawer->isVisible());
}

void MainWindow::onNewChat() {
    m_messages.clear();
    m_currentAssistantResponse.clear();
    renderChat();
}

void MainWindow::onClearHistory() {
    onNewChat();
}

QString MainWindow::markdownToHtml(const QString& md) {
    QString html = md;
    html.replace("&", "&amp;");
    html.replace("<", "&lt;");
    html.replace(">", "&gt;");

    // Code blocks ```code```
    QRegularExpression codeBlockRegex("```([a-zA-Z0-9_]*)\n?(.*?)```", QRegularExpression::DotMatchesEverythingOption);
    html.replace(codeBlockRegex, "<pre><code>\\2</code></pre>");

    // Inline code `code`
    QRegularExpression inlineCodeRegex("`([^`]+)`");
    html.replace(inlineCodeRegex, "<code>\\1</code>");

    // Bold **text**
    QRegularExpression boldRegex("\\*\\*([^*]+)\\*\\*");
    html.replace(boldRegex, "<b>\\1</b>");

    // Italic *text*
    QRegularExpression italicRegex("\\*([^*]+)\\*");
    html.replace(italicRegex, "<i>\\1</i>");

    // Line breaks
    html.replace("\n", "<br>");

    return html;
}

void MainWindow::renderChat() {
    QString html = R"(
        <html>
        <head>
        <style>
            body { font-family: 'Source Han Sans TC', 'Noto Sans TC', 'Microsoft JhengHei', sans-serif; background-color: #0b0f19; color: #f3f4f6; padding: 10px; }
            .msg-container { margin-bottom: 16px; }
            .user-bubble {
                background-color: #1f293d;
                border: 1px solid rgba(6, 182, 212, 0.3);
                border-radius: 12px;
                padding: 12px 16px;
                margin-left: 15%;
                color: #ffffff;
            }
            .bot-bubble {
                background-color: #111827;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 12px 16px;
                margin-right: 10%;
                color: #f3f4f6;
            }
            .role-header {
                font-weight: 700;
                font-size: 13px;
                margin-bottom: 6px;
                display: flex;
                align-items: center;
            }
            .user-header { color: #06b6d4; }
            .bot-header { color: #10b981; }
            .icon-img { vertical-align: middle; margin-right: 6px; }
            code {
                background-color: #1f293d;
                color: #06b6d4;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: Consolas, monospace;
            }
            pre {
                background-color: #060911;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 12px;
                font-family: Consolas, monospace;
                white-space: pre-wrap;
            }
        </style>
        </head>
        <body>
    )";

    for (const ChatMessage& msg : m_messages) {
        if (msg.role == "user") {
            html += "<div class='msg-container'><div class='user-bubble'>";
            html += "<div class='role-header user-header'><img class='icon-img' src='assets/icons/user.svg' width='16' height='16'> 使用者</div>";
            html += markdownToHtml(msg.content);
            html += "</div></div>";
        } else {
            html += "<div class='msg-container'><div class='bot-bubble'>";
            html += "<div class='role-header bot-header'><img class='icon-img' src='assets/icons/bot.svg' width='16' height='16'> AI 助理</div>";
            html += markdownToHtml(msg.content);
            html += "</div></div>";
        }
    }

    if (m_isGenerating || !m_currentAssistantResponse.isEmpty()) {
        html += "<div class='msg-container'><div class='bot-bubble'>";
        html += "<div class='role-header bot-header'><img class='icon-img' src='assets/icons/bot.svg' width='16' height='16'> AI 助理 (思考/回應中...)</div>";
        html += markdownToHtml(m_currentAssistantResponse);
        html += "</div></div>";
    }

    html += "</body></html>";

    m_chatBrowser->setHtml(html);
    m_chatBrowser->moveCursor(QTextCursor::End);
}
