#include "GraphStore.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QDateTime>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QCryptographicHash>
#include <QHash>
#include <QSet>
#include <QStringList>
#include <QVector>
#include <algorithm>

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

// Taxonomía CERRADA de tipos de arista. El 'pred' libre (verbo) se conserva como
// label humano, pero cada relación se clasifica en uno de estos tipos para que el
// agente NO trate una relación blanda ("relates_to") como una dependencia dura
// ("requires"). Idea del CKG (typed edges): separar dependencia de asociación.
QString normEdge(const QString &edgeType, const QString &pred)
{
    static const QSet<QString> ok{
        QStringLiteral("REQUIRES"), QStringLiteral("ENABLES"),
        QStringLiteral("IMPLEMENTS"), QStringLiteral("DEFINES"),
        QStringLiteral("CALLS"), QStringLiteral("IMPORTS"),
        QStringLiteral("RELATES_TO")};
    const QString explicitT = edgeType.trimmed().toUpper();
    if (ok.contains(explicitT)) return explicitT;

    // Inferir del verbo libre.
    const QString p = norm(pred);
    if (p.contains(QLatin1String("requir")) || p.contains(QLatin1String("depend"))
        || p.contains(QLatin1String("needs")) || p == QLatin1String("necesita")
        || p == QLatin1String("usa") || p == QLatin1String("uses"))
        return QStringLiteral("REQUIRES");
    if (p.contains(QLatin1String("enable")) || p.contains(QLatin1String("provide"))
        || p.contains(QLatin1String("habilita")))
        return QStringLiteral("ENABLES");
    if (p.contains(QLatin1String("implement")))
        return QStringLiteral("IMPLEMENTS");
    if (p.contains(QLatin1String("defin")))
        return QStringLiteral("DEFINES");
    if (p.contains(QLatin1String("call")) || p.contains(QLatin1String("invoke")))
        return QStringLiteral("CALLS");
    if (p.contains(QLatin1String("import")))
        return QStringLiteral("IMPORTS");
    return QStringLiteral("RELATES_TO");
}

// conf<0 → JSON null (unreviewed, NO = wrong). Si no, número acotado a [0,1].
QJsonValue confVal(double conf)
{
    if (conf < 0.0) return QJsonValue(QJsonValue::Null);
    return QJsonValue(qBound(0.0, conf, 1.0));
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
             const QString &obj, const QString &edgeType, double conf,
             const QString &prov)
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

    const QString et = normEdge(edgeType, p);
    appendObj(path, QJsonObject{
        {QStringLiteral("kind"), QStringLiteral("relation")},
        {QStringLiteral("id"), rid},
        {QStringLiteral("subj"), sid},
        {QStringLiteral("pred"), norm(p)},
        {QStringLiteral("obj"), oid},
        {QStringLiteral("etype"), et},
        {QStringLiteral("conf"), confVal(conf)},
        {QStringLiteral("prov"), prov.trimmed().isEmpty() ? QStringLiteral("llm")
                                                          : prov.trimmed()},
        {QStringLiteral("ts"), QDateTime::currentDateTime().toString(Qt::ISODate)}});
    return QStringLiteral("[relación creada · %1 -[%2]-> %3]").arg(s, et, o);
}

QString reviewRelation(const QString &cwd, const QString &subj, const QString &pred,
                       const QString &obj, double conf, const QString &prov, bool drop)
{
    const QString s = subj.trimmed(), p = pred.trimmed(), o = obj.trimmed();
    if (s.isEmpty() || p.isEmpty() || o.isEmpty())
        return QStringLiteral("[graph verify: subj/pred/obj requeridos]");

    const QString path = jsonlPath(cwd);
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text))
        return QStringLiteral("[grafo vacío]");

    const QString rid = relId(entId(s), p, entId(o));
    const QString provTag = prov.trimmed().isEmpty() ? QStringLiteral("user")
                                                     : prov.trimmed();
    QByteArray out;
    bool hit = false;
    while (!f.atEnd()) {
        const QByteArray l = f.readLine().trimmed();
        if (l.isEmpty()) continue;
        QJsonObject ro = QJsonDocument::fromJson(l).object();
        if (ro.value(QStringLiteral("kind")).toString() == QLatin1String("relation")
            && ro.value(QStringLiteral("id")).toString() == rid) {
            hit = true;
            if (drop) continue;   // tachar: no lo re-escribimos
            ro.insert(QStringLiteral("conf"), confVal(conf));
            ro.insert(QStringLiteral("prov"), provTag);
            out += QJsonDocument(ro).toJson(QJsonDocument::Compact);
            out += '\n';
            continue;
        }
        out += l;
        out += '\n';
    }
    f.close();
    if (!hit)
        return QStringLiteral("[graph verify: no existe el edge %1 -[%2]-> %3]").arg(s, p, o);

    QFile w(path);
    if (!w.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text))
        return QStringLiteral("[graph verify: no se pudo reescribir %1]").arg(path);
    w.write(out);
    w.close();
    if (drop)
        return QStringLiteral("[edge tachado · %1 -[%2]-> %3]").arg(s, p, o);
    return QStringLiteral("[edge revisado · %1 -[%2]-> %3 · conf=%4 prov=%5]")
        .arg(s, p, o).arg(conf < 0 ? QStringLiteral("null") : QString::number(conf, 'g', 2),
                          provTag);
}

