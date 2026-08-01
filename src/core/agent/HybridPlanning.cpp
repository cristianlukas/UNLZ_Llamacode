#include "HybridPlanning.h"

#include <QCryptographicHash>
#include <QJsonArray>
#include <QJsonDocument>

QJsonObject HybridPlanning::parsePlan(const QString &text, QString *error)
{
    QString clean = text.trimmed();
    if (clean.startsWith(QStringLiteral("```"))) {
        const int firstNl = clean.indexOf(QLatin1Char('\n'));
        const int lastFence = clean.lastIndexOf(QStringLiteral("```"));
        if (firstNl >= 0 && lastFence > firstNl)
            clean = clean.mid(firstNl + 1, lastFence - firstNl - 1).trimmed();
    }
    const int begin = clean.indexOf(QLatin1Char('{'));
    const int end = clean.lastIndexOf(QLatin1Char('}'));
    if (begin < 0 || end < begin) {
        if (error) *error = QStringLiteral("el plan no contiene un objeto JSON");
        return {};
    }
    QJsonParseError parseError;
    const QJsonDocument doc = QJsonDocument::fromJson(
        clean.mid(begin, end - begin + 1).toUtf8(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
        if (error) *error = QStringLiteral("JSON inválido: %1").arg(parseError.errorString());
        return {};
    }
    const QJsonObject plan = doc.object();
    if (!validatePlan(plan, error)) return {};
    return plan;
}

bool HybridPlanning::validatePlan(const QJsonObject &plan, QString *error)
{
    if (plan.value(QStringLiteral("schemaVersion")).toInt() != 1) {
        if (error) *error = QStringLiteral("schemaVersion debe ser 1");
        return false;
    }
    if (plan.value(QStringLiteral("goal")).toString().trimmed().isEmpty()) {
        if (error) *error = QStringLiteral("falta goal");
        return false;
    }
    for (const QString &key : {QStringLiteral("steps"), QStringLiteral("tests"),
                               QStringLiteral("risks"), QStringLiteral("doneWhen")}) {
        if (!plan.value(key).isArray()) {
            if (error) *error = QStringLiteral("%1 debe ser un array").arg(key);
            return false;
        }
    }
    if (plan.value(QStringLiteral("steps")).toArray().isEmpty()
        || plan.value(QStringLiteral("doneWhen")).toArray().isEmpty()) {
        if (error) *error = QStringLiteral("steps y doneWhen no pueden estar vacíos");
        return false;
    }
    if (QJsonDocument(plan).toJson(QJsonDocument::Compact).size() > 256 * 1024) {
        if (error) *error = QStringLiteral("plan demasiado grande");
        return false;
    }
    return true;
}

QString HybridPlanning::executorPrompt(const QString &request, const QJsonObject &plan)
{
    return QStringLiteral(
        "REQUEST ORIGINAL:\n%1\n\nPLAN ESTRUCTURADO DEL PLANIFICADOR (validalo contra la evidencia; "
        "si debés apartarte, registrá el motivo):\n%2\n\nEjecutá el trabajo completo, corré las "
        "verificaciones y respondé con el resultado final.")
        .arg(request.trimmed(), QString::fromUtf8(QJsonDocument(plan).toJson(QJsonDocument::Indented)));
}

QByteArray HybridPlanning::cacheKey(const QString &request, const QString &context,
                                    const QString &plannerId, int promptVersion)
{
    const QByteArray payload = request.toUtf8() + '\0' + context.toUtf8() + '\0'
        + plannerId.toUtf8() + '\0' + QByteArray::number(promptVersion);
    return QCryptographicHash::hash(payload, QCryptographicHash::Sha256).toHex();
}
