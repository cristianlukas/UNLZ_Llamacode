#include "TaskStore.h"
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QDateTime>
#include <QUuid>
#include <QRegularExpression>

TaskStore::TaskStore(QObject *parent) : QAbstractListModel(parent)
{
    load();
}

int TaskStore::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid()) return 0;
    return m_items.size();
}

QVariant TaskStore::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_items.size())
        return {};
    const QVariantMap &t = m_items.at(index.row());
    switch (role) {
    case IdRole:              return t.value("id");
    case NameRole:            return t.value("name");
    case DescriptionRole:     return t.value("description");
    case ProfileIdRole:       return t.value("profileId");
    case StepsRole:           return t.value("steps");
    case StepCountRole:       return t.value("steps").toList().size();
    case ScheduleEnabledRole: return t.value("scheduleEnabled", false);
    case ScheduleCronRole:    return t.value("scheduleCron");
    case CreatedAtRole:       return t.value("createdAt");
    case UpdatedAtRole:       return t.value("updatedAt");
    case LastRunAtRole:       return t.value("lastRunAt");
    case LastRunStatusRole:   return t.value("lastRunStatus");
    case LastRunSummaryRole:  return t.value("lastRunSummary");
    case PrePromptRole:       return t.value("prePrompt");
    case PostPromptRole:      return t.value("postPrompt");
    case SilentUnlessErrorRole: return t.value("silentUnlessError", false);
    default:                  return {};
    }
}

QHash<int, QByteArray> TaskStore::roleNames() const
{
    return {
        { IdRole,              "id" },
        { NameRole,            "name" },
        { DescriptionRole,     "description" },
        { ProfileIdRole,       "profileId" },
        { StepsRole,           "steps" },
        { StepCountRole,       "stepCount" },
        { ScheduleEnabledRole, "scheduleEnabled" },
        { ScheduleCronRole,    "scheduleCron" },
        { CreatedAtRole,       "createdAt" },
        { UpdatedAtRole,       "updatedAt" },
        { LastRunAtRole,       "lastRunAt" },
        { LastRunStatusRole,   "lastRunStatus" },
        { LastRunSummaryRole,  "lastRunSummary" },
        { PrePromptRole,       "prePrompt" },
        { PostPromptRole,      "postPrompt" },
        { SilentUnlessErrorRole, "silentUnlessError" },
    };
}

QString TaskStore::sanitize(const QString &name)
{
    QString s = name.trimmed().toLower();
    s.replace(QRegularExpression(QStringLiteral("[^a-z0-9_-]+")), QStringLiteral("-"));
    s.replace(QRegularExpression(QStringLiteral("-+")), QStringLiteral("-"));
    while (s.startsWith('-')) s.remove(0, 1);
    while (s.endsWith('-')) s.chop(1);
    return s;
}

int TaskStore::indexOfId(const QString &id) const
{
    for (int i = 0; i < m_items.size(); ++i)
        if (m_items.at(i).value("id").toString() == id) return i;
    return -1;
}

QString TaskStore::save(const QString &id, const QVariantMap &def)
{
    const QString now = QDateTime::currentDateTimeUtc().toString(Qt::ISODate);
    int row = id.isEmpty() ? -1 : indexOfId(id);

    QVariantMap t = (row >= 0) ? m_items.at(row) : QVariantMap{};
    t["name"]            = def.value("name", t.value("name"));
    t["description"]     = def.value("description", t.value("description"));
    t["profileId"]       = def.value("profileId", t.value("profileId"));
    t["prePrompt"]       = def.value("prePrompt", t.value("prePrompt"));
    t["postPrompt"]      = def.value("postPrompt", t.value("postPrompt"));
    t["silentUnlessError"] = def.value("silentUnlessError", t.value("silentUnlessError", false));
    t["steps"]           = def.value("steps", t.value("steps", QVariantList{}));
    t["scheduleEnabled"] = def.value("scheduleEnabled", t.value("scheduleEnabled", false));
    t["scheduleCron"]    = def.value("scheduleCron", t.value("scheduleCron"));
    t["updatedAt"]       = now;

    QString outId;
    if (row >= 0) {
        outId = id;
        m_items[row] = t;
        const QModelIndex mi = index(row);
        emit dataChanged(mi, mi);
    } else {
        outId = sanitize(def.value("name").toString());
        if (outId.isEmpty() || indexOfId(outId) >= 0)
            outId = QUuid::createUuid().toString(QUuid::WithoutBraces).left(8);
        t["id"]        = outId;
        t["createdAt"] = now;
        beginInsertRows({}, m_items.size(), m_items.size());
        m_items.append(t);
        endInsertRows();
        emit countChanged();
    }
    save();
    emit changed();
    return outId;
}

