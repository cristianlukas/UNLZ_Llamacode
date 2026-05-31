#pragma once
#include "IAgentBackend.h"
#include <QProcess>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <functional>

// Backend opencode: lanza `opencode serve` (headless) y habla por HTTP + SSE.
class OpencodeBackend : public IAgentBackend
{
    Q_OBJECT
public:
    explicit OpencodeBackend(QObject *parent = nullptr);
    ~OpencodeBackend() override;

    QString adapter() const override { return QStringLiteral("opencode"); }
    bool running() const override;

    void start(const AgentContext &ctx) override;
    void stop() override;
    void sendMessage(const QString &text) override;

    void newSession() override;
    void newSessionInProject(const QString &projectDir) override;
    void switchSession(const QString &sessionId) override;
    void renameSession(const QString &sessionId, const QString &title) override;
    void deleteSession(const QString &sessionId) override;
    void forkSession(const QString &sessionId) override;
    void refreshSessions() override;

    QString currentSessionId() const override { return m_sessionId; }
    QString currentSessionTitle() const override { return m_sessionTitle; }
    QString currentProjectDir() const override;
    QVariantList messages() const override { return m_messages; }
    QVariantList sessions() const override { return m_sessions; }

private:
    void launchProcess();
    void initSession();
    void loadSessionList(std::function<void()> then);
    void resumeOrCreateSession();
    void doCreateSession();
    void loadSessionMessages(const QString &sessionId);
    void subscribeEvents();
    void respondPermission(const QString &sessionId, const QString &permissionId);
    static QString projectNameFromDir(const QString &dir);

    QNetworkAccessManager *m_nam = nullptr;
    QProcess  *m_proc = nullptr;
    QNetworkReply *m_eventReply = nullptr;
    QString    m_attachUrl = QStringLiteral("http://127.0.0.1:4096");
    AgentContext m_ctx;
    QString    m_sessionId;
    QString    m_sessionTitle;
    QVariantList m_messages;
    QVariantList m_sessions;
    int        m_curAsstIdx = -1;
    bool       m_stopping = false;
    bool       m_forceNew = false;
};
