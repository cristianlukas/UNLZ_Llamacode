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
    void headlessBrowserCommandForcesHeadless();
    void artifactsRoundTripAndRedactSecrets();
    void keyBufferAccumulatesTextIntoTypeStep();
    void keyBufferFlushesTextBeforeNamedKey();
    void keyBufferEmitsShortcutWithModifiers();
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

QTEST_MAIN(AutomationTests)
#include "test_automation.moc"
