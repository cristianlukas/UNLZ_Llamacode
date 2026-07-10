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
    // Detecta una operación aritmética escrita en Calculadora y confirma que el
    // visor UIA actual coincide. Se usa para cerrar Tasks simples apenas
    // desktop_controls aporta evidencia suficiente, sin otra inferencia LLM.
    static bool verifiedArithmeticResult(const QString &typedExpression,
                                         const QString &controlsOutput,
                                         QString *summary = nullptr);
    // App nativa inequívoca que puede abrirse en paralelo al primer prefill del
    // agente. Vacío cuando el objetivo no es suficientemente específico.
    static QString safeDesktopPrelaunchApp(const QVariantMap &task);
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
};
