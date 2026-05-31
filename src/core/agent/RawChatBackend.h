#pragma once
#include "IAgentBackend.h"
#include <QHash>
#include <QNetworkAccessManager>
#include <QNetworkReply>

// Backend "raw": chat directo a llama-server /v1/chat/completions (stream SSE).
// No lanza proceso externo; usa sesiones locales en memoria.
class RawChatBackend : public IAgentBackend
{
    Q_OBJECT
public:
    explicit RawChatBackend(QObject *parent = nullptr);
    ~RawChatBackend() override;

    QString adapter() const override { return QStringLiteral("raw"); }
    bool running() const override { return m_running; }

    void start(const AgentContext &ctx) override;
    void stop() override;
    void sendMessage(const QString &text) override;
    void cancelGeneration() override;

    void newSession() override;
    void newSessionInProject(const QString &projectDir) override;
    void switchSession(const QString &sessionId) override;
    void renameSession(const QString &sessionId, const QString &title) override;
    void deleteSession(const QString &sessionId) override;
    void forkSession(const QString &sessionId) override;
    void refreshSessions() override;

    QString currentSessionId() const override { return m_sessionId; }
    QString currentSessionTitle() const override { return m_sessionTitle; }
    QString currentProjectDir() const override { return m_projectDir; }
    QVariantList messages() const override { return m_messages; }
    QVariantList sessions() const override { return m_sessions; }
    bool updateSessionProject(const QString &sessionId, const QString &projectId,
                              const QString &projectName, const QString &projectDir = QString());
    bool renameProject(const QString &oldName, const QString &newName);

private:
    void createSession(const QString &projectDir);
    void createSession(const QString &projectId, const QString &projectName, const QString &projectDir);
    void setCurrentSession(const QString &sessionId);
    void saveCurrentMessages();
    QVariantList loadMessagesForSession(const QString &sessionId) const;

    AgentContext m_ctx;
    QNetworkAccessManager *m_nam = nullptr;
    QNetworkReply *m_reply = nullptr;
    bool m_running = false;
    bool m_stopping = false;

    QString m_sessionId;
    QString m_sessionTitle;
    QString m_projectDir;
    QVariantList m_messages;
    QVariantList m_sessions;
    QHash<QString, QVariantList> m_sessionMessages;
    int m_curAsstIdx = -1;
    QByteArray m_sseBuf;
};
