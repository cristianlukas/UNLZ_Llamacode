#include "ToolExecutionSafety.h"

#include <QCryptographicHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonValue>
#include <QRegularExpression>
#include <QUrl>
#include <algorithm>

namespace {

QJsonValue canonicalValue(const QJsonValue &value)
{
    if (value.isArray()) {
        QJsonArray out;
        for (const QJsonValue &item : value.toArray())
            out.append(canonicalValue(item));
        return out;
    }
    if (!value.isObject()) return value;

    const QJsonObject object = value.toObject();
    QStringList keys = object.keys();
    std::sort(keys.begin(), keys.end());
    QJsonObject out;
    for (const QString &key : keys)
        out.insert(key, canonicalValue(object.value(key)));
    return out;
}

bool looksReadOnly(const QString &text)
{
    static const QStringList verbs{
        QStringLiteral("get"), QStringLiteral("list"), QStringLiteral("read"),
        QStringLiteral("search"), QStringLiteral("find"), QStringLiteral("fetch"),
        QStringLiteral("query"), QStringLiteral("inspect"), QStringLiteral("describe")
    };
    for (const QString &verb : verbs)
        if (text.startsWith(verb + QLatin1Char('_')) || text == verb) return true;
    return false;
}

QString foldDesktopVerificationText(const QString &text)
{
    const QString decomposed = text.normalized(QString::NormalizationForm_D);
    QString folded;
    folded.reserve(decomposed.size());
    for (const QChar c : decomposed) {
        if (c.category() != QChar::Mark_NonSpacing)
            folded.append(c.toLower());
    }
    return folded.simplified();
}

} // namespace

