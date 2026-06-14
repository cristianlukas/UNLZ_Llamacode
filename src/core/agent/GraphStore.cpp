#include "GraphStore.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QDateTime>
#include <QJsonDocument>
#include <QJsonObject>
#include <QCryptographicHash>
#include <QHash>
#include <QSet>
#include <QStringList>
#include <QVector>

namespace {

QString norm(const QString &s) { return s.trimmed().toLower(); }

QString normType(const QString &t)
{
    const QString v = norm(t);
    static const QSet<QString> ok{
        QStringLiteral("file"), QStringLiteral("module"), QStringLiteral("decision"),
        QStringLiteral("bug"), QStringLiteral("person"), QStringLiteral("concept"),
        QStringLiteral("other")};
    return ok.contains(v) ? v : QStringLiteral("concept");
}

// id estable de entidad: hash del nombre normalizado (mismo nombre → mismo id).
QString entId(const QString &name)
{
    const QByteArray h = QCryptographicHash::hash(
        norm(name).toUtf8(), QCryptographicHash::Sha1);
    return QStringLiteral("e_") + QString::fromLatin1(h.toHex().left(8));
}

QString relId(const QString &subj, const QString &pred, const QString &obj)
{
    const QByteArray h = QCryptographicHash::hash(
        (subj + QLatin1Char('|') + norm(pred) + QLatin1Char('|') + obj).toUtf8(),
        QCryptographicHash::Sha1);
    return QStringLiteral("r_") + QString::fromLatin1(h.toHex().left(8));
}

void appendObj(const QString &path, const QJsonObject &o)
{
    QFile f(path);
    if (!f.open(QIODevice::Append | QIODevice::Text)) return;
    f.write(QJsonDocument(o).toJson(QJsonDocument::Compact));
    f.write("\n");
    f.close();
}

}  // namespace

