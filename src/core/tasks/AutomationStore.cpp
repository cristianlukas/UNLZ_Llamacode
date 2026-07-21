#include "AutomationStore.h"
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QDateTime>
#include <QUuid>
#include <QRegularExpression>

AutomationStore::AutomationStore(QObject *parent) : QAbstractListModel(parent)
{
    load();
}

int AutomationStore::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid()) return 0;
    return m_items.size();
}

QVariant AutomationStore::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_items.size())
        return {};
    const QVariantMap &a = m_items.at(index.row());
    switch (role) {
    case IdRole:                return a.value("id");
    case NameRole:              return a.value("name");
    case ProcessIdRole:         return a.value("processId");
    case ScheduleEnabledRole:   return a.value("scheduleEnabled", false);
    case ScheduleCronRole:      return a.value("scheduleCron");
    case ScheduleSpecRole:      return a.value("scheduleSpec");
    case SilentUnlessErrorRole: return a.value("silentUnlessError", false);
    case CreatedAtRole:         return a.value("createdAt");
    case UpdatedAtRole:         return a.value("updatedAt");
    case LastRunAtRole:         return a.value("lastRunAt");
    case LastRunStatusRole:     return a.value("lastRunStatus");
    case LastRunSummaryRole:    return a.value("lastRunSummary");
    default:                    return {};
    }
}

QHash<int, QByteArray> AutomationStore::roleNames() const
{
    return {
        { IdRole,                "id" },
        { NameRole,              "name" },
        { ProcessIdRole,         "processId" },
        { ScheduleEnabledRole,   "scheduleEnabled" },
        { ScheduleCronRole,      "scheduleCron" },
        { ScheduleSpecRole,      "scheduleSpec" },
        { SilentUnlessErrorRole, "silentUnlessError" },
        { CreatedAtRole,         "createdAt" },
        { UpdatedAtRole,         "updatedAt" },
        { LastRunAtRole,         "lastRunAt" },
        { LastRunStatusRole,     "lastRunStatus" },
        { LastRunSummaryRole,    "lastRunSummary" },
    };
}

QString AutomationStore::sanitize(const QString &name)
{
    QString s = name.trimmed().toLower();
    s.replace(QRegularExpression(QStringLiteral("[^a-z0-9_-]+")), QStringLiteral("-"));
    s.replace(QRegularExpression(QStringLiteral("-+")), QStringLiteral("-"));
    while (s.startsWith('-')) s.remove(0, 1);
    while (s.endsWith('-')) s.chop(1);
    return s;
}

int AutomationStore::indexOfId(const QString &id) const
{
    for (int i = 0; i < m_items.size(); ++i)
        if (m_items.at(i).value("id").toString() == id) return i;
    return -1;
}

QString AutomationStore::save(const QString &id, const QVariantMap &def)
{
    const QString now = QDateTime::currentDateTimeUtc().toString(Qt::ISODate);
    int row = id.isEmpty() ? -1 : indexOfId(id);

    QVariantMap a = (row >= 0) ? m_items.at(row) : QVariantMap{};
    a["name"]              = def.value("name", a.value("name"));
    a["processId"]         = def.value("processId", a.value("processId"));
    a["scheduleEnabled"]   = def.value("scheduleEnabled", a.value("scheduleEnabled", true));
    a["scheduleCron"]      = def.value("scheduleCron", a.value("scheduleCron"));
    a["scheduleSpec"]      = def.value("scheduleSpec", a.value("scheduleSpec", QVariantMap{}));
    a["silentUnlessError"] = def.value("silentUnlessError", a.value("silentUnlessError", false));
    // Workflow declarativo opcional. Las automatizaciones legacy siguen usando
    // processId; conservar ambos permite migracion gradual sin romper scheduler.
    a["workflow"]          = def.value("workflow", a.value("workflow", QVariantMap{}));
    a["updatedAt"]         = now;

    QString outId;
    if (row >= 0) {
        outId = id;
        m_items[row] = a;
        const QModelIndex mi = index(row);
        emit dataChanged(mi, mi);
    } else {
        outId = sanitize(def.value("name").toString());
        if (outId.isEmpty() || indexOfId(outId) >= 0)
            outId = QUuid::createUuid().toString(QUuid::WithoutBraces).left(8);
        a["id"]        = outId;
        a["createdAt"] = now;
        beginInsertRows({}, m_items.size(), m_items.size());
        m_items.append(a);
        endInsertRows();
        emit countChanged();
    }
    save();
    emit changed();
    return outId;
}