namespace ToolExecutionSafety {

Contract fromMcpTool(const QString &name, const QString &description,
                     const QJsonObject &annotations)
{
    Contract c;
    const QJsonObject lc = annotations.value(QStringLiteral("llamacode")).toObject();
    const QString explicitEffect = lc.value(QStringLiteral("effect")).toString();
    if (explicitEffect == QLatin1String("read")
        || explicitEffect == QLatin1String("proposal")
        || explicitEffect == QLatin1String("external_write")) {
        c.effect = explicitEffect;
        c.source = QStringLiteral("llamacode_annotation");
    } else if (annotations.value(QStringLiteral("readOnlyHint")).toBool(false)) {
        c.effect = QStringLiteral("read");
        c.source = QStringLiteral("mcp_annotation");
    } else if (looksReadOnly(name.trimmed().toLower())
               && description.contains(QStringLiteral("read-only"), Qt::CaseInsensitive)) {
        // La heurística sólo relaja permisos cuando nombre Y descripción coinciden.
        c.effect = QStringLiteral("read");
        c.source = QStringLiteral("strong_heuristic");
    }

    c.destructive = annotations.value(QStringLiteral("destructiveHint")).toBool(false)
                    || lc.value(QStringLiteral("destructive")).toBool(false);
    c.idempotent = annotations.value(QStringLiteral("idempotentHint")).toBool(false)
                   || lc.value(QStringLiteral("idempotent")).toBool(false);
    c.openWorld = annotations.value(QStringLiteral("openWorldHint")).toBool(true);
    c.approvalRequired = c.effect != QLatin1String("read");
    if (lc.contains(QStringLiteral("approvalRequired")))
        c.approvalRequired = lc.value(QStringLiteral("approvalRequired")).toBool(true);
    if (c.destructive) c.approvalRequired = true;
    const QString receipt = lc.value(QStringLiteral("receipt")).toString();
    if (!receipt.isEmpty()) c.receipt = receipt;
    return c;
}

bool requiresWorkspaceMutationPaths(const QString &name, const QString &description,
                                    const QJsonObject &inputSchema,
                                    const QJsonObject &annotations,
                                    const QJsonObject &arguments,
                                    const QString &effect)
{
    const QJsonObject lc = annotations.value(QStringLiteral("llamacode")).toObject();
    if (lc.contains(QStringLiteral("workspaceMutation")))
        return lc.value(QStringLiteral("workspaceMutation")).toBool();
    if (effect.compare(QStringLiteral("read"), Qt::CaseInsensitive) == 0)
        return false;

    const QString identity = (name + QLatin1Char(' ') + description).toLower();
    const QJsonObject properties = inputSchema.value(QStringLiteral("properties")).toObject();
    const bool browserCapability = identity.contains(QStringLiteral("browser"))
        || identity.contains(QStringLiteral("playwright"))
        || identity.contains(QStringLiteral("web page"))
        || (properties.contains(QStringLiteral("url"))
            && (properties.contains(QStringLiteral("target"))
                || properties.contains(QStringLiteral("selector"))
                || properties.contains(QStringLiteral("ref"))));
    if (!browserCapability) return true; // tools desconocidas: mantener el default cerrado

    // Browser MCPs can create local artifacts only when the call supplies a
    // destination that the schema identifies as a saved/output file.
    for (auto it = arguments.constBegin(); it != arguments.constEnd(); ++it) {
        if (it.value().isNull() || it.value().toString().trimmed().isEmpty()) continue;
        const QJsonObject property = properties.value(it.key()).toObject();
        const QString key = it.key().toLower();
        const QString parameterDescription = property.value(QStringLiteral("description"))
                                                 .toString().toLower();
        const bool outputPathName = key.contains(QStringLiteral("output_path"))
            || key.contains(QStringLiteral("save_path"))
            || key.contains(QStringLiteral("download_path"))
            || key == QLatin1String("filename");
        const bool describesWorkspaceOutput =
            (parameterDescription.contains(QStringLiteral("workspace"))
             || parameterDescription.contains(QStringLiteral("local file")))
            && (parameterDescription.contains(QStringLiteral("save"))
                || parameterDescription.contains(QStringLiteral("write"))
                || parameterDescription.contains(QStringLiteral("output")));
        if (outputPathName || describesWorkspaceOutput) return true;
    }
    return false;
}

bool isBrowserNavigationCall(const QString &name, const QString &description,
                             const QJsonObject &inputSchema,
                             const QJsonObject &arguments)
{
    const QString identity = (name + QLatin1Char(' ') + description).toLower();
    const bool browserCapability = identity.contains(QStringLiteral("browser"))
        || identity.contains(QStringLiteral("playwright"))
        || identity.contains(QStringLiteral("web page"));
    if (!browserCapability) return false;

    const bool navigation = identity.contains(QStringLiteral("navigate"))
        || identity.contains(QStringLiteral("navigation"))
        || identity.contains(QStringLiteral("goto"))
        || identity.contains(QStringLiteral("go to url"))
        || identity.contains(QStringLiteral("open_url"))
        || identity.contains(QStringLiteral("open url"))
        || identity.contains(QStringLiteral("visit"));
    if (!navigation) return false;

    const QJsonObject properties = inputSchema.value(QStringLiteral("properties")).toObject();
    for (auto it = properties.constBegin(); it != properties.constEnd(); ++it) {
        const QString key = it.key().toLower();
        if (key != QLatin1String("url") && key != QLatin1String("uri")
            && key != QLatin1String("href") && key != QLatin1String("target_url"))
            continue;
        if (arguments.value(it.key()).isString())
            return !arguments.value(it.key()).toString().trimmed().isEmpty();
    }
    return false;
}

namespace {
QString navigationUrlArgument(const QJsonObject &inputSchema,
                              const QJsonObject &arguments)
{
    const QJsonObject properties = inputSchema.value(QStringLiteral("properties")).toObject();
    for (auto it = properties.constBegin(); it != properties.constEnd(); ++it) {
        const QString key = it.key().toLower();
        if (key != QLatin1String("url") && key != QLatin1String("uri")
            && key != QLatin1String("href") && key != QLatin1String("target_url"))
            continue;
        const QString value = arguments.value(it.key()).toString().trimmed();
        if (!value.isEmpty()) return value;
    }
    return {};
}
} // namespace

QString browserNavigationPolicyError(const QString &name, const QString &description,
                                     const QJsonObject &inputSchema,
                                     const QJsonObject &arguments)
{
    if (!isBrowserNavigationCall(name, description, inputSchema, arguments)) return {};
    const QString raw = navigationUrlArgument(inputSchema, arguments);
    const QUrl url(raw, QUrl::StrictMode);
    if (!url.isValid() || url.isRelative() || url.host().isEmpty())
        return QStringLiteral("la URL de navegación no es absoluta o válida");
    const QString scheme = url.scheme().toLower();
    if (scheme != QLatin1String("http") && scheme != QLatin1String("https"))
        return QStringLiteral("sólo se permite navegar a destinos HTTP o HTTPS");
    if (!url.userInfo().isEmpty())
        return QStringLiteral("no se permite navegar con credenciales embebidas en la URL");
    return {};
}

QString browserNavigationApprovalOrigin(const QString &name, const QString &description,
                                       const QJsonObject &inputSchema,
                                       const QJsonObject &arguments)
{
    if (!isBrowserNavigationCall(name, description, inputSchema, arguments)) return {};
    const QUrl url(navigationUrlArgument(inputSchema, arguments), QUrl::StrictMode);
    if (!url.isValid() || url.host().isEmpty())
        return QStringLiteral("destino no validado");
    QString origin = url.scheme().toLower() + QStringLiteral("://") + url.host();
    const int port = url.port(-1);
    const bool defaultPort = (url.scheme().compare(QStringLiteral("http"), Qt::CaseInsensitive) == 0
                               && port == 80)
        || (url.scheme().compare(QStringLiteral("https"), Qt::CaseInsensitive) == 0
            && port == 443);
    if (port > 0 && !defaultPort) {
        origin += QLatin1Char(':');
        origin += QString::number(port);
    }
    return origin;
}

void McpVerificationGate::recordAction(const QString &server, bool succeeded,
                                       bool verifiedReceipt)
{
    const QString key = server.trimmed();
    if (key.isEmpty() || !succeeded) return;
    if (!verifiedReceipt) m_pendingServers.insert(key);
}

void McpVerificationGate::recordObservation(const QString &server, bool succeeded,
                                            bool readOnly)
{
    const QString key = server.trimmed();
    if (!key.isEmpty() && succeeded && readOnly) {
        m_pendingServers.remove(key);
        if (key == QLatin1String("desktop")) m_observationToolRequested = false;
    }
}

void McpVerificationGate::requestObservationTool()
{
    m_observationToolRequested = m_pendingServers.contains(QStringLiteral("desktop"));
}

bool McpVerificationGate::requiresDesktopObservationTool() const
{
    return m_observationToolRequested
        && m_pendingServers.contains(QStringLiteral("desktop"));
}

QStringList McpVerificationGate::pendingServers() const
{
    QStringList servers = m_pendingServers.values();
    std::sort(servers.begin(), servers.end());
    return servers;
}

QString McpVerificationGate::observationPrompt() const
{
    const QStringList pending = pendingServers();
    const QString targets = pending.join(QStringLiteral(", "));
    QString prompt = QStringLiteral(
        "No declares la tarea completada: hay efectos sin verificación posterior en: %1. ")
                         .arg(targets);
    if (pending.contains(QStringLiteral("desktop"))) {
        prompt += QStringLiteral(
            "Tu siguiente llamada de herramienta debe ser sólo de lectura: ejecuta "
            "desktop_read_text una vez con el target_id literal de la ventana exacta que "
            "acabás de usar. Si ese target ya no existe, consulta desktop_windows una vez, "
            "resuelve la ventana exacta y luego léela. Si falta evidencia, usa "
            "desktop_controls o desktop_snapshot. No pulses teclas, escribas ni hagas clic "
            "hasta terminar esa observación. Esta lectura es un checkpoint intermedio, no el "
            "final de la tarea. Después continúa con el siguiente paso pendiente de la solicitud "
            "original; no respondas final si aún falta guardar, cerrar o verificar otro efecto.");
    }
    QStringList mcpServers = pending;
    mcpServers.removeAll(QStringLiteral("desktop"));
    if (!mcpServers.isEmpty()) {
        prompt += QStringLiteral(
            "Para MCP, usa una tool de sólo lectura del mismo servidor pendiente: %1. ")
                      .arg(mcpServers.join(QStringLiteral(", ")));
    }
    prompt += QStringLiteral(
        "Compara lo observado con el objetivo del usuario. Si no hay lectura disponible, "
        "informa que quedó sin verificar. Esta lectura es un checkpoint intermedio: después "
        "continúa los pasos pendientes de la solicitud original y no declares completa una "
        "tarea que todavía tenga acciones pedidas sin realizar. No repitas una escritura sólo "
        "para comprobarla.");
    return prompt;
}

McpVerificationGate::CompletionDecision
McpVerificationGate::completionDecision(int nudges, int maxNudges) const
{
    if (!hasPending()) return CompletionDecision::Allow;
    return nudges < qMax(0, maxNudges)
        ? CompletionDecision::RequestObservation : CompletionDecision::Block;
}

void DesktopActionSafetyGate::recordFailedVerification(const QString &expectedText,
                                                      const QString &conditionKey)
{
    const QString foldedExpected = foldDesktopVerificationText(expectedText);
    if (!m_verificationFailed && m_actionPendingVerification && !foldedExpected.isEmpty()
        && foldDesktopVerificationText(m_lastTextObservation).contains(foldedExpected)) {
        recordVerified(conditionKey);
        return;
    }
    m_verificationFailed = true;
    m_expectedText = expectedText.trimmed();
    m_failedConditionKey = conditionKey;
}

void DesktopActionSafetyGate::recordVerified(const QString &conditionKey)
{
    const bool resolvesFailedCondition = !m_verificationFailed
        || (!m_failedConditionKey.isEmpty() && conditionKey == m_failedConditionKey);
    if (!resolvesFailedCondition)
        return;
    m_verificationFailed = false;
    m_expectedText.clear();
    m_failedConditionKey.clear();
    m_actionPendingVerification = false;
    m_lastTextObservation.clear();
    m_staleRetryPending = false;
    m_staleObservationDone = false;
    m_staleRetryBlocked = false;
}

void DesktopActionSafetyGate::recordObservation()
{
    if (m_staleRetryPending)
        m_staleObservationDone = true;
}

void DesktopActionSafetyGate::recordTextObservation(bool succeeded, const QString &text)
{
    if (!succeeded) return;
    m_lastTextObservation = text;
    if (!m_verificationFailed || m_expectedText.isEmpty()) return;
    const QString expected = foldDesktopVerificationText(m_expectedText);
    if (!expected.isEmpty() && foldDesktopVerificationText(text).contains(expected)) {
        m_verificationFailed = false;
        m_expectedText.clear();
        m_failedConditionKey.clear();
        m_actionPendingVerification = false;
        m_lastTextObservation.clear();
        m_staleRetryPending = false;
        m_staleObservationDone = false;
        m_staleRetryBlocked = false;
    }
}

void DesktopActionSafetyGate::recordActionResult(bool succeeded, bool staleOrAmbiguous)
{
    if (staleOrAmbiguous) {
        if (m_staleRetryPending) {
            m_staleRetryPending = false;
            m_staleObservationDone = false;
            m_staleRetryBlocked = true;
        } else {
            m_staleRetryPending = true;
            m_staleObservationDone = false;
        }
        return;
    }
    m_actionPendingVerification = true;
    m_lastTextObservation.clear();
    if (!m_staleRetryPending)
        return;

    const bool wasReobserved = m_staleObservationDone;
    m_staleRetryPending = false;
    m_staleObservationDone = false;
    if (!succeeded || !wasReobserved)
        m_staleRetryBlocked = true;
}

void DesktopActionSafetyGate::clear()
{
    m_verificationFailed = false;
    m_expectedText.clear();
    m_failedConditionKey.clear();
    m_actionPendingVerification = false;
    m_lastTextObservation.clear();
    m_staleRetryPending = false;
    m_staleObservationDone = false;
    m_staleRetryBlocked = false;
}

void DesktopActionRepeatGuard::recordAction(const QString &actionSignature,
                                            const QString &observationKey)
{
    if (actionSignature.isEmpty() || observationKey.isEmpty()) {
        clearPending();
        return;
    }
    m_pendingActionSignature = actionSignature;
    m_pendingObservationKey = observationKey;
    m_pendingStateFingerprint = m_observationFingerprints.value(observationKey);
}

void DesktopActionRepeatGuard::blockAction(const QString &actionSignature,
                                           const QString &observationKey)
{
    if (!actionSignature.isEmpty()) {
        m_blockedActionSignatures.insert(actionSignature);
        if (!observationKey.isEmpty())
            m_blockedObservationKeysByAction.insert(actionSignature, observationKey);
    }
}

void DesktopActionRepeatGuard::recordObservation(const QString &observationKey,
                                                 const QString &state)
{
    if (observationKey.isEmpty()) return;
    QString stableState = state;
    stableState.remove(QRegularExpression(QStringLiteral("(?m)^receipt_id=[^\\r\\n]*(?:\\r?\\n|$)")));
    const QString fingerprint = resultHash(stableState);
    const QString previousFingerprint = m_observationFingerprints.value(observationKey);
    if (!previousFingerprint.isEmpty() && previousFingerprint != fingerprint) {
        const auto blocked = m_blockedObservationKeysByAction;
        for (auto it = blocked.cbegin(); it != blocked.cend(); ++it) {
            if (it.value() == observationKey) {
                m_blockedActionSignatures.remove(it.key());
                m_blockedObservationKeysByAction.remove(it.key());
            }
        }
    }
    if (!m_pendingActionSignature.isEmpty()
        && m_pendingObservationKey == observationKey) {
        if (!m_pendingStateFingerprint.isEmpty()
            && m_pendingStateFingerprint == fingerprint) {
            m_blockedActionSignatures.insert(m_pendingActionSignature);
            m_blockedObservationKeysByAction.insert(m_pendingActionSignature, observationKey);
        } else {
            m_blockedActionSignatures.remove(m_pendingActionSignature);
            m_blockedObservationKeysByAction.remove(m_pendingActionSignature);
        }
        m_pendingActionSignature.clear();
        m_pendingObservationKey.clear();
        m_pendingStateFingerprint.clear();
    }
    m_observationFingerprints.insert(observationKey, fingerprint);
}

void DesktopActionRepeatGuard::clearPending()
{
    m_pendingActionSignature.clear();
    m_pendingObservationKey.clear();
    m_pendingStateFingerprint.clear();
}

void DesktopActionRepeatGuard::clear()
{
    clearPending();
    m_observationFingerprints.clear();
    m_blockedObservationKeysByAction.clear();
    m_blockedActionSignatures.clear();
}

QVariantMap toVariantMap(const Contract &c)
{
    return {
        {QStringLiteral("effect"), c.effect},
        {QStringLiteral("approvalRequired"), c.approvalRequired},
        {QStringLiteral("destructive"), c.destructive},
        {QStringLiteral("idempotent"), c.idempotent},
        {QStringLiteral("openWorld"), c.openWorld},
        {QStringLiteral("receipt"), c.receipt},
        {QStringLiteral("source"), c.source}
    };
}

QByteArray canonicalJson(const QJsonObject &object)
{
    return QJsonDocument(canonicalValue(object).toObject()).toJson(QJsonDocument::Compact);
}

QString desktopActionRepeatSignature(const QString &tool, QJsonObject arguments)
{
    arguments.remove(QStringLiteral("snapshot_id"));
    return tool.trimmed().toLower() + QLatin1Char('|')
        + QString::fromUtf8(canonicalJson(arguments));
}

QString payloadHash(const QString &server, const QString &tool,
                    const QJsonObject &arguments)
{
    const QByteArray payload = server.toUtf8() + '\0' + tool.toUtf8() + '\0'
                               + canonicalJson(arguments);
    return QString::fromLatin1(QCryptographicHash::hash(payload, QCryptographicHash::Sha256).toHex());
}

QString idempotencyKey(const QString &correlationId, const QString &hash)
{
    return QStringLiteral("lc_%1").arg(QString::fromLatin1(QCryptographicHash::hash(
        correlationId.toUtf8() + '\0' + hash.toUtf8(),
        QCryptographicHash::Sha256).toHex()));
}

QString resultHash(const QString &result)
{
    return QString::fromLatin1(QCryptographicHash::hash(result.toUtf8(),
                                                         QCryptographicHash::Sha256).toHex());
}

} // namespace ToolExecutionSafety
