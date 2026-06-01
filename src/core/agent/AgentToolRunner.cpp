#include "AgentToolRunner.h"
#include "McpClient.h"
#include "LlamaAgentBackend.h"   // LlamaAgentBackend::makeDiff (static)

#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QProcess>

static const QString kMcpPrefix = QStringLiteral("mcp__");

AgentToolRunner::AgentToolRunner(QObject *parent) : QObject(parent) {}
AgentToolRunner::~AgentToolRunner() { shutdown(); }

void AgentToolRunner::setConfined(bool confined) { m_confined = confined; }

void AgentToolRunner::shutdown()
{
    for (McpClient *c : std::as_const(m_mcp)) { c->shutdown(); delete c; }
    m_mcp.clear();
}

void AgentToolRunner::initServers(const QVariantList &cfg, const QString &cwd)
{
    shutdown();
    for (const QVariant &v : cfg) {
        const QVariantMap s = v.toMap();
        if (!s.value(QStringLiteral("enabled"), true).toBool()) continue;
        if (s.value(QStringLiteral("type"), QStringLiteral("local")).toString()
                != QLatin1String("local")) continue;
        const QString name = s.value(QStringLiteral("name")).toString();
        const QString cmd  = s.value(QStringLiteral("command")).toString();
        if (name.isEmpty() || cmd.isEmpty()) continue;

        auto *c = new McpClient(name);   // sin parent: vive en este hilo worker
        connect(c, &McpClient::logAppended, this, &AgentToolRunner::logAppended);
        if (c->start(cmd, cwd)) m_mcp.append(c);
        else delete c;
    }

    QVariantList defs;
    for (McpClient *c : m_mcp) {
        for (const McpClient::ToolDef &t : c->tools()) {
            defs.append(QVariantMap{
                {QStringLiteral("server"), c->serverName()},
                {QStringLiteral("name"), t.name},
                {QStringLiteral("description"), t.description},
                {QStringLiteral("schema"), QVariant::fromValue(
                     QString::fromUtf8(QJsonDocument(t.inputSchema).toJson(QJsonDocument::Compact)))}
            });
        }
    }
    emit serversReady(defs);
}

void AgentToolRunner::executeTool(const QString &callId, const QString &name,
                                  const QString &argsJson, const QString &cwd)
{
    const QJsonObject args = QJsonDocument::fromJson(argsJson.toUtf8()).object();
    QVariantMap out{{QStringLiteral("callId"), callId}, {QStringLiteral("name"), name}};
    bool ok = false;
    QString result;

    if (name.startsWith(kMcpPrefix)) {
        // mcp__<server>__<tool>
        const QString rest = name.mid(kMcpPrefix.size());
        const int sep = rest.indexOf(QStringLiteral("__"));
        McpClient *c = nullptr;
        QString bare;
        if (sep >= 0) {
            const QString server = rest.left(sep);
            bare = rest.mid(sep + 2);
            for (McpClient *cc : m_mcp)
                if (cc->serverName() == server) { c = cc; break; }
        }
        if (!c) result = QStringLiteral("[mcp: server/tool no encontrado: %1]").arg(name);
        else    result = c->callTool(bare, args, &ok);
    } else {
        result = runNative(name, args, cwd, out, &ok);
    }

    out[QStringLiteral("result")] = result;
    out[QStringLiteral("ok")] = ok;
    emit toolExecuted(out);
}

