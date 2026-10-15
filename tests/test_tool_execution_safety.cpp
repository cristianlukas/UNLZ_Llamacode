#include <QtTest>

#include "core/agent/ToolExecutionSafety.h"
#include "core/automation/DesktopComputerUse.h"

class ToolExecutionSafetyTests : public QObject
{
    Q_OBJECT
private slots:
    void unknownIsConservative();
    void standardAnnotationsAreHonored();
    void explicitContractOverridesHints();
    void workspaceMutationPathsApplyOnlyToLocalFileEffects();
    void browserNavigationNeedsHostApprovalAndHttpScheme();
    void mcpVerificationGateRequiresFreshReadFromSameServer();
    void desktopFailedVerificationBlocksMutationUntilEvidence();
    void desktopVerificationCoversKeyboardAndSemanticActions();
    void desktopStaleRecoveryAllowsOnlyOneReobservedRetry();
    void canonicalHashIgnoresObjectKeyOrder();
    void idempotencyIsScopedByCorrelation();
};

void ToolExecutionSafetyTests::unknownIsConservative()
{
    const auto c = ToolExecutionSafety::fromMcpTool(
        QStringLiteral("do_thing"), QString(), {});
    QCOMPARE(c.effect, QStringLiteral("external_write"));
    QVERIFY(c.approvalRequired);
    QCOMPARE(c.source, QStringLiteral("conservative_default"));
}

void ToolExecutionSafetyTests::standardAnnotationsAreHonored()
{
    const auto c = ToolExecutionSafety::fromMcpTool(
        QStringLiteral("lookup"), QString(),
        {{QStringLiteral("readOnlyHint"), true},
         {QStringLiteral("destructiveHint"), false},
         {QStringLiteral("idempotentHint"), true},
         {QStringLiteral("openWorldHint"), false}});
    QCOMPARE(c.effect, QStringLiteral("read"));
    QVERIFY(!c.approvalRequired);
    QVERIFY(c.idempotent);
    QVERIFY(!c.openWorld);
}

void ToolExecutionSafetyTests::explicitContractOverridesHints()
{
    const QJsonObject annotations{
        {QStringLiteral("readOnlyHint"), true},
        {QStringLiteral("llamacode"), QJsonObject{
             {QStringLiteral("effect"), QStringLiteral("proposal")},
             {QStringLiteral("approvalRequired"), true},
             {QStringLiteral("receipt"), QStringLiteral("external_id")}}}};
    const auto c = ToolExecutionSafety::fromMcpTool(
        QStringLiteral("draft_update"), QString(), annotations);
    QCOMPARE(c.effect, QStringLiteral("proposal"));
    QVERIFY(c.approvalRequired);
    QCOMPARE(c.receipt, QStringLiteral("external_id"));
}

void ToolExecutionSafetyTests::workspaceMutationPathsApplyOnlyToLocalFileEffects()
{
    const QJsonObject browserSchema{
        {QStringLiteral("properties"), QJsonObject{
             {QStringLiteral("url"), QJsonObject{{QStringLiteral("type"), QStringLiteral("string")}}},
             {QStringLiteral("filename"), QJsonObject{
                  {QStringLiteral("type"), QStringLiteral("string")},
                  {QStringLiteral("description"), QStringLiteral(
                       "Relative file names are saved against the workspace root.")}}}}}};
    QVERIFY(!ToolExecutionSafety::requiresWorkspaceMutationPaths(
        QStringLiteral("browser_navigate"), QStringLiteral("Navigate the browser to a URL."),
        browserSchema, {}, {{QStringLiteral("url"), QStringLiteral("https://example.test")}},
        QStringLiteral("external_write")));
    QVERIFY(!ToolExecutionSafety::requiresWorkspaceMutationPaths(
        QStringLiteral("browser_take_screenshot"), QStringLiteral("Capture the browser page."),
        browserSchema, {}, {{QStringLiteral("scale"), QStringLiteral("css")}},
        QStringLiteral("external_write")));
    QVERIFY(ToolExecutionSafety::requiresWorkspaceMutationPaths(
        QStringLiteral("browser_take_screenshot"), QStringLiteral("Capture the browser page."),
        browserSchema, {}, {{QStringLiteral("filename"), QStringLiteral("capture.png")}},
        QStringLiteral("external_write")));
    QVERIFY(ToolExecutionSafety::requiresWorkspaceMutationPaths(
        QStringLiteral("opaque_operation"), QStringLiteral("Unknown operation."),
        {}, {}, {}, QStringLiteral("external_write")));
    QVERIFY(!ToolExecutionSafety::requiresWorkspaceMutationPaths(
        QStringLiteral("opaque_read"), QStringLiteral("Read-only operation."),
        {}, {}, {}, QStringLiteral("read")));
    QVERIFY(!ToolExecutionSafety::requiresWorkspaceMutationPaths(
        QStringLiteral("opaque_operation"), QStringLiteral("Unknown operation."),
        {}, {{QStringLiteral("llamacode"), QJsonObject{
                 {QStringLiteral("workspaceMutation"), false}}}}, {},
        QStringLiteral("external_write")));
}