QString addBatch(const QString &cwd,
                 const QVector<QPair<QString, QString>> &entities,
                 const QVector<Triple> &relations,
                 int *addedEnt, int *addedRel, const QString &prov, double conf)
{
    const QString path = jsonlPath(cwd);
    QDir().mkpath(QFileInfo(path).absolutePath());
    const QString provTag = prov.trimmed().isEmpty() ? QStringLiteral("indexer")
                                                     : prov.trimmed();

    // 1. Una sola lectura: junta los ids de entidades/relaciones ya presentes.
    QSet<QString> haveEnt, haveRel;
    {
        QFile f(path);
        if (f.open(QIODevice::ReadOnly | QIODevice::Text)) {
            while (!f.atEnd()) {
                const QByteArray l = f.readLine().trimmed();
                if (l.isEmpty()) continue;
                const QJsonObject o = QJsonDocument::fromJson(l).object();
                const QString k = o.value(QStringLiteral("kind")).toString();
                if (k == QLatin1String("entity"))
                    haveEnt.insert(o.value(QStringLiteral("id")).toString());
                else if (k == QLatin1String("relation"))
                    haveRel.insert(o.value(QStringLiteral("id")).toString());
            }
            f.close();
        }
    }

    // 2. Un solo Append con todo lo nuevo (dedupe contra lo existente y dentro
    //    del propio lote vía los sets, que vamos engordando a medida que escribimos).
    QFile f(path);
    if (!f.open(QIODevice::Append | QIODevice::Text))
        return QStringLiteral("[graph batch: no se pudo abrir %1]").arg(path);

    const QString ts = QDateTime::currentDateTime().toString(Qt::ISODate);
    int nE = 0, nR = 0;
    auto writeEnt = [&](const QString &name, const QString &etype) {
        const QString nm = name.trimmed();
        if (nm.isEmpty()) return;
        const QString id = entId(nm);
        if (haveEnt.contains(id)) return;
        haveEnt.insert(id);
        const QJsonObject o{
            {QStringLiteral("kind"), QStringLiteral("entity")},
            {QStringLiteral("id"), id},
            {QStringLiteral("name"), nm},
            {QStringLiteral("etype"), normType(etype)},
            {QStringLiteral("ts"), ts}};
        f.write(QJsonDocument(o).toJson(QJsonDocument::Compact));
        f.write("\n");
        ++nE;
    };
    for (const auto &e : entities) writeEnt(e.first, e.second);
    for (const Triple &t : relations) {
        const QString s = t.subj.trimmed(), p = t.pred.trimmed(), o = t.obj.trimmed();
        if (s.isEmpty() || p.isEmpty() || o.isEmpty()) continue;
        writeEnt(s, QString());   // auto-crea las entidades referidas (dedupe interno)
        writeEnt(o, QString());
        const QString sid = entId(s), oid = entId(o), rid = relId(sid, p, oid);
        if (haveRel.contains(rid)) continue;
        haveRel.insert(rid);
        const QJsonObject ro{
            {QStringLiteral("kind"), QStringLiteral("relation")},
            {QStringLiteral("id"), rid},
            {QStringLiteral("subj"), sid},
            {QStringLiteral("pred"), norm(p)},
            {QStringLiteral("obj"), oid},
            {QStringLiteral("etype"), normEdge(QString(), p)},
            {QStringLiteral("conf"), confVal(conf)},
            {QStringLiteral("prov"), provTag},
            {QStringLiteral("ts"), ts}};
        f.write(QJsonDocument(ro).toJson(QJsonDocument::Compact));
        f.write("\n");
        ++nR;
    }
    f.close();

    if (addedEnt) *addedEnt = nE;
    if (addedRel) *addedRel = nR;
    return QStringLiteral("[graph batch: +%1 entidades, +%2 relaciones]").arg(nE).arg(nR);
}

