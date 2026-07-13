#pragma once

#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>

class AutomationRunner
{
public:
    static bool isSensitiveAction(const QString &intent);

    // ¿La receta grabó algún paso web (browser)? Una automatización de puro
    // escritorio (teclado/UIA) no lo hace → no necesita el MCP de navegador ni,
    // en general, ningún MCP: sólo las tools nativas desktop_*. Sirve para no
    // inflar el prompt con esquemas de tools inútiles en perfiles de n_ctx chico.
    static bool recipeHasWebStep(const QVariantList &steps);
    static QString validateTask(const QVariantMap &task, bool hasVision);
    static bool arithmeticResultMismatch(const QVariantMap &task, const QString &workLog,
                                         QString *message = nullptr);
    // Prefijo Teach de teclado que puede reproducirse mientras el agente hace su
    // primer prefill. Es genérico (WIN/type/ENTER, etc.) y corta sólo ante mouse o
    // pasos no representables; no reinterpreta el contenido elegido por el
    // usuario. Cada fila mantiene key/text/atMs.
    static QVariantList safeDesktopWarmStart(const QVariantMap &task,
                                             const QVariantMap &recipe);
    static QVariantMap limits(const QVariantMap &task);
    static QString augmentPrompt(const QVariantMap &task, const QVariantMap &manifest,
                                 const QVariantMap &recipe);

    // Resuelve el "Tipo de proceso" a una superficie concreta. Acepta el modo
    // "auto" (y los legacy "agent"/"prompt"/vacío) y decide de forma determinista
    // mirando los pasos: si hay algún paso de escritorio → "desktop"; si no →
    // "browserBackground" (la mayoría de las automatizaciones son web). Los modos
    // concretos ("desktop"/"browserBackground") se devuelven tal cual.
    static QString resolveExecutionMode(const QVariantMap &task);

    // Devuelve el comando del MCP de navegador forzado a headless para que las
    // automatizaciones "Navegador background" no roben el foco con una ventana.
    // Respeta un --headed/--headless explícito del usuario y sólo toca el MCP de
    // Playwright (la superficie que controlamos).
    static QString headlessBrowserCommand(const QString &command);
    static QString foregroundBrowserCommand(const QString &command);

    // Tools mínimas esperadas para escritorio foreground. Automatizaciones no las
    // usan para recortar el catálogo: el agente corre con todas las built-in.
    static QStringList desktopToolNames();

    // ── Data-driven (RPA por lote): el mismo flujo, datos distintos ──────────────
    // Sustituye {{clave}} (con o sin espacios) por el valor de esa clave en la fila.
    // Claves no presentes se dejan intactas. Case-insensitive en la clave.
    static QString expandVariables(const QString &text, const QVariantMap &row);
    // Parsea un dataset a filas (cada fila = mapa columna→valor). `format`:
    // "json" (array de objetos), "csv" (primera fila = encabezados), o vacío para
    // autodetectar (empieza con '['/'{' → json; si no → csv). Pura (no toca disco).
    static QVariantList parseDataset(const QString &raw, const QString &format = QString());
    // Resuelve las filas del dataset de una Task: prioridad datasetRows (lista ya
    // parseada) > datasetInline+datasetFormat (texto) > datasetPath (archivo).
    // Devuelve {} si la Task no tiene dataset. Acota a 1000 filas.
    static QVariantList datasetRows(const QVariantMap &task);

    // ── Triggers (arranque desatendido) ─────────────────────────────────────────
    // Filas {id, path, debounceMs} de las Tasks con triggerType=="fileWatch" y un
    // triggerPath no vacío. Alimenta el QFileSystemWatcher: al cambiar ese archivo
    // o carpeta se dispara la Task. Pura (no toca disco). Debounce acotado 0..60000.
    static QVariantList fileWatchTriggers(const QVariantList &tasks);
};
