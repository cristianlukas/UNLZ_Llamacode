#include <QtTest>
#include "core/agent/AgentProgressGovernor.h"

class AgentProgressTests : public QObject
{
    Q_OBJECT
private slots:
    void semanticVariantsCollapse();
    void distinctRequestedArtifactsRemainDistinct();
    void progressRenewsBudget();
    void stagnantVariantsReplanThenStop();
    void explicitMultiLanguageTaskAllowsVariants();
    void namedArtifactTriggersEarlyClosureHint();
    void repeatedEditsToSameFileCanMakeProgress();
    void repeatedIdenticalFailureCostsDouble();
};

void AgentProgressTests::semanticVariantsCollapse()
{
    const QString py = AgentProgressGovernor::semanticKey(
        "write_file", R"({"path":"run_test.py"})");
    const QString cpp = AgentProgressGovernor::semanticKey(
        "write_file", R"({"path":"run_test.cpp"})");
    QCOMPARE(py, cpp);
}

void AgentProgressTests::distinctRequestedArtifactsRemainDistinct()
{
    QVERIFY(AgentProgressGovernor::semanticKey("write_file", R"({"path":"client.py"})")
            != AgentProgressGovernor::semanticKey("write_file", R"({"path":"server.cpp"})"));
}

void AgentProgressTests::progressRenewsBudget()
{
    AgentProgressGovernor g({4, 8, 3, 3});
    const auto first = g.record("write_file", R"({"path":"answer.py"})",
                                true, "[escrito 20 bytes]", true);
    QVERIFY(first.progress);
    QVERIFY(first.credits > 4);
    const auto read = g.record("read_file", R"({"path":"answer.py"})",
                               true, "def answer(): return 42", false);
    QVERIFY(read.progress);
    QCOMPARE(read.action, AgentProgressGovernor::Continue);
}

void AgentProgressTests::stagnantVariantsReplanThenStop()
{
    AgentProgressGovernor g({6, 10, 3, 3});
    QCOMPARE(g.record("write_file", R"({"path":"run_test.py"})",
                      true, "ok", true).action, AgentProgressGovernor::Continue);
    QCOMPARE(g.record("write_file", R"({"path":"run_test.cpp"})",
                      true, "ok2", true).action, AgentProgressGovernor::Continue);
    QCOMPARE(g.record("write_file", R"({"path":"run_test.go"})",
                      true, "ok3", true).action, AgentProgressGovernor::Continue);
    QCOMPARE(g.record("write_file", R"({"path":"run_test.java"})",
                      true, "ok4", true).action, AgentProgressGovernor::Replan);
    g.record("write_file", R"({"path":"run_test.js"})", true, "ok5", true);
    g.record("write_file", R"({"path":"run_test.rs"})", true, "ok6", true);
    QCOMPARE(g.record("write_file", R"({"path":"run_test.rb"})",
                      true, "ok7", true).action, AgentProgressGovernor::Stop);
}

void AgentProgressTests::explicitMultiLanguageTaskAllowsVariants()
{
    AgentProgressGovernor g({4, 8, 3, 3});
    g.reset(QStringLiteral("Create the example in multiple languages"));
    QVERIFY(g.record("write_file", R"({"path":"run_test.py"})", true, "py", true).progress);
    QVERIFY(g.record("write_file", R"({"path":"run_test.cpp"})", true, "cpp", true).progress);
}

void AgentProgressTests::namedArtifactTriggersEarlyClosureHint()
{
    AgentProgressGovernor g;
    g.reset(QStringLiteral("Create answer.py with the requested function"));
    const auto d = g.record("write_file", R"({"path":"answer.py"})",
                            true, "written", true);
    QVERIFY(d.objectiveSatisfied);
}

void AgentProgressTests::repeatedEditsToSameFileCanMakeProgress()
{
    AgentProgressGovernor g;
    QVERIFY(g.record("edit_file", R"({"path":"app.cpp"})", true, "diff one", true).progress);
    QVERIFY(g.record("edit_file", R"({"path":"app.cpp"})", true, "diff two", true).progress);
}

// El bucle clasico: list_dir ".." rechazado una y otra vez. Cada repeticion
// identica cuesta doble para llegar al replanteo sin gastar diez turnos.
void AgentProgressTests::repeatedIdenticalFailureCostsDouble()
{
    AgentProgressGovernor g({8, 16, 99, 99});
    const char *args = R"({"path":".."})";
    const QString refusal = QStringLiteral("[ruta fuera del proyecto: ...]");
    const auto first = g.record("list_dir", args, false, refusal, false);
    QVERIFY(!first.repeatedFailure);
    QCOMPARE(first.credits, 7);
    const auto second = g.record("list_dir", args, false, refusal, false);
    QVERIFY(second.repeatedFailure);
    QCOMPARE(second.credits, 5);
    QCOMPARE(g.record("list_dir", args, false, refusal, false).credits, 3);
    QCOMPARE(g.record("list_dir", args, false, refusal, false).credits, 1);
    QCOMPARE(g.record("list_dir", args, false, refusal, false).action,
             AgentProgressGovernor::Replan);
}

QTEST_MAIN(AgentProgressTests)
#include "test_agent_progress.moc"