int removeRelationsBySubject(const QString &cwd, const QString &subjName)
{
    const QString nm = subjName.trimmed();
    if (nm.isEmpty()) return 0;
    const QString path = jsonlPath(cwd);
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) return 0;

    const QString sid = entId(nm);
    QByteArray kept;
    int removed = 0;
    while (!f.atEnd()) {
        const QByteArray raw = f.readLine();
        const QByteArray l = raw.trimmed();
        if (l.isEmpty()) continue;
        const QJsonObject o = QJsonDocument::fromJson(l).object();
        if (o.value(QStringLiteral("kind")).toString() == QLatin1String("relation")
            && o.value(QStringLiteral("subj")).toString() == sid) {
            ++removed;
            continue;   // dropear
        }
        kept += l;
        kept += '\n';
    }
    f.close();
    if (removed == 0) return 0;   // nada que reescribir

    QFile w(path);
    if (!w.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text))
        return 0;
    w.write(kept);
    w.close();
    return removed;
}

QStringList entityNames(const QString &cwd, const QString &etype)
{
    QStringList out;
    QFile f(jsonlPath(cwd));
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) return out;
    const QString want = norm(etype);
    while (!f.atEnd()) {
        const QByteArray l = f.readLine().trimmed();
        if (l.isEmpty()) continue;
        const QJsonObject o = QJsonDocument::fromJson(l).object();
        if (o.value(QStringLiteral("kind")).toString() != QLatin1String("entity"))
            continue;
        if (!want.isEmpty() && o.value(QStringLiteral("etype")).toString() != want)
            continue;
        out << o.value(QStringLiteral("name")).toString();
    }
    f.close();
    return out;
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
    // conf<0 → unreviewed (campo ausente en relaciones viejas: back-compat).
    struct Rel { QString subj, pred, obj, etype, prov; double conf; };
    QVector<Rel> rels;
    while (!f.atEnd()) {
        const QByteArray l = f.readLine().trimmed();
        if (l.isEmpty()) continue;
        const QJsonObject o = QJsonDocument::fromJson(l).object();
        const QString kind = o.value(QStringLiteral("kind")).toString();
        if (kind == QLatin1String("entity"))
            idToName.insert(o.value(QStringLiteral("id")).toString(),
                            o.value(QStringLiteral("name")).toString());
        else if (kind == QLatin1String("relation")) {
            const QString pr = o.value(QStringLiteral("pred")).toString();
            // etype ausente (relación vieja) → inferir del pred.
            QString et = o.value(QStringLiteral("etype")).toString();
            if (et.isEmpty()) et = normEdge(QString(), pr);
            const QJsonValue cv = o.value(QStringLiteral("conf"));
            const double c = cv.isDouble() ? cv.toDouble() : -1.0;   // null/ausente → -1
            rels.append({o.value(QStringLiteral("subj")).toString(), pr,
                         o.value(QStringLiteral("obj")).toString(), et,
                         o.value(QStringLiteral("prov")).toString(), c});
        }
    }
    f.close();

    const QString startId = entId(nm);
    if (!idToName.contains(startId))
        return QStringLiteral("[grafo: no existe la entidad '%1']").arg(nm);

    auto nameOf = [&](const QString &id) {
        return idToName.value(id, id);
    };

    // BFS hasta 'depth' saltos; recolecta aristas tocadas.
    struct Edge { double conf; QString line; };
    QSet<QString> frontier{startId}, visited{startId};
    QVector<Edge> edges;
    QSet<QString> seenEdge;
    for (int d = 0; d < depth; ++d) {
        QSet<QString> next;
        for (const Rel &r : rels) {
            QString other; bool outgoing;
            if (frontier.contains(r.subj)) { other = r.obj; outgoing = true; }
            else if (frontier.contains(r.obj)) { other = r.subj; outgoing = false; }
            else continue;

            const QString edgeKey = r.subj + r.pred + r.obj;
            if (!seenEdge.contains(edgeKey)) {
                seenEdge.insert(edgeKey);
                // Marca de confianza/origen: unreviewed si conf<0 (NO = incorrecto),
                // si no muestra el score. Evita que el agente trate una inferencia
                // del LLM como hecho verificado.
                const QString tag = r.conf < 0.0
                    ? QStringLiteral(" [unreviewed·%1]").arg(r.prov.isEmpty()
                        ? QStringLiteral("llm") : r.prov)
                    : QStringLiteral(" [conf=%1·%2]").arg(r.conf, 0, 'g', 2)
                        .arg(r.prov.isEmpty() ? QStringLiteral("indexer") : r.prov);
                edges.append({r.conf,
                    QStringLiteral("- %1 -[%2]-> %3%4%5").arg(
                        nameOf(r.subj), r.etype, nameOf(r.obj),
                        outgoing ? QString() : QStringLiteral(" (entrante)"), tag)});
            }
            if (!visited.contains(other)) { next.insert(other); visited.insert(other); }
        }
        frontier = next;
        if (frontier.isEmpty()) break;
    }

    if (edges.isEmpty())
        return QStringLiteral("[entidad '%1' sin relaciones]").arg(nm);

    // Ordenar: verificados (conf alta) primero, unreviewed (conf<0) al final.
    std::stable_sort(edges.begin(), edges.end(), [](const Edge &a, const Edge &b) {
        const double ca = a.conf < 0.0 ? -1.0 : a.conf;
        const double cb = b.conf < 0.0 ? -1.0 : b.conf;
        return ca > cb;
    });
    QStringList lines;
    for (const Edge &e : edges) lines << e.line;
    return QStringLiteral("Vecindario de '%1' (depth=%2):\n").arg(nm).arg(depth)
           + lines.join(QLatin1Char('\n'));
}

