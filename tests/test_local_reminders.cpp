#include <QtTest>

#include "core/tasks/LocalReminderStore.h"

#include <QSignalSpy>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QUuid>

class LocalReminderTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void init();
    void cleanup();
    void dueAtRequiresAnExplicitZoneAndFutureTime();
    void createPersistsDeduplicatesAndCancels();
    void schedulerDeliversDueReminderOnlyOnceAcrossRestart();

private:
    QTemporaryDir m_dir;
};

void LocalReminderTests::initTestCase()
{
    QStandardPaths::setTestModeEnabled(true);
}

void LocalReminderTests::init()
{
    QVERIFY(m_dir.isValid());
    const QString path = m_dir.filePath(QUuid::createUuid().toString(QUuid::WithoutBraces)
                                         + QStringLiteral(".json"));
    QVERIFY(LocalReminderStore::setFilePathForTests(path));
}

void LocalReminderTests::cleanup()
{
    QVERIFY(LocalReminderStore::setFilePathForTests(QString()));
}

void LocalReminderTests::dueAtRequiresAnExplicitZoneAndFutureTime()
{
    const QDateTime future = QDateTime::currentDateTimeUtc().addSecs(3600);
    const QString zoned = future.toOffsetFromUtc(-3 * 3600).toString(Qt::ISODateWithMs);
    QDateTime parsed;
    QString error;
    QVERIFY2(LocalReminderStore::parseDueAt(zoned, &parsed, &error), qPrintable(error));
    QCOMPARE(parsed.toMSecsSinceEpoch(), future.toMSecsSinceEpoch());
    QVERIFY(!LocalReminderStore::parseDueAt(
        future.toString(QStringLiteral("yyyy-MM-dd'T'HH:mm:ss")), nullptr, &error));
    QVERIFY(!LocalReminderStore::parseDueAt(
        QDateTime::currentDateTimeUtc().addSecs(-30).toString(Qt::ISODate), nullptr, &error));
}

void LocalReminderTests::createPersistsDeduplicatesAndCancels()
{
    const QDateTime due = QDateTime::currentDateTimeUtc().addSecs(3600);
    const QString dueAt = due.toString(Qt::ISODateWithMs);
    const QString key = QString(64, QLatin1Char('a'));
    QString error;
    bool duplicate = false;
    const QString id = LocalReminderStore::create(
        dueAt, QStringLiteral("Llamar a Ana"), QStringLiteral("Llevar el informe"),
        key, &duplicate, &error);
    QVERIFY2(!id.isEmpty(), qPrintable(error));
    QVERIFY(!duplicate);

    const QString repeated = LocalReminderStore::create(
        dueAt, QStringLiteral("Llamar a Ana"), QStringLiteral("Llevar el informe"),
        key, &duplicate, &error);
    QCOMPARE(repeated, id);
    QVERIFY(duplicate);
    QCOMPARE(LocalReminderStore::all().size(), 1);

    QVERIFY(LocalReminderStore::cancel(id, &error));
    QVERIFY(!LocalReminderStore::cancel(id, &error));
    const QVariantList rows = LocalReminderStore::all();
    QCOMPARE(rows.size(), 1);
    QCOMPARE(rows.constFirst().toMap().value(QStringLiteral("status")).toString(),
             QStringLiteral("cancelled"));
    QVERIFY(LocalReminderStore::takeDue(due.addSecs(1)).isEmpty());
}

void LocalReminderTests::schedulerDeliversDueReminderOnlyOnceAcrossRestart()
{
    const QDateTime due = QDateTime::currentDateTimeUtc().addSecs(60);
    const QString key = QString(64, QLatin1Char('b'));
    QString error;
    const QString id = LocalReminderStore::create(due.toString(Qt::ISODateWithMs),
        QStringLiteral("Reunión"), QString(), key, nullptr, &error);
    QVERIFY2(!id.isEmpty(), qPrintable(error));

    LocalReminderScheduler scheduler;
    QSignalSpy dueSpy(&scheduler, &LocalReminderScheduler::reminderDue);
    scheduler.setEnabled(true);
    scheduler.evaluate(due.addSecs(1));
    QCOMPARE(dueSpy.size(), 1);
    scheduler.evaluate(due.addSecs(2));
    QCOMPARE(dueSpy.size(), 1);
    QCOMPARE(LocalReminderStore::all().constFirst().toMap()
                 .value(QStringLiteral("status")).toString(), QStringLiteral("dispatching"));
    QVERIFY(scheduler.acknowledge(id));
    scheduler.evaluate(due.addSecs(2));
    QCOMPARE(dueSpy.size(), 1);

    LocalReminderScheduler afterRestart;
    QSignalSpy restartSpy(&afterRestart, &LocalReminderScheduler::reminderDue);
    afterRestart.setEnabled(true);
    afterRestart.evaluate(due.addSecs(3));
    QCOMPARE(restartSpy.size(), 0);
    QCOMPARE(LocalReminderStore::all().constFirst().toMap()
                 .value(QStringLiteral("status")).toString(), QStringLiteral("delivered"));

    const QDateTime dueAfterCrash = QDateTime::currentDateTimeUtc().addSecs(60);
    const QString crashId = LocalReminderStore::create(
        dueAfterCrash.toString(Qt::ISODateWithMs), QStringLiteral("Recuperación"),
        QString(), QString(64, QLatin1Char('c')), nullptr, &error);
    QVERIFY2(!crashId.isEmpty(), qPrintable(error));
    scheduler.evaluate(dueAfterCrash.addSecs(1));
    QCOMPARE(dueSpy.size(), 2);
    LocalReminderScheduler recoveryScheduler;
    QSignalSpy recoverySpy(&recoveryScheduler, &LocalReminderScheduler::reminderDue);
    recoveryScheduler.setEnabled(true);
    recoveryScheduler.evaluate(dueAfterCrash.addSecs(2));
    QCOMPARE(recoverySpy.size(), 1);
    QVERIFY(recoveryScheduler.acknowledge(crashId));
}

QTEST_GUILESS_MAIN(LocalReminderTests)
#include "test_local_reminders.moc"
