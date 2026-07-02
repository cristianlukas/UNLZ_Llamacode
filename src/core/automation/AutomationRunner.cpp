#include "AutomationRunner.h"

bool AutomationRunner::isSensitiveAction(const QString &intent)
{
    const QString s = intent.toLower();
    static const QStringList markers{
        QStringLiteral("comprar"), QStringLiteral("pagar"), QStringLiteral("transfer"),
        QStringLiteral("enviar"), QStringLiteral("publicar"), QStringLiteral("borrar"),
        QStringLiteral("eliminar"), QStringLiteral("confirmar"), QStringLiteral("delete"),
        QStringLiteral("purchase"), QStringLiteral("payment"), QStringLiteral("send")};
    for (const QString &marker : markers)
        if (s.contains(marker)) return true;
    return false;
}

QString AutomationRunner::validateTask(const QVariantMap &task, bool hasVision)
{
    const QString mode = task.value(QStringLiteral("executionMode"), QStringLiteral("auto")).toString();
    if (mode == QLatin1String("desktop") && !hasVision)
        return QStringLiteral("Esta automatización de escritorio requiere un perfil con visión (--mmproj).");
    if (mode == QLatin1String("desktop")
        && task.value(QStringLiteral("teachArtifactId")).toString().isEmpty())
        return QStringLiteral("La automatización de escritorio todavía no fue enseñada.");
    return {};
}

QVariantMap AutomationRunner::limits(const QVariantMap &task)
{
    return {
        {QStringLiteral("timeoutSec"), qBound(30, task.value(QStringLiteral("timeoutSec"), 300).toInt(), 3600)},
        {QStringLiteral("maxActions"), qBound(1, task.value(QStringLiteral("maxActions"), 50).toInt(), 500)},
        {QStringLiteral("maxRetries"), qBound(0, task.value(QStringLiteral("maxRetries"), 2).toInt(), 10)}};
}

QString AutomationRunner::resolveExecutionMode(const QVariantMap &task)
{
    const QString mode = task.value(QStringLiteral("executionMode"), QStringLiteral("auto")).toString();
    if (mode == QLatin1String("desktop") || mode == QLatin1String("browserBackground"))
        return mode;
    // "auto" (o legacy "agent"/"prompt"/vacío): el sistema elige la superficie.
    // Señal fuerte y determinista: el tipo de los pasos. Cualquier paso de
    // escritorio implica controlar la pantalla real → "desktop". Si no, la tarea
    // es web → "browserBackground".
    const QVariantList steps = task.value(QStringLiteral("steps")).toList();
    for (const QVariant &value : steps)
        if (value.toMap().value(QStringLiteral("kind")).toString() == QLatin1String("desktop"))
            return QStringLiteral("desktop");
    return QStringLiteral("browserBackground");
}

QString AutomationRunner::headlessBrowserCommand(const QString &command)
{
    const QString c = command.trimmed();
    if (c.isEmpty()) return c;
    // Respeta una elección explícita del usuario.
    if (c.contains(QLatin1String("--headless")) || c.contains(QLatin1String("--headed")))
        return c;
    // Sólo el MCP de Playwright: no tocamos comandos MCP de terceros.
    if (!c.contains(QLatin1String("@playwright/mcp")) && !c.contains(QLatin1String("playwright-mcp")))
        return c;
    return c + QStringLiteral(" --headless");
}

QString AutomationRunner::foregroundBrowserCommand(const QString &command)
{
    QString c = command.trimmed();
    if (c.isEmpty()) return c;
    if (!c.contains(QLatin1String("@playwright/mcp")) && !c.contains(QLatin1String("playwright-mcp")))
        return c;
    c.replace(QStringLiteral(" --headless"), QString());
    c.replace(QStringLiteral("--headless "), QString());
    c.replace(QStringLiteral("--headless"), QString());
    while (c.contains(QStringLiteral("  "))) c.replace(QStringLiteral("  "), QStringLiteral(" "));
    c = c.trimmed();
    if (!c.contains(QLatin1String("--headed")))
        c += QStringLiteral(" --headed");
    return c;
}

QStringList AutomationRunner::desktopToolNames()
{
    return {
        QStringLiteral("desktop_windows"),
        QStringLiteral("desktop_controls"),
        QStringLiteral("desktop_click_element"),
        QStringLiteral("desktop_observe"),
        QStringLiteral("desktop_click"),
        QStringLiteral("desktop_type"),
        QStringLiteral("desktop_key"),
        QStringLiteral("desktop_scroll"),
        QStringLiteral("desktop_focus"),
        QStringLiteral("desktop_wait"),
        QStringLiteral("desktop_launch")};
}

