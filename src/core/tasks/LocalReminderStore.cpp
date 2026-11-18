#include "LocalReminderStore.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLockFile>
#include <QMutex>
#include <QMutexLocker>
#include <QRegularExpression>
#include <QSaveFile>
#include <QStandardPaths>
#include <QTimer>
#include <QUuid>

namespace {

constexpr int kMaxReminders = 500;
QMutex g_storeMutex;
QString g_testFilePath;

QString storePath()
{
    if (!g_testFilePath.isEmpty()) return g_testFilePath;
    QString root = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    if (root.isEmpty()) root = QDir::homePath() + QStringLiteral("/.llamacode");
    return QDir(root).filePath(QStringLiteral("reminders/reminders.json"));
}

bool readRows(const QString &path, QJsonArray *rows, QString *error)
{
    QFile file(path);
    if (!file.exists()) {
        *rows = {};
        return true;
    }
    if (!file.open(QIODevice::ReadOnly)) {
        if (error) *error = QStringLiteral("No pude leer el archivo local de recordatorios.");
        return false;
    }
    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isArray()) {
        if (error) *error = QStringLiteral("El archivo local de recordatorios no tiene formato válido.");
        return false;
    }
    *rows = document.array();
    return true;
}

bool writeRows(const QString &path, const QJsonArray &rows, QString *error)
{
    if (!QDir().mkpath(QFileInfo(path).absolutePath())) {
        if (error) *error = QStringLiteral("No pude crear la carpeta local de recordatorios.");
        return false;
    }
    QSaveFile file(path);
    const QByteArray encoded = QJsonDocument(rows).toJson(QJsonDocument::Compact);
    if (!file.open(QIODevice::WriteOnly)
        || file.write(encoded) != encoded.size() || !file.commit()) {
        if (error) *error = QStringLiteral("No pude guardar el recordatorio de forma segura.");
        return false;
    }
    return true;
}

bool lockStore(QLockFile *lock, QString *error)
{
    lock->setStaleLockTime(30000);
    if (lock->tryLock(2000)) return true;
    if (error) *error = QStringLiteral("El archivo de recordatorios está ocupado; reintentá en unos segundos.");
    return false;
}

QVariantMap rowMap(const QJsonValue &value)
{
    return value.toObject().toVariantMap();
}

} // namespace

bool LocalReminderStore::parseDueAt(const QString &value, QDateTime *result,
                                    QString *error)
{
    static const QRegularExpression explicitZone(QStringLiteral("(?:Z|[+-]\\d{2}:\\d{2})$"),
                                                 QRegularExpression::CaseInsensitiveOption);
    if (value.size() > 40 || !explicitZone.match(value).hasMatch()) {
        if (error) *error = QStringLiteral("Indicá fecha y hora RFC3339 con zona horaria, por ejemplo 2026-11-18T15:30:00-03:00.");
        return false;
    }
    QDateTime dateTime = QDateTime::fromString(value, Qt::ISODateWithMs);
    if (!dateTime.isValid()) dateTime = QDateTime::fromString(value, Qt::ISODate);
    if (!dateTime.isValid()) {
        if (error) *error = QStringLiteral("La fecha y hora del recordatorio no son válidas.");
        return false;
    }
    const QDateTime now = QDateTime::currentDateTimeUtc();
    const QDateTime utc = dateTime.toUTC();
    if (utc <= now.addSecs(10) || utc > now.addYears(5)) {
        if (error) *error = QStringLiteral("El recordatorio debe ser futuro (más de 10 segundos) y estar dentro de los próximos cinco años.");
        return false;
    }
    if (result) *result = dateTime;
    return true;
}