// Ejecución de tools nativas (idéntica a la vieja LlamaAgentBackend::executeTool,
// pero sin tocar UI: el write devuelve metadata para que el main arme diff/snapshot).
QString AgentToolRunner::runNative(const QString &name, const QJsonObject &args,
                                   const QString &cwd, QVariantMap &out, bool *ok)
{
    if (ok) *ok = false;
    const QDir base(cwd);
    auto resolve = [&](const QString &rel) { return QDir::cleanPath(base.absoluteFilePath(rel)); };
    // En modo "Super Agente" (no confinado) se permite cualquier ruta del disco.
    auto inProject = [&](const QString &abs) {
        if (!m_confined) return true;
        const QString root = QDir::cleanPath(base.absolutePath());
        return abs == root || abs.startsWith(root + QStringLiteral("/"))
               || abs.startsWith(root + QStringLiteral("\\"));
    };

    if (name == QLatin1String("read_file")) {
        const QString abs = resolve(args.value(QStringLiteral("path")).toString());
        if (!inProject(abs)) return QStringLiteral("[ruta fuera del proyecto]");
        QFile f(abs);
        if (!f.open(QIODevice::ReadOnly)) return QStringLiteral("[no se pudo abrir: %1]").arg(abs);
        const QByteArray raw = f.read(256 * 1024);
        if (ok) *ok = true;
        return QString::fromUtf8(raw);
    }
    if (name == QLatin1String("list_dir")) {
        const QString abs = resolve(args.value(QStringLiteral("path")).toString());
        if (!inProject(abs)) return QStringLiteral("[ruta fuera del proyecto]");
        QDir d(abs);
        if (!d.exists()) return QStringLiteral("[no existe: %1]").arg(abs);
        QStringList outList;
        const auto entries = d.entryInfoList(QDir::NoDotAndDotDot | QDir::AllEntries, QDir::Name);
        for (const QFileInfo &fi : entries)
            outList << (fi.isDir() ? fi.fileName() + QStringLiteral("/") : fi.fileName());
        if (ok) *ok = true;
        return outList.join(QLatin1Char('\n'));
    }
    if (name == QLatin1String("grep")) {
        const QString pattern = args.value(QStringLiteral("pattern")).toString();
        const QString sub = args.value(QStringLiteral("path")).toString();
        const QString rootAbs = resolve(sub);
        if (!inProject(rootAbs)) return QStringLiteral("[ruta fuera del proyecto]");
        QStringList hits;
        QDirIterator it(rootAbs, QDir::Files, QDirIterator::Subdirectories);
        int scanned = 0;
        while (it.hasNext() && hits.size() < 100 && scanned < 2000) {
            const QString fp = it.next();
            ++scanned;
            QFile f(fp);
            if (!f.open(QIODevice::ReadOnly)) continue;
            const QByteArray raw = f.read(512 * 1024);
            if (raw.contains('\0')) continue;
            const QStringList lines = QString::fromUtf8(raw).split(QLatin1Char('\n'));
            for (int i = 0; i < lines.size(); ++i) {
                if (lines[i].contains(pattern, Qt::CaseInsensitive)) {
                    hits << QStringLiteral("%1:%2: %3")
                            .arg(base.relativeFilePath(fp)).arg(i + 1).arg(lines[i].trimmed());
                    if (hits.size() >= 100) break;
                }
            }
        }
        if (ok) *ok = true;
        return hits.isEmpty() ? QStringLiteral("[sin coincidencias]") : hits.join(QLatin1Char('\n'));
    }
    if (name == QLatin1String("write_file")) {
        const QString rel = args.value(QStringLiteral("path")).toString();
        const QString abs = resolve(rel);
        if (!inProject(abs)) return QStringLiteral("[ruta fuera del proyecto]");

        QFile prev(abs);
        const bool existed = prev.exists();
        QByteArray oldContent;
        if (existed && prev.open(QIODevice::ReadOnly)) { oldContent = prev.read(4 * 1024 * 1024); prev.close(); }

        QDir().mkpath(QFileInfo(abs).absolutePath());
        QFile f(abs);
        if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate))
            return QStringLiteral("[no se pudo escribir: %1]").arg(abs);
        const QByteArray data = args.value(QStringLiteral("content")).toString().toUtf8();
        f.write(data);
        f.close();
        if (ok) *ok = true;

        // Metadata para que el main arme el snapshot (revert) y el mensaje diff.
        out[QStringLiteral("isWrite")]      = true;
        out[QStringLiteral("relPath")]      = base.relativeFilePath(abs);
        out[QStringLiteral("absPath")]      = abs;
        out[QStringLiteral("existed")]      = existed;
        out[QStringLiteral("oldContentB64")] = QString::fromLatin1(oldContent.toBase64());
        out[QStringLiteral("diff")] = LlamaAgentBackend::makeDiff(QString::fromUtf8(oldContent),
                                                              QString::fromUtf8(data));
        return QStringLiteral("[escrito %1 bytes en %2]").arg(data.size()).arg(rel);
    }
    if (name == QLatin1String("run_shell")) {
        const QString command = args.value(QStringLiteral("command")).toString();
        QProcess proc;
        proc.setWorkingDirectory(cwd);
        proc.setProcessChannelMode(QProcess::MergedChannels);
#ifdef Q_OS_WIN
        // No usar el arg-list de QProcess para cmd: re-cita los argumentos y
        // rompe las comillas anidadas (p.ej. python -c "import x; print('y')")
        // → cmd recibe comillas mal cerradas → SyntaxError. setNativeArguments
        // pasa la línea cruda y deja que cmd.exe la parsee tal cual.
        proc.setProgram(QStringLiteral("cmd"));
        proc.setNativeArguments(QStringLiteral("/c ") + command);
        proc.start();
#else
        proc.start(QStringLiteral("sh"), {QStringLiteral("-c"), command});
#endif
        if (!proc.waitForStarted(5000)) return QStringLiteral("[no se pudo iniciar el comando]");
        proc.waitForFinished(30000);
        const QString outStr = QString::fromUtf8(proc.readAll());
        if (ok) *ok = true;
        return QStringLiteral("exit=%1\n%2").arg(proc.exitCode()).arg(outStr.left(64 * 1024));
    }
    return QStringLiteral("[tool desconocida: %1]").arg(name);
}
