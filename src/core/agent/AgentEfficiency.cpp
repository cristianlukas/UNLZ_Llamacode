#include "AgentEfficiency.h"

#include <QtMath>

static double firstNumber(const QJsonObject &a, const QJsonObject &b,
                          const QStringList &keys)
{
    for (const QString &key : keys) {
        if (a.value(key).isDouble()) return a.value(key).toDouble();
        if (b.value(key).isDouble()) return b.value(key).toDouble();
    }
    return 0.0;
}

QVariantMap AgentEfficiency::Request::toVariant() const
{
    return {{QStringLiteral("phase"), phase},
            {QStringLiteral("promptTokens"), promptTokens},
            {QStringLiteral("generatedTokens"), generatedTokens},
            {QStringLiteral("promptMs"), promptMs},
            {QStringLiteral("generatedMs"), generatedMs},
            {QStringLiteral("wallMs"), wallMs},
            {QStringLiteral("toolCalls"), toolCalls},
            {QStringLiteral("toolBytes"), toolBytes}};
}

AgentEfficiency::Request AgentEfficiency::Request::fromResponse(
    const QJsonObject &root, const QString &phaseName, double elapsed)
{
    const QJsonObject timings = root.value(QStringLiteral("timings")).toObject();
    const QJsonObject usage = root.value(QStringLiteral("usage")).toObject();
    Request r;
    r.phase = AgentEfficiency::normalizedPhase(phaseName);
    r.promptTokens = qRound(firstNumber(timings, usage,
        {QStringLiteral("prompt_n"), QStringLiteral("prompt_tokens")}));
    r.generatedTokens = qRound(firstNumber(timings, usage,
        {QStringLiteral("predicted_n"), QStringLiteral("completion_tokens")}));
    r.promptMs = firstNumber(timings, root, {QStringLiteral("prompt_ms")});
    r.generatedMs = firstNumber(timings, root, {QStringLiteral("predicted_ms")});
    r.wallMs = qMax(0.0, elapsed);
    return r;
}

QVariantMap AgentEfficiency::summarize(const QVariantList &requests)
{
    QVariantMap out{{QStringLiteral("requests"), requests.size()}};
    qint64 prompt = 0, generated = 0, toolBytes = 0;
    int tools = 0;
    double promptMs = 0.0, generatedMs = 0.0, wallMs = 0.0;
    QVariantMap phases;
    for (const QVariant &v : requests) {
        const QVariantMap r = v.toMap();
        prompt += r.value(QStringLiteral("promptTokens")).toLongLong();
        generated += r.value(QStringLiteral("generatedTokens")).toLongLong();
        promptMs += r.value(QStringLiteral("promptMs")).toDouble();
        generatedMs += r.value(QStringLiteral("generatedMs")).toDouble();
        wallMs += r.value(QStringLiteral("wallMs")).toDouble();
        tools += r.value(QStringLiteral("toolCalls")).toInt();
        toolBytes += r.value(QStringLiteral("toolBytes")).toLongLong();
        const QString phase = normalizedPhase(r.value(QStringLiteral("phase")).toString());
        QVariantMap p = phases.value(phase).toMap();
        p[QStringLiteral("requests")] = p.value(QStringLiteral("requests")).toInt() + 1;
        p[QStringLiteral("promptTokens")] = p.value(QStringLiteral("promptTokens")).toLongLong()
                                               + r.value(QStringLiteral("promptTokens")).toLongLong();
        p[QStringLiteral("wallMs")] = p.value(QStringLiteral("wallMs")).toDouble()
                                      + r.value(QStringLiteral("wallMs")).toDouble();
        phases[phase] = p;
    }
    out[QStringLiteral("promptTokens")] = prompt;
    out[QStringLiteral("generatedTokens")] = generated;
    out[QStringLiteral("promptMs")] = promptMs;
    out[QStringLiteral("generatedMs")] = generatedMs;
    out[QStringLiteral("wallMs")] = wallMs;
    out[QStringLiteral("toolCalls")] = tools;
    out[QStringLiteral("toolBytes")] = toolBytes;
    out[QStringLiteral("phases")] = phases;
    return out;
}

QVariantMap AgentEfficiency::compare(const QVariantMap &base, const QVariantMap &candidate)
{
    QVariantMap out;
    for (const QString &key : {QStringLiteral("promptTokens"), QStringLiteral("generatedTokens"),
                               QStringLiteral("promptMs"), QStringLiteral("wallMs"),
                               QStringLiteral("toolCalls"), QStringLiteral("toolBytes")}) {
        const double a = base.value(key).toDouble();
        const double b = candidate.value(key).toDouble();
        out[key + QStringLiteral("Delta")] = b - a;
        out[key + QStringLiteral("ChangePct")] = a > 0.0 ? ((b - a) * 100.0 / a) : 0.0;
    }
    return out;
}

QString AgentEfficiency::normalizedPhase(const QString &phase)
{
    const QString p = phase.trimmed().toLower();
    if (p == QLatin1String("explore") || p == QLatin1String("explorar")) return QStringLiteral("explore");
    if (p == QLatin1String("plan") || p == QLatin1String("planificar")) return QStringLiteral("plan");
    if (p == QLatin1String("execute") || p == QLatin1String("ejecutar")) return QStringLiteral("execute");
    if (p == QLatin1String("verify") || p == QLatin1String("verificar")) return QStringLiteral("verify");
    return p.isEmpty() ? QStringLiteral("general") : p;
}
