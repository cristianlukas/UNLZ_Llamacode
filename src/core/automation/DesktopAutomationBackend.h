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
    // Lanza una app DESPRENDIDA (no bloquea, no hereda pipes): a diferencia de
    // run_shell, lanzar una app GUI (calc, notepad, ms-settings:, una ruta .exe)
    // acá vuelve al instante y no cuelga el turno esperando que el proceso termine.
    // `app` = programa/comando/verbo del shell; `args` = argumentos extra (opcional).
    static bool launchApp(const QString &app, const QString &args, QString *error = nullptr);
    static bool focusWindow(const QString &targetId, QString *error = nullptr);
    static bool click(const QString &kind, const QString &targetId, double x, double y,
                      const QString &button = QStringLiteral("left"),
                      QString *error = nullptr, QVariantMap *trace = nullptr);
    static bool typeText(const QString &text, QString *error = nullptr);
    static bool pressKey(const QString &key, const QStringList &modifiers = {},
                         QString *error = nullptr);
    static bool scroll(int delta, QString *error = nullptr);
    static QVariantMap cursorState();

    // ── UI Automation: el escritorio como árbol de controles (DOM-aware) ──
    // Enumera los controles (control-view) descendientes de una ventana: nombre,
    // rol, geometría, habilitado e invocable. `windowTargetId` = id hex de la
    // ventana (ver windows()). `query` filtra por substring del nombre (vacío =
    // todos). `max` acota la cantidad. Devuelve filas {controlId,name,role,x,y,
    // width,height,enabled,invokable}. controlId = RuntimeId serializado, estable
    // dentro de la vida de la ventana → usalo con clickElement. Sólo Windows.
    static QVariantList controls(const QString &windowTargetId, const QString &query,
                                 int max, QString *error = nullptr);
    // Click sobre un control por su controlId (de controls()): si expone el patrón
    // Invoke lo invoca (más robusto que pixel); si no, clickea el centro de su
    // bounding rect. Sólo Windows.
    static bool clickElement(const QString &windowTargetId, const QString &controlId,
                             QString *error = nullptr, QVariantMap *trace = nullptr);
};
