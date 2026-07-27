#include "AgentEfficiency.h"

#include <algorithm>
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

static double median(QList<double> values)
{
    if (values.isEmpty()) return 0.0;
    std::sort(values.begin(), values.end());
    const qsizetype middle = values.size() / 2;
    return values.size() % 2
        ? values.at(middle)
        : (values.at(middle - 1) + values.at(middle)) / 2.0;
}

QVariantMap AgentEfficiency::benchmarkComparison(const QVariantList &runs)
{
    QMap<QString, QVariantList> grouped;
    for (const QVariant &value : runs) {
        const QVariantMap run = value.toMap();
        const QString profileId = run.value(QStringLiteral("profileId")).toString().trimmed();
        if (!profileId.isEmpty())
            grouped[profileId].append(run);
    }

    QVariantList profiles;
    QMap<QString, QVariantMap> aggregateById;
    for (auto it = grouped.cbegin(); it != grouped.cend(); ++it) {
        const QVariantList profileRuns = it.value();
        QList<double> qualityPct;
        QList<double> elapsedSec;
        QList<double> firstAttemptSec;
        QList<double> repairAttempts;
        int successful = 0;
        int fullyAccepted = 0;
        int failed = 0;
        QString profileName;

        for (const QVariant &value : profileRuns) {
            const QVariantMap run = value.toMap();
            if (profileName.isEmpty())
                profileName = run.value(QStringLiteral("profileName")).toString()
                                      .section(QStringLiteral(" · pasada "), 0, 0);
            const bool runFailed = run.value(QStringLiteral("failed")).toBool();
            if (runFailed) {
                failed++;
                continue;
            }
            successful++;
            const int score = run.value(QStringLiteral("qualityScore")).toInt();
            const int total = run.value(QStringLiteral("qualityTotal")).toInt();
            if (total > 0) {
                qualityPct.append(100.0 * score / total);
                if (score >= total) fullyAccepted++;
            }
            const double elapsed = run.value(QStringLiteral("elapsedSec")).toDouble();
            if (elapsed > 0.0) elapsedSec.append(elapsed);
            const double first = run.value(QStringLiteral("timeToFirstAttempt")).toDouble();
            if (first > 0.0) firstAttemptSec.append(first);
            repairAttempts.append(run.value(QStringLiteral("repairAttempts")).toDouble());
        }

        const int totalRuns = profileRuns.size();
        const int majority = qMax(successful, failed);
        const auto minmaxQuality = std::minmax_element(qualityPct.cbegin(), qualityPct.cend());
        QVariantMap aggregate{
            {QStringLiteral("profileId"), it.key()},
            {QStringLiteral("profileName"), profileName},
            {QStringLiteral("runs"), totalRuns},
            {QStringLiteral("successfulRuns"), successful},
            {QStringLiteral("failedRuns"), failed},
            {QStringLiteral("fullyAcceptedRuns"), fullyAccepted},
            {QStringLiteral("successRatePct"), totalRuns > 0 ? 100.0 * successful / totalRuns : 0.0},
            {QStringLiteral("stabilityRatePct"), totalRuns > 0 ? 100.0 * majority / totalRuns : 0.0},
            {QStringLiteral("outcomeSpread"), successful > 0 && failed > 0},
            {QStringLiteral("medianQualityPct"), median(qualityPct)},
            {QStringLiteral("medianElapsedSec"), median(elapsedSec)},
            {QStringLiteral("medianFirstAttemptSec"), median(firstAttemptSec)},
            {QStringLiteral("medianRepairAttempts"), median(repairAttempts)}
        };
        aggregate[QStringLiteral("qualityRangePctPoints")] = qualityPct.isEmpty()
            ? 0.0 : *minmaxQuality.second - *minmaxQuality.first;
        profiles.append(aggregate);
        aggregateById.insert(it.key(), aggregate);
    }

    QVariantList comparisons;
    const QStringList ids = aggregateById.keys();
    for (qsizetype i = 0; i < ids.size(); ++i) {
        for (qsizetype j = i + 1; j < ids.size(); ++j) {
            const QVariantMap baseline = aggregateById.value(ids.at(i));
            const QVariantMap candidate = aggregateById.value(ids.at(j));
            const double baseTime = baseline.value(QStringLiteral("medianElapsedSec")).toDouble();
            const double candidateTime = candidate.value(QStringLiteral("medianElapsedSec")).toDouble();
            comparisons.append(QVariantMap{
                {QStringLiteral("baselineProfileId"), ids.at(i)},
                {QStringLiteral("candidateProfileId"), ids.at(j)},
                {QStringLiteral("qualityDeltaPctPoints"),
                 candidate.value(QStringLiteral("medianQualityPct")).toDouble()
                     - baseline.value(QStringLiteral("medianQualityPct")).toDouble()},
                {QStringLiteral("successRateDeltaPctPoints"),
                 candidate.value(QStringLiteral("successRatePct")).toDouble()
                     - baseline.value(QStringLiteral("successRatePct")).toDouble()},
                {QStringLiteral("elapsedChangePct"),
                 baseTime > 0.0 ? (candidateTime / baseTime - 1.0) * 100.0 : 0.0}
            });
        }
    }

    return {
        {QStringLiteral("schemaVersion"), 1},
        {QStringLiteral("runCount"), runs.size()},
        {QStringLiteral("profileCount"), profiles.size()},
        {QStringLiteral("profiles"), profiles},
        {QStringLiteral("comparisons"), comparisons}
    };
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
