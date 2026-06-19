#pragma once

#include <QImage>
#include <QPointF>
#include <QRect>
#include <QString>
#include <QVariantList>
#include <QVariantMap>

class DesktopAutomationBackend
{
public:
    static QVariantList screens();
    static QVariantList windows();
    static QVariantMap targetInfo(const QString &kind, const QString &targetId);
    static QImage capture(const QString &kind, const QString &targetId, QString *error = nullptr);
    static QString saveCapture(const QString &kind, const QString &targetId,
                               const QString &path, QString *error = nullptr);

    static QPointF normalizePoint(const QPoint &absolute, const QRect &bounds);
    static QPoint denormalizePoint(const QPointF &normalized, const QRect &bounds);

    static bool interactiveSessionAvailable();
    static bool focusWindow(const QString &targetId, QString *error = nullptr);
    static bool click(const QString &kind, const QString &targetId, double x, double y,
                      QString *error = nullptr);
    static bool typeText(const QString &text, QString *error = nullptr);
    static bool pressKey(const QString &key, const QStringList &modifiers = {},
                         QString *error = nullptr);
    static bool scroll(int delta, QString *error = nullptr);
    static QVariantMap cursorState();
};