QString LocalReminderStore::create(const QString &dueAt, const QString &title,
                                   const QString &note, const QString &idempotencyKey,
                                   bool *duplicate, QString *error)
{
    if (duplicate) *duplicate = false;
    QDateTime dueDateTime;
    if (!parseDueAt(dueAt, &dueDateTime, error)) return {};
    static const QRegularExpression unsafeText(QStringLiteral("[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]"));
    static const QRegularExpression validIdempotencyKey(QStringLiteral("^[0-9a-f]{64}$"));
    const QString cleanTitle = title.trimmed();
    if (cleanTitle.isEmpty() || cleanTitle.size() > 160 || unsafeText.match(cleanTitle).hasMatch()
        || note.size() > 1000 || unsafeText.match(note).hasMatch()
        || !validIdempotencyKey.match(idempotencyKey).hasMatch()) {
        if (error) *error = QStringLiteral("El título, la nota o la clave de deduplicación del recordatorio no son válidos.");
        return {};
    }

    QMutexLocker<QMutex> locker(&g_storeMutex);
    const QString path = storePath();
    QDir().mkpath(QFileInfo(path).absolutePath());
    QLockFile lock(path + QStringLiteral(".lock"));
    if (!lockStore(&lock, error)) return {};
    QJsonArray rows;
    if (!readRows(path, &rows, error)) return {};
    for (const QJsonValue &value : rows) {
        const QJsonObject row = value.toObject();
        if (row.value(QStringLiteral("idempotencyKey")).toString() != idempotencyKey) continue;
        if (row.value(QStringLiteral("dueAtMs")).toDouble() != dueDateTime.toMSecsSinceEpoch()
            || row.value(QStringLiteral("title")).toString() != cleanTitle
            || row.value(QStringLiteral("note")).toString() != note.trimmed()) {
            if (error) *error = QStringLiteral("La clave de deduplicación ya se usó para otro recordatorio.");
            return {};
        }
        if (duplicate) *duplicate = true;
        return row.value(QStringLiteral("id")).toString();
    }
    if (rows.size() >= kMaxReminders) {
        if (error) *error = QStringLiteral("Hay 500 recordatorios guardados; cancelá o limpiá algunos antes de agregar otro.");
        return {};
    }

    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    rows.append(QJsonObject{
        {QStringLiteral("id"), id},
        {QStringLiteral("title"), cleanTitle},
        {QStringLiteral("note"), note.trimmed()},
        {QStringLiteral("dueAt"), dueDateTime.toString(Qt::ISODateWithMs)},
        {QStringLiteral("dueAtMs"), static_cast<double>(dueDateTime.toMSecsSinceEpoch())},
        {QStringLiteral("status"), QStringLiteral("pending")},
        {QStringLiteral("idempotencyKey"), idempotencyKey},
        {QStringLiteral("createdAt"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)}});
    if (!writeRows(path, rows, error)) return {};
    return id;
}

QVariantList LocalReminderStore::all(QString *error)
{
    QMutexLocker<QMutex> locker(&g_storeMutex);
    const QString path = storePath();
    QDir().mkpath(QFileInfo(path).absolutePath());
    QLockFile lock(path + QStringLiteral(".lock"));
    if (!lockStore(&lock, error)) return {};
    QJsonArray rows;
    if (!readRows(path, &rows, error)) return {};
    QVariantList result;
    for (const QJsonValue &value : rows)
        result.append(rowMap(value));
    return result;
}

