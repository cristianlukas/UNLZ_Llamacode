#include "KnowledgePacket.h"

#include "GraphStore.h"
#include "MemoryStore.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QSet>

namespace {

QStringList terms(const QString &text)
{
    QStringList out;
    for (const QString &term : text.toLower().split(
             QRegularExpression(QStringLiteral("[^\\p{L}\\p{N}_]+")), Qt::SkipEmptyParts)) {
        if (term.size() >= 3 && !out.contains(term)) out << term;
    }
    return out;
}

QString edgeKey(const QJsonObject &edge)
{
    return edge.value(QStringLiteral("id")).toString()
        + edge.value(QStringLiteral("subj")).toString()
        + edge.value(QStringLiteral("obj")).toString();
}

} // namespace

namespace KnowledgePacket {

QJsonObject build(const QString &root, const QString &query, int maxFacts, int maxEdges)
{
    maxFacts = qBound(0, maxFacts, 50);
    maxEdges = qBound(0, maxEdges, 100);
    const QString facts = maxFacts > 0
        ? MemoryStore::recall(root, query, QStringLiteral("project"), maxFacts)
        : QString();

    QJsonArray edges;
    QJsonArray nodes;
    QJsonArray sources;
    QSet<QString> seenEdges, seenNodes, seenSources;
    const QStringList qterms = terms(query);
    const QStringList names = GraphStore::entityNames(root, QString());
    for (const QString &name : names) {
        const QString low = name.toLower();
        bool match = qterms.isEmpty();
        for (const QString &term : qterms) {
            if (low.contains(term)) { match = true; break; }
        }
        if (!match || edges.size() >= maxEdges) continue;
        const QJsonObject packet = GraphStore::queryPacket(root, name, 2);
        if (!packet.value(QStringLiteral("ok")).toBool()) continue;
        for (const QJsonValue &v : packet.value(QStringLiteral("nodes")).toArray()) {
            const QJsonObject node = v.toObject();
            const QString key = node.value(QStringLiteral("id")).toString();
            if (!key.isEmpty() && !seenNodes.contains(key)) {
                seenNodes.insert(key);
                nodes.append(node);
            }
        }
        for (const QJsonValue &v : packet.value(QStringLiteral("edges")).toArray()) {
            const QJsonObject edge = v.toObject();
            const QString key = edgeKey(edge);
            if (key.isEmpty() || seenEdges.contains(key)) continue;
            seenEdges.insert(key);
            edges.append(edge);
            for (const QJsonValue &sv : edge.value(QStringLiteral("sources")).toArray()) {
                const QJsonObject source = sv.toObject();
                const QString skey = QString::fromUtf8(
                    QJsonDocument(source).toJson(QJsonDocument::Compact));
                if (!seenSources.contains(skey)) {
                    seenSources.insert(skey);
                    sources.append(source);
                }
            }
            if (edges.size() >= maxEdges) break;
        }
    }

    const bool budgetCut = edges.size() >= maxEdges;
    return {{QStringLiteral("schemaVersion"), 1},
            {QStringLiteral("query"), query},
            {QStringLiteral("factsText"), facts},
            {QStringLiteral("nodes"), nodes},
            {QStringLiteral("edges"), edges},
            {QStringLiteral("sources"), sources},
            {QStringLiteral("receipt"), QJsonObject{
                {QStringLiteral("maxFacts"), maxFacts},
                {QStringLiteral("maxEdges"), maxEdges},
                {QStringLiteral("factChars"), facts.size()},
                {QStringLiteral("edgeCount"), edges.size()},
                {QStringLiteral("sourceCount"), sources.size()},
             {QStringLiteral("budgetCut"), budgetCut}}}};
}

QString format(const QJsonObject &packet, int maxChars)
{
    if (maxChars <= 0) maxChars = 12000;
    QStringList lines{QStringLiteral("[knowledge-packet · evidencia durable]")};
    const QString facts = packet.value(QStringLiteral("factsText")).toString().trimmed();
    if (!facts.isEmpty() && !facts.startsWith(QLatin1Char('['))) {
        lines << QStringLiteral("Hechos:") << facts;
    }
    const QJsonArray edges = packet.value(QStringLiteral("edges")).toArray();
    if (!edges.isEmpty()) {
        lines << QStringLiteral("Relaciones:");
        for (const QJsonValue &v : edges) {
            const QJsonObject e = v.toObject();
            QString line = QStringLiteral("- %1 -[%2]-> %3")
                .arg(e.value(QStringLiteral("subj")).toString(),
                     e.value(QStringLiteral("etype")).toString(),
                     e.value(QStringLiteral("obj")).toString());
            if (e.value(QStringLiteral("status")).toString() == QLatin1String("unreviewed"))
                line += QStringLiteral(" [unreviewed]");
            else
                line += QStringLiteral(" [verified conf=%1]")
                    .arg(e.value(QStringLiteral("conf")).toDouble(), 0, 'g', 2);
            QStringList citations;
            for (const QJsonValue &c : e.value(QStringLiteral("citations")).toArray())
                citations << c.toString();
            if (!citations.isEmpty()) line += QStringLiteral(" · ") + citations.join(", ");
            lines << line;
        }
    }
    const QJsonObject receipt = packet.value(QStringLiteral("receipt")).toObject();
    lines << QStringLiteral("\n── knowledge-receipt ──")
          << QString::fromUtf8(QJsonDocument(receipt).toJson(QJsonDocument::Compact));
    QString out = lines.join(QLatin1Char('\n'));
    if (out.size() > maxChars) {
        out.truncate(qMax(0, maxChars - 32));
        out += QStringLiteral("\n[knowledge-packet truncado]");
    }
    return out;
}

} // namespace KnowledgePacket
