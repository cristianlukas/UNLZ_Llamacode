#include <QtTest>
#include "core/automation/AutomationArtifactStore.h"
#include "core/automation/AutomationRunner.h"
#include "core/automation/DesktopAutomationBackend.h"
#include "core/automation/TeachKeyBuffer.h"

class AutomationTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void normalizedCoordinatesScaleAcrossResolutions();
    void sensitiveActionClassification();
    void desktopRequiresVisionAndTraining();
    void limitsAreClamped();
    void autoModeRoutesBySurface();
    void desktopPromptPrefersNativeTools();
    void desktopToolPolicyKeepsGuiToolsAvailable();
    void browserPromptUsesForegroundTeachEvidence();
    void headlessBrowserCommandForcesHeadless();
    void artifactsRoundTripAndRedactSecrets();
    void artifactLearningsAppendAndPrompt();
    void keyBufferAccumulatesTextIntoTypeStep();
    void keyBufferFlushesTextBeforeNamedKey();
    void keyBufferEmitsShortcutWithModifiers();
    void winTapDistinguishesLoneTapFromShortcut();
};

void AutomationTests::initTestCase()
{
    QStandardPaths::setTestModeEnabled(true);
}

void AutomationTests::normalizedCoordinatesScaleAcrossResolutions()
{
    const QPointF normalized = DesktopAutomationBackend::normalizePoint(
        QPoint(960, 540), QRect(0, 0, 1920, 1080));
    QVERIFY(qAbs(normalized.x() - 0.5) < 0.001);
    QVERIFY(qAbs(normalized.y() - 0.5) < 0.001);
    QCOMPARE(DesktopAutomationBackend::denormalizePoint(
                 normalized, QRect(100, 50, 3840, 2160)),
             QPoint(2020, 1130));
}

void AutomationTests::sensitiveActionClassification()
{
    QVERIFY(AutomationRunner::isSensitiveAction(QStringLiteral("Confirmar pago")));
    QVERIFY(AutomationRunner::isSensitiveAction(QStringLiteral("Enviar formulario")));
    QVERIFY(!AutomationRunner::isSensitiveAction(QStringLiteral("Abrir la calculadora")));
}

void AutomationTests::desktopRequiresVisionAndTraining()
{
    QVariantMap task{{"executionMode", "desktop"}};
    QVERIFY(AutomationRunner::validateTask(task, false).contains(QStringLiteral("visión")));
    QVERIFY(AutomationRunner::validateTask(task, true).contains(QStringLiteral("enseñada")));
    task["teachArtifactId"] = QStringLiteral("demo");
    QVERIFY(AutomationRunner::validateTask(task, true).isEmpty());
}

void AutomationTests::limitsAreClamped()
{
    const QVariantMap limits = AutomationRunner::limits(
        QVariantMap{{"timeoutSec", 1}, {"maxActions", 9999}, {"maxRetries", -4}});
    QCOMPARE(limits.value("timeoutSec").toInt(), 30);
    QCOMPARE(limits.value("maxActions").toInt(), 500);
    QCOMPARE(limits.value("maxRetries").toInt(), 0);
}

void AutomationTests::autoModeRoutesBySurface()
{
    using R = AutomationRunner;
    // "auto" sin pasos de escritorio → web (browserBackground).
    QCOMPARE(R::resolveExecutionMode(QVariantMap{{"executionMode", "auto"}}),
             QStringLiteral("browserBackground"));
    QCOMPARE(R::resolveExecutionMode(QVariantMap{
                 {"executionMode", "auto"},
                 {"steps", QVariantList{QVariantMap{{"kind", "browser"}}}}}),
             QStringLiteral("browserBackground"));
    // "auto" con algún paso de escritorio → escritorio.
    QCOMPARE(R::resolveExecutionMode(QVariantMap{
                 {"executionMode", "auto"},
                 {"steps", QVariantList{QVariantMap{{"kind", "browser"}},
                                        QVariantMap{{"kind", "desktop"}}}}}),
             QStringLiteral("desktop"));
    // Modos concretos pasan tal cual.
    QCOMPARE(R::resolveExecutionMode(QVariantMap{{"executionMode", "desktop"}}),
             QStringLiteral("desktop"));
    QCOMPARE(R::resolveExecutionMode(QVariantMap{{"executionMode", "browserBackground"}}),
             QStringLiteral("browserBackground"));
    // Legacy/vacío caen en "auto" (→ web por defecto, sin pasos de escritorio).
    QCOMPARE(R::resolveExecutionMode(QVariantMap{{"executionMode", "agent"}}),
             QStringLiteral("browserBackground"));
    QCOMPARE(R::resolveExecutionMode(QVariantMap{}),
             QStringLiteral("browserBackground"));
}

