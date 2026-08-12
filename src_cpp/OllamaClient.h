#ifndef OLLAMA_CLIENT_H
#define OLLAMA_CLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QStringList>

class OllamaClient : public QObject {
    Q_OBJECT

public:
    explicit OllamaClient(QObject* parent = nullptr);
    ~OllamaClient();

    void fetchModels(const QString& baseUrl = "http://127.0.0.1:11434");
    void sendChatRequest(const QString& baseUrl,
                        const QString& model,
                        const QJsonArray& messages,
                        const QJsonObject& parameters);
    void cancelRequest();

signals:
    void modelsReceived(const QStringList& models);
    void chunkReceived(const QString& chunk);
    void errorOccurred(const QString& errorMsg);
    void finished();

private slots:
    void handleModelsFinished(QNetworkReply* reply);
    void handleChatReadyRead();
    void handleChatFinished();
    void handleChatError(QNetworkReply::NetworkError code);

private:
    QNetworkAccessManager* m_networkManager;
    QNetworkReply* m_currentReply;
    QByteArray m_buffer;
};

#endif // OLLAMA_CLIENT_H