namespace GraphStore {

QString jsonlPath(const QString &cwd)
{
    return QDir::cleanPath(cwd + QStringLiteral("/.llamacode/graph.jsonl"));
}

QString addEntity(const QString &cwd, const QString &name, const QString &etype)
{
    const QString nm = name.trimmed();
    if (nm.isEmpty()) return QStringLiteral("[graph: 'name' vacío]");

    const QString path = jsonlPath(cwd);
    QDir().mkpath(QFileInfo(path).absolutePath());
    const QString id = entId(nm);

    // Dedupe: si ya existe esa entidad, no la re-agregamos.
    QFile f(path);
    if (f.open(QIODevice::ReadOnly | QIODevice::Text)) {
        while (!f.atEnd()) {
            const QByteArray l = f.readLine().trimmed();
            if (l.isEmpty()) continue;
            const QJsonObject o = QJsonDocument::fromJson(l).object();
            if (o.value(QStringLiteral("kind")).toString() == QLatin1String("entity")
                && o.value(QStringLiteral("id")).toString() == id) {
                f.close();
                return QStringLiteral("[entidad ya existe · id=%1 '%2']").arg(id, nm);
            }
        }
        f.close();
    }

    appendObj(path, QJsonObject{
        {QStringLiteral("kind"), QStringLiteral("entity")},
        {QStringLiteral("id"), id},
        {QStringLiteral("name"), nm},
        {QStringLiteral("etype"), normType(etype)},
        {QStringLiteral("ts"), QDateTime::currentDateTime().toString(Qt::ISODate)}});
    return QStringLiteral("[entidad creada · id=%1 etype=%2 '%3']")
        .arg(id, normType(etype), nm);
}

QString link(const QString &cwd, const QString &subj, const QString &pred,
             const QString &obj)
{
    const QString s = subj.trimmed(), p = pred.trimmed(), o = obj.trimmed();
    if (s.isEmpty() || p.isEmpty() || o.isEmpty())
        return QStringLiteral("[graph link: subj/pred/obj requeridos]");

    addEntity(cwd, s, QString());      // auto-crea (dedupe interno)
    addEntity(cwd, o, QString());

    const QString path = jsonlPath(cwd);
    const QString sid = entId(s), oid = entId(o), rid = relId(sid, p, oid);

    // Dedupe de la relación.
    QFile f(path);
    if (f.open(QIODevice::ReadOnly | QIODevice::Text)) {
        while (!f.atEnd()) {
            const QByteArray l = f.readLine().trimmed();
            if (l.isEmpty()) continue;
            const QJsonObject ro = QJsonDocument::fromJson(l).object();
            if (ro.value(QStringLiteral("kind")).toString() == QLatin1String("relation")
                && ro.value(QStringLiteral("id")).toString() == rid) {
                f.close();
                return QStringLiteral("[relación ya existe · %1 -[%2]-> %3]").arg(s, p, o);
            }
        }
        f.close();
    }

    appendObj(path, QJsonObject{
        {QStringLiteral("kind"), QStringLiteral("relation")},
        {QStringLiteral("id"), rid},
        {QStringLiteral("subj"), sid},
        {QStringLiteral("pred"), norm(p)},
        {QStringLiteral("obj"), oid},
        {QStringLiteral("ts"), QDateTime::currentDateTime().toString(Qt::ISODate)}});
    return QStringLiteral("[relación creada · %1 -[%2]-> %3]").arg(s, norm(p), o);
}

QString query(const QString &cwd, const QString &name, int depth)
{
    if (depth <= 0) depth = 1;
    depth = qBound(1, depth, 2);
    const QString nm = name.trimmed();
    if (nm.isEmpty()) return QStringLiteral("[graph query: 'name' vacío]");

    QFile f(jsonlPath(cwd));
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text))
        return QStringLiteral("[grafo vacío]");

    // Cargar entidades y relaciones en memoria (grafos chicos).
    QHash<QString, QString> idToName;          // entId -> nombre
    struct Rel { QString subj, pred, obj; };
    QVector<Rel> rels;
    while (!f.atEnd()) {
        const QByteArray l = f.readLine().trimmed();
        if (l.isEmpty()) continue;
        const QJsonObject o = QJsonDocument::fromJson(l).object();
        const QString kind = o.value(QStringLiteral("kind")).toString();
        if (kind == QLatin1String("entity"))
            idToName.insert(o.value(QStringLiteral("id")).toString(),
                            o.value(QStringLiteral("name")).toString());
        else if (kind == QLatin1String("relation"))
            rels.append({o.value(QStringLiteral("subj")).toString(),
                         o.value(QStringLiteral("pred")).toString(),
                         o.value(QStringLiteral("obj")).toString()});
    }
    f.close();

    const QString startId = entId(nm);
    if (!idToName.contains(startId))
        return QStringLiteral("[grafo: no existe la entidad '%1']").arg(nm);

    auto nameOf = [&](const QString &id) {
        return idToName.value(id, id);
    };

    // BFS hasta 'depth' saltos; recolecta aristas tocadas.
    QSet<QString> frontier{startId}, visited{startId};
    QStringList lines;
    QSet<QString> seenEdge;
    for (int d = 0; d < depth; ++d) {
        QSet<QString> next;
        for (const Rel &r : rels) {
            QString hub, other; bool outgoing;
            if (frontier.contains(r.subj)) { hub = r.subj; other = r.obj; outgoing = true; }
            else if (frontier.contains(r.obj)) { hub = r.obj; other = r.subj; outgoing = false; }
            else continue;

            const QString edgeKey = r.subj + r.pred + r.obj;
            if (!seenEdge.contains(edgeKey)) {
                seenEdge.insert(edgeKey);
                lines << (outgoing
                    ? QStringLiteral("- %1 -[%2]-> %3").arg(nameOf(r.subj), r.pred, nameOf(r.obj))
                    : QStringLiteral("- %1 -[%2]-> %3 (entrante)").arg(nameOf(r.subj), r.pred, nameOf(r.obj)));
            }
            if (!visited.contains(other)) { next.insert(other); visited.insert(other); }
        }
        frontier = next;
        if (frontier.isEmpty()) break;
    }

    if (lines.isEmpty())
        return QStringLiteral("[entidad '%1' sin relaciones]").arg(nm);
    return QStringLiteral("Vecindario de '%1' (depth=%2):\n").arg(nm).arg(depth)
           + lines.join(QLatin1Char('\n'));
}

}  // namespace GraphStore
