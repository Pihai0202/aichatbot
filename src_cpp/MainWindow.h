#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QComboBox>
#include <QTextBrowser>
#include <QTextEdit>
#include <QPushButton>
#include <QSlider>
#include <QLabel>
#include <QSplitter>
#include <QFrame>
#include <QListWidget>
#include <QSpinBox>
#include <QLineEdit>
#include <QJsonArray>
#include <QJsonObject>
#include "OllamaClient.h"

struct ChatMessage {
    QString role; // "user", "assistant", "system"
    QString content;
};

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow();

private slots:
    void onRefreshModels();
    void onModelsReceived(const QStringList& models);
    void onModelChanged(int index);
    void onSendMessage();
    void onStopGeneration();
    void onChunkReceived(const QString& chunk);
    void onErrorOccurred(const QString& errorMsg);
    void onGenerationFinished();
    void onTempSliderChanged(int value);
    void onToggleTuningDrawer();
    void onNewChat();
    void onClearHistory();

private:
    void initUI();
    void setupStyles();
    void renderChat();
    QString markdownToHtml(const QString& md);

    // Backend
    OllamaClient* m_ollamaClient;

    // State
    QString m_baseUrl;
    QString m_selectedModel;
    double m_temperature;
    double m_topP;
    int m_maxTokens;
    double m_repeatPenalty;
    QString m_systemPrompt;

    QList<ChatMessage> m_messages;
    QString m_currentAssistantResponse;
    bool m_isGenerating;

    // UI Widgets
    QLabel* m_statusBadge;
    QComboBox* m_modelCombo;
    QPushButton* m_btnRefreshModels;
    QPushButton* m_btnToggleDrawer;

    QListWidget* m_chatHistoryList;
    QPushButton* m_btnNewChat;

    QTextBrowser* m_chatBrowser;
    QTextEdit* m_inputPrompt;
    QPushButton* m_btnSend;
    QPushButton* m_btnStop;

    QFrame* m_tuningDrawer;
    QSlider* m_sliderTemp;
    QLabel* m_lblTempVal;
    QTextEdit* m_inputSystemPrompt;
    QLineEdit* m_inputBaseUrl;
};

#endif // MAINWINDOW_H
