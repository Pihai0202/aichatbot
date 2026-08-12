#include "OllamaClient.h"
#include <QNetworkRequest>
#include <QUrl>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDebug>

OllamaClient::OllamaClient(QObject* parent)
    : QObject(parent)
    , m_networkManager(new QNetworkAccessManager(this))
    , m_currentReply(nullptr)
{}

OllamaClient::~OllamaClient() {
    cancelRequest();
}

void OllamaClient::fetchModels(const QString& baseUrl) {
    QString urlStr = baseUrl;
    if (!urlStr.endsWith("/")) urlStr += "/";
    urlStr += "api/tags";

    QNetworkRequest request((QUrl(urlStr)));
    request.setTransferTimeout(5000);

    QNetworkReply* reply = m_networkManager->get(request);
    connect(reply, &QNetworkReply::finished, [this, reply]() {
        handleModelsFinished(reply);
    });
}

void OllamaClient::handleModelsFinished(QNetworkReply* reply) {
    reply->deleteLater();
    if (reply->error() != QNetworkReply::NoError) {
        emit errorOccurred("Failed to connect to Ollama: " + reply->errorString());
        emit modelsReceived(QStringList());
        return;
    }

    QByteArray data = reply->readAll();
    QJsonDocument doc = QJsonDocument::fromJson(data);
    if (!doc.isObject()) {
        emit modelsReceived(QStringList());
        return;
    }

    QStringList modelList;
    QJsonArray modelsArray = doc.object()["models"].toArray();
    for (const QJsonValue& val : modelsArray) {
        if (val.isObject()) {
            modelList.append(val.toObject()["name"].toString());
        }
    }

    emit modelsReceived(modelList);
}

void OllamaClient::sendChatRequest(const QString& baseUrl,
                                   const QString& model,
                                   const QJsonArray& messages,
                                   const QJsonObject& parameters) {
    cancelRequest();

    QString urlStr = baseUrl;
    if (!urlStr.endsWith("/")) urlStr += "/";
    urlStr += "api/chat";

    QNetworkRequest request((QUrl(urlStr)));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject payload;
    payload["model"] = model;
    payload["messages"] = messages;
    payload["stream"] = true;

    QJsonObject options;
    if (parameters.contains("temperature"))
        options["temperature"] = parameters["temperature"].toDouble();
    if (parameters.contains("top_p"))
        options["top_p"] = parameters["top_p"].toDouble();
    if (parameters.contains("max_tokens"))
        options["num_predict"] = parameters["max_tokens"].toInt();
    if (parameters.contains("repeat_penalty"))
        options["repeat_penalty"] = parameters["repeat_penalty"].toDouble();

    payload["options"] = options;

    QJsonDocument doc(payload);
    QByteArray body = doc.toJson(QJsonDocument::Compact);

    m_buffer.clear();
    m_currentReply = m_networkManager->post(request, body);

    connect(m_currentReply, &QNetworkReply::readyRead, this, &OllamaClient::handleChatReadyRead);
    connect(m_currentReply, &QNetworkReply::finished, this, &OllamaClient::handleChatFinished);
    connect(m_currentReply, &QNetworkReply::errorOccurred, this, &OllamaClient::handleChatError);
}

void OllamaClient::cancelRequest() {
    if (m_currentReply) {
        m_currentReply->abort();
        m_currentReply->deleteLater();
        m_currentReply = nullptr;
        emit finished();
    }
}

void OllamaClient::handleChatReadyRead() {
    if (!m_currentReply) return;

    m_buffer.append(m_currentReply->readAll());

    int newlinePos;
    while ((newlinePos = m_buffer.indexOf('\n')) != -1) {
        QByteArray line = m_buffer.left(newlinePos).trimmed();
        m_buffer.remove(0, newlinePos + 1);

        if (line.isEmpty()) continue;

        QJsonDocument doc = QJsonDocument::fromJson(line);
        if (doc.isObject()) {
            QJsonObject obj = doc.object();
            if (obj.contains("message") && obj["message"].isObject()) {
                QJsonObject msgObj = obj["message"].toObject();
                if (msgObj.contains("content")) {
                    QString content = msgObj["content"].toString();
                    if (!content.isEmpty()) {
                        emit chunkReceived(content);
                    }
                }
            }
        }
    }
}

void OllamaClient::handleChatFinished() {
    if (m_currentReply) {
        m_currentReply->deleteLater();
        m_currentReply = nullptr;
    }
    emit finished();
}

void OllamaClient::handleChatError(QNetworkReply::NetworkError code) {
    if (code != QNetworkReply::OperationCanceledError && m_currentReply) {
        emit errorOccurred(m_currentReply->errorString());
    }
}
