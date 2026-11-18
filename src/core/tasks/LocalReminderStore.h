#pragma once

#include <QDateTime>
#include <QObject>
#include <QSet>
#include <QString>
#include <QVariantList>
#include <QVariantMap>

class QTimer;

// File-backed local one-shot reminders shared by the agent worker and GUI.
// Writes are serialized across threads/processes and use atomic replacement.
class LocalReminderStore
{
public:
    static bool parseDueAt(const QString &value, QDateTime *result,
                           QString *error = nullptr);
    static QString create(const QString &dueAt, const QString &title,
                          const QString &note, const QString &idempotencyKey,
                          bool *duplicate = nullptr, QString *error = nullptr);
    static QVariantList all(QString *error = nullptr);
    static bool cancel(const QString &id, QString *error = nullptr);
    // Atomically claims due rows for delivery. The caller acknowledges only
    // after persisting its notification event; dispatching rows are recoverable.
    static QVariantList takeDue(const QDateTime &nowUtc, QString *error = nullptr);
    static bool markDelivered(const QString &id, QString *error = nullptr);

    static bool setFilePathForTests(const QString &path);
};

class LocalReminderScheduler final : public QObject
{
    Q_OBJECT
public:
    explicit LocalReminderScheduler(QObject *parent = nullptr);
    void setEnabled(bool enabled);
    bool enabled() const { return m_enabled; }
    void evaluate(const QDateTime &nowUtc);
    bool acknowledge(const QString &id);
    void retry(const QString &id);

signals:
    void reminderDue(const QVariantMap &reminder);

private:
    QTimer *m_timer = nullptr;
    bool m_enabled = false;
    QSet<QString> m_inFlight;
};
