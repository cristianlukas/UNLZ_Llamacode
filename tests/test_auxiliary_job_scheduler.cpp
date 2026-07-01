#include <QtTest>

#include "core/AuxiliaryJobScheduler.h"

class AuxiliaryJobSchedulerTests : public QObject
{
    Q_OBJECT
private slots:
    void startsHighestPriorityFirst();
    void respectsClassLimit();
    void blocksBusyResource();
    void cancelQueuedJob();
};

static QString stateFor(const QVariantList &rows, const QString &id)
{
    for (const QVariant &row : rows) {
        const QVariantMap m = row.toMap();
        if (m.value(QStringLiteral("id")).toString() == id)
            return m.value(QStringLiteral("state")).toString();
    }
    return {};
}

void AuxiliaryJobSchedulerTests::startsHighestPriorityFirst()
{
    AuxiliaryJobScheduler s;
    const QString low = s.enqueue(QStringLiteral("document"), {}, 1);
    const QString high = s.enqueue(QStringLiteral("voice"), {}, 10);

    QString started;
    QVERIFY(s.startNext(&started));
    QCOMPARE(started, high);
    QCOMPARE(stateFor(s.snapshot(), high), QStringLiteral("running"));
    QCOMPARE(stateFor(s.snapshot(), low), QStringLiteral("queued"));
}

void AuxiliaryJobSchedulerTests::respectsClassLimit()
{
    AuxiliaryJobScheduler s;
    s.setClassLimit(QStringLiteral("document"), 1);
    const QString first = s.enqueue(QStringLiteral("document"), {}, 5);
    const QString second = s.enqueue(QStringLiteral("document"), {}, 4);

    QString started;
    QVERIFY(s.startNext(&started));
    QCOMPARE(started, first);
    QVERIFY(!s.startNext(&started));

    QVERIFY(s.complete(first));
    QVERIFY(s.startNext(&started));
    QCOMPARE(started, second);
}

void AuxiliaryJobSchedulerTests::blocksBusyResource()
{
    AuxiliaryJobScheduler s;
    s.setClassLimit(QStringLiteral("voice"), 2);
    const QString gpuDoc = s.enqueue(QStringLiteral("document"), QStringLiteral("gpu"), 1);
    const QString gpuVoice = s.enqueue(QStringLiteral("voice"), QStringLiteral("gpu"), 10);
    const QString diskVoice = s.enqueue(QStringLiteral("voice"), QStringLiteral("disk"), 5);

    QString started;
    QVERIFY(s.startNext(&started));
    QCOMPARE(started, gpuVoice);
    QVERIFY(s.startNext(&started));
    QCOMPARE(started, diskVoice);
    QCOMPARE(stateFor(s.snapshot(), gpuDoc), QStringLiteral("queued"));
}

void AuxiliaryJobSchedulerTests::cancelQueuedJob()
{
    AuxiliaryJobScheduler s;
    const QString id = s.enqueue(QStringLiteral("verification"));
    QVERIFY(s.cancel(id, QStringLiteral("user")));
    QCOMPARE(stateFor(s.snapshot(), id), QStringLiteral("cancelled"));
    QVERIFY(!s.startNext());
}

QTEST_MAIN(AuxiliaryJobSchedulerTests)
#include "test_auxiliary_job_scheduler.moc"
