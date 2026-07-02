#pragma once

#include <QString>
#include <QStringList>
#include <QVariantMap>

class AutomationRunner
{
public:
    static bool isSensitiveAction(const QString &intent);
    static QString validateTask(const QVariantMap &task, bool hasVision);
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
