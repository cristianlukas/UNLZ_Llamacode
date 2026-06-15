// Unit tests de TaskStore: (de)serialización JSON roundtrip, composición pura del
// prompt-objetivo (incluye la consigna de adaptación), y CRUD persistente con
// aislamiento de disco (QStandardPaths test mode).

#include <QtTest>
#include "core/tasks/TaskStore.h"

class TasksTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void jsonRoundTrip();
    void composePrompt_includesGoalStepsAndAdaptation();
    void sanitize_slug();
    void crud_persistsAcrossInstances();
    void duplicate_clonesWithNewId();
    void markRun_updatesStatus();
};

static QVariantMap sampleTask()
{
    QVariantList steps;
    steps.append(QVariantMap{{"kind", "browser"}, {"intent", "abrir banco"}, {"ref", "https://x"}});
    steps.append(QVariantMap{{"kind", "instruction"}, {"intent", "copiar el valor"}, {"ref", ""}});
    return QVariantMap{
        {"id", "t1"}, {"name", "Cotización dólar"}, {"description", "extraer la cotización"},
        {"profileId", "p1"}, {"scheduleEnabled", true}, {"scheduleCron", "0 9 * * *"},
        {"steps", steps}
    };
}

void TasksTests::initTestCase()
{
    QStandardPaths::setTestModeEnabled(true);
}

void TasksTests::jsonRoundTrip()
{
    const QVariantMap in = sampleTask();
    const QVariantMap out = TaskStore::fromJson(TaskStore::toJson(in));
    QCOMPARE(out.value("name").toString(), in.value("name").toString());
    QCOMPARE(out.value("profileId").toString(), QStringLiteral("p1"));
    QCOMPARE(out.value("scheduleEnabled").toBool(), true);
    QCOMPARE(out.value("scheduleCron").toString(), QStringLiteral("0 9 * * *"));
    const QVariantList steps = out.value("steps").toList();
    QCOMPARE(steps.size(), 2);
    QCOMPARE(steps.at(0).toMap().value("kind").toString(), QStringLiteral("browser"));
    QCOMPARE(steps.at(0).toMap().value("ref").toString(), QStringLiteral("https://x"));
}

void TasksTests::composePrompt_includesGoalStepsAndAdaptation()
{
    const QString p = TaskStore::composePrompt(sampleTask());
    QVERIFY(p.contains(QStringLiteral("Cotización dólar")));
    QVERIFY(p.contains(QStringLiteral("extraer la cotización")));
    QVERIFY(p.contains(QStringLiteral("[browser] abrir banco")));
    QVERIFY(p.contains(QStringLiteral("ref: https://x")));
    // La consigna clave: pasos son guía, no guion literal (replay adaptativo).
    QVERIFY(p.contains(QStringLiteral("no un guion literal")));
    QVERIFY(p.contains(QStringLiteral("adaptate")));
}

void TasksTests::sanitize_slug()
{
    QCOMPARE(TaskStore::sanitize(QStringLiteral("  Hola Mundo!! ")), QStringLiteral("hola-mundo"));
    QCOMPARE(TaskStore::sanitize(QStringLiteral("A/B__C")), QStringLiteral("a-b__c"));
    QVERIFY(TaskStore::sanitize(QStringLiteral("!!!")).isEmpty());
}

void TasksTests::crud_persistsAcrossInstances()
{
    QString id;
    {
        TaskStore s;
        const int before = s.count();
        id = s.save({}, sampleTask());
        QVERIFY(!id.isEmpty());
        QCOMPARE(s.count(), before + 1);
        QVERIFY(!s.get(id).isEmpty());
    }
    {
        TaskStore s2;   // recarga desde disco
        const QVariantMap t = s2.get(id);
        QCOMPARE(t.value("name").toString(), QStringLiteral("Cotización dólar"));
        QCOMPARE(t.value("steps").toList().size(), 2);
        QVERIFY(s2.remove(id));
        QVERIFY(s2.get(id).isEmpty());
    }
    { TaskStore s3; QVERIFY(s3.get(id).isEmpty()); }   // borrado persistió
}

void TasksTests::duplicate_clonesWithNewId()
{
    TaskStore s;
    const QString id = s.save({}, sampleTask());
    const QString dupId = s.duplicate(id);
    QVERIFY(!dupId.isEmpty());
    QVERIFY(dupId != id);
    QVERIFY(s.get(dupId).value("name").toString().contains(QStringLiteral("copia")));
    s.remove(id);
    s.remove(dupId);
}

void TasksTests::markRun_updatesStatus()
{
    TaskStore s;
    const QString id = s.save({}, sampleTask());
    s.markRun(id, QStringLiteral("ok"));
    QCOMPARE(s.get(id).value("lastRunStatus").toString(), QStringLiteral("ok"));
    QVERIFY(!s.get(id).value("lastRunAt").toString().isEmpty());
    s.remove(id);
}

QTEST_MAIN(TasksTests)
#include "test_tasks.moc"
