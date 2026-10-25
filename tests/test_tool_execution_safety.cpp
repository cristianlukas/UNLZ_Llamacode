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
    void mcpVerificationNudgeRequiresImmediateReadOnlyDesktopObservation();
    void desktopFailedVerificationBlocksMutationUntilEvidence();
    void desktopVerificationCoversKeyboardAndSemanticActions();
    void desktopStaleRecoveryAllowsOnlyOneReobservedRetry();
    void desktopRepeatedClickAfterUnchangedObservationIsBlocked();
    void desktopRepeatedTypingAfterSuccessIsBlockedForTurn();
    void desktopRepeatedSetValueAfterSuccessIsBlockedForTurn();
    void desktopRepeatedFailedMutationBlocksOnlySameArguments();
    void desktopActionRepeatSignatureIgnoresOnlySnapshotId();
    void canonicalHashIgnoresObjectKeyOrder();
    void idempotencyIsScopedByCorrelation();
    void localPrincipalIsBoundToWorkspace();
    void resourceAuthorizationFailsClosed();
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

void ToolExecutionSafetyTests::mcpVerificationNudgeRequiresImmediateReadOnlyDesktopObservation()
{
    ToolExecutionSafety::McpVerificationGate gate;
    gate.recordAction(QStringLiteral("desktop"), true, false);
    QVERIFY(!gate.requiresDesktopObservationTool());
    const QString desktopPrompt = gate.observationPrompt();
    QVERIFY(desktopPrompt.contains(QStringLiteral("siguiente llamada de herramienta debe ser sólo de lectura")));
    QVERIFY(desktopPrompt.contains(QStringLiteral("desktop_read_text una vez")));
    QVERIFY(desktopPrompt.contains(QStringLiteral("target_id literal")));
    QVERIFY(desktopPrompt.contains(QStringLiteral("No pulses teclas, escribas ni hagas clic")));
    QVERIFY(desktopPrompt.contains(QStringLiteral("checkpoint intermedio")));
    QVERIFY(desktopPrompt.contains(QStringLiteral("continúa con el siguiente paso pendiente")));
    QVERIFY(desktopPrompt.contains(QStringLiteral("no respondas final si aún falta guardar")));

    gate.requestObservationTool();
    QVERIFY(gate.requiresDesktopObservationTool());
    gate.recordObservation(QStringLiteral("desktop"), false, true);
    QVERIFY(gate.requiresDesktopObservationTool());
    gate.recordObservation(QStringLiteral("desktop"), true, true);
    QVERIFY(!gate.requiresDesktopObservationTool());

    gate.clear();
    gate.recordAction(QStringLiteral("drive"), true, false);
    gate.requestObservationTool();
    QVERIFY(!gate.requiresDesktopObservationTool());
    const QString mcpPrompt = gate.observationPrompt();
    QVERIFY(mcpPrompt.contains(QStringLiteral("lectura del mismo servidor pendiente")));
    QVERIFY(mcpPrompt.contains(QStringLiteral("drive")));
    QVERIFY(mcpPrompt.contains(QStringLiteral("checkpoint intermedio")));
    QVERIFY(mcpPrompt.contains(QStringLiteral("continúa los pasos pendientes")));
    QVERIFY(!mcpPrompt.contains(QStringLiteral("desktop_read_text")));
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

void ToolExecutionSafetyTests::desktopRepeatedClickAfterUnchangedObservationIsBlocked()
{
    ToolExecutionSafety::DesktopActionRepeatGuard guard;
    const QString key = QStringLiteral("desktop_controls|paint-window");
    const QString clickFormas = QStringLiteral("click-element-formas");
    const QString clickRectangle = QStringLiteral("click-element-rectangle");
    const QString before = QStringLiteral("32 controls; same snapshot");

    guard.recordObservation(key, before);
    guard.recordAction(clickFormas, key);
    guard.recordObservation(key, before);
    QVERIFY(guard.blocks(clickFormas));
    QVERIFY(!guard.blocks(clickRectangle));

    // A different action is allowed; stale evidence keeps the original action blocked.
    guard.recordAction(clickRectangle, key);
    QVERIFY(guard.blocks(clickFormas));
    QVERIFY(!guard.blocks(clickRectangle));
    guard.recordObservation(key, QStringLiteral("31 controls; menu changed"));
    QVERIFY(!guard.blocks(clickFormas));
    QVERIFY(!guard.blocks(clickRectangle));

    // Once state changes, the same click can be retried against fresh evidence.
    guard.recordAction(clickFormas, key);
    guard.recordObservation(key, QStringLiteral("30 controls; shape selected"));
    QVERIFY(!guard.blocks(clickFormas));
}

void ToolExecutionSafetyTests::desktopRepeatedTypingAfterSuccessIsBlockedForTurn()
{
    ToolExecutionSafety::DesktopActionRepeatGuard guard;
    const QString key = QStringLiteral("desktop_read_text|excel-window|b2");
    const QString typeFour = QStringLiteral("desktop_type|target=excel-window|text=4");
    const QString differentAction = QStringLiteral("desktop_click|target=excel-window|x=0.25");

    guard.recordObservation(key, QStringLiteral("B2: 2\nreceipt_id=before"));
    // LlamaAgentBackend blocks the successful signature as soon as the tool
    // settles, even if the control appended the text wrongly.
    guard.blockAction(typeFour);
    guard.clearPending();
    QVERIFY(guard.blocks(typeFour));

    // A changed readback does not authorize repeating a type that may already
    // have changed the application state.
    guard.recordAction(differentAction, key);
    QVERIFY(guard.blocks(typeFour));
    guard.recordObservation(key, QStringLiteral("B2: 42\nreceipt_id=changed"));
    QVERIFY(guard.blocks(typeFour));

    // The next user turn clears the one-turn repeat block.
    guard.clear();
    QVERIFY(!guard.blocks(typeFour));
}

void ToolExecutionSafetyTests::desktopRepeatedSetValueAfterSuccessIsBlockedForTurn()
{
    ToolExecutionSafety::DesktopActionRepeatGuard guard;
    const QString setB2ToFour = QStringLiteral(
        "desktop_control_action|{\"action\":\"set_value\",\"control_id\":\"B2\","
        "\"target_id\":\"excel-window\",\"value\":\"4\"}");
    const QString setB2ToFive = QStringLiteral(
        "desktop_control_action|{\"action\":\"set_value\",\"control_id\":\"B2\","
        "\"target_id\":\"excel-window\",\"value\":\"5\"}");

    // set_value reports a UIA readback; the same successful assignment is
    // unnecessary again during this turn, even if another cell still looks stale.
    guard.blockAction(setB2ToFour);
    QVERIFY(guard.blocks(setB2ToFour));
    QVERIFY(!guard.blocks(setB2ToFive));

    // A new user turn clears the per-turn repeat block.
    guard.clear();
    QVERIFY(!guard.blocks(setB2ToFour));
}

void ToolExecutionSafetyTests::desktopRepeatedFailedMutationBlocksOnlySameArguments()
{
    ToolExecutionSafety::DesktopActionRepeatGuard guard;
    const QString key = QStringLiteral("desktop_controls|excel-window");
    const QString failedSetValue = QStringLiteral(
        "desktop_control_action|{\"action\":\"set_value\",\"control_id\":\"\","
        "\"target_id\":\"excel-window\",\"value\":\"B2\"}");
    const QString correctedControl = QStringLiteral(
        "desktop_control_action|{\"action\":\"set_value\",\"control_id\":\"name-box\","
        "\"target_id\":\"excel-window\",\"value\":\"B2\"}");

    guard.recordObservation(key, QStringLiteral("32 controls; before"));
    guard.blockAction(failedSetValue, key);
    QVERIFY(guard.blocks(failedSetValue));
    QVERIFY(!guard.blocks(correctedControl));

    // Una lectura igual no habilita el mismo error; un cambio UIA real sí.
    guard.recordObservation(key, QStringLiteral("32 controls; before"));
    QVERIFY(guard.blocks(failedSetValue));
    guard.recordObservation(key, QStringLiteral("31 controls; dialog changed"));
    QVERIFY(!guard.blocks(failedSetValue));

    guard.blockAction(failedSetValue);
    guard.clear();
    QVERIFY(!guard.blocks(failedSetValue));
}

void ToolExecutionSafetyTests::desktopActionRepeatSignatureIgnoresOnlySnapshotId()
{
    const QString first = ToolExecutionSafety::desktopActionRepeatSignature(
        QStringLiteral("desktop_control_action"), QJsonObject{
            {QStringLiteral("action"), QStringLiteral("set_value")},
            {QStringLiteral("control_id"), QString()},
            {QStringLiteral("snapshot_id"), QStringLiteral("snapshot-1")},
            {QStringLiteral("target_id"), QStringLiteral("excel-window")},
            {QStringLiteral("value"), QStringLiteral("B2")}});
    const QString refreshedSnapshot = ToolExecutionSafety::desktopActionRepeatSignature(
        QStringLiteral("desktop_control_action"), QJsonObject{
            {QStringLiteral("action"), QStringLiteral("set_value")},
            {QStringLiteral("control_id"), QString()},
            {QStringLiteral("snapshot_id"), QStringLiteral("snapshot-2")},
            {QStringLiteral("target_id"), QStringLiteral("excel-window")},
            {QStringLiteral("value"), QStringLiteral("B2")}});
    const QString correctedControl = ToolExecutionSafety::desktopActionRepeatSignature(
        QStringLiteral("desktop_control_action"), QJsonObject{
            {QStringLiteral("action"), QStringLiteral("set_value")},
            {QStringLiteral("control_id"), QStringLiteral("name-box")},
            {QStringLiteral("snapshot_id"), QStringLiteral("snapshot-2")},
            {QStringLiteral("target_id"), QStringLiteral("excel-window")},
            {QStringLiteral("value"), QStringLiteral("B2")}});

    QCOMPARE(first, refreshedSnapshot);
    QVERIFY(first != correctedControl);
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

void ToolExecutionSafetyTests::localPrincipalIsBoundToWorkspace()
{
    const QJsonObject one = ToolExecutionSafety::localPrincipal(
        QStringLiteral("/home/alice"), QStringLiteral("/work/project-a"));
    const QJsonObject same = ToolExecutionSafety::localPrincipal(
        QStringLiteral("/home/alice"), QStringLiteral("/work/project-a"));
    const QJsonObject otherWorkspace = ToolExecutionSafety::localPrincipal(
        QStringLiteral("/home/alice"), QStringLiteral("/work/project-b"));
    QVERIFY(!one.isEmpty());
    QCOMPARE(one.value(QStringLiteral("issuer")).toString(),
             QStringLiteral("io.llamacode.local"));
    QCOMPARE(one.value(QStringLiteral("subjectId")), same.value(QStringLiteral("subjectId")));
    QCOMPARE(one.value(QStringLiteral("workspaceId")), same.value(QStringLiteral("workspaceId")));
    QVERIFY(one.value(QStringLiteral("workspaceId")).toString()
            != otherWorkspace.value(QStringLiteral("workspaceId")).toString());
    QVERIFY(!one.value(QStringLiteral("subjectId")).toString().contains(QStringLiteral("alice")));
}

void ToolExecutionSafetyTests::resourceAuthorizationFailsClosed()
{
    const QJsonObject principal = ToolExecutionSafety::localPrincipal(
        QStringLiteral("/home/alice"), QStringLiteral("/work/project-a"));
    const QString workspaceId = principal.value(QStringLiteral("workspaceId")).toString();
    const QJsonObject workspaceAnnotations{{QStringLiteral("llamacode"), QJsonObject{
        {QStringLiteral("authorization"), QJsonObject{
             {QStringLiteral("scope"), QStringLiteral("workspace")},
             {QStringLiteral("resourceParameter"), QStringLiteral("workspace_id")}}}}}};
    QVERIFY(ToolExecutionSafety::resourceAuthorizationError(
        workspaceAnnotations, {{QStringLiteral("workspace_id"), workspaceId}}, principal).isEmpty());
    QVERIFY(!ToolExecutionSafety::resourceAuthorizationError(
        workspaceAnnotations, {{QStringLiteral("workspace_id"), QStringLiteral("other-workspace")}},
        principal).isEmpty());
    QVERIFY(!ToolExecutionSafety::resourceAuthorizationError(
        workspaceAnnotations, {{QStringLiteral("workspace_id"), workspaceId}}, {}).isEmpty());

    const QJsonObject tenantAnnotations{{QStringLiteral("llamacode"), QJsonObject{
        {QStringLiteral("authorization"), QJsonObject{
             {QStringLiteral("scope"), QStringLiteral("tenant")}}}}}};
    QVERIFY(!ToolExecutionSafety::resourceAuthorizationError(
        tenantAnnotations, {{QStringLiteral("record_id"), QStringLiteral("42")}}, principal).isEmpty());
    QVERIFY(!ToolExecutionSafety::resourceAuthorizationError(
        {}, {{QStringLiteral("filter"), QJsonObject{
                 {QStringLiteral("tenant_id"), QStringLiteral("other-tenant")}}}}, principal).isEmpty());
}

QTEST_MAIN(ToolExecutionSafetyTests)
#include "test_tool_execution_safety.moc"
