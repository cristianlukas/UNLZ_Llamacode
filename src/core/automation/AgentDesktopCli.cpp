#include "AgentDesktopCli.h"
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QStandardPaths>

namespace AgentDesktopCli {
namespace {

void collectRefs(const QVariantMap &node, QVariantList *out)
{
    if (node.contains(QStringLiteral("ref_id"))) out->append(node);
    for (const QVariant &c : node.value(QStringLiteral("children")).toList())
        collectRefs(c.toMap(), out);
}

} // namespace

QString binaryPath()
{
    const QString env = qEnvironmentVariable("LLAMACODE_AGENT_DESKTOP");
    if (!env.isEmpty()) return QFileInfo(env).isExecutable() ? env : QString();
    const QString bundled = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                            + QStringLiteral("/tools/agent-desktop/agent-desktop");
    if (QFileInfo(bundled).isExecutable()) return bundled;
    return QStandardPaths::findExecutable(QStringLiteral("agent-desktop"));
}

bool available() { return !binaryPath().isEmpty(); }

QVariant parseEnvelope(const QByteArray &json, QString *error)
{
    const QJsonDocument doc = QJsonDocument::fromJson(json);
    if (!doc.isObject()) {
        if (error) *error = QStringLiteral("agent-desktop devolvió una respuesta no JSON.");
        return {};
    }
    const QVariantMap env = doc.object().toVariantMap();
    if (!env.value(QStringLiteral("ok")).toBool()) {
        const QVariantMap err = env.value(QStringLiteral("error")).toMap();
        if (error)
            *error = QStringLiteral("agent-desktop %1: %2")
                         .arg(err.value(QStringLiteral("code")).toString(),
                              err.value(QStringLiteral("message")).toString());
        return {};
    }
    if (error) error->clear();
    // Un `data` null (acciones sin payload) igual es éxito.
    return env.contains(QStringLiteral("data")) && !env.value(QStringLiteral("data")).isNull()
        ? env.value(QStringLiteral("data")) : QVariant(QVariantMap{});
}

QString windowIdForPid(const QVariant &listWindowsData, qint64 pid)
{
    QString fallback;
    for (const QVariant &v : listWindowsData.toList()) {
        const QVariantMap w = v.toMap();
        if (w.value(QStringLiteral("pid")).toLongLong() != pid) continue;
        if (!w.value(QStringLiteral("accessible"), true).toBool()) continue;
        // Una app con varias ventanas: la que tiene el foco primero.
        if (w.value(QStringLiteral("is_focused")).toBool()) return w.value(QStringLiteral("id")).toString();
        if (fallback.isEmpty()) fallback = w.value(QStringLiteral("id")).toString();
    }
    return fallback;
}

QVariantList rowsFromSnapshot(const QVariant &snapshotData, const QString &query, int max)
{
    QVariantList nodes;
    collectRefs(snapshotData.toMap().value(QStringLiteral("tree")).toMap(), &nodes);
    const QString needle = query.trimmed().toLower();
    QVariantList out;
    for (const QVariant &v : std::as_const(nodes)) {
        if (out.size() >= max) break;
        const QVariantMap n = v.toMap();
        const QString name = n.value(QStringLiteral("name")).toString();
        const QString value = n.value(QStringLiteral("value")).toString();
        if (!needle.isEmpty() && !name.toLower().contains(needle) && !value.toLower().contains(needle))
            continue;
        const QStringList actions = n.value(QStringLiteral("available_actions")).toStringList();
        const QStringList states = n.value(QStringLiteral("states")).toStringList();
        const QVariantMap b = n.value(QStringLiteral("bounds")).toMap();
        QVariantMap row{{QStringLiteral("controlId"), QStringLiteral("ad:") + n.value(QStringLiteral("ref_id")).toString()},
                        {QStringLiteral("name"), name},
                        {QStringLiteral("role"), n.value(QStringLiteral("role")).toString()},
                        {QStringLiteral("x"), qRound(b.value(QStringLiteral("x")).toDouble())},
                        {QStringLiteral("y"), qRound(b.value(QStringLiteral("y")).toDouble())},
                        {QStringLiteral("width"), qRound(b.value(QStringLiteral("width")).toDouble())},
                        {QStringLiteral("height"), qRound(b.value(QStringLiteral("height")).toDouble())},
                        {QStringLiteral("enabled"), !states.contains(QStringLiteral("disabled"))},
                        {QStringLiteral("invokable"), actions.contains(QStringLiteral("Click"))
                                                       || actions.contains(QStringLiteral("Toggle"))},
                        {QStringLiteral("actions"), actions},
                        {QStringLiteral("backend"), QStringLiteral("agent-desktop")}};
        if (!value.isEmpty()) row.insert(QStringLiteral("value"), value);
        out << row;
    }
    return out;
}

QStringList actionArgs(const QString &ref, const QString &action, const QString &value)
{
    const QString op = action.trimmed().toLower();
    if (op.isEmpty() || op == QLatin1String("click") || op == QLatin1String("invoke"))
        return {QStringLiteral("click"), ref};
    if (op == QLatin1String("set_value")) return {QStringLiteral("set-value"), ref, value};
    if (op == QLatin1String("type")) return {QStringLiteral("type"), ref, value};
    if (op == QLatin1String("focus")) return {QStringLiteral("focus"), ref};
    if (op == QLatin1String("toggle")) return {QStringLiteral("toggle"), ref};
    if (op == QLatin1String("select")) return {QStringLiteral("select"), ref, value};
    if (op == QLatin1String("expand")) return {QStringLiteral("expand"), ref};
    if (op == QLatin1String("collapse")) return {QStringLiteral("collapse"), ref};
    if (op == QLatin1String("scroll_into_view")) return {QStringLiteral("scroll-to"), ref};
    if (op == QLatin1String("read")) return {QStringLiteral("get"), ref, QStringLiteral("--property"), QStringLiteral("text")};
    return {};
}

QVariant run(const QStringList &args, QString *error, int timeoutMs)
{
    const QString bin = binaryPath();
    if (bin.isEmpty()) {
        if (error) *error = QStringLiteral("agent-desktop no está instalado.");
        return {};
    }
    QProcess p;
    p.start(bin, args);
    if (!p.waitForFinished(timeoutMs)) {
        p.kill();
        p.waitForFinished(1000);
        if (error) *error = QStringLiteral("agent-desktop %1: sin respuesta en %2 ms.").arg(args.value(0)).arg(timeoutMs);
        return {};
    }
    return parseEnvelope(p.readAllStandardOutput(), error);
}

QVariantList controlsForPid(qint64 pid, const QString &query, int max, QString *error)
{
    if (pid <= 0) {
        if (error) *error = QStringLiteral("La ventana no publica _NET_WM_PID.");
        return {};
    }
    const QVariant windows = run({QStringLiteral("list-windows")}, error);
    const QString windowId = windowIdForPid(windows, pid);
    if (windowId.isEmpty()) {
        if (error && error->isEmpty())
            *error = QStringLiteral("agent-desktop no ve una ventana accesible del proceso %1.").arg(pid);
        return {};
    }
    const QVariant snap = run({QStringLiteral("snapshot"), QStringLiteral("--window-id"), windowId,
                               QStringLiteral("-i"), QStringLiteral("--compact"),
                               QStringLiteral("--include-bounds"), QStringLiteral("--max-depth"),
                               QStringLiteral("30")}, error);
    return rowsFromSnapshot(snap, query, max);
}

bool controlAction(const QString &controlId, const QString &action, const QString &value,
                   QString *error, QVariantMap *trace)
{
    const QString ref = refFromControlId(controlId);
    const QStringList args = actionArgs(ref, action, value);
    if (args.isEmpty()) {
        if (error) *error = QStringLiteral("agent-desktop no soporta la acción '%1'.").arg(action);
        return false;
    }
    QString err;
    const QVariant data = run(args, &err);
    if (!err.isEmpty()) {
        if (error) *error = err;
        return false;
    }
    if (trace) {
        *trace = {{QStringLiteral("surface"), QStringLiteral("desktop")},
                  {QStringLiteral("action"), action.isEmpty() ? QStringLiteral("invoke") : action},
                  {QStringLiteral("strategy"), QStringLiteral("agent-desktop")},
                  {QStringLiteral("controlId"), controlId}};
        const QVariantMap d = data.toMap();
        if (d.contains(QStringLiteral("value"))) (*trace)[QStringLiteral("value")] = d.value(QStringLiteral("value"));
        if (d.contains(QStringLiteral("delivery"))) (*trace)[QStringLiteral("delivery")] = d.value(QStringLiteral("delivery"));
    }
    return true;
}

} // namespace AgentDesktopCli
