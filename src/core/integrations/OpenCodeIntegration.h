#pragma once

#include <QJsonArray>
#include <QJsonObject>
#include <QString>

// Construcción pura de la configuración efímera que LlamaCode inyecta al
// proceso OpenCode. No modifica la configuración global ni la del proyecto.
class OpenCodeIntegration
{
public:
    static QJsonObject buildConfig(const QString &gatewayV1Url,
                                   const QJsonArray &models,
                                   const QString &selectedModelId);
    static QString modelRef(const QString &modelId);
    static QString preferredWindowsExecutable(const QString &commandWrapper,
                                              const QString &nativeExecutable,
                                              const QString &genericExecutable);
    static bool requiresWindowsCommandShell(const QString &executable);
    static QString windowsCommand(const QString &executable,
                                  const QString &projectDir,
                                  const QString &model);
    static QByteArray windowsLauncherScript(const QString &executable,
                                            const QString &projectDir,
                                            const QString &model);
};