void ToolExecutionSafetyTests::browserNavigationNeedsHostApprovalAndHttpScheme()
{
    const QJsonObject schema{{QStringLiteral("properties"), QJsonObject{
        {QStringLiteral("url"), QJsonObject{{QStringLiteral("type"), QStringLiteral("string")}}}}}};
    const QJsonObject https{{QStringLiteral("url"), QStringLiteral(
        "https://example.test/account?token=secret")}};
    QVERIFY(ToolExecutionSafety::isBrowserNavigationCall(
        QStringLiteral("browser_navigate"), QStringLiteral("Navigate browser to URL"),
        schema, https));
    QCOMPARE(ToolExecutionSafety::browserNavigationPolicyError(
                 QStringLiteral("browser_navigate"), QStringLiteral("Navigate browser"),
                 schema, https), QString());
    QCOMPARE(ToolExecutionSafety::browserNavigationApprovalOrigin(
                 QStringLiteral("browser_navigate"), QStringLiteral("Navigate browser"),
                 schema, https), QStringLiteral("https://example.test"));

    for (const QString &url : {QStringLiteral("file:///etc/passwd"),
                               QStringLiteral("javascript:alert(1)"),
                               QStringLiteral("https://user:pass@example.test/")}) {
        QVERIFY(!ToolExecutionSafety::browserNavigationPolicyError(
                     QStringLiteral("browser_navigate"), QStringLiteral("Navigate browser"),
                     schema, {{QStringLiteral("url"), url}}).isEmpty());
    }
    QVERIFY(!ToolExecutionSafety::isBrowserNavigationCall(
        QStringLiteral("browser_snapshot"), QStringLiteral("Read current page"),
        schema, https));
    QVERIFY(!ToolExecutionSafety::isBrowserNavigationCall(
        QStringLiteral("email_lookup"), QStringLiteral("Find a URL"), schema, https));
}

void ToolExecutionSafetyTests::mcpVerificationGateRequiresFreshReadFromSameServer()
{
    ToolExecutionSafety::McpVerificationGate gate;
    gate.recordAction(QStringLiteral("browser"), true, false);
    QVERIFY(gate.hasPending());
    QCOMPARE(gate.pendingServers(), QStringList{QStringLiteral("browser")});
    gate.recordObservation(QStringLiteral("mail"), true, true);
    QVERIFY(gate.hasPending());
    gate.recordObservation(QStringLiteral("browser"), false, true);
    QVERIFY(gate.hasPending());
    gate.recordObservation(QStringLiteral("browser"), true, false);
    QVERIFY(gate.hasPending());
    gate.recordObservation(QStringLiteral("browser"), true, true);
    QVERIFY(!gate.hasPending());

    gate.recordAction(QStringLiteral("calendar"), true, true);
    QVERIFY(!gate.hasPending());
    gate.recordAction(QStringLiteral("calendar"), false, false);
    QVERIFY(!gate.hasPending());
    QCOMPARE(gate.completionDecision(0, 2),
             ToolExecutionSafety::McpVerificationGate::CompletionDecision::Allow);

    gate.recordAction(QStringLiteral("drive"), true, false);
    QCOMPARE(gate.completionDecision(0, 2),
             ToolExecutionSafety::McpVerificationGate::CompletionDecision::RequestObservation);
    QCOMPARE(gate.completionDecision(2, 2),
             ToolExecutionSafety::McpVerificationGate::CompletionDecision::Block);
    gate.recordObservation(QStringLiteral("drive"), true, true);
    QCOMPARE(gate.completionDecision(2, 2),
             ToolExecutionSafety::McpVerificationGate::CompletionDecision::Allow);
}

void ToolExecutionSafetyTests::desktopFailedVerificationBlocksMutationUntilEvidence()
{
    ToolExecutionSafety::DesktopActionSafetyGate gate;
    QVERIFY(!gate.blocksActions());
    QVERIFY(!gate.needsBlockedCompletion());

    gate.recordFailedVerification(QStringLiteral("TOTAL 42"));
    QVERIFY(gate.blocksActions());
    QVERIFY(gate.needsBlockedCompletion());

    // Un texto de lectura sin la condición esperada no autoriza otra mutación.
    gate.recordTextObservation(true, QStringLiteral("El total todavía no aparece"));
    QVERIFY(gate.blocksActions());
    gate.recordTextObservation(false, QStringLiteral("TOTAL 42"));
    QVERIFY(gate.blocksActions());

    // La lectura visible puede resolver un assert UIA que no expuso el contenido.
    gate.recordTextObservation(true, QStringLiteral("Se muestra Tótal 42"));
    QVERIFY(!gate.blocksActions());
    QVERIFY(!gate.needsBlockedCompletion());

    // Una lectura intermedia no borra que hubo una mutación aún sin verificar.
    gate.recordActionResult(true, false);
    gate.recordObservation();
    QVERIFY(gate.hasUnverifiedAction());
    gate.recordFailedVerification(QStringLiteral("otro valor"), QStringLiteral("condition-2"));
    QVERIFY(gate.blocksActions());
    gate.recordVerified(QStringLiteral("condition-1"));
    QVERIFY(gate.blocksActions());
    gate.recordVerified(QStringLiteral("condition-2"));
    QVERIFY(!gate.blocksActions());

    // Una lectura OCR positiva anterior al FAIL del assert ya confirma el texto.
    gate.clear();
    gate.recordActionResult(true, false);
    gate.recordTextObservation(true, QStringLiteral("Se muestra TOTAL 42"));
    gate.recordFailedVerification(QStringLiteral("TOTAL 42"), QStringLiteral("condition-3"));
    QVERIFY(!gate.blocksActions());
    QVERIFY(!gate.hasUnverifiedAction());
}

