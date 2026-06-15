// Unit tests del scheduler de Tasks: parser cron PURO (campos, listas, rangos,
// pasos, día de semana 0/7, OR dom/dow) y selección de Tasks vencidas
// (TaskScheduler::dueTaskIds, también pura).

#include <QtTest>
#include "core/tasks/CronSchedule.h"
#include "core/tasks/TaskScheduler.h"

class CronTests : public QObject
{
    Q_OBJECT
private slots:
    void parse_rejectsBadFieldCount();
    void parse_rejectsOutOfRange();
    void matches_exactMinuteHour();
    void matches_wildcards();
    void matches_stepAndRange();
    void matches_list();
    void matches_sundayZeroOrSeven();
    void matches_domDowOrSemantics();
    void dueTaskIds_selectsEnabledMatching();
};

static QDateTime dt(int y, int mo, int d, int h, int mi)
{
    return QDateTime(QDate(y, mo, d), QTime(h, mi));
}

void CronTests::parse_rejectsBadFieldCount()
{
    QVERIFY(!CronSchedule::parse(QStringLiteral("* * * *")).isValid());
    QVERIFY(!CronSchedule::parse(QStringLiteral("")).isValid());
    QVERIFY(CronSchedule::parse(QStringLiteral("* * * * *")).isValid());
}

void CronTests::parse_rejectsOutOfRange()
{
    QVERIFY(!CronSchedule::parse(QStringLiteral("60 * * * *")).isValid());
    QVERIFY(!CronSchedule::parse(QStringLiteral("* 24 * * *")).isValid());
    QVERIFY(!CronSchedule::parse(QStringLiteral("* * 0 * *")).isValid());   // dom min 1
    QVERIFY(!CronSchedule::parse(QStringLiteral("* * * 13 *")).isValid());
    QVERIFY(!CronSchedule::parse(QStringLiteral("* * * * 8")).isValid());
}

void CronTests::matches_exactMinuteHour()
{
    const CronSchedule c = CronSchedule::parse(QStringLiteral("30 9 * * *"));
    QVERIFY(c.isValid());
    QVERIFY(c.matches(dt(2026, 6, 15, 9, 30)));
    QVERIFY(!c.matches(dt(2026, 6, 15, 9, 31)));
    QVERIFY(!c.matches(dt(2026, 6, 15, 10, 30)));
}

void CronTests::matches_wildcards()
{
    const CronSchedule c = CronSchedule::parse(QStringLiteral("* * * * *"));
    QVERIFY(c.matches(dt(2026, 1, 1, 0, 0)));
    QVERIFY(c.matches(dt(2026, 12, 31, 23, 59)));
}

void CronTests::matches_stepAndRange()
{
    const CronSchedule c = CronSchedule::parse(QStringLiteral("*/15 9-17 * * *"));
    QVERIFY(c.matches(dt(2026, 6, 15, 9, 0)));
    QVERIFY(c.matches(dt(2026, 6, 15, 17, 45)));
    QVERIFY(!c.matches(dt(2026, 6, 15, 8, 0)));    // hora fuera de rango
    QVERIFY(!c.matches(dt(2026, 6, 15, 9, 10)));   // minuto no múltiplo de 15
}

void CronTests::matches_list()
{
    const CronSchedule c = CronSchedule::parse(QStringLiteral("0 8,12,18 * * *"));
    QVERIFY(c.matches(dt(2026, 6, 15, 8, 0)));
    QVERIFY(c.matches(dt(2026, 6, 15, 12, 0)));
    QVERIFY(c.matches(dt(2026, 6, 15, 18, 0)));
    QVERIFY(!c.matches(dt(2026, 6, 15, 9, 0)));
}

void CronTests::matches_sundayZeroOrSeven()
{
    // 2026-06-14 es domingo.
    const CronSchedule c0 = CronSchedule::parse(QStringLiteral("0 10 * * 0"));
    const CronSchedule c7 = CronSchedule::parse(QStringLiteral("0 10 * * 7"));
    QVERIFY(c0.matches(dt(2026, 6, 14, 10, 0)));
    QVERIFY(c7.matches(dt(2026, 6, 14, 10, 0)));
    QVERIFY(!c0.matches(dt(2026, 6, 15, 10, 0)));  // lunes
}

void CronTests::matches_domDowOrSemantics()
{
    // dom=1 y dow=lunes(1) ambos restringidos → OR. 2026-06-15 es lunes (no día 1).
    const CronSchedule c = CronSchedule::parse(QStringLiteral("0 0 1 * 1"));
    QVERIFY(c.matches(dt(2026, 6, 15, 0, 0)));   // lunes
    QVERIFY(c.matches(dt(2026, 7, 1, 0, 0)));    // día 1 (miércoles)
    QVERIFY(!c.matches(dt(2026, 6, 16, 0, 0)));  // martes, no día 1
}

void CronTests::dueTaskIds_selectsEnabledMatching()
{
    QVariantList tasks;
    tasks.append(QVariantMap{{"id", "a"}, {"scheduleEnabled", true},  {"scheduleCron", "30 9 * * *"}});
    tasks.append(QVariantMap{{"id", "b"}, {"scheduleEnabled", false}, {"scheduleCron", "30 9 * * *"}}); // off
    tasks.append(QVariantMap{{"id", "c"}, {"scheduleEnabled", true},  {"scheduleCron", "0 0 * * *"}});  // no match
    tasks.append(QVariantMap{{"id", "d"}, {"scheduleEnabled", true},  {"scheduleCron", "garbage"}});    // inválido

    const QStringList due = TaskScheduler::dueTaskIds(tasks, dt(2026, 6, 15, 9, 30));
    QCOMPARE(due, QStringList{QStringLiteral("a")});
}

QTEST_MAIN(CronTests)
#include "test_cron.moc"
