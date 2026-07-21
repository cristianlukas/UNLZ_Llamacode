#pragma once

#include <QVariantList>
#include <QVariantMap>

class AutomationArtifactStore
{
public:
    static constexpr int FormatVersion = 2;
    static QString rootDir();
    static QString artifactDir(const QString &id);
    static QString create(const QVariantMap &task, const QVariantMap &scope,
                          const QVariantList &events, const QStringList &evidence,
                          const QString &browserScript = QString());
    static QVariantMap manifest(const QString &id);
    static QVariantMap recipe(const QString &id);
    static QVariantList timeline(const QString &id);
    static QVariantList templates(const QString &id);
    static bool removeTemplate(const QString &id, const QString &fileName);
    static bool replaceTemplate(const QString &id, const QString &fileName,
                                const QString &sourcePath);
    static bool addTemplateVariant(const QString &id, const QString &fileName,
                                   const QString &sourcePath);
    static QString importBrowserSkill(const QString &skillName, const QVariantMap &task);
    static bool appendLearning(const QString &id, const QString &summary, const QString &log);
    static bool removeEvidence(const QString &id, const QString &fileName);
    static QString redact(const QString &text);
};
