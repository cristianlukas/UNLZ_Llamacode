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
    // Traza continua (Paint, sliders, gestos): apretar el botón en el primer punto,
    // arrastrar por la secuencia y soltar en el último. `points` = lista de {x,y}
    // NORMALIZADOS 0..1 dentro del alcance (mínimo 2). Interpola segmentos para que
    // la línea salga continua aunque los puntos vengan espaciados. `holdMs` = pausa
    // por segmento (default ~8ms). Sólo Windows.
    static bool stroke(const QString &kind, const QString &targetId,
                       const QVariantList &points, const QString &button = QStringLiteral("left"),
                       int holdMs = 8, QString *error = nullptr, QVariantMap *trace = nullptr);
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

    // Control UIA bajo un punto absoluto de pantalla. Lo usa el grabador Teach para
    // anclar cada click/stroke a un control semántico (name/role/controlId + la
    // ventana dueña) en vez de sólo coordenadas → replay robusto ante reflow de UI.
    // Devuelve {} si no hay elemento o UIA no está. Sólo Windows.
    static QVariantMap controlAtPoint(const QPoint &absolute);

    // Espera (poll) hasta que exista una condición o venza el timeout. Sincroniza
    // el replay sin sleeps fijos. Un caso por parámetros:
    //  - windowTitle no vacío → espera una ventana cuyo título contenga el texto.
    //  - windowTargetId + (query|role) → espera un control (name contiene query,
    //    role coincide) dentro de esa ventana.
    // Devuelve {found:bool, elapsedMs, ...datos del match}. Sólo Windows.
    static QVariantMap waitFor(const QString &windowTargetId, const QString &windowTitle,
                               const QString &query, const QString &role, int timeoutMs,
                               QString *error = nullptr);

    // Aserción verificable para el replay/RPA: comprueba una condición y devuelve
    // {pass:bool, detail}. Casos (poll hasta timeout):
    //  - expectText no vacío → pasa si algún control (de la ventana target, o de
    //    cualquier ventana si no se da target) tiene ese texto en su nombre.
    //  - si no, delega en waitFor (existencia de ventana por título / control por
    //    query/role). Es el primitivo que hace el objetivo comprobable, no opinable.
    static QVariantMap assertCondition(const QString &windowTargetId, const QString &windowTitle,
                                       const QString &query, const QString &role,
                                       const QString &expectText, int timeoutMs,
                                       QString *error = nullptr);
};
