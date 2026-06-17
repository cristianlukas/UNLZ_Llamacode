#include "AgentEventLog.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QUuid>

namespace {

QString baseDir(const QString &cwd)
{
    const QString root = cwd.trimmed().isEmpty() ? QDir::homePath() : cwd;
    const QString dir = QDir(root).filePath(QStringLiteral(".llamacode"));
    QDir().mkpath(dir);
    return dir;
}

}  // namespace

namespace AgentEventLog {

QString jsonlPath(const QString &cwd)
{
    return QDir(baseDir(cwd)).filePath(QStringLiteral("agent_events.jsonl"));
}

bool append(const QString &cwd, const QString &sessionId, const QString &kind,
            QJsonObject data)
{
    if (kind.trimmed().isEmpty()) return false;

    data[QStringLiteral("kind")] = kind;
    data[QStringLiteral("id")] = QUuid::createUuid().toString(QUuid::WithoutBraces);
    data[QStringLiteral("ts")] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
    if (!sessionId.isEmpty())
        data[QStringLiteral("sessionId")] = sessionId;

    QFile f(jsonlPath(cwd));
    if (!f.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text))
        return false;
    f.write(QJsonDocument(data).toJson(QJsonDocument::Compact));
    f.write("\n");
    return true;
}

}  // namespace AgentEventLog
