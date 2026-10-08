#pragma once

#include <QPoint>
#include <QRect>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>

// X11/AT-SPI implementation of the desktop surface.  It is deliberately kept
// behind this small adapter so the existing Win32 UI Automation path remains
// unchanged and the public DesktopAutomationBackend contract stays portable.
class LinuxDesktopBackend final
{
public:
    static QVariantList windows();
    static QRect targetBounds(const QString &kind, const QString &targetId);
    static bool interactiveSessionAvailable();
    static bool launchApp(const QString &app, const QString &args, QString *error = nullptr);
    static bool focusWindow(const QString &targetId, QString *error = nullptr);
    static bool setWindowMaximized(const QString &targetId, bool maximized,
                                   QString *error = nullptr);
    static bool setWindowSize(const QString &targetId, int width, int height,
                              QString *error = nullptr);
    static bool click(const QString &kind, const QString &targetId, double x, double y,
                      const QString &button, QString *error, QVariantMap *trace);
    static bool stroke(const QString &kind, const QString &targetId,
                       const QVariantList &points, const QString &button, int holdMs,
                       QString *error, QVariantMap *trace);
    static bool typeText(const QString &text, QString *error = nullptr);
    static bool pressKey(const QString &key, const QStringList &modifiers = {},
                         QString *error = nullptr);
    static bool scroll(int delta, QString *error = nullptr);
    static QPoint cursorPos();
    static bool moveCursor(const QPoint &physical);

    static QVariantList controls(const QString &windowTargetId, const QString &query,
                                 int max, QString *error = nullptr);
    static bool clickElement(const QString &windowTargetId, const QString &controlId,
                             bool allowFuzzy, QString *error, QVariantMap *trace);
    static bool controlAction(const QString &windowTargetId, const QString &controlId,
                              const QString &action, const QString &value,
                              QString *error, QVariantMap *trace);
    static QVariantMap controlAtPoint(const QPoint &absolute);
};