QString AutomationRunner::augmentPrompt(const QVariantMap &task, const QVariantMap &manifest,
                                        const QVariantMap &recipe)
{
    // El bloque de receta sólo tiene sentido con una superficie concreta; los
    // callers ya gatean por teachArtifactId, así que el modo siempre resuelve a
    // "desktop"/"browserBackground".
    const QString mode = resolveExecutionMode(task);
    QString out = QStringLiteral(
        "\n\nMODO DE AUTOMATIZACIÓN: %1.\n"
        "Usá la receta enseñada como evidencia semántica, no como replay rígido. "
        "Observá antes de cada acción, ejecutá una sola acción, volvé a observar y "
        "verificá progreso. Detenete si no podés verificar el objetivo.\n")
        .arg(mode);
    if (mode == QLatin1String("desktop")) {
        out += QStringLiteral(
            "Superficie: escritorio foreground nativo. Usá las tools desktop_* "
            "(desktop_windows, desktop_observe, desktop_key, desktop_type, desktop_click, "
            "desktop_click_element, desktop_launch, desktop_wait) para operar y verificar "
            "la pantalla real. Playwright está disponible en foreground/headed para flujos web "
            "dentro de la misma automatización, pero no reemplaza desktop_* para aplicaciones "
            "nativas de Windows. "
            "Podés usar cualquier otra tool disponible cuando aporte contexto o diagnóstico, "
            "pero verificá la GUI con desktop_observe/desktop_windows. Las capturas "
            "evidence/*.jpg son evidencia histórica de Teach; no las leas con read_file.\n");
    } else if (mode == QLatin1String("browserBackground")) {
        out += QStringLiteral(
            "Superficie: navegador background al ejecutar. El Teach se grabó con un "
            "browser foreground de Playwright y evidencia visual por acción para entender "
            "la intención del usuario. Usá las tools de browser/Playwright para navegar y "
            "verificar páginas web; adaptá selectores, textos y posiciones si la interfaz "
            "cambió.\n");
    }
    out += QStringLiteral("Artefacto: %1\n").arg(manifest.value(QStringLiteral("id")).toString());
    const QVariantList steps = recipe.value(QStringLiteral("steps")).toList();
    for (const QVariant &value : steps) {
        const QVariantMap step = value.toMap();
        out += QStringLiteral("- [%1] %2")
                   .arg(step.value(QStringLiteral("kind")).toString(),
                        step.value(QStringLiteral("intent")).toString());
        if (step.contains(QStringLiteral("x")))
            out += QStringLiteral(" (referencia normalizada %1,%2)")
                       .arg(step.value(QStringLiteral("x")).toDouble(), 0, 'f', 3)
                       .arg(step.value(QStringLiteral("y")).toDouble(), 0, 'f', 3);
        if (step.contains(QStringLiteral("evidence")))
            out += QStringLiteral(" (captura: evidence/%1)")
                       .arg(step.value(QStringLiteral("evidence")).toString());
        out += QLatin1Char('\n');
    }
    const QVariantList learnings = recipe.value(QStringLiteral("learnings")).toList();
    if (!learnings.isEmpty()) {
        out += QStringLiteral("Aprendizajes auto-actualizados de corridas previas:\n");
        int n = 0;
        for (const QVariant &value : learnings) {
            const QVariantMap item = value.toMap();
            const QString summary = item.value(QStringLiteral("summary")).toString().trimmed();
            if (summary.isEmpty()) continue;
            out += QStringLiteral("- %1\n").arg(summary.left(700));
            if (++n >= 6) break;
        }
        out += QStringLiteral("Si durante esta corrida la interfaz cambió y lográs completar el objetivo, "
                              "explicá en la respuesta final qué adaptación funcionó para que el Teach "
                              "pueda actualizarse.\n");
    } else {
        out += QStringLiteral("Si la interfaz cambió y aun así lográs completar el objetivo, "
                              "documentá en la respuesta final qué adaptación funcionó para auto-actualizar el Teach.\n");
    }
    const QVariantMap l = limits(task);
    out += QStringLiteral("Límites: %1 acciones, %2 segundos, %3 reintentos.\n")
               .arg(l.value(QStringLiteral("maxActions")).toInt())
               .arg(l.value(QStringLiteral("timeoutSec")).toInt())
               .arg(l.value(QStringLiteral("maxRetries")).toInt());
    return out;
}
