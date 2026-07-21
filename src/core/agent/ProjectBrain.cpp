#include "ProjectBrain.h"
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QHash>
#include <QSaveFile>
#include <QSet>
#include <QStandardPaths>

namespace {
QByteArray contentHash(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) return {};
    QCryptographicHash hash(QCryptographicHash::Sha256);
    if (!hash.addData(&file)) return {};
    return hash.result().toHex();
}
}

QString ProjectBrain::cachePath(const QString &root)
{
    const QString key = QString::fromLatin1(QCryptographicHash::hash(
        QDir(root).absolutePath().toUtf8(), QCryptographicHash::Sha256).toHex().left(24));
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                        + QStringLiteral("/project_brain");
    QDir().mkpath(dir);
    return dir + QLatin1Char('/') + key + QStringLiteral(".json");
}

QVariantMap ProjectBrain::load(const QString &root)
{
    QFile file(cachePath(root));
    if (!file.open(QIODevice::ReadOnly)) return {};
    return QJsonDocument::fromJson(file.readAll()).object().toVariantMap();
}

QVariantMap ProjectBrain::refresh(const QString &root, int maxFiles)
{
    const QDir base(root);
    if (!base.exists()) return {{QStringLiteral("error"), QStringLiteral("workspace inexistente")}};
    const int effectiveMax = qBound(1, maxFiles, 20000);
    static const QSet<QString> ignored{QStringLiteral(".git"), QStringLiteral("build"),
        QStringLiteral("build_tests"), QStringLiteral("node_modules"), QStringLiteral("dist"),
        QStringLiteral("target"), QStringLiteral(".venv"), QStringLiteral("venv")};
    QVariantList files;
    QVariantMap extensions;
    qint64 bytes = 0;
    const QVariantMap previous = load(root);
    QHash<QString, QVariantMap> previousFiles;
    for (const QVariant &value : previous.value(QStringLiteral("files")).toList()) {
        const QVariantMap item = value.toMap();
        previousFiles.insert(item.value(QStringLiteral("path")).toString(), item);
    }
    int added = 0, updated = 0, reused = 0;
    QDirIterator it(root, QDir::Files | QDir::NoDotAndDotDot, QDirIterator::Subdirectories);
    while (it.hasNext() && files.size() < effectiveMax) {
        it.next();
        const QFileInfo info = it.fileInfo();
        const QString rel = base.relativeFilePath(info.absoluteFilePath());
        bool skip = false;
        for (const QString &part : rel.split(QLatin1Char('/')))
            if (ignored.contains(part)) { skip = true; break; }
        if (skip || info.size() > 4 * 1024 * 1024) continue;
        const QString ext = info.suffix().toLower();
        extensions[ext.isEmpty() ? QStringLiteral("(none)") : ext]
            = extensions.value(ext.isEmpty() ? QStringLiteral("(none)") : ext).toInt() + 1;
        bytes += info.size();
        const qint64 modifiedMs = info.lastModified().toMSecsSinceEpoch();
        const QVariantMap old = previousFiles.take(rel);
        QByteArray hash;
        if (!old.isEmpty() && old.value(QStringLiteral("bytes")).toLongLong() == info.size()
            && old.value(QStringLiteral("modifiedMs")).toLongLong() == modifiedMs
            && !old.value(QStringLiteral("sha256")).toString().isEmpty()) {
            hash = old.value(QStringLiteral("sha256")).toString().toLatin1();
            ++reused;
        } else {
            hash = contentHash(info.absoluteFilePath());
            old.isEmpty() ? ++added : ++updated;
        }
        files.append(QVariantMap{{QStringLiteral("path"), rel},
            {QStringLiteral("bytes"), info.size()},
            {QStringLiteral("modifiedMs"), modifiedMs},
            {QStringLiteral("sha256"), QString::fromLatin1(hash)}});
    }
    const int removed = previousFiles.size();
    QVariantMap brain{{QStringLiteral("schemaVersion"), 2},
        {QStringLiteral("root"), base.absolutePath()},
        {QStringLiteral("refreshedAt"), QDateTime::currentDateTimeUtc().toString(Qt::ISODate)},
        {QStringLiteral("fileCount"), files.size()}, {QStringLiteral("bytes"), bytes},
        {QStringLiteral("extensions"), extensions}, {QStringLiteral("files"), files},
        {QStringLiteral("changes"), QVariantMap{{QStringLiteral("added"), added},
            {QStringLiteral("updated"), updated}, {QStringLiteral("removed"), removed},
            {QStringLiteral("reused"), reused}}},
        {QStringLiteral("truncated"), files.size() >= effectiveMax}};
    QSaveFile file(cachePath(root));
    if (file.open(QIODevice::WriteOnly)) {
        file.write(QJsonDocument(QJsonObject::fromVariantMap(brain)).toJson(QJsonDocument::Compact));
        file.commit();
    }
    return brain;
}
