#include "AutomationRunner.h"

#include <QRegularExpression>

namespace {

bool parseArithmetic(const QString &text, double *expected)
{
    static const QRegularExpression exprRe(
        QStringLiteral("(-?\\d+(?:[\\.,]\\d+)?)\\s*([+\\-*/x×÷])\\s*(-?\\d+(?:[\\.,]\\d+)?)"));
    const QRegularExpressionMatch match = exprRe.match(text.toLower());
    if (!match.hasMatch()) return false;
    auto number = [](QString value, bool *ok) {
        return value.replace(QLatin1Char(','), QLatin1Char('.')).toDouble(ok);
    };
    bool aOk = false, bOk = false;
    const double a = number(match.captured(1), &aOk);
    const double b = number(match.captured(3), &bOk);
    if (!aOk || !bOk) return false;
    const QString op = match.captured(2);
    if (op == QLatin1String("+")) *expected = a + b;
    else if (op == QLatin1String("-")) *expected = a - b;
    else if (op == QLatin1String("*") || op == QLatin1String("x") || op == QLatin1String("×"))
        *expected = a * b;
    else if (op == QLatin1String("/") || op == QLatin1String("÷")) {
        if (qFuzzyIsNull(b)) return false;
        *expected = a / b;
    } else return false;
    return true;
}

QString lastCalculatorDisplay(const QString &text)
{
    static const QRegularExpression displayRe(
        QStringLiteral("Se muestra\\s+(-?\\d+(?:[\\.,]\\d+)?)"),
        QRegularExpression::CaseInsensitiveOption);
    QRegularExpressionMatchIterator it = displayRe.globalMatch(text);
    QString value;
    while (it.hasNext()) value = it.next().captured(1);
    return value;
}

} // namespace

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

bool AutomationRunner::recipeHasWebStep(const QVariantList &steps)
{
    for (const QVariant &s : steps) {
        const QString k = s.toMap().value(QStringLiteral("kind")).toString();
        if (k == QLatin1String("browser") || k == QLatin1String("web"))
            return true;
    }
    return false;
}

QString AutomationRunner::validateTask(const QVariantMap &task, bool hasVision)
{
    Q_UNUSED(hasVision)
    const QString mode = task.value(QStringLiteral("executionMode"), QStringLiteral("auto")).toString();
    if (mode == QLatin1String("desktop")
        && task.value(QStringLiteral("teachArtifactId")).toString().isEmpty())
        return QStringLiteral("La automatización de escritorio todavía no fue enseñada.");
    return {};
}

bool AutomationRunner::arithmeticResultMismatch(const QVariantMap &task, const QString &workLog,
                                                QString *message)
{
    if (message)
        message->clear();

    const QString taskText = (task.value(QStringLiteral("name")).toString()
                              + QLatin1Char('\n')
                              + task.value(QStringLiteral("description")).toString()).toLower();
    if (!taskText.contains(QStringLiteral("calculadora")))
        return false;

    double expected = 0.0;
    if (!parseArithmetic(taskText, &expected))
        return false;
    const QString lastDisplay = lastCalculatorDisplay(workLog);
    if (lastDisplay.isEmpty()) {
        if (message) {
            *message = QStringLiteral("No se pudo verificar la Calculadora: falta el visor "
                                      "actual ('Se muestra X') en desktop_controls. "
                                      "No se acepta Historial/Memoria como resultado final.");
        }
        return true;
    }

    const QString normalized = QString(lastDisplay).replace(QLatin1Char(','), QLatin1Char('.'));
    bool ok = false;
    const double actual = normalized.toDouble(&ok);
    if (!ok || qAbs(actual - expected) < 0.001)
        return false;

    if (message) {
        *message = QStringLiteral("La verificación de Calculadora contradice el objetivo: "
                                  "el visor actual dice %1, pero se esperaba %2. "
                                  "No se acepta historial viejo como éxito.")
                       .arg(lastDisplay, QString::number(expected, 'g', 12));
    }
    return true;
}

