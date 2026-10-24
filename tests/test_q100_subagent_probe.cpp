#include <QtTest>
#include <QCoreApplication>
#include <QDir>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QThread>
#include <QUrl>

#include "core/agent/LlamaAgentBackend.h"

static bool q100HasExactMarkerLabels(const QString &text, const QString &alphaMarker,
                                    const QString &betaMarker)
{
    QString finalAnswer = text;
    const qsizetype thinkEnd = finalAnswer.lastIndexOf(QStringLiteral("</think>"),
                                                        Qt::CaseInsensitive);
    if (thinkEnd >= 0)
        finalAnswer = finalAnswer.mid(thinkEnd + QStringLiteral("</think>").size());
    finalAnswer = finalAnswer.simplified();

    const QString expected = QStringLiteral("^ALPHA=%1; BETA=%2$")
                                 .arg(QRegularExpression::escape(alphaMarker),
                                      QRegularExpression::escape(betaMarker));
    return QRegularExpression(expected).match(finalAnswer).hasMatch();
}

class Q100SubagentProbe final : public QObject
{
    Q_OBJECT
private slots:
    void productionOneMillionContextStaysSerial();
    void exactMarkerLabelsAcceptCorrectOrder();
    void exactMarkerLabelsRejectSwappedOrder();
    void exactMarkerLabelsRejectMissingValue();
    void exactMarkerLabelsRejectCorrectReasoningWithWrongFinalAnswer();
    void realBackendSubagentFanoutProbe();
};

void Q100SubagentProbe::productionOneMillionContextStaysSerial()
{
    using Backend = LlamaAgentBackend;
    // The production ASTRA DEFAULT 1M profile uses its full context budget for
    // subagents unless a smaller subagentContextTokens budget is configured.
    QCOMPARE(Backend::adaptiveSubagentLimit(2, 1048576, 49152, 4096), 1);
    // This is a distinct, explicit 8K-per-subagent candidate policy, not evidence
    // that the unmodified production profile can safely fan out at 1M.
    QCOMPARE(Backend::adaptiveSubagentLimit(2, 1048576, 49152, 4096, 8192), 2);
}

void Q100SubagentProbe::exactMarkerLabelsAcceptCorrectOrder()
{
    QVERIFY(q100HasExactMarkerLabels(
        QStringLiteral("<think>reasoning</think>\nALPHA=alpha-7; BETA=beta-3"),
        QStringLiteral("alpha-7"), QStringLiteral("beta-3")));
}

void Q100SubagentProbe::exactMarkerLabelsRejectSwappedOrder()
{
    QVERIFY(!q100HasExactMarkerLabels(
        QStringLiteral("ALPHA=beta-3; BETA=alpha-7"),
        QStringLiteral("alpha-7"), QStringLiteral("beta-3")));
}

void Q100SubagentProbe::exactMarkerLabelsRejectMissingValue()
{
    QVERIFY(!q100HasExactMarkerLabels(
        QStringLiteral("ALPHA=alpha-7; BETA=<no leído>"),
        QStringLiteral("alpha-7"), QStringLiteral("beta-3")));
}

void Q100SubagentProbe::exactMarkerLabelsRejectCorrectReasoningWithWrongFinalAnswer()
{
    QVERIFY(!q100HasExactMarkerLabels(
        QStringLiteral("<think>Expected: ALPHA=alpha-7; BETA=beta-3</think>\n"
                       "ALPHA=beta-3; BETA=alpha-7"),
        QStringLiteral("alpha-7"), QStringLiteral("beta-3")));
}

static void q100WriteJson(const QString &path, const QJsonObject &value)
{
    if (path.isEmpty()) return;
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly)) return;
    file.write(QJsonDocument(value).toJson(QJsonDocument::Indented));
    file.write("\n");
    file.commit();
}

static int q100ActiveTaskCards(const QVariantList &messages)
{
    int active = 0;
    for (const QVariant &value : messages) {
        const QVariantMap card = value.toMap();
        if (card.value(QStringLiteral("role")).toString() == QLatin1String("toolcall")
            && card.value(QStringLiteral("name")).toString() == QLatin1String("task")
            && card.value(QStringLiteral("typing")).toBool())
            ++active;
    }
    return active;
}

