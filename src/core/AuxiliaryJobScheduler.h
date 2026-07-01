#pragma once

#include <QObject>
#include <QHash>
#include <QSet>
#include <QString>
#include <QVariantList>
#include <QVector>

// Scheduler liviano para operaciones auxiliares: no dispara cron ni ejecuta
// trabajo por su cuenta. Mantiene colas por clase/recurso, prioridad y estado
// consultable para que AppController/ControlApi puedan orquestar sin bloquear
// chat/agente interactivo.
class AuxiliaryJobScheduler : public QObject
{
    Q_OBJECT
public:
    enum class JobState { Queued, Running, Completed, Failed, Cancelled };
    Q_ENUM(JobState)

    struct Job
    {
        QString id;
        QString jobClass;
        QString resourceKey;
        int priority = 0;
        JobState state = JobState::Queued;
        QString detail;
        quint64 sequence = 0;
    };

    explicit AuxiliaryJobScheduler(QObject *parent = nullptr);

    void setClassLimit(const QString &jobClass, int limit);
    int classLimit(const QString &jobClass) const;

    QString enqueue(const QString &jobClass, const QString &resourceKey = {},
                    int priority = 0, const QString &detail = {});
    bool startNext(QString *startedId = nullptr);
    bool complete(const QString &id, bool ok = true, const QString &detail = {});
    bool cancel(const QString &id, const QString &detail = {});

    QVariantList snapshot() const;
    static QString stateName(JobState state);

signals:
    void jobQueued(const QString &id);
    void jobStarted(const QString &id);
    void jobFinished(const QString &id, bool ok);
    void jobCancelled(const QString &id);

private:
    int runningCountForClass(const QString &jobClass) const;
    bool resourceBusy(const QString &resourceKey) const;
    int bestQueuedIndex() const;
    Job *findJob(const QString &id);
    const Job *findJob(const QString &id) const;

    QVector<Job> m_jobs;
    QHash<QString, int> m_classLimits;
    quint64 m_nextSequence = 1;
};