bool AutomationStore::remove(const QString &id)
{
    const int row = indexOfId(id);
    if (row < 0) return false;
    beginRemoveRows({}, row, row);
    m_items.removeAt(row);
    endRemoveRows();
    save();
    emit countChanged();
    emit changed();
    return true;
}

QVariantMap AutomationStore::get(const QString &id) const
{
    const int row = indexOfId(id);
    return (row >= 0) ? m_items.at(row) : QVariantMap{};
}

QVariantList AutomationStore::all() const
{
    QVariantList out;
    for (const QVariantMap &a : m_items) out.append(a);
    return out;
}

void AutomationStore::markRun(const QString &id, const QString &status, const QString &summary)
{
    const int row = indexOfId(id);
    if (row < 0) return;
    m_items[row]["lastRunStatus"] = status;
    m_items[row]["lastRunAt"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODate);
    if (!summary.isEmpty())
        m_items[row]["lastRunSummary"] = summary;
    const QModelIndex mi = index(row);
    emit dataChanged(mi, mi);
    save();
    emit changed();
}

int AutomationStore::pruneOrphans(const QStringList &validProcessIds)
{
    int removed = 0;
    for (int i = m_items.size() - 1; i >= 0; --i) {
        if (!validProcessIds.contains(m_items.at(i).value("processId").toString())) {
            beginRemoveRows({}, i, i);
            m_items.removeAt(i);
            endRemoveRows();
            ++removed;
        }
    }
    if (removed > 0) {
        save();
        emit countChanged();
        emit changed();
    }
    return removed;
}

void AutomationStore::refresh()
{
    beginResetModel();
    load();
    endResetModel();
    emit countChanged();
    emit changed();
}

QJsonObject AutomationStore::toJson(const QVariantMap &a)
{
    QJsonObject o;
    o["id"]                = a.value("id").toString();
    o["name"]              = a.value("name").toString();
    o["processId"]         = a.value("processId").toString();
    o["scheduleEnabled"]   = a.value("scheduleEnabled", true).toBool();
    o["scheduleCron"]      = a.value("scheduleCron").toString();
    o["scheduleSpec"]      = QJsonObject::fromVariantMap(a.value("scheduleSpec").toMap());
    o["silentUnlessError"] = a.value("silentUnlessError", false).toBool();
    o["workflow"]          = QJsonObject::fromVariantMap(a.value("workflow").toMap());
    o["createdAt"]         = a.value("createdAt").toString();
    o["updatedAt"]         = a.value("updatedAt").toString();
    o["lastRunAt"]         = a.value("lastRunAt").toString();
    o["lastRunStatus"]     = a.value("lastRunStatus").toString();
    o["lastRunSummary"]    = a.value("lastRunSummary").toString();
    return o;
}

QVariantMap AutomationStore::fromJson(const QJsonObject &obj)
{
    QVariantMap a;
    a["id"]                = obj.value("id").toString();
    a["name"]              = obj.value("name").toString();
    a["processId"]         = obj.value("processId").toString();
    a["scheduleEnabled"]   = obj.value("scheduleEnabled").toBool(true);
    a["scheduleCron"]      = obj.value("scheduleCron").toString();
    a["scheduleSpec"]      = obj.value("scheduleSpec").toObject().toVariantMap();
    a["silentUnlessError"] = obj.value("silentUnlessError").toBool(false);
    a["workflow"]          = obj.value("workflow").toObject().toVariantMap();
    a["createdAt"]         = obj.value("createdAt").toString();
    a["updatedAt"]         = obj.value("updatedAt").toString();
    a["lastRunAt"]         = obj.value("lastRunAt").toString();
    a["lastRunStatus"]     = obj.value("lastRunStatus").toString();
    a["lastRunSummary"]    = obj.value("lastRunSummary").toString();
    return a;
}

QString AutomationStore::storagePath() const
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                        + QStringLiteral("/automations");
    QDir().mkpath(dir);
    return dir + QStringLiteral("/automations.json");
}

void AutomationStore::load()
{
    m_items.clear();
    QFile f(storagePath());
    if (!f.open(QIODevice::ReadOnly)) return;
    const QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
    f.close();
    for (const QJsonValue &v : doc.array())
        m_items.append(fromJson(v.toObject()));
}

void AutomationStore::save() const
{
    QJsonArray arr;
    for (const QVariantMap &a : m_items)
        arr.append(toJson(a));
    QFile f(storagePath());
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return;
    f.write(QJsonDocument(arr).toJson(QJsonDocument::Indented));
    f.close();
}