void Q100SubagentProbe::realBackendSubagentFanoutProbe()
{
    const QString baseUrl = qEnvironmentVariable("LLAMACODE_Q100_SERVER_URL").trimmed();
    if (baseUrl.isEmpty())
        QSKIP("Q100 is opt-in; set LLAMACODE_Q100_SERVER_URL to the owned loopback ASTRA endpoint.");

    const QUrl endpoint(baseUrl, QUrl::StrictMode);
    QVERIFY2(endpoint.isValid(), qPrintable(QStringLiteral("invalid Q100 endpoint: %1").arg(baseUrl)));
    QVERIFY2(endpoint.scheme() == QLatin1String("http"), "Q100 accepts loopback HTTP only.");
    QVERIFY2(endpoint.host() == QLatin1String("127.0.0.1")
                 || endpoint.host() == QLatin1String("localhost"),
             "Q100 must never send prompts outside this host.");
    QVERIFY2(endpoint.port(-1) > 0, "Q100 endpoint must include an explicit port.");
    QVERIFY2(endpoint.path().isEmpty() || endpoint.path() == QLatin1String("/"),
             "Provide the server base URL without an API path.");

    QStandardPaths::setTestModeEnabled(true);
    const QString outputPath = qEnvironmentVariable("LLAMACODE_Q100_OUT").trimmed();
    const QStringList seeds{QStringLiteral("5051"), QStringLiteral("5052"), QStringLiteral("5053")};
    QJsonArray runResults;
    QJsonObject partial{{QStringLiteral("taskId"), QStringLiteral("Q-20261024-VF-ITERATION-100")},
                        {QStringLiteral("experimentId"), QStringLiteral("VF-20261019-01-S1-ASTRA-LLAMACODE-SUBAGENT-FANOUT-Q100")},
                        {QStringLiteral("serverBaseUrl"), baseUrl},
                        {QStringLiteral("contextTokens"), 65536},
                        {QStringLiteral("serverSlots"), 2},
                        {QStringLiteral("runs"), runResults}};
    q100WriteJson(outputPath, partial);

    for (const QString &seedText : seeds) {
        const int seed = seedText.toInt();
        QStringList policies{QStringLiteral("serial"), QStringLiteral("parallel2")};
        if (seed == 5052) policies.swapItemsAt(0, 1); // balance warm-cache/order effects

        for (const QString &policy : policies) {
            QJsonObject run{{QStringLiteral("seed"), seed},
                            {QStringLiteral("policy"), policy},
                            {QStringLiteral("started"), true}};
            QTemporaryDir project;
            if (!project.isValid()) {
                run.insert(QStringLiteral("error"), QStringLiteral("temporary project unavailable"));
                run.insert(QStringLiteral("acceptedTasks"), 0);
                runResults.append(run);
                partial.insert(QStringLiteral("runs"), runResults);
                q100WriteJson(outputPath, partial);
                continue;
            }

            const QByteArray alphaMarker = QByteArray("Q100_ALPHA_PRIVATE_")
                + QByteArray::number(seed) + QByteArray("_7c1d9");
            const QByteArray betaMarker = QByteArray("Q100_BETA_PRIVATE_")
                + QByteArray::number(seed) + QByteArray("_3f8a2");
            QFile alpha(project.filePath(QStringLiteral("marker-alpha.txt")));
            QFile beta(project.filePath(QStringLiteral("marker-beta.txt")));
            const bool alphaOpened = alpha.open(QIODevice::WriteOnly | QIODevice::Truncate);
            const bool alphaWritten = alphaOpened && alpha.write(alphaMarker) == alphaMarker.size();
            if (alphaOpened) alpha.close();
            const bool betaOpened = beta.open(QIODevice::WriteOnly | QIODevice::Truncate);
            const bool betaWritten = betaOpened && beta.write(betaMarker) == betaMarker.size();
            if (betaOpened) beta.close();
            const bool fixturesReady = alphaWritten && betaWritten;
            if (!fixturesReady) {
                run.insert(QStringLiteral("error"), QStringLiteral("fixture write failed"));
                run.insert(QStringLiteral("acceptedTasks"), 0);
                runResults.append(run);
                partial.insert(QStringLiteral("runs"), runResults);
                q100WriteJson(outputPath, partial);
                continue;
            }

            AgentContext context;
            context.adapter = QStringLiteral("llamaagent");
            context.cwd = project.path();
            context.serverBaseUrl = baseUrl;
            context.modelId = QStringLiteral("q100-astra-flash-next-iq2xs");
            context.ctxOverride = 65536;
            context.externalEndpoint = true;
            context.parallelSlots = policy == QLatin1String("parallel2") ? 2 : 1;
            context.vramTotalMb = 49152.0;
            context.vramFreeMb = 4096.0;

            LlamaAgentBackend backend;
            backend.setEphemeralSessions(true);
            backend.setMcpToolsEnabled(false);
            backend.setApprovalPolicy(QStringLiteral("auto"));
            backend.setDeterministicSeed(seed);
            backend.setAgentTuning(QString(), 0.6);
            backend.setThinkingEnabled(true);
            backend.setReasoningPolicy(QStringLiteral("medium"), 1024);

            HarnessEscalationModule escalation;
            escalation.set = true;
            escalation.subagentsEnabled = true;
            escalation.maxParallelSubagents = 2;
            escalation.subagentContextTokens = 65536;
            escalation.isolateSubagents = true;
            backend.setEscalationPolicy(escalation);

            QStringList disabledTools;
            for (const QVariant &entry : LlamaAgentBackend::toolCatalog()) {
                const QString name = entry.toMap().value(QStringLiteral("name")).toString();
                if (name != QLatin1String("task")) disabledTools << name;
            }
            disabledTools << QStringLiteral("mcp_search_tools") << QStringLiteral("mcp_call_tool");
            backend.setDisabledTools(disabledTools);
            backend.start(context);

            int maxBusy = 0;
            QObject::connect(&backend, &IAgentBackend::messagesChanged, &backend, [&]() {
                maxBusy = qMax(maxBusy, q100ActiveTaskCards(backend.messages()));
            });
            QSignalSpy finished(&backend, &IAgentBackend::turnFinished);
            QElapsedTimer timer;
            timer.start();
            const QString prompt = QStringLiteral(
                "Delegá exactamente dos subtareas independientes con dos llamadas a `task` "
                "en el mismo mensaje. La primera subtarea debe hacer una sola llamada a "
                "read_file para marker-alpha.txt y devolver su única línea exacta; la segunda "
                "debe hacer una sola llamada a read_file para marker-beta.txt. Cada subagente "
                "sólo puede usar read_file, una vez. El agente principal sólo puede usar task: "
                "no leas los archivos ni llames read_file directamente, no uses shell, web, "
                "edición, escritura ni otras herramientas. No alteres los archivos. Esperá "
                "ambos resultados; luego no uses más herramientas y respondé únicamente "
                "ALPHA=<línea leída>; BETA=<línea leída>.");
            backend.sendMessage(prompt);

            const qint64 timeoutMs = 12 * 60 * 1000;
            while (finished.isEmpty() && timer.elapsed() < timeoutMs) {
                QCoreApplication::processEvents(QEventLoop::AllEvents, 100);
                QThread::msleep(40);
            }
            const bool turnFinished = !finished.isEmpty();
            const qint64 elapsedMs = timer.elapsed();
            if (!turnFinished) backend.cancelGeneration();

            const QJsonArray api = backend.apiMessagesForTest();
            const QVariantList messages = backend.messages();
            QJsonArray firstBatch;
            for (const QJsonValue &value : api) {
                const QJsonObject item = value.toObject();
                const QJsonArray calls = item.value(QStringLiteral("tool_calls")).toArray();
                if (item.value(QStringLiteral("role")).toString() == QLatin1String("assistant")
                    && !calls.isEmpty()) {
                    firstBatch = calls;
                    break;
                }
            }

            int taskCalls = 0;
            int unexpectedParentTools = 0;
            for (const QJsonValue &value : api) {
                const QJsonObject item = value.toObject();
                if (item.value(QStringLiteral("role")).toString() != QLatin1String("assistant")) continue;
                for (const QJsonValue &callValue : item.value(QStringLiteral("tool_calls")).toArray()) {
                    const QString name = callValue.toObject().value(QStringLiteral("function"))
                        .toObject().value(QStringLiteral("name")).toString();
                    if (name == QLatin1String("task")) ++taskCalls;
                    else ++unexpectedParentTools;
                }
            }
            int firstBatchTaskCalls = 0;
            for (const QJsonValue &value : firstBatch) {
                if (value.toObject().value(QStringLiteral("function")).toObject()
                        .value(QStringLiteral("name")).toString() == QLatin1String("task"))
                    ++firstBatchTaskCalls;
            }

            QJsonArray taskCards;
            QJsonArray subagentTools;
            int acceptedTasks = 0;
            bool alphaReturned = false;
            bool betaReturned = false;
            QString finalText;
            const QRegularExpression toolTrace(QStringLiteral("🔧\\s*([A-Za-z0-9_]+)"));
            for (const QVariant &value : messages) {
                const QVariantMap message = value.toMap();
                const QString role = message.value(QStringLiteral("role")).toString();
                if (role == QLatin1String("assistant")
                    && !message.value(QStringLiteral("content")).toString().trimmed().isEmpty())
                    finalText = message.value(QStringLiteral("content")).toString();
                if (role != QLatin1String("toolcall")
                    || message.value(QStringLiteral("name")).toString() != QLatin1String("task"))
                    continue;
                const QString output = message.value(QStringLiteral("output")).toString();
                const bool ok = message.value(QStringLiteral("ok")).toBool();
                if (ok && output.contains(QString::fromLatin1(alphaMarker))) alphaReturned = true;
                if (ok && output.contains(QString::fromLatin1(betaMarker))) betaReturned = true;
                if (ok && (output.contains(QString::fromLatin1(alphaMarker))
                           || output.contains(QString::fromLatin1(betaMarker)))) ++acceptedTasks;
                QJsonArray tools;
                auto it = toolTrace.globalMatch(output);
                while (it.hasNext()) {
                    const QString name = it.next().captured(1);
                    tools.append(name);
                    if (name != QLatin1String("read_file")) subagentTools.append(name);
                }
                taskCards.append(QJsonObject{{QStringLiteral("ok"), ok},
                                             {QStringLiteral("output"), output},
                                             {QStringLiteral("toolTrace"), tools}});
            }
            const bool exactFinal = q100HasExactMarkerLabels(
                finalText, QString::fromLatin1(alphaMarker), QString::fromLatin1(betaMarker));
            const bool noUnexpectedTools = unexpectedParentTools == 0 && subagentTools.isEmpty();
            const bool twoTaskCards = taskCards.size() == 2;
            const bool qualityPassed = turnFinished && firstBatchTaskCalls == 2 && twoTaskCards
                && acceptedTasks == 2 && alphaReturned && betaReturned && exactFinal
                && noUnexpectedTools;

            QProcess git;
            git.start(QStringLiteral("git"), {QStringLiteral("-C"), project.path(),
                                               QStringLiteral("worktree"), QStringLiteral("list"),
                                               QStringLiteral("--porcelain")});
            const bool gitDone = git.waitForFinished(5000);
            const QString worktrees = QString::fromLocal8Bit(git.readAllStandardOutput());
            const int worktreeCount = worktrees.count(QStringLiteral("\nworktree ")) + 1;
            backend.stop();

            run.insert(QStringLiteral("turnFinished"), turnFinished);
            run.insert(QStringLiteral("elapsedMs"), elapsedMs);
            run.insert(QStringLiteral("acceptedTasks"), acceptedTasks);
            run.insert(QStringLiteral("taskCalls"), taskCalls);
            run.insert(QStringLiteral("firstBatchTaskCalls"), firstBatchTaskCalls);
            run.insert(QStringLiteral("unexpectedParentTools"), unexpectedParentTools);
            run.insert(QStringLiteral("unexpectedSubagentTools"), subagentTools);
            run.insert(QStringLiteral("maxBusySubagentCards"), maxBusy);
            run.insert(QStringLiteral("alphaMarkerReturned"), alphaReturned);
            run.insert(QStringLiteral("betaMarkerReturned"), betaReturned);
            run.insert(QStringLiteral("exactFinal"), exactFinal);
            run.insert(QStringLiteral("qualityPassed"), qualityPassed);
            run.insert(QStringLiteral("gitWorktreeListRead"), gitDone);
            run.insert(QStringLiteral("remainingWorktreeCount"), worktreeCount);
            run.insert(QStringLiteral("taskCards"), taskCards);
            run.insert(QStringLiteral("finalText"), finalText);
            runResults.append(run);
            partial.insert(QStringLiteral("runs"), runResults);
            q100WriteJson(outputPath, partial);
            qInfo().noquote() << "Q100_RUN_RESULT "
                              << QString::fromUtf8(QJsonDocument(run).toJson(QJsonDocument::Compact));
        }
    }

    int acceptedByPolicy[2] = {0, 0};
    qint64 elapsedByPolicy[2] = {0, 0};
    bool allQuality = runResults.size() == 6;
    bool concurrencyObserved = true;
    for (const QJsonValue &value : runResults) {
        const QJsonObject run = value.toObject();
        const QString policy = run.value(QStringLiteral("policy")).toString();
        const int index = policy == QLatin1String("parallel2") ? 1 : 0;
        acceptedByPolicy[index] += run.value(QStringLiteral("acceptedTasks")).toInt();
        elapsedByPolicy[index] += run.value(QStringLiteral("elapsedMs")).toVariant().toLongLong();
        allQuality = allQuality && run.value(QStringLiteral("qualityPassed")).toBool();
        const int expectedBusy = index == 1 ? 2 : 1;
        concurrencyObserved = concurrencyObserved
            && run.value(QStringLiteral("maxBusySubagentCards")).toInt() == expectedBusy;
    }
    const double serialRate = elapsedByPolicy[0] > 0
        ? acceptedByPolicy[0] * 1000.0 / elapsedByPolicy[0] : 0.0;
    const double parallelRate = elapsedByPolicy[1] > 0
        ? acceptedByPolicy[1] * 1000.0 / elapsedByPolicy[1] : 0.0;
    const double ratio = serialRate > 0.0 ? parallelRate / serialRate : 0.0;
    const bool noAccuracyLoss = acceptedByPolicy[1] >= acceptedByPolicy[0];
    const bool throughputGate = ratio >= 1.10;
    const bool screenPass = allQuality && concurrencyObserved && noAccuracyLoss && throughputGate;
    partial.insert(QStringLiteral("aggregate"), QJsonObject{
        {QStringLiteral("acceptedTasksSerial"), acceptedByPolicy[0]},
        {QStringLiteral("acceptedTasksParallel2"), acceptedByPolicy[1]},
        {QStringLiteral("elapsedSerialMs"), static_cast<double>(elapsedByPolicy[0])},
        {QStringLiteral("elapsedParallel2Ms"), static_cast<double>(elapsedByPolicy[1])},
        {QStringLiteral("acceptedTasksPerSecondSerial"), serialRate},
        {QStringLiteral("acceptedTasksPerSecondParallel2"), parallelRate},
        {QStringLiteral("throughputRatioParallelVsSerial"), ratio},
        {QStringLiteral("allSixQualityPass"), allQuality},
        {QStringLiteral("expectedConcurrencyObserved"), concurrencyObserved},
        {QStringLiteral("noAccuracyLoss"), noAccuracyLoss},
        {QStringLiteral("throughputAtLeast10PctFaster"), throughputGate},
        {QStringLiteral("screenPass"), screenPass},
        {QStringLiteral("productionAdoption"), false}
    });
    partial.insert(QStringLiteral("completed"), runResults.size() == 6);
    q100WriteJson(outputPath, partial);
    qInfo().noquote() << "Q100_SCREEN_GATE "
                      << QString::fromUtf8(QJsonDocument(partial.value(QStringLiteral("aggregate")).toObject())
                                                .toJson(QJsonDocument::Compact));
    QVERIFY2(runResults.size() == 6,
             "Q100 live screen did not finish all six preregistered runs; inspect LLAMACODE_Q100_OUT.");
}

QTEST_GUILESS_MAIN(Q100SubagentProbe)

#include "test_q100_subagent_probe.moc"
