#include <QtTest>

#include "core/agent/AgentEfficiency.h"
#include "core/agent/StructuredSourceView.h"
#include "core/tasks/WorkflowEngine.h"

class AgentEfficiencyTests : public QObject
{
    Q_OBJECT
private slots:
    void metrics_parsesLlamaAndOpenAI();
    void metrics_summarizesAndCompares();
    void structured_compactsAndProjects();
    void structured_rejectsUnsafeLanguagesAndSyntax();
    void workflow_validatesRoutesAndApproval();
    void workflow_budgetAndSnapshot();
};

void AgentEfficiencyTests::metrics_parsesLlamaAndOpenAI()
{
    QJsonObject llama{{"timings", QJsonObject{{"prompt_n", 100}, {"predicted_n", 20},
                                                {"prompt_ms", 50.0}, {"predicted_ms", 80.0}}}};
    auto a = AgentEfficiency::Request::fromResponse(llama, "explorar", 150.0);
    QCOMPARE(a.phase, QString("explore"));
    QCOMPARE(a.promptTokens, 100);
    QCOMPARE(a.generatedTokens, 20);

    QJsonObject cloud{{"usage", QJsonObject{{"prompt_tokens", 60}, {"completion_tokens", 10}}}};
    auto b = AgentEfficiency::Request::fromResponse(cloud, "plan", 90.0);
    QCOMPARE(b.promptTokens, 60);
    QCOMPARE(b.generatedTokens, 10);
}

void AgentEfficiencyTests::metrics_summarizesAndCompares()
{
    QVariantList rows{QVariantMap{{"phase", "explore"}, {"promptTokens", 100}, {"wallMs", 50.0}},
                      QVariantMap{{"phase", "plan"}, {"promptTokens", 50}, {"wallMs", 25.0}}};
    const QVariantMap total = AgentEfficiency::summarize(rows);
    QCOMPARE(total.value("promptTokens").toLongLong(), 150);
    QCOMPARE(total.value("phases").toMap().size(), 2);
    const QVariantMap delta = AgentEfficiency::compare(total,
        QVariantMap{{"promptTokens", 120}, {"wallMs", 60.0}});
    QCOMPARE(delta.value("promptTokensChangePct").toDouble(), -20.0);
}

void AgentEfficiencyTests::structured_compactsAndProjects()
{
    const QString src = "int  main() {\r\n  QString s = \"a  b\"; // keep\r\n  return 0;\r\n}\r\n";
    const auto view = StructuredSourceView::build(src, "main.cpp", true);
    QVERIFY2(view.safe, qPrintable(view.error));
    QVERIFY(view.compact.size() < src.size());
    QVERIFY(view.compact.contains("a  b"));
    const int compactPos = view.compact.indexOf("return");
    int originalPos = -1, originalLen = 0;
    QVERIFY(StructuredSourceView::projectRange(view, compactPos, 6, &originalPos, &originalLen));
    QCOMPARE(src.mid(originalPos, originalLen), QString("return"));
}

void AgentEfficiencyTests::structured_rejectsUnsafeLanguagesAndSyntax()
{
    QVERIFY(!StructuredSourceView::build("def x():\n  pass\n", "x.py").safe);
    QVERIFY(!StructuredSourceView::build("void x( {", "x.cpp").safe);
}

static QJsonObject workflowDefinition()
{
    return {{"schemaVersion", 1}, {"entry", "explore"},
            {"budget", QJsonObject{{"maxIterations", 8}, {"maxSeconds", 60}}},
            {"steps", QJsonObject{
                {"explore", QJsonObject{{"type", "agent"}, {"next", "review"}}},
                {"review", QJsonObject{{"type", "approval"}, {"accept", "execute"}, {"reject", "stop"}}},
                {"execute", QJsonObject{{"type", "tool"}, {"onSuccess", "finish"}, {"onFailure", "stop"}}},
                {"finish", QJsonObject{{"type", "finish"}}}}}};
}

void AgentEfficiencyTests::workflow_validatesRoutesAndApproval()
{
    const QJsonObject def = workflowDefinition();
    QVERIFY(WorkflowEngine::validate(def).isEmpty());
    auto state = WorkflowEngine::start(def, "wf-1");
    QCOMPARE(state.currentStep, QString("explore"));
    QVERIFY(WorkflowEngine::completeStep(def, &state, "context", true));
    QCOMPARE(state.status, WorkflowEngine::WaitingApproval);
    QVERIFY(WorkflowEngine::approve(def, &state, "accept"));
    QCOMPARE(state.currentStep, QString("execute"));
    QVERIFY(WorkflowEngine::completeStep(def, &state, "ok", true));
    QCOMPARE(state.currentStep, QString("finish"));
    QVERIFY(WorkflowEngine::completeStep(def, &state, "done", true));
    QCOMPARE(state.status, WorkflowEngine::Completed);
}

void AgentEfficiencyTests::workflow_budgetAndSnapshot()
{
    QJsonObject def = workflowDefinition();
    QJsonObject budget = def.value("budget").toObject(); budget["maxIterations"] = 1; def["budget"] = budget;
    auto state = WorkflowEngine::start(def, "wf-2", {{"goal", "test"}});
    QVERIFY(!WorkflowEngine::completeStep(def, &state, "x", true));
    QCOMPARE(state.status, WorkflowEngine::Failed);
    QString error;
    const auto restored = WorkflowEngine::fromJson(WorkflowEngine::toJson(state), &error);
    QVERIFY(error.isEmpty());
    QCOMPARE(restored.workflowId, state.workflowId);
    QCOMPARE(restored.status, state.status);
    QCOMPARE(restored.variables.value("goal").toString(), QString("test"));
}

QTEST_MAIN(AgentEfficiencyTests)
#include "test_agent_efficiency.moc"