void ToolExecutionSafetyTests::desktopVerificationCoversKeyboardAndSemanticActions()
{
    // Los dos recorridos de regresión usan un editor de texto (teclado) y una
    // calculadora (acción UIA); la política común no depende de esos nombres.
    const QList<QPair<QString, QVariantMap>> appActions{
        {QStringLiteral("desktop_type"), {}},
        {QStringLiteral("desktop_control_action"),
         {{QStringLiteral("action"), QStringLiteral("invoke")}}}};
    for (const auto &entry : appActions) {
        QVERIFY(DesktopComputerUse::isDesktopMutationTool(entry.first, entry.second));
        ToolExecutionSafety::DesktopActionSafetyGate gate;
        gate.recordActionResult(true, false);
        gate.recordFailedVerification(QStringLiteral("42"), entry.first);
        QVERIFY(gate.blocksActions());
        gate.recordTextObservation(true, QStringLiteral("Se muestra 42"));
        QVERIFY(!gate.blocksActions());
    }
}

void ToolExecutionSafetyTests::desktopStaleRecoveryAllowsOnlyOneReobservedRetry()
{
    ToolExecutionSafety::DesktopActionSafetyGate gate;
    gate.recordActionResult(false, true);
    QVERIFY(gate.needsFreshObservation());
    QVERIFY(gate.needsBlockedCompletion());
    QVERIFY(!gate.blocksActions());

    // Si vuelve a fallar stale antes de reobservar, no se permite otro intento.
    gate.recordActionResult(false, true);
    QVERIFY(gate.blocksActions());
    gate.clear();

    // El flujo válido refresca una vez y permite una sola acción re-resuelta.
    gate.recordActionResult(false, true);
    gate.recordObservation();
    QVERIFY(!gate.needsFreshObservation());
    gate.recordActionResult(true, false);
    QVERIFY(!gate.blocksActions());
    QVERIFY(!gate.needsBlockedCompletion());

    // Un segundo fallo stale del intento re-resuelto cierra la recuperación.
    gate.clear();
    gate.recordActionResult(false, true);
    gate.recordObservation();
    gate.recordActionResult(false, true);
    QVERIFY(gate.blocksActions());
    QVERIFY(gate.needsBlockedCompletion());

    // También se bloquea si la única acción re-resuelta falla por otra causa.
    gate.clear();
    gate.recordActionResult(false, true);
    gate.recordObservation();
    gate.recordActionResult(false, false);
    QVERIFY(gate.blocksActions());
}

void ToolExecutionSafetyTests::canonicalHashIgnoresObjectKeyOrder()
{
    const QJsonObject a{{QStringLiteral("z"), 1},
                        {QStringLiteral("nested"), QJsonObject{
                             {QStringLiteral("b"), 2}, {QStringLiteral("a"), 1}}}};
    const QJsonObject b{{QStringLiteral("nested"), QJsonObject{
                             {QStringLiteral("a"), 1}, {QStringLiteral("b"), 2}}},
                        {QStringLiteral("z"), 1}};
    QCOMPARE(ToolExecutionSafety::payloadHash(QStringLiteral("s"), QStringLiteral("t"), a),
             ToolExecutionSafety::payloadHash(QStringLiteral("s"), QStringLiteral("t"), b));
}

void ToolExecutionSafetyTests::idempotencyIsScopedByCorrelation()
{
    const QString hash = ToolExecutionSafety::payloadHash(
        QStringLiteral("s"), QStringLiteral("t"), {{QStringLiteral("x"), 1}});
    const QString one = ToolExecutionSafety::idempotencyKey(QStringLiteral("run-1"), hash);
    QCOMPARE(one, ToolExecutionSafety::idempotencyKey(QStringLiteral("run-1"), hash));
    QVERIFY(one != ToolExecutionSafety::idempotencyKey(QStringLiteral("run-2"), hash));
}

QTEST_MAIN(ToolExecutionSafetyTests)
#include "test_tool_execution_safety.moc"
