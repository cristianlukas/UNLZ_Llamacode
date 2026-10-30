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
    // Clic con N pulsaciones y modificadores sostenidos, y rueda horizontal.
    static bool clickEx(const QString &kind, const QString &targetId, double x, double y,
                        const QString &button, int clickCount, const QStringList &modifiers,
                        QString *error, QVariantMap *trace);
    static bool scrollHorizontal(int delta, QString *error = nullptr);

    // ── Puras (compiladas en todas las plataformas; testeables en Windows) ──
    // Argumentos de UNA invocación de xdotool: mover, apretar modificadores,
    // clickear N veces y soltarlos. Encadenar todo en un solo proceso evita que
    // un modificador quede apretado si falla un paso intermedio. "" en error si
    // algún modificador no se reconoce.
    static QStringList buildClickArgs(const QPoint &p, const QString &button, int clickCount,
                                      const QStringList &modifiers, QString *error = nullptr);
    // X11: botones 4/5 = rueda vertical, 6/7 = horizontal (izq/der). delta como
    // Windows: múltiplos de 120; vertical positivo = arriba, horizontal positivo
    // = derecha.
    static QStringList buildScrollArgs(int delta, bool horizontal);
    static QPoint cursorPos();
    static bool moveCursor(const QPoint &physical);

    // budgetMs < 0 = sin límite. Cada nodo AT-SPI cuesta varios subprocesos:
    // con apps grandes abiertas (Chrome) un recorrido completo lleva minutos, y
    // desktop_assert / desktop_wait_for tienen que respetar su timeout.
    static QVariantList controls(const QString &windowTargetId, const QString &query,
                                 int max, QString *error = nullptr, int budgetMs = -1);
    // Un solo recorrido sobre todo el escritorio (antes desktop_assert sin
    // ventana repetía el árbol completo una vez por cada ventana).
    static QVariantList controlsOnDesktop(const QString &query, int max, int budgetMs);
    static bool clickElement(const QString &windowTargetId, const QString &controlId,
                             bool allowFuzzy, QString *error, QVariantMap *trace);
    static bool controlAction(const QString &windowTargetId, const QString &controlId,
                              const QString &action, const QString &value,
                              QString *error, QVariantMap *trace);
    static QVariantMap controlAtPoint(const QPoint &absolute);
};
