#pragma once

#include <QString>
#include <QVariantMap>

class AutomationRunner
{
public:
    static bool isSensitiveAction(const QString &intent);
    static QString validateTask(const QVariantMap &task, bool hasVision);
    static QVariantMap limits(const QVariantMap &task);
    static QString augmentPrompt(const QVariantMap &task, const QVariantMap &manifest,
                                 const QVariantMap &recipe);
};