bool TaskStore::remove(const QString &id)
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

QVariantMap TaskStore::get(const QString &id) const
{
    const int row = indexOfId(id);
    return (row >= 0) ? m_items.at(row) : QVariantMap{};
}

QVariantList TaskStore::all() const
{
    QVariantList out;
    for (const QVariantMap &t : m_items) out.append(t);
    return out;
}

QString TaskStore::duplicate(const QString &id)
{
    const int row = indexOfId(id);
    if (row < 0) return {};
    QVariantMap t = m_items.at(row);
    t.remove("id");
    t["name"] = t.value("name").toString() + QStringLiteral(" (copia)");
    return save({}, t);
}

void TaskStore::markRun(const QString &id, const QString &status, const QString &summary)
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

void TaskStore::refresh()
{
    beginResetModel();
    load();
    endResetModel();
    emit countChanged();
    emit changed();
}

QString TaskStore::composePrompt(const QVariantMap &task)
{
    QStringList out;
    const QString name = task.value("name").toString().trimmed();
    const QString desc = task.value("description").toString().trimmed();

    out << QStringLiteral("Ejecutá la siguiente Task guardada de forma autónoma.");
    const QString pre = task.value("prePrompt").toString().trimmed();
    if (!pre.isEmpty()) {
        out << QString();
        out << QStringLiteral("Preprompt operativo:");
        out << pre;
    }
    if (!name.isEmpty())
        out << QStringLiteral("Task: %1").arg(name);
    if (!desc.isEmpty())
        out << QStringLiteral("Objetivo: %1").arg(desc);

    const QVariantList steps = task.value("steps").toList();
    if (!steps.isEmpty()) {
        out << QString();
        out << QStringLiteral("Pasos de referencia (grabados en una corrida previa):");
        int i = 1;
        for (const QVariant &sv : steps) {
            const QVariantMap s = sv.toMap();
            const QString kind = s.value("kind").toString();
            const QString intent = s.value("intent").toString().trimmed();
            const QString ref = s.value("ref").toString().trimmed();
            QString line = QStringLiteral("%1. [%2] %3").arg(i++)
                               .arg(kind.isEmpty() ? QStringLiteral("instruction") : kind, intent);
            if (!ref.isEmpty())
                line += QStringLiteral(" (ref: %1)").arg(ref);
            out << line;
        }
    }

    out << QString();
    out << QStringLiteral("IMPORTANTE: los pasos son una guía, no un guion literal. "
                          "Entendé QUÉ se busca y POR QUÉ en cada paso. Si un botón, "
                          "elemento o archivo cambió de lugar o de nombre, adaptate y "
                          "logrueá el objetivo igual usando tus herramientas. Si algo "
                          "es ambiguo o riesgoso, explicá qué hiciste al terminar. "
                          "Si el objetivo requiere consultar una web, ejecutar comandos, "
                          "leer archivos o usar otra fuente externa, usá herramientas y "
                          "no respondas de memoria. Si no podés usar herramientas o no "
                          "podés verificar el dato, decilo explícitamente como error.");
    return out.join(QLatin1Char('\n'));
}