bool LocalReminderStore::cancel(const QString &id, QString *error)
{
    if (id.trimmed().isEmpty()) {
        if (error) *error = QStringLiteral("Falta el ID del recordatorio.");
        return false;
    }
    QMutexLocker<QMutex> locker(&g_storeMutex);
    const QString path = storePath();
    QDir().mkpath(QFileInfo(path).absolutePath());
    QLockFile lock(path + QStringLiteral(".lock"));
    if (!lockStore(&lock, error)) return false;
    QJsonArray rows;
    if (!readRows(path, &rows, error)) return false;
    bool found = false;
    for (qsizetype i = 0; i < rows.size(); ++i) {
        QJsonObject row = rows.at(i).toObject();
        if (row.value(QStringLiteral("id")).toString() != id) continue;
        found = true;
        if (row.value(QStringLiteral("status")).toString() != QLatin1String("pending")) {
            if (error) *error = QStringLiteral("Sólo se pueden cancelar recordatorios pendientes.");
            return false;
        }
        row.insert(QStringLiteral("status"), QStringLiteral("cancelled"));
        row.insert(QStringLiteral("cancelledAt"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
        rows.replace(i, row);
        break;
    }
    if (!found) {
        if (error) *error = QStringLiteral("No encontré ese recordatorio.");
        return false;
    }
    return writeRows(path, rows, error);
}

QVariantList LocalReminderStore::takeDue(const QDateTime &nowUtc, QString *error)
{
    QMutexLocker<QMutex> locker(&g_storeMutex);
    const QString path = storePath();
    QDir().mkpath(QFileInfo(path).absolutePath());
    QLockFile lock(path + QStringLiteral(".lock"));
    if (!lockStore(&lock, error)) return {};
    QJsonArray rows;
    if (!readRows(path, &rows, error)) return {};
    const qint64 nowMs = nowUtc.toUTC().toMSecsSinceEpoch();
    QVariantList due;
    bool changed = false;
    for (qsizetype i = 0; i < rows.size(); ++i) {
        QJsonObject row = rows.at(i).toObject();
        const QString status = row.value(QStringLiteral("status")).toString();
        if ((status != QLatin1String("pending") && status != QLatin1String("dispatching"))
            || row.value(QStringLiteral("dueAtMs")).toDouble() > nowMs)
            continue;
        if (status == QLatin1String("pending")) {
            row.insert(QStringLiteral("status"), QStringLiteral("dispatching"));
            row.insert(QStringLiteral("dispatchStartedAt"), nowUtc.toUTC().toString(Qt::ISODateWithMs));
            rows.replace(i, row);
            changed = true;
        }
        due.append(row.toVariantMap());
    }
    if (changed && !writeRows(path, rows, error)) return {};
    return due;
}

bool LocalReminderStore::markDelivered(const QString &id, QString *error)
{
    QMutexLocker<QMutex> locker(&g_storeMutex);
    const QString path = storePath();
    QDir().mkpath(QFileInfo(path).absolutePath());
    QLockFile lock(path + QStringLiteral(".lock"));
    if (!lockStore(&lock, error)) return false;
    QJsonArray rows;
    if (!readRows(path, &rows, error)) return false;
    for (qsizetype i = 0; i < rows.size(); ++i) {
        QJsonObject row = rows.at(i).toObject();
        if (row.value(QStringLiteral("id")).toString() != id) continue;
        const QString status = row.value(QStringLiteral("status")).toString();
        if (status == QLatin1String("delivered")) return true;
        if (status != QLatin1String("dispatching")) {
            if (error) *error = QStringLiteral("El recordatorio no está pendiente de entrega.");
            return false;
        }
        row.insert(QStringLiteral("status"), QStringLiteral("delivered"));
        row.insert(QStringLiteral("deliveredAt"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
        rows.replace(i, row);
        return writeRows(path, rows, error);
    }
    if (error) *error = QStringLiteral("No encontré ese recordatorio.");
    return false;
}

bool LocalReminderStore::setFilePathForTests(const QString &path)
{
    if (!QStandardPaths::isTestModeEnabled()) return false;
    QMutexLocker<QMutex> locker(&g_storeMutex);
    g_testFilePath = path;
    return true;
}

LocalReminderScheduler::LocalReminderScheduler(QObject *parent)
    : QObject(parent), m_timer(new QTimer(this))
{
    m_timer->setInterval(5000);
    connect(m_timer, &QTimer::timeout, this, [this]() {
        evaluate(QDateTime::currentDateTimeUtc());
    });
}

void LocalReminderScheduler::setEnabled(bool enabled)
{
    if (m_enabled == enabled) return;
    m_enabled = enabled;
    if (enabled) {
        m_timer->start();
        QTimer::singleShot(0, this, [this]() {
            if (m_enabled) evaluate(QDateTime::currentDateTimeUtc());
        });
    } else {
        m_timer->stop();
    }
}

void LocalReminderScheduler::evaluate(const QDateTime &nowUtc)
{
    if (!m_enabled) return;
    const QVariantList due = LocalReminderStore::takeDue(nowUtc);
    for (const QVariant &value : due) {
        const QVariantMap reminder = value.toMap();
        const QString id = reminder.value(QStringLiteral("id")).toString();
        if (id.isEmpty() || m_inFlight.contains(id)) continue;
        m_inFlight.insert(id);
        emit reminderDue(reminder);
    }
}

bool LocalReminderScheduler::acknowledge(const QString &id)
{
    if (!m_inFlight.contains(id)) return false;
    if (!LocalReminderStore::markDelivered(id)) return false;
    m_inFlight.remove(id);
    return true;
}

void LocalReminderScheduler::retry(const QString &id)
{
    if (!m_enabled) return;
    m_inFlight.remove(id);
    evaluate(QDateTime::currentDateTimeUtc());
}
