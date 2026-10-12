#include "MasterCli.h"
#include <QProcess>
#include <QStandardPaths>
#include <QFileInfo>
#include <QFutureWatcher>
#include <QtConcurrent>

QString MasterCli::label(const QString &name)
{
    if (name == QLatin1String("claude")) return QStringLiteral("Claude Code");
    if (name == QLatin1String("codex"))  return QStringLiteral("Codex CLI");
    return name;
}

QString MasterCli::installCommand(const QString &name)
{
    if (name == QLatin1String("claude"))
        return QStringLiteral("npm install -g @anthropic-ai/claude-code");
    if (name == QLatin1String("codex"))
        return QStringLiteral("npm install -g @openai/codex");
    return QString();
}

QString MasterCli::resolvePath(const QString &name)
{
    return status(name).value(QStringLiteral("path")).toString();
}

QVariantMap MasterCli::status(const QString &name, bool force)
{
    if (!force && m_cache.contains(name))
        return m_cache.value(name);
    const QVariantMap out = probe(name);
    m_cache.insert(name, out);
    return out;
}

QVariantMap MasterCli::requestStatus(const QString &name, bool force)
{
    if (!force && m_cache.contains(name))
        return m_cache.value(name);

    QVariantMap placeholder = m_cache.value(name);
    if (placeholder.isEmpty()) {
        placeholder[QStringLiteral("name")]           = name;
        placeholder[QStringLiteral("label")]          = label(name);
        placeholder[QStringLiteral("installCommand")] = installCommand(name);
        placeholder[QStringLiteral("installed")]      = false;
        placeholder[QStringLiteral("version")]        = QString();
        placeholder[QStringLiteral("path")]           = QString();
        placeholder[QStringLiteral("probeOk")]        = false;
        placeholder[QStringLiteral("capabilities")]   = QStringList();
    }
    placeholder[QStringLiteral("probing")] = true;

    if (m_probing.contains(name))
        return placeholder;
    m_probing.insert(name);

    auto *watcher = new QFutureWatcher<QVariantMap>(this);
    connect(watcher, &QFutureWatcher<QVariantMap>::finished, this, [this, watcher, name]() {
        m_cache.insert(name, watcher->result());
        m_probing.remove(name);
        watcher->deleteLater();
        emit statusChanged(name);
    });
    watcher->setFuture(QtConcurrent::run([name]() { return MasterCli::probe(name); }));
    return placeholder;
}

QVariantMap MasterCli::probe(const QString &name)
{
    QVariantMap out;
    out[QStringLiteral("name")]           = name;
    out[QStringLiteral("label")]          = label(name);
    out[QStringLiteral("installCommand")] = installCommand(name);
    out[QStringLiteral("installed")]      = false;
    out[QStringLiteral("version")]        = QString();
    out[QStringLiteral("path")]           = QString();
    out[QStringLiteral("probeOk")]        = false;
    out[QStringLiteral("capabilities")]   = QStringList();

    // Resolver binario en PATH (Windows agrega .cmd/.exe automáticamente).
    QString exe = QStandardPaths::findExecutable(name);
    if (exe.isEmpty())
        return out;

    // Probar `--version` con timeout corto; capturar primera línea no vacía.
    QProcess p;
    p.start(exe, {QStringLiteral("--version")});
    QString version;
    if (p.waitForStarted(3000) && p.waitForFinished(8000)) {
        const QString raw = QString::fromUtf8(p.readAllStandardOutput())
                          + QString::fromUtf8(p.readAllStandardError());
        for (const QString &line : raw.split(QLatin1Char('\n'))) {
            const QString t = line.trimmed();
            if (!t.isEmpty()) { version = t; break; }
        }
    }

    out[QStringLiteral("installed")] = true;
    out[QStringLiteral("path")]      = exe;
    out[QStringLiteral("version")]   = version.isEmpty()
        ? QStringLiteral("instalado") : version;

    // La UI y el supervisor pueden advertir cuando un wrapper/versión no
    // expone el contrato esperado, sin asumir que todo binario con ese nombre
    // es compatible. Nunca se ejecutan acciones de escritura en este probe.
    QProcess help;
    QStringList capabilities;
    help.start(exe, {QStringLiteral("--help")});
    if (help.waitForStarted(3000) && help.waitForFinished(8000)) {
        const QString raw = QString::fromUtf8(help.readAllStandardOutput())
                          + QString::fromUtf8(help.readAllStandardError());
        if (!raw.trimmed().isEmpty()) {
            out[QStringLiteral("probeOk")] = true;
            const QStringList markers = name == QLatin1String("claude")
                ? QStringList{QStringLiteral("-p"), QStringLiteral("--permission-mode"),
                              QStringLiteral("--model")}
                : QStringList{QStringLiteral("exec"), QStringLiteral("--model"),
                              QStringLiteral("--full-auto")};
            for (const QString &marker : markers)
                if (raw.contains(marker)) capabilities << marker;
        }
    }
    out[QStringLiteral("capabilities")] = capabilities;
    return out;
}