QString TaskStore::composePostPrompt(const QVariantMap &task)
{
    const QString post = task.value("postPrompt").toString().trimmed();
    if (post.isEmpty()) return {};
    QStringList out;
    out << QStringLiteral("Postprompt de verificación de la Task recién ejecutada.");
    out << QStringLiteral("Revisá el resultado anterior con criterio agéntico. Si detectás un problema, explicá el error concreto y qué habría que corregir; si está correcto, resumí la evidencia de éxito.");
    out << QString();
    out << post;
    return out.join(QLatin1Char('\n'));
}

QJsonObject TaskStore::toJson(const QVariantMap &task)
{
    QJsonObject o;
    o["id"]              = task.value("id").toString();
    o["name"]            = task.value("name").toString();
    o["description"]     = task.value("description").toString();
    o["profileId"]       = task.value("profileId").toString();
    o["prePrompt"]       = task.value("prePrompt").toString();
    o["postPrompt"]      = task.value("postPrompt").toString();
    o["silentUnlessError"] = task.value("silentUnlessError", false).toBool();
    o["scheduleEnabled"] = task.value("scheduleEnabled", false).toBool();
    o["scheduleCron"]    = task.value("scheduleCron").toString();
    o["createdAt"]       = task.value("createdAt").toString();
    o["updatedAt"]       = task.value("updatedAt").toString();
    o["lastRunAt"]       = task.value("lastRunAt").toString();
    o["lastRunStatus"]   = task.value("lastRunStatus").toString();
    o["lastRunSummary"]  = task.value("lastRunSummary").toString();

    QJsonArray steps;
    for (const QVariant &sv : task.value("steps").toList()) {
        const QVariantMap s = sv.toMap();
        QJsonObject js;
        js["kind"]   = s.value("kind").toString();
        js["intent"] = s.value("intent").toString();
        js["ref"]    = s.value("ref").toString();
        steps.append(js);
    }
    o["steps"] = steps;
    return o;
}

QVariantMap TaskStore::fromJson(const QJsonObject &obj)
{
    QVariantMap t;
    t["id"]              = obj.value("id").toString();
    t["name"]            = obj.value("name").toString();
    t["description"]     = obj.value("description").toString();
    t["profileId"]       = obj.value("profileId").toString();
    t["prePrompt"]       = obj.value("prePrompt").toString();
    t["postPrompt"]      = obj.value("postPrompt").toString();
    t["silentUnlessError"] = obj.value("silentUnlessError").toBool(false);
    t["scheduleEnabled"] = obj.value("scheduleEnabled").toBool(false);
    t["scheduleCron"]    = obj.value("scheduleCron").toString();
    t["createdAt"]       = obj.value("createdAt").toString();
    t["updatedAt"]       = obj.value("updatedAt").toString();
    t["lastRunAt"]       = obj.value("lastRunAt").toString();
    t["lastRunStatus"]   = obj.value("lastRunStatus").toString();
    t["lastRunSummary"]  = obj.value("lastRunSummary").toString();

    QVariantList steps;
    for (const QJsonValue &sv : obj.value("steps").toArray()) {
        const QJsonObject js = sv.toObject();
        QVariantMap s;
        s["kind"]   = js.value("kind").toString();
        s["intent"] = js.value("intent").toString();
        s["ref"]    = js.value("ref").toString();
        steps.append(s);
    }
    t["steps"] = steps;
    return t;
}

QString TaskStore::storagePath() const
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                        + QStringLiteral("/tasks");
    QDir().mkpath(dir);
    return dir + QStringLiteral("/tasks.json");
}

void TaskStore::load()
{
    m_items.clear();
    QFile f(storagePath());
    if (!f.open(QIODevice::ReadOnly)) return;
    const QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
    f.close();
    for (const QJsonValue &v : doc.array())
        m_items.append(fromJson(v.toObject()));
}

void TaskStore::save() const
{
    QJsonArray arr;
    for (const QVariantMap &t : m_items)
        arr.append(toJson(t));
    QFile f(storagePath());
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return;
    f.write(QJsonDocument(arr).toJson(QJsonDocument::Indented));
    f.close();
}
