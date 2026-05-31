#pragma once
#include "AgentTypes.h"
#include <QObject>
#include <QVariantList>

// Interfaz común para todos los runtimes de agente (opencode, goose, raw, ...).
// Cada backend es un QObject que gestiona su proceso/conexión y emite señales
// que AppController repropaga a QML. La UI nunca conoce el backend concreto.
class IAgentBackend : public QObject
{
    Q_OBJECT
public:
    explicit IAgentBackend(QObject *parent = nullptr) : QObject(parent) {}
    ~IAgentBackend() override = default;

    virtual QString adapter() const = 0;
    virtual bool running() const = 0;

    // Ciclo de vida
    virtual void start(const AgentContext &ctx) = 0;
    virtual void stop() = 0;

    // Conversación
    virtual void sendMessage(const QString &text) = 0;
    virtual void cancelGeneration() {}

    // Sesiones (no todos los backends las soportan; default: no-op)
    virtual void newSession() {}
    virtual void newSessionInProject(const QString &projectDir) { Q_UNUSED(projectDir) }
    virtual void switchSession(const QString &sessionId) { Q_UNUSED(sessionId) }
    virtual void renameSession(const QString &sessionId, const QString &title)
        { Q_UNUSED(sessionId) Q_UNUSED(title) }
    virtual void deleteSession(const QString &sessionId) { Q_UNUSED(sessionId) }
    virtual void forkSession(const QString &sessionId) { Q_UNUSED(sessionId) }
    virtual void refreshSessions() {}

    // Aprobación de herramientas (human-in-the-loop)
    virtual void approveTool(const QString &id, bool always = false)
        { Q_UNUSED(id) Q_UNUSED(always) }
    virtual void rejectTool(const QString &id) { Q_UNUSED(id) }

    // Estado expuesto a la UI
    virtual QString currentSessionId() const { return {}; }
    virtual QString currentSessionTitle() const { return {}; }
    virtual QString currentProjectDir() const { return {}; }
    virtual QVariantList messages() const { return {}; }
    virtual QVariantList sessions() const { return {}; }

signals:
    void runningChanged();
    void messagesChanged();
    void sessionsChanged();
    void logAppended(const QString &chunk);
    void toolApprovalNeeded(const QVariantMap &toolCall);
    void errorOccurred(const QString &message);
};
