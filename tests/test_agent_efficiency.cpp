#include <QtTest>

#include "core/agent/AgentEfficiency.h"
#include "core/agent/StructuredSourceView.h"
#include "core/tasks/WorkflowEngine.h"
#include "core/tasks/WorkflowRunner.h"
#include "core/tasks/WorkflowVisualModel.h"

class AgentEfficiencyTests : public QObject
{
    Q_OBJECT
private slots:
    void metrics_parsesLlamaAndOpenAI();
    void metrics_summarizesAndCompares();
    void metrics_aggregatesRepeatedBenchmarkRuns();
    void metrics_groupsByAgentProfileForHarnessAb();
    void structured_compactsAndProjects();
    void structured_rejectsUnsafeLanguagesAndSyntax();
    void workflow_validatesRoutesAndApproval();
    void workflow_budgetAndSnapshot();
    void workflow_gateVerdictAndBoundedRepair();
    void workflowRunner_dispatchApprovalConditionAndFinish();
    void workflowVisual_roundTripPreservesAdvancedFields();
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

void AgentEfficiencyTests::metrics_aggregatesRepeatedBenchmarkRuns()
{
    const QVariantList runs{
        QVariantMap{{"profileId", "qwen"}, {"profileName", "Qwen · pasada 1/3"},
                    {"qualityScore", 8}, {"qualityTotal", 10}, {"elapsedSec", 100.0},
                    {"timeToFirstAttempt", 70.0}, {"repairAttempts", 1}, {"failed", false}, {"pass", 1},
                    {"agentVariant", "honey"}, {"honeyEnabled", true},
                    {"complexityMetrics", QVariantMap{{"filesChanged", 2}, {"addedLines", 20}, {"removedLines", 1}}}},
        QVariantMap{{"profileId", "qwen"}, {"profileName", "Qwen · pasada 2/3"},
                    {"qualityScore", 10}, {"qualityTotal", 10}, {"elapsedSec", 120.0},
                    {"timeToFirstAttempt", 80.0}, {"repairAttempts", 0}, {"failed", false}, {"pass", 2},
                    {"agentVariant", "honey"}, {"honeyEnabled", true},
                    {"complexityMetrics", QVariantMap{{"filesChanged", 4}, {"addedLines", 40}, {"removedLines", 2}}}},
        QVariantMap{{"profileId", "qwen"}, {"profileName", "Qwen · pasada 3/3"},
                    {"failed", true}},
        QVariantMap{{"profileId", "kat"}, {"profileName", "KAT · pasada 1/3"},
                    {"qualityScore", 10}, {"qualityTotal", 10}, {"elapsedSec", 80.0},
                    {"timeToFirstAttempt", 55.0}, {"repairAttempts", 0}, {"failed", false}, {"pass", 1},
                    {"agentVariant", "baseline"}, {"honeyEnabled", false},
                    {"complexityMetrics", QVariantMap{{"filesChanged", 1}, {"addedLines", 10}, {"removedLines", 0}}}},
        QVariantMap{{"profileId", "kat"}, {"profileName", "KAT · pasada 2/3"},
                    {"qualityScore", 10}, {"qualityTotal", 10}, {"elapsedSec", 90.0},
                    {"timeToFirstAttempt", 60.0}, {"repairAttempts", 0}, {"failed", false}, {"pass", 2},
                    {"agentVariant", "baseline"}, {"honeyEnabled", false},
                    {"complexityMetrics", QVariantMap{{"filesChanged", 3}, {"addedLines", 30}, {"removedLines", 1}}}},
        QVariantMap{{"profileId", "kat"}, {"profileName", "KAT · pasada 3/3"},
                    {"qualityScore", 9}, {"qualityTotal", 10}, {"elapsedSec", 85.0},
                    {"timeToFirstAttempt", 58.0}, {"repairAttempts", 1}, {"failed", false}, {"pass", 3},
                    {"agentVariant", "baseline"}, {"honeyEnabled", false},
                    {"complexityMetrics", QVariantMap{{"filesChanged", 2}, {"addedLines", 20}, {"removedLines", 1}}}}
    };
    const QVariantMap report = AgentEfficiency::benchmarkComparison(runs);
    QCOMPARE(report.value("runCount").toInt(), 6);
    QCOMPARE(report.value("profileCount").toInt(), 2);

    QVariantMap qwen;
    QVariantMap kat;
    for (const QVariant &value : report.value("profiles").toList()) {
        const QVariantMap profile = value.toMap();
        if (profile.value("profileId").toString() == "qwen") qwen = profile;
        if (profile.value("profileId").toString() == "kat") kat = profile;
    }
    QCOMPARE(qwen.value("medianQualityPct").toDouble(), 90.0);
    QCOMPARE(qwen.value("medianElapsedSec").toDouble(), 110.0);
    QCOMPARE(qwen.value("medianColdFirstAttemptSec").toDouble(), 70.0);
    QCOMPARE(qwen.value("medianWarmFirstAttemptSec").toDouble(), 80.0);
    QCOMPARE(kat.value("medianColdFirstAttemptSec").toDouble(), 55.0);
    QCOMPARE(kat.value("medianWarmFirstAttemptSec").toDouble(), 59.0);
    QCOMPARE(qwen.value("comparisonTimeMetric").toString(), QString("warmTimeToFirstAttempt"));
    QCOMPARE(qwen.value("stabilityRatePct").toDouble(), 200.0 / 3.0);
    QCOMPARE(qwen.value("medianFilesChanged").toDouble(), 3.0);
    QCOMPARE(qwen.value("medianAddedLines").toDouble(), 30.0);
    QCOMPARE(qwen.value("agentVariant").toString(), QStringLiteral("honey"));
    QVERIFY(qwen.value("honeyEnabled").toBool());
    QVERIFY(qwen.value("outcomeSpread").toBool());
    QCOMPARE(kat.value("successRatePct").toDouble(), 100.0);
    QCOMPARE(kat.value("qualityRangePctPoints").toDouble(), 10.0);
    QVERIFY(!kat.value("outcomeSpread").toBool());

    const QVariantMap comparison = report.value("comparisons").toList().first().toMap();
    QCOMPARE(comparison.value("baselineProfileId").toString(), QString("kat"));
    QCOMPARE(comparison.value("candidateProfileId").toString(), QString("qwen"));
    QCOMPARE(comparison.value("qualityDeltaPctPoints").toDouble(), -10.0);
    QCOMPARE(comparison.value("elapsedChangePct").toDouble(), (80.0 / 59.0 - 1.0) * 100.0);
    QCOMPARE(comparison.value("comparisonTimeChangePct").toDouble(), (80.0 / 59.0 - 1.0) * 100.0);
}

void AgentEfficiencyTests::structured_compactsAndProjects()
{
    const QString src = "int  main() {\r\n  QString s = \"a  b\"; // keep\r\n  return 0;\r\n}\r\n";
    const auto view = StructuredSourceView::build(src, "main.cpp", true);
    QCOMPARE(view.parserBackend, QStringLiteral("lexical"));
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

void AgentEfficiencyTests::workflow_gateVerdictAndBoundedRepair()
{
    const QJsonObject def{
        {"schemaVersion", 1}, {"entry", "implement"},
        {"budget", QJsonObject{{"maxIterations", 20}, {"maxRepairs", 2}}},
        {"steps", QJsonObject{
            {"implement", QJsonObject{{"type", "agent"}, {"verdictRequired", true},
                {"onSuccess", "review"}, {"onFailure", "repair"}}},
            {"review", QJsonObject{{"type", "parallel"}, {"verdictRequired", true},
                {"onSuccess", "finish"}, {"onFailure", "repair"}}},
            {"repair", QJsonObject{{"type", "repair"}, {"verdictRequired", true},
                {"onSuccess", "review"}, {"onFailure", "review"}}},
            {"finish", QJsonObject{{"type", "finish"}}}}}};
    QVERIFY(WorkflowEngine::validate(def).isEmpty());
    QCOMPARE(WorkflowEngine::resultVerdict(QStringLiteral("LC_GATE: PASS\nlisto")),
             QStringLiteral("pass"));
    QCOMPARE(WorkflowEngine::resultVerdict(QStringLiteral("VERDICT: blocked")),
             QStringLiteral("blocked"));
    QVERIFY(WorkflowEngine::resultVerdict(QStringLiteral("texto\nLC_GATE: PASS"))
            .isEmpty());
    QCOMPARE(WorkflowEngine::resultVerdict(QVariantMap{
                 {QStringLiteral("reviewer"), QStringLiteral("LC_GATE: PASS")},
                 {QStringLiteral("verifier"), QStringLiteral("LC_GATE: PASS")}}),
             QStringLiteral("pass"));

    WorkflowRunner runner;
    QSignalSpy requested(&runner, &WorkflowRunner::stepRequested);
    QVERIFY(runner.start(def, QStringLiteral("autoprompt-test")));
    runner.completeCurrent(QStringLiteral("LC_GATE: PASS\nimplementado"));
    QCOMPARE(requested.size(), 2);
    QCOMPARE(runner.state().currentStep, QStringLiteral("review"));
    runner.completeCurrent(QVariantMap{
        {QStringLiteral("reviewer"), QStringLiteral("LC_GATE: FAIL\nregresión")},
        {QStringLiteral("verifier"), QStringLiteral("LC_GATE: PASS\ntests ok")}});
    QCOMPARE(runner.state().currentStep, QStringLiteral("repair"));
    QCOMPARE(runner.state().repairAttempts, 1);
    runner.completeCurrent(QStringLiteral("LC_GATE: FAIL\nno reparado"));
    QCOMPARE(runner.state().currentStep, QStringLiteral("review"));
    runner.completeCurrent(QStringLiteral("LC_GATE: FAIL\nsegunda falla"));
    QCOMPARE(runner.state().currentStep, QStringLiteral("repair"));
    QCOMPARE(runner.state().repairAttempts, 2);
    runner.completeCurrent(QStringLiteral("LC_GATE: PASS\nreparado"));
    QCOMPARE(runner.state().currentStep, QStringLiteral("review"));
    runner.completeCurrent(QStringLiteral("LC_GATE: FAIL\ntercera falla"));
    QCOMPARE(runner.state().status, WorkflowEngine::Failed);
    QVERIFY(runner.state().error.contains(QStringLiteral("reparaciones")));
}

void AgentEfficiencyTests::workflowRunner_dispatchApprovalConditionAndFinish()
{
    QJsonObject def{{"schemaVersion", 1}, {"entry", "work"},
        {"steps", QJsonObject{
            {"work", QJsonObject{{"type", "agent"}, {"next", "gate"}}},
            {"gate", QJsonObject{{"type", "approval"}, {"accept", "check"}}},
            {"check", QJsonObject{{"type", "condition"}, {"variable", "verified"},
                                    {"onTrue", "done"}, {"onFalse", "stop"}}},
            {"done", QJsonObject{{"type", "finish"}}}}}};
    WorkflowRunner runner;
    QSignalSpy steps(&runner, &WorkflowRunner::stepRequested);
    QSignalSpy approvals(&runner, &WorkflowRunner::approvalRequested);
    QSignalSpy finished(&runner, &WorkflowRunner::finished);
    QVERIFY(runner.start(def, "run-1", {{"verified", true}}));
    QCOMPARE(steps.size(), 1);
    runner.completeCurrent(QStringLiteral("ok"));
    QCOMPARE(approvals.size(), 1);
    const QJsonObject paused = runner.snapshot();
    QCOMPARE(paused.value("status").toString(), QStringLiteral("waiting_approval"));
    runner.approve(QStringLiteral("accept"), QStringLiteral("go"));
    QCOMPARE(finished.size(), 1);
    QVERIFY(finished.first().at(0).toBool());
    QCOMPARE(runner.snapshot().value("status").toString(), QStringLiteral("completed"));
}

void AgentEfficiencyTests::workflowVisual_roundTripPreservesAdvancedFields()
{
    const QVariantMap definition{{"schemaVersion", 1}, {"entry", "tool"},
        {"budget", QVariantMap{{"maxIterations", 9}}},
        {"steps", QVariantMap{
            {"tool", QVariantMap{{"type", "tool"}, {"tool", "grep"},
                {"arguments", QVariantMap{{"pattern", "TODO"}}}, {"onSuccess", "branch"},
                {"onFailure", "stop"}, {"direct", true}}},
            {"branch", QVariantMap{{"type", "parallel"},
                {"branches", QVariantList{QVariantMap{{"prompt", "a"}}, QVariantMap{{"prompt", "b"}}}},
                {"next", "done"}}},
            {"done", QVariantMap{{"type", "finish"}}}}}};
    QVariantList rows = WorkflowVisualModel::rows(definition);
    QCOMPARE(rows.size(), 3);
    QVariantMap first = rows.first().toMap();
    first["stepPrompt"] = QStringLiteral("nuevo prompt");
    rows[0] = first;
    const QVariantMap merged = WorkflowVisualModel::merge(definition, rows);
    QCOMPARE(merged.value("budget").toMap().value("maxIterations").toInt(), 9);
    const QVariantMap tool = merged.value("steps").toMap().value("tool").toMap();
    QCOMPARE(tool.value("tool").toString(), QStringLiteral("grep"));
    QCOMPARE(tool.value("arguments").toMap().value("pattern").toString(), QStringLiteral("TODO"));
    QCOMPARE(tool.value("onFailure").toString(), QStringLiteral("stop"));
    QVERIFY(tool.value("direct").toBool());
    QCOMPARE(tool.value("prompt").toString(), QStringLiteral("nuevo prompt"));
    QCOMPARE(merged.value("steps").toMap().value("branch").toMap()
                 .value("branches").toList().size(), 2);
}

// A/B de HARNESS: mismo modelo (profileId), distinto perfil de agente. Agrupar
// por profileId daria UNA fila y ninguna comparacion; hay que agrupar por
// agentProfileId para que el barrido de tools/harness_ab.ps1 tenga sentido.
void AgentEfficiencyTests::metrics_groupsByAgentProfileForHarnessAb()
{
    auto run = [](const QString &agentId, const QString &agentName, int score,
                  double elapsed, double firstAttempt) {
        return QVariantMap{{"profileId", "qwen"}, {"profileName", "Qwen"},
                           {"agentProfileId", agentId}, {"agentProfileName", agentName},
                           {"qualityScore", score}, {"qualityTotal", 10},
                           {"elapsedSec", elapsed}, {"timeToFirstAttempt", firstAttempt},
                           {"repairAttempts", 0}, {"failed", false}, {"pass", 1},
                           {"complexityMetrics", QVariantMap{{"filesChanged", 2},
                                                             {"addedLines", 10},
                                                             {"removedLines", 1}}}};
    };
    const QVariantList runs{
        run("agent-intermedio", "Intermedio", 9, 100.0, 60.0),
        run("agent-intermedio", "Intermedio", 9, 110.0, 62.0),
        run("agent-minimal", "Minimal", 8, 70.0, 40.0),
        run("agent-minimal", "Minimal", 8, 74.0, 42.0)
    };

    // Agrupado por modelo: un solo grupo, nada que comparar.
    const QVariantMap byModel = AgentEfficiency::benchmarkComparison(runs);
    QCOMPARE(byModel.value("profileCount").toInt(), 1);
    QVERIFY(byModel.value("comparisons").toList().isEmpty());

    // Agrupado por harness: dos grupos y su delta.
    const QVariantMap byHarness =
        AgentEfficiency::benchmarkComparison(runs, QStringLiteral("agentProfileId"));
    QCOMPARE(byHarness.value("profileCount").toInt(), 2);
    QCOMPARE(byHarness.value("comparisons").toList().size(), 1);

    QVariantMap minimal;
    for (const QVariant &value : byHarness.value("profiles").toList()) {
        const QVariantMap profile = value.toMap();
        if (profile.value("profileId").toString() == "agent-minimal") minimal = profile;
    }
    // El nombre visible sale del perfil de AGENTE, no del modelo: si mostrara
    // "Qwen" en las dos filas el informe seria ilegible.
    QCOMPARE(minimal.value("profileName").toString(), QStringLiteral("Minimal"));
    QCOMPARE(minimal.value("medianQualityPct").toDouble(), 80.0);
    QCOMPARE(minimal.value("medianElapsedSec").toDouble(), 72.0);
}

QTEST_MAIN(AgentEfficiencyTests)
#include "test_agent_efficiency.moc"
