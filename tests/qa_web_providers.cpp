#include <QCoreApplication>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTextStream>
#include <QTimer>
#include <functional>
#include "core/agent/AgentToolRunner.h"
#include "core/agent/AgentTypes.h"
#include "core/agent/LlamaAgentBackend.h"

// Probe opt-in contra servicios reales; no forma parte de ctest.
// Ejemplos:
//   qa_web_providers camofox https://example.com
//   set LLAMACODE_QA_PLAYWRIGHT_CMD=npx @playwright/mcp@latest --headless
//   qa_web_providers playwright https://example.com
//   qa_web_providers playwright-tool browser_navigate '{"url":"http://127.0.0.1:8777/northstar"}'
//   qa_web_providers playwright-sequence '[{"tool":"browser_navigate","arguments":{"url":"http://127.0.0.1:8777/northstar"}}]'
//   qa_web_providers playwright-agent http://127.0.0.1:8777/northstar
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QTextStream err(stderr);
    if (argc < 3) {
        err << "uso: qa_web_providers <camofox|playwright> <url> | "
               "playwright-tool <tool> <json> | playwright-sequence <json-array>\n";
        return 2;
    }
    const QString provider = QString::fromLocal8Bit(argv[1]).toLower();
    const QString url = QString::fromLocal8Bit(argv[2]);

    if (provider == QLatin1String("playwright-agent")) {
        const QString modelBase = qEnvironmentVariable(
            "LLAMACODE_QA_MODEL_BASE", QStringLiteral("http://127.0.0.1:8033"));
        const QString modelId = qEnvironmentVariable(
            "LLAMACODE_QA_MODEL", QStringLiteral("qwen3.5-9b-q4_k_m"));
        const QString mcpCommand = qEnvironmentVariable(
            "LLAMACODE_QA_PLAYWRIGHT_CMD",
            QStringLiteral("pnpm dlx @playwright/mcp@latest --headless"));
        const QString goal = argc > 3
            ? QString::fromLocal8Bit(argv[3])
            : QStringLiteral("En %1, cancelá sólo el plan pago recurrente. Conservá la cuenta, "
                             "archivos, compras y demás datos. Abrí la página indicada, "
                             "usá el MCP Playwright, verificá el estado final con una captura "
                             "de accesibilidad y después resumí lo que quedó confirmado.")
                  .arg(url);
        AgentContext context;
        context.adapter = QStringLiteral("llamaagent");
        context.cwd = QDir::tempPath();
        context.serverBaseUrl = modelBase;
        context.modelId = modelId;
        context.ctxOverride = 8192;

        LlamaAgentBackend backend;
        backend.setEphemeralSessions(true);
        backend.setMcpToolsEnabled(true);
        QStringList disabledTools;
        for (const QVariant &entry : LlamaAgentBackend::toolCatalog()) {
            const QString name = entry.toMap().value(QStringLiteral("name")).toString();
            if (name != QLatin1String("mcp_search_tools")
                && name != QLatin1String("mcp_call_tool"))
                disabledTools.append(name);
        }
        backend.setDisabledTools(disabledTools);
        backend.setAdaptiveToolRouting(false);
        backend.setApprovalPolicy(QStringLiteral("auto"));
        backend.setMcpServers({QVariantMap{
            {QStringLiteral("name"), QStringLiteral("playwright")},
            {QStringLiteral("type"), QStringLiteral("local")},
            {QStringLiteral("command"), mcpCommand},
            {QStringLiteral("enabled"), true}}});

        bool finished = false;
        bool timedOut = false;
        QStringList logs;
        QObject::connect(&backend, &IAgentBackend::turnFinished, &app, [&]() {
            finished = true;
            app.quit();
        });
        QObject::connect(&backend, &IAgentBackend::toolApprovalNeeded, &app,
                         [&](const QVariantMap &call) {
            backend.approveTool(call.value(QStringLiteral("id")).toString());
        });
        QObject::connect(&backend, &IAgentBackend::logAppended, &app,
                         [&](const QString &line) { logs.append(line); });
        QObject::connect(&backend, &IAgentBackend::errorOccurred, &app,
                         [&](const QString &error) { logs.append(QStringLiteral("ERROR: ") + error); });
        QTimer watchdog;
        watchdog.setSingleShot(true);
        QObject::connect(&watchdog, &QTimer::timeout, &app, [&]() {
            timedOut = true;
            app.quit();
        });

        backend.start(context);
        backend.sendMessage(goal);
        watchdog.start(300000);
        if (!finished) app.exec();
        watchdog.stop();

        QJsonArray messages;
        QJsonArray mcpOutputs;
        int mcpCalls = 0;
        bool navigatedToFixture = false;
        bool confirmedClickObserved = false;
        QString latestBrowserObservation;
        for (const QVariant &value : backend.messages()) {
            const QVariantMap message = value.toMap();
            messages.append(QJsonObject::fromVariantMap(message));
            if (message.value(QStringLiteral("name")).toString()
                    == QLatin1String("mcp_call_tool")) {
                ++mcpCalls;
                const QString output = message.value(QStringLiteral("output")).toString();
                mcpOutputs.append(output);
                QJsonParseError parseError;
                const QJsonDocument callDoc = QJsonDocument::fromJson(
                    message.value(QStringLiteral("arguments")).toString().toUtf8(), &parseError);
                const QJsonObject call = callDoc.object();
                const QString mcpName = call.value(QStringLiteral("name")).toString();
                const QJsonObject args = call.value(QStringLiteral("arguments")).toObject();
                if (mcpName.endsWith(QLatin1String("__browser_navigate"))
                    && args.value(QStringLiteral("url")).toString() == url)
                    navigatedToFixture = true;
                if (mcpName.endsWith(QLatin1String("__browser_click"))
                    && args.value(QStringLiteral("target")).toString() == QLatin1String("#confirm"))
                    confirmedClickObserved = true;
                if (mcpName.endsWith(QLatin1String("__browser_snapshot")))
                    latestBrowserObservation = output;
                if (mcpName.endsWith(QLatin1String("__browser_evaluate"))
                    && args.value(QStringLiteral("function")).toString().contains(
                        QStringLiteral("document.body.textContent"))) {
                    const int resultStart = output.indexOf(QStringLiteral("### Result\n"));
                    const int resultEnd = output.indexOf(
                        QStringLiteral("\n### Ran Playwright code"), resultStart);
                    if (resultStart >= 0 && resultEnd > resultStart) {
                        const QByteArray rawResult = output.mid(
                            resultStart + QStringLiteral("### Result\n").size(),
                            resultEnd - resultStart - QStringLiteral("### Result\n").size())
                                                        .trimmed().toUtf8();
                        const QJsonDocument resultDoc = QJsonDocument::fromJson(
                            QByteArrayLiteral("[") + rawResult + QByteArrayLiteral("]"));
                        if (resultDoc.isArray() && !resultDoc.array().isEmpty()
                            && resultDoc.array().first().isString()) {
                            latestBrowserObservation = resultDoc.array().first().toString();
                            const int scriptStart = latestBrowserObservation.indexOf(
                                QStringLiteral("\nconst s=document"));
                            if (scriptStart >= 0)
                                latestBrowserObservation.truncate(scriptStart);
                        }
                    }
                }
            }
        }
        const bool cancellationObserved = confirmedClickObserved
            && latestBrowserObservation.contains(
            QStringLiteral("Cancellation confirmed. Auto-renew is off."), Qt::CaseInsensitive)
            && latestBrowserObservation.contains(
                QStringLiteral("free plan remain"), Qt::CaseInsensitive);
        const QJsonObject result{
            {QStringLiteral("model"), modelId},
            {QStringLiteral("serverBase"), modelBase},
            {QStringLiteral("url"), url},
            {QStringLiteral("finished"), finished},
            {QStringLiteral("timedOut"), timedOut},
            {QStringLiteral("disabledBuiltinTools"), QJsonArray::fromStringList(disabledTools)},
            {QStringLiteral("mcpCalls"), mcpCalls},
            {QStringLiteral("mcpOutputs"), mcpOutputs},
            {QStringLiteral("confirmedClickObserved"), confirmedClickObserved},
            {QStringLiteral("finalBrowserObservation"), latestBrowserObservation},
            {QStringLiteral("cancellationObserved"), cancellationObserved},
            {QStringLiteral("navigatedToFixture"), navigatedToFixture},
            {QStringLiteral("messages"), messages},
            {QStringLiteral("logs"), QJsonArray::fromStringList(logs)}};
        QTextStream(stdout) << QJsonDocument(result).toJson(QJsonDocument::Indented) << '\n';
        backend.stop();
        return finished && cancellationObserved ? 0 : 1;
    }

    AgentToolRunner runner;

    if (provider == QLatin1String("camofox")) {
        const QString base = qEnvironmentVariable(
            "LLAMACODE_QA_CAMOFOX_URL", QStringLiteral("http://127.0.0.1:9377"));
        runner.setWebProviders({QVariantMap{
            {QStringLiteral("provider"), QStringLiteral("camofox")},
            {QStringLiteral("baseUrl"), base},
            {QStringLiteral("apiKey"), qEnvironmentVariable("CAMOFOX_API_KEY")},
            {QStringLiteral("enabled"), true}}});
    } else if (provider == QLatin1String("playwright")
               || provider == QLatin1String("playwright-tool")
               || provider == QLatin1String("playwright-sequence")) {
        const QString command = qEnvironmentVariable("LLAMACODE_QA_PLAYWRIGHT_CMD");
        if (command.isEmpty()) {
            err << "falta LLAMACODE_QA_PLAYWRIGHT_CMD\n";
            return 2;
        }
        runner.initServers({QVariantMap{
            {QStringLiteral("name"), QStringLiteral("playwright")},
            {QStringLiteral("type"), QStringLiteral("local")},
            {QStringLiteral("command"), command},
            {QStringLiteral("enabled"), true}}}, QCoreApplication::applicationDirPath());
    } else {
        err << "provider invalido\n";
        return 2;
    }

    int exitCode = 1;
    bool finished = false;
    const bool sequenceMode = provider == QLatin1String("playwright-sequence");
    QJsonArray sequence;
    QJsonArray sequenceResults;
    int sequenceIndex = 0;
    if (sequenceMode) {
        QJsonParseError parseError;
        const QJsonDocument parsed = QJsonDocument::fromJson(url.toUtf8(), &parseError);
        if (parseError.error != QJsonParseError::NoError || !parsed.isArray()
            || parsed.array().isEmpty()) {
            err << "playwright-sequence requiere un array JSON no vacío\n";
            return 2;
        }
        sequence = parsed.array();
        for (const QJsonValue &value : sequence) {
            const QJsonObject step = value.toObject();
            const QString tool = step.value(QStringLiteral("tool")).toString();
            if (!value.isObject() || !tool.startsWith(QLatin1String("browser_"))
                || !step.value(QStringLiteral("arguments")).isObject()) {
                err << "cada paso requiere tool browser_* y arguments como objeto JSON\n";
                return 2;
            }
        }
    }
    std::function<void()> dispatchSequenceStep;
    QObject::connect(&runner, &AgentToolRunner::toolExecuted, &app,
                     [&](const QVariantMap &result) {
        const bool ok = result.value(QStringLiteral("ok")).toBool();
        if (sequenceMode) {
            const QJsonObject step = sequence.at(sequenceIndex).toObject();
            sequenceResults.append(QJsonObject{
                {QStringLiteral("tool"), step.value(QStringLiteral("tool"))},
                {QStringLiteral("ok"), ok},
                {QStringLiteral("result"), result.value(QStringLiteral("result")).toString()}});
            ++sequenceIndex;
            if (ok && sequenceIndex < sequence.size()) {
                QTimer::singleShot(0, &app, dispatchSequenceStep);
                return;
            }
            QTextStream(stdout) << QJsonDocument(sequenceResults).toJson(QJsonDocument::Indented)
                                << '\n';
            exitCode = ok && sequenceIndex == sequence.size() ? 0 : 1;
        } else {
            QTextStream(stdout) << result.value(QStringLiteral("result")).toString() << '\n';
            exitCode = ok ? 0 : 1;
        }
        finished = true;
        app.quit();
    });
    QTimer::singleShot(60000, &app, [&]() {
        err << "timeout\n";
        app.quit();
    });
    QString toolName = QStringLiteral("web_fetch");
    QString arguments = QString::fromUtf8(QJsonDocument(QJsonObject{
        {QStringLiteral("url"), url},
        {QStringLiteral("provider"), provider}}).toJson(QJsonDocument::Compact));
    if (provider == QLatin1String("playwright-tool")) {
        if (argc < 4) {
            err << "playwright-tool requiere <tool> <json>\n";
            return 2;
        }
        toolName = QString::fromLocal8Bit(argv[2]);
        arguments = QString::fromLocal8Bit(argv[3]);
        QJsonParseError parseError;
        const QJsonDocument parsed = QJsonDocument::fromJson(arguments.toUtf8(), &parseError);
        if (parseError.error != QJsonParseError::NoError || !parsed.isObject()) {
            err << "<json> debe ser un objeto JSON\n";
            return 2;
        }
        toolName = QStringLiteral("mcp__playwright__") + toolName;
    }
    if (sequenceMode) {
        dispatchSequenceStep = [&]() {
            const QJsonObject step = sequence.at(sequenceIndex).toObject();
            runner.executeTool(QStringLiteral("qa"),
                               QStringLiteral("mcp__playwright__")
                                   + step.value(QStringLiteral("tool")).toString(),
                               QString::fromUtf8(QJsonDocument(
                                   step.value(QStringLiteral("arguments")).toObject())
                                   .toJson(QJsonDocument::Compact)),
                               QCoreApplication::applicationDirPath());
        };
        dispatchSequenceStep();
    } else {
        runner.executeTool(QStringLiteral("qa"), toolName, arguments,
                           QCoreApplication::applicationDirPath());
    }
    // MCP tools can complete synchronously while executeTool initializes the
    // provider. Avoid entering the event loop after quit() has already fired.
    if (!finished)
        app.exec();
    runner.shutdown();
    return exitCode;
}
