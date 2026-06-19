#pragma once

#include <QVariantList>
#include <QVariantMap>

class AutomationArtifactStore
{
public:
    static constexpr int FormatVersion = 1;
    static QString rootDir();
    static QString artifactDir(const QString &id);
    static QString create(const QVariantMap &task, const QVariantMap &scope,
                          const QVariantList &events, const QStringList &evidence,
                          const QString &browserScript = QString());
    static QVariantMap manifest(const QString &id);
    static QVariantMap recipe(const QString &id);
    static QVariantList timeline(const QString &id);
    static QString importBrowserSkill(const QString &skillName, const QVariantMap &task);
    static bool removeEvidence(const QString &id, const QString &fileName);
    static QString redact(const QString &text);
};