QString decide(const QString &cwd, const QString &topic, const QString &chosen,
               const Rejected &rejected, const QString &reason)
{
    const QString tp = topic.trimmed(), ch = chosen.trimmed();
    if (tp.isEmpty() || ch.isEmpty())
        return QStringLiteral("[graph decide: 'topic' y 'chosen' requeridos]");

    const QString path = jsonlPath(cwd);
    QDir().mkpath(QFileInfo(path).absolutePath());

    // id estable por tema: re-decidir el mismo tema crea una entrada nueva
    // (el log es append-only/inmutable), pero comparten prefijo para agrupar.
    const QByteArray h = QCryptographicHash::hash(
        (norm(tp) + QLatin1Char('|') + QDateTime::currentDateTime().toString(Qt::ISODate)).toUtf8(),
        QCryptographicHash::Sha1);
    const QString id = QStringLiteral("d_") + QString::fromLatin1(h.toHex().left(8));

    QJsonArray rej;
    for (const auto &r : rejected) {
        if (r.first.trimmed().isEmpty()) continue;
        rej.append(QJsonObject{
            {QStringLiteral("alt"), r.first.trimmed()},
            {QStringLiteral("reason"), r.second.trimmed()}});
    }

    appendObj(path, QJsonObject{
        {QStringLiteral("kind"), QStringLiteral("decision")},
        {QStringLiteral("id"), id},
        {QStringLiteral("topic"), tp},
        {QStringLiteral("chosen"), ch},
        {QStringLiteral("reason"), reason.trimmed()},
        {QStringLiteral("rejected"), rej},
        {QStringLiteral("ts"), QDateTime::currentDateTime().toString(Qt::ISODate)}});
    return QStringLiteral("[decisión registrada · id=%1 '%2' → %3 (%4 rechazada/s)]")
        .arg(id, tp, ch).arg(rej.size());
}

QString decisions(const QString &cwd, const QString &topic)
{
    QFile f(jsonlPath(cwd));
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text))
        return QStringLiteral("[sin decisiones registradas]");

    const QString filt = norm(topic);
    QStringList blocks;
    while (!f.atEnd()) {
        const QByteArray l = f.readLine().trimmed();
        if (l.isEmpty()) continue;
        const QJsonObject o = QJsonDocument::fromJson(l).object();
        if (o.value(QStringLiteral("kind")).toString() != QLatin1String("decision"))
            continue;
        const QString tp = o.value(QStringLiteral("topic")).toString();
        if (!filt.isEmpty() && !norm(tp).contains(filt)) continue;

        QString b = QStringLiteral("### %1\n- elegido: %2")
            .arg(tp, o.value(QStringLiteral("chosen")).toString());
        const QString rs = o.value(QStringLiteral("reason")).toString();
        if (!rs.isEmpty()) b += QStringLiteral("\n- motivo: %1").arg(rs);
        const QJsonArray rej = o.value(QStringLiteral("rejected")).toArray();
        for (const QJsonValue &v : rej) {
            const QJsonObject ro = v.toObject();
            const QString rr = ro.value(QStringLiteral("reason")).toString();
            b += QStringLiteral("\n- ✗ rechazado: %1%2")
                .arg(ro.value(QStringLiteral("alt")).toString(),
                     rr.isEmpty() ? QString() : QStringLiteral(" — ") + rr);
        }
        b += QStringLiteral("\n- ts: %1").arg(o.value(QStringLiteral("ts")).toString());
        blocks << b;
    }
    f.close();

    if (blocks.isEmpty())
        return filt.isEmpty() ? QStringLiteral("[sin decisiones registradas]")
                              : QStringLiteral("[sin decisiones para '%1']").arg(topic.trimmed());
    return QStringLiteral("Decisiones (%1):\n").arg(blocks.size()) + blocks.join(QStringLiteral("\n\n"));
}

}  // namespace GraphStore
