#pragma once

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QString>
#include "ProfileTypes.h"

namespace ManagedServerCapabilities {

// The adaptive VRAM ladder mutates llama.cpp CLI flags such as --fit and
// --fit-target. Strata is configured through its JSON file and rejects them.
inline bool supportsAdaptiveLlamaMemoryPolicy(const BackendProfile &backend)
{
    return backend.managedServer.value(QStringLiteral("type")).toString()
        != QLatin1String("astra-strata");
}

// Strata keeps its vision encoder outside the normal OpenAI server arguments.
// Only advertise image support when the config enables vision and both files
// needed to serve images are present.
inline bool strataVisionAvailable(const QString &configPath, const QString &root)
{
    QFile configFile(configPath);
    if (!configFile.open(QIODevice::ReadOnly))
        return false;

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(configFile.readAll(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject())
        return false;

    const QJsonObject object = document.object();
    bool visionFlag = false;
    for (const QJsonValue &value : object.value(QStringLiteral("args")).toArray()) {
        if (value.toString() == QLatin1String("--vision")) {
            visionFlag = true;
            break;
        }
    }
    if (!visionFlag)
        return false;

    const QJsonObject vision = object.value(QStringLiteral("vision")).toObject();
    const QString exe = vision.value(QStringLiteral("exe")).toString().trimmed();
    const QString mmproj = vision.value(QStringLiteral("mmproj")).toString().trimmed();
    if (exe.isEmpty() || mmproj.isEmpty())
        return false;

    const QDir base(root);
    const QString exePath = QDir::isAbsolutePath(exe) ? exe : base.filePath(exe);
    const QString mmprojPath = QDir::isAbsolutePath(mmproj) ? mmproj : base.filePath(mmproj);
    return QFileInfo(exePath).isFile() && QFileInfo(mmprojPath).isFile();
}

} // namespace ManagedServerCapabilities
