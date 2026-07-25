#include "OpenCodeIntegration.h"

#include <QDir>
#include <QFileInfo>

QString OpenCodeIntegration::modelRef(const QString &modelId)
{
    return QStringLiteral("llamacode/") + modelId;
}

QJsonObject OpenCodeIntegration::buildConfig(const QString &gatewayV1Url,
                                             const QJsonArray &models,
                                             const QString &selectedModelId)
{
    QJsonObject modelMap;
    for (const QJsonValue &value : models) {
        const QJsonObject entry = value.toObject();
        const QString id = entry.value(QStringLiteral("id")).toString();
        if (id.isEmpty()) continue;

        QJsonObject model{
            {QStringLiteral("name"), entry.value(QStringLiteral("name")).toString(id)},
            {QStringLiteral("tool_call"), true}
        };
        const int context = entry.value(QStringLiteral("context")).toInt();
        const int output = entry.value(QStringLiteral("output")).toInt();
        if (context > 0 || output > 0) {
            QJsonObject limit;
            if (context > 0) limit.insert(QStringLiteral("context"), context);
            if (output > 0) limit.insert(QStringLiteral("output"), output);
            model.insert(QStringLiteral("limit"), limit);
        }
        modelMap.insert(id, model);
    }

    const QJsonObject provider{
        {QStringLiteral("npm"), QStringLiteral("@ai-sdk/openai-compatible")},
        {QStringLiteral("name"), QStringLiteral("LlamaCode local")},
        {QStringLiteral("options"), QJsonObject{
            {QStringLiteral("baseURL"), gatewayV1Url},
            {QStringLiteral("apiKey"), QStringLiteral("{env:LLAMACODE_GATEWAY_API_KEY}")}
        }},
        {QStringLiteral("models"), modelMap}
    };

    QJsonObject root{
        {QStringLiteral("$schema"), QStringLiteral("https://opencode.ai/config.json")},
        {QStringLiteral("enabled_providers"), QJsonArray{QStringLiteral("llamacode")}},
        {QStringLiteral("provider"), QJsonObject{{QStringLiteral("llamacode"), provider}}}
    };
    if (!selectedModelId.isEmpty())
        root.insert(QStringLiteral("model"), modelRef(selectedModelId));
    return root;
}

QString OpenCodeIntegration::preferredWindowsExecutable(
    const QString &commandWrapper, const QString &nativeExecutable,
    const QString &genericExecutable)
{
    if (!commandWrapper.isEmpty()) return commandWrapper;
    if (!nativeExecutable.isEmpty()) return nativeExecutable;
    return genericExecutable;
}

bool OpenCodeIntegration::requiresWindowsCommandShell(const QString &executable)
{
    const QString suffix = QFileInfo(executable).suffix().toLower();
    return suffix == QLatin1String("cmd") || suffix == QLatin1String("bat");
}

static QString quoteForCmd(QString value)
{
    value.replace(QLatin1Char('"'), QStringLiteral("\"\""));
    return QStringLiteral("\"%1\"").arg(QDir::toNativeSeparators(value));
}

QString OpenCodeIntegration::windowsCommand(const QString &executable,
                                            const QString &projectDir,
                                            const QString &model)
{
    const QString call = requiresWindowsCommandShell(executable)
        ? QStringLiteral("call ") : QString();
    return QStringLiteral("%1%2 %3 -m %4 || "
                          "(echo. & echo OpenCode no pudo iniciar. & pause)")
        .arg(call, quoteForCmd(executable), quoteForCmd(projectDir),
             quoteForCmd(model));
}

QByteArray OpenCodeIntegration::windowsLauncherScript(const QString &executable,
                                                      const QString &projectDir,
                                                      const QString &model)
{
    const QString command = windowsCommand(executable, projectDir, model);
    return QStringLiteral("@echo off\r\n%1\r\n")
        .arg(command).toUtf8();
}
