#include "AutomationArtifactStore.h"
#include "core/agent/BrowserTeach.h"
#include "core/tasks/TaskStore.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QUuid>

namespace {
bool writeJson(const QString &path, const QVariantMap &value)
{
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
    f.write(QJsonDocument(QJsonObject::fromVariantMap(value)).toJson(QJsonDocument::Indented));
    return true;
}
QVariantMap readJson(const QString &path)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) return {};
    return QJsonDocument::fromJson(f.readAll()).object().toVariantMap();
}
}

QString AutomationArtifactStore::rootDir()
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                        + QStringLiteral("/automations");
    QDir().mkpath(dir);
    return dir;
}

QString AutomationArtifactStore::artifactDir(const QString &id)
{
    return rootDir() + QLatin1Char('/') + TaskStore::sanitize(id);
}

QString AutomationArtifactStore::create(const QVariantMap &task, const QVariantMap &scope,
                                        const QVariantList &events, const QStringList &evidence,
                                        const QString &browserScript)
{
    QString id = TaskStore::sanitize(task.value(QStringLiteral("id")).toString());
    if (id.isEmpty()) id = QUuid::createUuid().toString(QUuid::WithoutBraces).left(12);
    const QString dir = artifactDir(id);
    QDir().mkpath(dir + QStringLiteral("/evidence"));
    const QString now = QDateTime::currentDateTimeUtc().toString(Qt::ISODate);
    QVariantMap manifest{
        {QStringLiteral("formatVersion"), FormatVersion},
        {QStringLiteral("id"), id},
        {QStringLiteral("taskId"), task.value(QStringLiteral("id"))},
        {QStringLiteral("name"), task.value(QStringLiteral("name"))},
        {QStringLiteral("objective"), task.value(QStringLiteral("description"))},
        {QStringLiteral("executionMode"), task.value(QStringLiteral("executionMode"), QStringLiteral("agent"))},
        {QStringLiteral("approvalPolicy"), task.value(QStringLiteral("approvalPolicy"), QStringLiteral("sensitive"))},
        {QStringLiteral("scope"), scope},
        {QStringLiteral("requiresVision"), task.value(QStringLiteral("executionMode")) == QLatin1String("desktop")},
        {QStringLiteral("trainedAt"), now},
        {QStringLiteral("status"), QStringLiteral("ready")}};
    QVariantList steps;
    int index = 1;
    for (const QVariant &value : events) {
        QVariantMap event = value.toMap();
        event[QStringLiteral("index")] = index++;
        if (event.contains(QStringLiteral("text")))
            event[QStringLiteral("text")] = redact(event.value(QStringLiteral("text")).toString());
        steps.append(event);
    }
    QVariantMap recipe{
        {QStringLiteral("formatVersion"), FormatVersion},
        {QStringLiteral("objective"), task.value(QStringLiteral("description"))},
        {QStringLiteral("prompt"), task.value(QStringLiteral("prePrompt"))},
        {QStringLiteral("steps"), steps},
        {QStringLiteral("evidence"), evidence},
        {QStringLiteral("successCriteria"), task.value(QStringLiteral("postPrompt"))}};
    if (!writeJson(dir + QStringLiteral("/manifest.json"), manifest)
        || !writeJson(dir + QStringLiteral("/recipe.json"), recipe))
        return {};
    if (!browserScript.isEmpty()) {
        QFile::remove(dir + QStringLiteral("/browser.mjs"));
        QFile::copy(browserScript, dir + QStringLiteral("/browser.mjs"));
    }
    return id;
}

QVariantMap AutomationArtifactStore::manifest(const QString &id)
{
    return readJson(artifactDir(id) + QStringLiteral("/manifest.json"));
}

QVariantMap AutomationArtifactStore::recipe(const QString &id)
{
    return readJson(artifactDir(id) + QStringLiteral("/recipe.json"));
}

QVariantList AutomationArtifactStore::timeline(const QString &id)
{
    return recipe(id).value(QStringLiteral("steps")).toList();
}

QString AutomationArtifactStore::importBrowserSkill(const QString &skillName, const QVariantMap &task)
{
    if (!BrowserTeach::hasSkill(skillName)) return {};
    QVariantList events{
        QVariantMap{{QStringLiteral("kind"), QStringLiteral("browser")},
                    {QStringLiteral("intent"), QStringLiteral("Reproducir y adaptar la demostración importada")},
                    {QStringLiteral("ref"), skillName},
                    {QStringLiteral("verification"), QStringLiteral("Verificar el objetivo de la Task")}}};
    QVariantMap browserTask = task;
    browserTask[QStringLiteral("executionMode")] = QStringLiteral("browserBackground");
    return create(browserTask, QVariantMap{{QStringLiteral("kind"), QStringLiteral("browser")}},
                  events, {}, BrowserTeach::skillPath(skillName));
}

bool AutomationArtifactStore::removeEvidence(const QString &id, const QString &fileName)
{
    const QString safe = QFileInfo(fileName).fileName();
    if (safe.isEmpty()) return false;
    return QFile::remove(artifactDir(id) + QStringLiteral("/evidence/") + safe);
}

QString AutomationArtifactStore::redact(const QString &text)
{
    QString out = text;
    static const QRegularExpression secrets(
        QStringLiteral("(?i)(password|passwd|token|secret|api[_ -]?key)\\s*[:=]\\s*\\S+"));
    out.replace(secrets, QStringLiteral("\\1=[REDACTED]"));
    return out;
}
