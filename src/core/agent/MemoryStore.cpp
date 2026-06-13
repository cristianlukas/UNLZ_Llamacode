#include "MemoryStore.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QDateTime>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QSet>
#include <algorithm>

namespace {

QString normScope(const QString &s)
{
    const QString v = s.trimmed().toLower();
    if (v == QLatin1String("session") || v == QLatin1String("project")
        || v == QLatin1String("personal"))
        return v;
    return QStringLiteral("project");   // default: lo más útil para coding
}

QString normType(const QString &t)
{
    const QString v = t.trimmed().toLower();
    static const QSet<QString> ok{QStringLiteral("preference"), QStringLiteral("decision"),
                                  QStringLiteral("fact"), QStringLiteral("bug"),
                                  QStringLiteral("other")};
    return ok.contains(v) ? v : QStringLiteral("fact");
}

// Tokens útiles (lowercase, >=2 chars, únicos) para scoring de keywords.
QStringList terms(const QString &s)
{
    QStringList out;
    const auto parts = s.toLower().split(
        QRegularExpression(QStringLiteral("[^\\p{L}\\p{N}_]+")), Qt::SkipEmptyParts);
    for (const QString &t : parts)
        if (t.size() >= 2 && !out.contains(t)) out << t;
    return out;
}

}  // namespace

namespace MemoryStore {

QString jsonlPath(const QString &cwd)
{
    return QDir::cleanPath(cwd + QStringLiteral("/.llamacode/memory.jsonl"));
}

QString save(const QString &cwd, const QString &content, const QString &scope,
             const QString &type, double confidence)
{
    const QString text = content.trimmed();
    if (text.isEmpty()) return QStringLiteral("[memory save: 'content' vacío]");

    const QString path = jsonlPath(cwd);
    QDir().mkpath(QFileInfo(path).absolutePath());

    QJsonObject fact{
        {QStringLiteral("content"), text},
        {QStringLiteral("scope"), normScope(scope)},
        {QStringLiteral("type"), normType(type)},
        {QStringLiteral("confidence"), qBound(0.0, confidence <= 0.0 ? 0.8 : confidence, 1.0)},
        {QStringLiteral("ts"), QDateTime::currentDateTime().toString(Qt::ISODate)}};

    QFile f(path);
    if (!f.open(QIODevice::Append | QIODevice::Text))
        return QStringLiteral("[no se pudo escribir la memoria: %1]").arg(path);
    f.write(QJsonDocument(fact).toJson(QJsonDocument::Compact));
    f.write("\n");
    f.close();
    return QStringLiteral("[memoria guardada · scope=%1 type=%2]")
        .arg(fact.value(QStringLiteral("scope")).toString(),
             fact.value(QStringLiteral("type")).toString());
}

QString recall(const QString &cwd, const QString &query, const QString &scope, int k)
{
    if (k <= 0) k = 8;
    k = qBound(1, k, 30);
    const QString path = jsonlPath(cwd);

    QFile f(path);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text))
        return QStringLiteral("[memoria estructurada vacía]");

    const QString scopeFilter = scope.trimmed().toLower();
    const QStringList qterms = terms(query);

    struct Row { QJsonObject obj; double score; };
    QVector<Row> rows;
    while (!f.atEnd()) {
        const QByteArray line = f.readLine().trimmed();
        if (line.isEmpty()) continue;
        const QJsonObject o = QJsonDocument::fromJson(line).object();
        if (o.isEmpty()) continue;
        if (!scopeFilter.isEmpty()
            && o.value(QStringLiteral("scope")).toString() != scopeFilter)
            continue;

        // Score: solapamiento de keywords + leve sesgo por confianza/recencia.
        double score = 0.0;
        if (!qterms.isEmpty()) {
            const QString hay = o.value(QStringLiteral("content")).toString().toLower();
            int hits = 0;
            for (const QString &t : qterms)
                if (hay.contains(t)) ++hits;
            if (hits == 0) continue;                    // sin query-match → descartar
            score = double(hits) / qterms.size();
        }
        score += 0.05 * o.value(QStringLiteral("confidence")).toDouble(0.8);
        rows.append({o, score});
    }
    f.close();

    if (rows.isEmpty())
        return query.isEmpty() ? QStringLiteral("[memoria estructurada vacía]")
                               : QStringLiteral("[sin hechos para: %1]").arg(query);

    std::stable_sort(rows.begin(), rows.end(),
                     [](const Row &a, const Row &b) { return a.score > b.score; });

    QStringList out;
    for (int i = 0; i < rows.size() && i < k; ++i) {
        const QJsonObject &o = rows[i].obj;
        out << QStringLiteral("- [%1/%2] %3")
                   .arg(o.value(QStringLiteral("scope")).toString(),
                        o.value(QStringLiteral("type")).toString(),
                        o.value(QStringLiteral("content")).toString());
    }
    return out.join(QLatin1Char('\n'));
}

}  // namespace MemoryStore