void AutomationTests::desktopPromptPrefersNativeTools()
{
    const QString prompt = AutomationRunner::augmentPrompt(
        QVariantMap{{"executionMode", "desktop"}},
        QVariantMap{{"id", "calc-demo"}},
        QVariantMap{{"steps", QVariantList{
            QVariantMap{{"kind", "key"}, {"intent", "Tecla WIN"}},
            QVariantMap{{"kind", "type"}, {"intent", "Escribir: \"2+2\""}}}}});
    QVERIFY(prompt.contains(QStringLiteral("Superficie: escritorio foreground nativo")));
    QVERIFY(prompt.contains(QStringLiteral("desktop_observe")));
    QVERIFY(prompt.contains(QStringLiteral("Playwright headed")));
    QVERIFY(prompt.contains(QStringLiteral("no las leas con read_file")));
    // Regresión del bug "sumar 2+2": el modelo se colgaba repitiendo
    // desktop_windows/desktop_observe sin nunca escribir. El prompt debe empujar
    // el camino rápido por teclado, verificación por texto y una regla anti-loop.
    QVERIFY(prompt.contains(QStringLiteral("CAMINO RÁPIDO")));
    QVERIFY(prompt.contains(QStringLiteral("TECLADO primero")));
    QVERIFY(prompt.contains(QStringLiteral("desktop_type")));
    QVERIFY(prompt.contains(QStringLiteral("desktop_controls")));
    QVERIFY(prompt.contains(QStringLiteral("ANTI-LOOP")));
    QVERIFY(prompt.contains(QStringLiteral("NO repitas desktop_windows")));
}

void AutomationTests::desktopToolPolicyKeepsGuiToolsAvailable()
{
    const QStringList tools = AutomationRunner::desktopToolNames();
    QVERIFY(tools.contains(QStringLiteral("desktop_observe")));
    QVERIFY(tools.contains(QStringLiteral("desktop_launch")));
    QVERIFY(tools.contains(QStringLiteral("desktop_key")));
    QVERIFY(tools.contains(QStringLiteral("desktop_type")));
    QVERIFY(!tools.contains(QStringLiteral("run_shell")));
}

void AutomationTests::browserPromptUsesForegroundTeachEvidence()
{
    const QString prompt = AutomationRunner::augmentPrompt(
        QVariantMap{{"executionMode", "browserBackground"}},
        QVariantMap{{"id", "web-demo"}},
        QVariantMap{{"steps", QVariantList{
            QVariantMap{{"kind", "click"}, {"intent", "Click login"},
                        {"x", 0.4}, {"y", 0.2}, {"evidence", "0002.jpg"}}}}});
    QVERIFY(prompt.contains(QStringLiteral("browser foreground de Playwright")));
    QVERIFY(prompt.contains(QStringLiteral("captura: evidence/0002.jpg")));
    QVERIFY(prompt.contains(QStringLiteral("adaptá selectores")));
}

