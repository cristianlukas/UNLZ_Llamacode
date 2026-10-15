#pragma once

#include <QJsonObject>
#include <QSet>
#include <QString>
#include <QStringList>
#include <QVariantMap>

// Contrato uniforme para tools externas. MCP annotations es opcional; cuando un
// server no declara efectos, la politica es deliberadamente conservadora.
namespace ToolExecutionSafety {

struct Contract {
    QString effect = QStringLiteral("external_write"); // read|proposal|external_write
    bool approvalRequired = true;
    bool destructive = false;
    bool idempotent = false;
    bool openWorld = true;
    QString receipt = QStringLiteral("result_hash");
    QString source = QStringLiteral("conservative_default");
};

Contract fromMcpTool(const QString &name, const QString &description,
                     const QJsonObject &annotations);
// changed_paths coordina mutaciones del workspace, no cualquier efecto externo.
// MCP browser actions remain subject to approval, but only require paths when
// the call actually names a workspace output file.
bool requiresWorkspaceMutationPaths(const QString &name, const QString &description,
                                    const QJsonObject &inputSchema,
                                    const QJsonObject &annotations,
                                    const QJsonObject &arguments,
                                    const QString &effect);
bool isBrowserNavigationCall(const QString &name, const QString &description,
                             const QJsonObject &inputSchema,
                             const QJsonObject &arguments);
QString browserNavigationPolicyError(const QString &name, const QString &description,
                                     const QJsonObject &inputSchema,
                                     const QJsonObject &arguments);
QString browserNavigationApprovalOrigin(const QString &name, const QString &description,
                                       const QJsonObject &inputSchema,
                                       const QJsonObject &arguments);

// Una escritura MCP no equivale a estado confirmado. La tarea conserva cada
// servidor con efectos externos pendientes hasta una lectura posterior del
// mismo servidor o un recibo explícito con status=verified.
class McpVerificationGate
{
public:
    enum class CompletionDecision { Allow, RequestObservation, Block };
    void recordAction(const QString &server, bool succeeded, bool verifiedReceipt);
    void recordObservation(const QString &server, bool succeeded, bool readOnly);
    bool hasPending() const { return !m_pendingServers.isEmpty(); }
    QStringList pendingServers() const;
    CompletionDecision completionDecision(int nudges, int maxNudges) const;
    void clear() { m_pendingServers.clear(); }

private:
    QSet<QString> m_pendingServers;
};

// Protege las acciones de escritorio después de una verificación fallida y
// limita a una acción la recuperación de un target obsoleto/ambiguo por turno.
class DesktopActionSafetyGate
{
public:
    bool blocksActions() const { return m_verificationFailed || m_staleRetryBlocked; }
    bool needsFreshObservation() const
    { return m_staleRetryPending && !m_staleObservationDone; }
    bool needsBlockedCompletion() const
    { return m_verificationFailed || m_staleRetryPending || m_staleRetryBlocked; }
    bool hasUnverifiedAction() const { return m_actionPendingVerification; }

    void recordFailedVerification(const QString &expectedText = {},
                                 const QString &conditionKey = {});
    void recordVerified(const QString &conditionKey = {});
    void recordObservation();
    void recordTextObservation(bool succeeded, const QString &text);
    void recordActionResult(bool succeeded, bool staleOrAmbiguous);
    void clear();

private:
    bool m_verificationFailed = false;
    QString m_expectedText;
    QString m_failedConditionKey;
    bool m_actionPendingVerification = false;
    QString m_lastTextObservation;
    bool m_staleRetryPending = false;
    bool m_staleObservationDone = false;
    bool m_staleRetryBlocked = false;
};

QVariantMap toVariantMap(const Contract &contract);

// JSON canonico (claves ordenadas recursivamente) para ligar aprobación,
// idempotencia y recibos al payload exacto.
QByteArray canonicalJson(const QJsonObject &object);
QString payloadHash(const QString &server, const QString &tool,
                    const QJsonObject &arguments);
QString idempotencyKey(const QString &correlationId, const QString &payloadHash);
QString resultHash(const QString &result);

} // namespace ToolExecutionSafety
