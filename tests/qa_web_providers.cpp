#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTextStream>
#include <QTimer>
#include <functional>
#include "core/agent/AgentToolRunner.h"

// Probe opt-in contra servicios reales; no forma parte de ctest.
// Ejemplos:
//   qa_web_providers camofox https://example.com
//   set LLAMACODE_QA_PLAYWRIGHT_CMD=npx @playwright/mcp@latest --headless
//   qa_web_providers playwright https://example.com
//   qa_web_providers playwright-tool browser_navigate '{"url":"http://127.0.0.1:8777/northstar"}'
//   qa_web_providers playwright-sequence '[{"tool":"browser_navigate","arguments":{"url":"http://127.0.0.1:8777/northstar"}}]'
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