bool AutomationRunner::verifiedArithmeticResult(const QString &typedExpression,
                                                const QString &controlsOutput,
                                                QString *summary)
{
    if (summary) summary->clear();
    double expected = 0.0;
    if (!parseArithmetic(typedExpression, &expected)) return false;
    const QString display = lastCalculatorDisplay(controlsOutput);
    if (display.isEmpty()) return false;
    bool ok = false;
    const double actual = QString(display).replace(QLatin1Char(','), QLatin1Char('.')).toDouble(&ok);
    if (!ok || qAbs(actual - expected) >= 0.001) return false;
    if (summary) {
        *summary = QStringLiteral("Automatización completada: Calculadora verificó %1 = %2 en el visor actual.")
                       .arg(typedExpression.trimmed().remove(QLatin1Char('=')), display);
    }
    return true;
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
        "Ejecutá una acción por vez y verificá el progreso por el medio más barato "
        "disponible (texto/estructura antes que captura). Detenete si no podés "
        "verificar el objetivo.\n")
        .arg(mode);
    if (mode == QLatin1String("desktop")) {
        out += QStringLiteral(
            "Superficie: escritorio foreground nativo. Usá las tools desktop_* para operar y "
            "verificar la pantalla real.\n"
            "CAMINO RÁPIDO (seguilo, evita el loop de observar):\n"
            "1) desktop_launch <app> (ej. calc); no uses run_shell para apps GUI.\n"
            "2) desktop_wait ~800 ms y UNA sola desktop_windows. NO repitas desktop_windows; "
            "si aparece la ventana, enfocá y actuá.\n"
            "3) TECLADO primero: desktop_focus <id>, desktop_type texto, desktop_key ENTER/=.\n"
            "Para cálculos cortos: primero limpiá con desktop_key ESC, después detectá la "
            "expresión del objetivo y escribila completa con '=' en una sola llamada "
            "(desktop_type \"<expresión>=\"); no la partas ni presiones ENTER después.\n"
            "4) Si no hay teclado: desktop_controls <id> y desktop_click_element por nombre/controlId.\n"
            "5) Verificá con desktop_controls usando el visor ACTUAL ('Se muestra X'); "
            "no aceptes Historial/Memoria como resultado final.\n"
            "Cada tool de click devuelve trace con pointer/target; usalo para validar "
            "qué se accionó. Preferí target semántico (controlId/selector) y dejá "
            "coordenadas sólo como respaldo o diagnóstico.\n"
            "ANTI-LOOP: una acción -> una verificación por texto -> terminá. Los pasos "
            "[type]/[key]/[click] son intención; traducilos a desktop_* sobre la app. "
            "No leas evidence/*.jpg con read_file.\n");
    } else if (mode == QLatin1String("browserBackground")) {
        out += QStringLiteral(
            "Superficie: navegador background al ejecutar. El Teach se grabó con un "
            "browser foreground de Playwright y evidencia visual por acción para entender "
            "la intención del usuario. Usá las tools de browser/Playwright para navegar y "
            "verificar páginas web; adaptá selectores, textos y posiciones si la interfaz "
            "cambió. Tratá selector/control como target primario; coordenadas de mouse "
            "son respaldo cuando no haya selector confiable. Registrá y validá cada click "
            "contra la salida/trace de la tool o el snapshot posterior.\n");
    }
    out += QStringLiteral("Artefacto: %1\n").arg(manifest.value(QStringLiteral("id")).toString());
    const QVariantList steps = recipe.value(QStringLiteral("steps")).toList();
    for (const QVariant &value : steps) {
        const QVariantMap step = value.toMap();
        out += QStringLiteral("- [%1] %2")
                   .arg(step.value(QStringLiteral("kind")).toString(),
                        step.value(QStringLiteral("intent")).toString().left(180));
        if (step.contains(QStringLiteral("x")))
            out += QStringLiteral(" (referencia normalizada %1,%2)")
                       .arg(step.value(QStringLiteral("x")).toDouble(), 0, 'f', 3)
                       .arg(step.value(QStringLiteral("y")).toDouble(), 0, 'f', 3);
        const QString button = step.value(QStringLiteral("button")).toString();
        if (!button.isEmpty())
            out += QStringLiteral(" (botón %1)").arg(button);
        const QVariantMap target = step.value(QStringLiteral("target")).toMap();
        const QString role = target.value(QStringLiteral("role")).toString();
        const QString name = target.value(QStringLiteral("name")).toString();
        if (!role.isEmpty() || !name.isEmpty())
            out += QStringLiteral(" (target %1 \"%2\")").arg(role, name.left(80));
        out += QLatin1Char('\n');
    }
    const QVariantList learnings = recipe.value(QStringLiteral("learnings")).toList();
    // Dedup en el prompt: artefactos viejos ya acumularon varios learnings de
    // éxito casi idénticos (antes del dedup en appendLearning). Colapsarlos acá
    // por firma normalizada evita reinyectar el mismo texto N veces. Recorremos
    // de lo más RECIENTE a lo más viejo (adaptaciones nuevas primero) y cortamos
    // en 4 distintos: prompt más chico → primer turno más rápido.
    auto signature = [](const QString &s) {
        QString t;
        for (const QChar &c : s) {
            if (c.isLetter()) t += c.toLower();
            else if (c.isSpace() && !t.endsWith(QLatin1Char(' '))) t += QLatin1Char(' ');
        }
        return t.trimmed().left(160);
    };
    QStringList seenSig, picked;
    for (int i = learnings.size() - 1; i >= 0 && picked.size() < 2; --i) {
        const QString summary = learnings.at(i).toMap()
                                    .value(QStringLiteral("summary")).toString().trimmed();
        if (summary.isEmpty()) continue;
        const QString sig = signature(summary);
        if (seenSig.contains(sig)) continue;
        seenSig << sig;
        picked << summary.left(260);
    }
    if (!picked.isEmpty()) {
        out += QStringLiteral("Aprendizajes auto-actualizados de corridas previas:\n");
        for (const QString &p : picked)
            out += QStringLiteral("- %1\n").arg(p);
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