void AutomationTests::headlessBrowserCommandForcesHeadless()
{
    using R = AutomationRunner;
    // El MCP de Playwright por defecto se fuerza headless.
    QCOMPARE(R::headlessBrowserCommand(QStringLiteral("npx @playwright/mcp@latest")),
             QStringLiteral("npx @playwright/mcp@latest --headless"));
    // Si ya hay un flag explícito, se respeta (no se duplica).
    QCOMPARE(R::headlessBrowserCommand(QStringLiteral("npx @playwright/mcp@latest --headless")),
             QStringLiteral("npx @playwright/mcp@latest --headless"));
    QCOMPARE(R::headlessBrowserCommand(QStringLiteral("npx @playwright/mcp@latest --headed")),
             QStringLiteral("npx @playwright/mcp@latest --headed"));
    // MCP de terceros no se toca.
    QCOMPARE(R::headlessBrowserCommand(QStringLiteral("node mi-mcp.js")),
             QStringLiteral("node mi-mcp.js"));
    QCOMPARE(R::foregroundBrowserCommand(QStringLiteral("npx @playwright/mcp@latest")),
             QStringLiteral("npx @playwright/mcp@latest --headed"));
    QCOMPARE(R::foregroundBrowserCommand(QStringLiteral("npx @playwright/mcp@latest --headless")),
             QStringLiteral("npx @playwright/mcp@latest --headed"));
    QCOMPARE(R::foregroundBrowserCommand(QStringLiteral("node mi-mcp.js")),
             QStringLiteral("node mi-mcp.js"));
}

void AutomationTests::artifactsRoundTripAndRedactSecrets()
{
    QVariantMap task{{"id", "demo-automation"}, {"name", "Demo"},
                     {"description", "Completar formulario"},
                     {"executionMode", "desktop"}, {"approvalPolicy", "sensitive"}};
    const QVariantList events{
        QVariantMap{{"kind", "note"}, {"text", "password=secreto"},
                    {"intent", "Ingresar datos"}}};
    const QString id = AutomationArtifactStore::create(
        task, QVariantMap{{"kind", "screen"}, {"targetId", "0"}}, events, {});
    QCOMPARE(id, QStringLiteral("demo-automation"));
    QCOMPARE(AutomationArtifactStore::manifest(id).value("formatVersion").toInt(), 1);
    const QVariantList timeline = AutomationArtifactStore::timeline(id);
    QCOMPARE(timeline.size(), 1);
    QVERIFY(timeline.first().toMap().value("text").toString().contains(QStringLiteral("[REDACTED]")));
    QDir(AutomationArtifactStore::artifactDir(id)).removeRecursively();
}

void AutomationTests::artifactLearningsAppendAndPrompt()
{
    QVariantMap task{{"id", "learn-demo"}, {"name", "Demo"},
                     {"description", "Completar login"},
                     {"executionMode", "browserBackground"}};
    const QString id = AutomationArtifactStore::create(
        task, QVariantMap{{"kind", "screen"}, {"targetId", "0"}},
        QVariantList{QVariantMap{{"kind", "browser"}, {"intent", "Abrir login"}}}, {});
    QCOMPARE(id, QStringLiteral("learn-demo"));
    QVERIFY(AutomationArtifactStore::appendLearning(
        id,
        QStringLiteral("La interfaz movió Login a Acceder y se completó con el selector nuevo."),
        QStringLiteral("[tool] mcp__playwright__browser_click ok")));
    const QVariantList learnings = AutomationArtifactStore::recipe(id)
                                       .value(QStringLiteral("learnings")).toList();
    QCOMPARE(learnings.size(), 1);

    // Dedup: partiendo del learning previo (login), un resumen de éxito nuevo
    // distinto se guarda (→2); su repetición casi idéntica (sólo cambian números/
    // emoji/puntuación) NO apila otro (→sigue 2); una adaptación con texto
    // distinto SÍ (→3).
    QVERIFY(AutomationArtifactStore::appendLearning(
        id, QStringLiteral("¡Tarea completada! La calculadora muestra 2+2 = 4."),
        QStringLiteral("[tool] desktop_type ok")));
    QCOMPARE(AutomationArtifactStore::recipe(id)
                 .value(QStringLiteral("learnings")).toList().size(), 2);   // distinto del login → guarda
    QVERIFY(AutomationArtifactStore::appendLearning(
        id, QStringLiteral("Tarea completada :) la calculadora muestra 5+5 = 10"),
        QStringLiteral("[tool] desktop_type ok")));
    QCOMPARE(AutomationArtifactStore::recipe(id)
                 .value(QStringLiteral("learnings")).toList().size(), 2);   // firma igual → sin duplicar
    QVERIFY(AutomationArtifactStore::appendLearning(
        id, QStringLiteral("La UI movió el visor a otro control; leí el resultado por desktop_controls."),
        QStringLiteral("[tool] desktop_controls ok")));
    QCOMPARE(AutomationArtifactStore::recipe(id)
                 .value(QStringLiteral("learnings")).toList().size(), 3);   // texto distinto → sí guarda
    const QString prompt = AutomationRunner::augmentPrompt(
        QVariantMap{{"executionMode", "browserBackground"}},
        AutomationArtifactStore::manifest(id),
        AutomationArtifactStore::recipe(id));
    QVERIFY(prompt.contains(QStringLiteral("Aprendizajes auto-actualizados")));
    QVERIFY(prompt.contains(QStringLiteral("selector nuevo")));
    QDir(AutomationArtifactStore::artifactDir(id)).removeRecursively();
}

void AutomationTests::keyBufferAccumulatesTextIntoTypeStep()
{
    TeachKeyBuffer kb;
    for (QChar c : QStringLiteral("2 + 2")) kb.feedChar(c);
    QVERIFY(kb.hasPending());
    const QVariantList steps = kb.flush();
    QCOMPARE(steps.size(), 1);
    const QVariantMap step = steps.first().toMap();
    QCOMPARE(step.value("kind").toString(), QStringLiteral("type"));
    QCOMPARE(step.value("text").toString(), QStringLiteral("2 + 2"));
    QVERIFY(step.value("intent").toString().contains(QStringLiteral("2 + 2")));
    // El buffer queda vacío tras el flush → no re-emite.
    QVERIFY(!kb.hasPending());
    QVERIFY(kb.flush().isEmpty());
}

void AutomationTests::keyBufferFlushesTextBeforeNamedKey()
{
    TeachKeyBuffer kb;
    for (QChar c : QStringLiteral("hola")) kb.feedChar(c);
    const QVariantList steps = kb.feedKey(QStringLiteral("ENTER"));
    // Orden real: primero el texto tipeado, después la tecla.
    QCOMPARE(steps.size(), 2);
    QCOMPARE(steps.at(0).toMap().value("kind").toString(), QStringLiteral("type"));
    QCOMPARE(steps.at(0).toMap().value("text").toString(), QStringLiteral("hola"));
    QCOMPARE(steps.at(1).toMap().value("kind").toString(), QStringLiteral("key"));
    QCOMPARE(steps.at(1).toMap().value("key").toString(), QStringLiteral("ENTER"));
    // Sin texto pendiente, feedKey emite sólo el paso de tecla.
    const QVariantList only = kb.feedKey(QStringLiteral("TAB"));
    QCOMPARE(only.size(), 1);
    QCOMPARE(only.first().toMap().value("key").toString(), QStringLiteral("TAB"));
}

void AutomationTests::keyBufferEmitsShortcutWithModifiers()
{
    TeachKeyBuffer kb;
    const QVariantList steps = kb.feedKey(QStringLiteral("R"),
                                          QStringList{QStringLiteral("WIN")});
    QCOMPARE(steps.size(), 1);
    const QVariantMap step = steps.first().toMap();
    QCOMPARE(step.value("kind").toString(), QStringLiteral("key"));
    QCOMPARE(step.value("key").toString(), QStringLiteral("R"));
    QCOMPARE(step.value("modifiers").toStringList(), QStringList{QStringLiteral("WIN")});
    QCOMPARE(step.value("intent").toString(), QStringLiteral("Tecla WIN+R"));
}

void AutomationTests::winTapDistinguishesLoneTapFromShortcut()
{
    WinTapTracker t;
    // Tap solo: down → up sin combo → es tap (abre menú Inicio).
    t.down();
    QVERIFY(t.up());
    // up sin down previo → no es tap.
    QVERIFY(!t.up());
    // Win+R: down → markCombo (al pulsar R) → up NO es tap solo.
    t.down();
    t.markCombo();
    QVERIFY(!t.up());
    // Tras un combo, el estado se reinicia: un nuevo tap solo vuelve a contar.
    t.down();
    QVERIFY(t.up());
    // markCombo sin down no arma nada → el próximo down/up es tap limpio.
    t.markCombo();
    t.down();
    QVERIFY(t.up());
}

QTEST_MAIN(AutomationTests)
#include "test_automation.moc"
