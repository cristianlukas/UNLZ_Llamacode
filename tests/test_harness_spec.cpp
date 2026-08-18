// Unit tests del CONTRATO del harness modular (HarnessSpec):
//   - herencia por módulo: "ausente = heredado", nunca "vacío".
//   - round-trip JSON y migración de un AgentProfile legacy (fixture congelado).
//   - cadena de `extends` resuelta por ProfileManager, incluido un ciclo.
//   - packs de tools: expansión, precedencia include/exclude, orden estable,
//     presupuesto en tokens y preflight de dependencias.
//   - invariantes de permisos: el guardrail Zero-Autonomy no se puede bajar
//     fuera de `super`, y el scope de un perfil nunca amplía el de la Task.
//   - overrides por fase (plan/exec/verify).
//
// NOTA: storagePath cachea la raíz en un 'static' → LLAMACODE_PROFILES_DIR se
// setea en initTestCase, antes del primer ProfileManager.

#include <QtTest>
#include <QTemporaryDir>
#include <QJsonDocument>
#include <QJsonObject>
#include "core/profiles/HarnessSpec.h"
#include "core/profiles/ProfileTypes.h"
#include "core/profiles/ProfileManager.h"
#include "core/agent/LlamaAgentBackend.h"

class HarnessSpecTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();

    void modules_defaultsMatchHistoricBehaviour();
    void resolve_absentModuleIsInherited();
    void resolve_declaredEmptyModuleWins();
    void json_roundTripKeepsDeclaredModulesOnly();
    void legacyProfile_migratesToEquivalentSpec();
    void legacyJsonFixture_stillLoads();
    void chain_resolvesParentThenChild();
    void chain_cycleDoesNotHang();
    void packs_expandIncludeExcludeAndOrder();
    void packs_budgetAndDependencyWarnings();
    void permissions_guardrailOnlyDroppableInSuper();
    void permissions_scopeNeverWidens();
    void phases_patchOverridesResolvedSpec();
    void diff_listsOnlyChangedFields();
    void presets_minimalAndRpaExist();

private:
    QTemporaryDir m_dir;
};

void HarnessSpecTests::initTestCase()
{
    QVERIFY(m_dir.isValid());
    qputenv("LLAMACODE_PROFILES_DIR", m_dir.path().toLocal8Bit());
}

// Los defaults son el contrato de no-regresión: si alguien los cambia, un perfil
// que no declara nada empieza a comportarse distinto sin haberlo pedido.
void HarnessSpecTests::modules_defaultsMatchHistoricBehaviour()
{
    const HarnessSpec s;
    QCOMPARE(s.loop.sameCallLimit, 3);
    QCOMPARE(s.loop.failureSpiral, 3);
    QCOMPARE(s.loop.transportRetries, 60);
    QCOMPARE(s.loop.credits, 8);
    QCOMPARE(s.loop.maxCredits, 16);
    QCOMPARE(s.loop.quickToolTimeoutSec, 15);
    QCOMPARE(s.loop.webToolTimeoutSec, 180);
    QCOMPARE(s.loop.streamIdleTimeoutSec, 0);      // 0 = env/3600, como antes
    QCOMPARE(s.context.keepLastImages, 1);
    QVERIFY(s.context.compaction);
    QVERIFY(s.context.prune);
    QVERIFY(s.context.readDedup);
    QVERIFY(!s.context.preflight);                 // estaba tras un #ifdef de debug
    QVERIFY(s.context.warmup);
    QCOMPARE(s.permissions.approvalMode, QStringLiteral("ask"));
    QVERIFY(s.permissions.hitlDestructive);
    QVERIFY(!s.permissions.mailAutoSend);
    QCOMPARE(s.protocol.toolProtocol, QStringLiteral("auto"));
    QCOMPARE(s.escalation.maxParallelSubagents, 5);
    QVERIFY(s.escalation.isolateSubagents);
    QVERIFY(s.isEmpty());
}

void HarnessSpecTests::resolve_absentModuleIsInherited()
{
    HarnessSpec base;
    base.loop.set = true;
    base.loop.sameCallLimit = 7;
    base.tools.set = true;
    base.tools.packs = {QStringLiteral("core")};

    HarnessSpec child;                     // no declara NADA
    const HarnessSpec r = HarnessSpec::resolve(base, child);
    QCOMPARE(r.loop.sameCallLimit, 7);
    QCOMPARE(r.tools.packs, QStringList{QStringLiteral("core")});
}

void HarnessSpecTests::resolve_declaredEmptyModuleWins()
{
    HarnessSpec base;
    base.tools.set = true;
    base.tools.packs = {QStringLiteral("core"), QStringLiteral("rag")};

    HarnessSpec child;
    child.tools.set = true;                // declarado y vacío = a propósito
    const HarnessSpec r = HarnessSpec::resolve(base, child);
    QVERIFY(r.tools.packs.isEmpty());
    QVERIFY(HarnessTools::resolve(r.tools).isEmpty());
}

void HarnessSpecTests::json_roundTripKeepsDeclaredModulesOnly()
{
    HarnessSpec s;
    s.extends = QStringLiteral("agent-avanzado");
    s.loop.set = true;
    s.loop.sameCallLimit = 2;
    s.context.set = true;
    s.context.keepLastImages = 0;

    const QJsonObject json = s.toJson();
    QVERIFY(json.contains(QStringLiteral("loop")));
    QVERIFY(json.contains(QStringLiteral("context")));
    QVERIFY(!json.contains(QStringLiteral("tools")));     // no declarado → no viaja
    QVERIFY(!json.contains(QStringLiteral("permissions")));

    const HarnessSpec back = HarnessSpec::fromJson(json);
    QCOMPARE(back.extends, QStringLiteral("agent-avanzado"));
    QVERIFY(back.loop.set);
    QCOMPARE(back.loop.sameCallLimit, 2);
    QVERIFY(back.context.set);
    QCOMPARE(back.context.keepLastImages, 0);
    QVERIFY(!back.tools.set);
    QVERIFY(!back.permissions.set);
}

void HarnessSpecTests::legacyProfile_migratesToEquivalentSpec()
{
    AgentProfile p;
    p.id = QStringLiteral("legacy");
    p.enabledTools = {QStringLiteral("read_file"), QStringLiteral("grep")};
    p.directives = {QStringLiteral("discipline")};
    p.approvalMode = QStringLiteral("manual");
    p.thinking = true;
    p.temperature = 0.4;
    p.progressCredits = 11;
    p.quickToolTimeoutSec = 42;
    p.mcpEnabled = false;

    const HarnessSpec s = p.toSpec();
    QCOMPARE(HarnessTools::resolve(s.tools),
             (QStringList{QStringLiteral("read_file"), QStringLiteral("grep")}));
    QCOMPARE(s.prompt.builtin, QStringList{QStringLiteral("discipline")});
    QCOMPARE(s.permissions.approvalMode, QStringLiteral("manual"));
    QVERIFY(s.protocol.thinking);
    QCOMPARE(s.protocol.temperature, 0.4);
    QCOMPARE(s.loop.credits, 11);
    QCOMPARE(s.loop.quickToolTimeoutSec, 42);
    QVERIFY(!s.tools.mcpToolsEnabled);
    // Lo NO declarado por el perfil legacy conserva los defaults del harness.
    QCOMPARE(s.loop.sameCallLimit, 3);
    QVERIFY(!s.context.set);
}

// Fixture congelado: JSON tal como lo escribía la versión anterior a la feature.
// Si esto se rompe, un usuario pierde su perfil al actualizar.
void HarnessSpecTests::legacyJsonFixture_stillLoads()
{
    const QByteArray legacy = R"({
        "id": "ap-1",
        "name": "Mi perfil",
        "enabledTools": ["read_file","list_dir","run_shell"],
        "directives": ["discipline","style"],
        "approvalMode": "ask",
        "thinking": false,
        "temperature": -1,
        "systemExtra": "hola",
        "mcpEnabled": true,
        "progressCredits": 9,
        "progressMaxCredits": 18,
        "progressReplanAfter": 4,
        "progressStopAfter": 6,
        "quickToolTimeoutSec": 20
    })";
    const AgentProfile p =
        AgentProfile::fromJson(QJsonDocument::fromJson(legacy).object());
    QCOMPARE(p.name, QStringLiteral("Mi perfil"));
    QVERIFY(!p.hasSpec);                     // sin bloque spec: sigue siendo legacy
    const HarnessSpec s = p.toSpec();
    QCOMPARE(s.loop.credits, 9);
    QCOMPARE(s.loop.maxCredits, 18);
    QCOMPARE(s.prompt.systemExtra, QStringLiteral("hola"));
    QCOMPARE(HarnessTools::resolve(s.tools).size(), 3);
}

void HarnessSpecTests::chain_resolvesParentThenChild()
{
    ProfileManager pm;
    const QString parentId = pm.addAgentProfile(QStringLiteral("Padre"));
    QVERIFY(!parentId.isEmpty());
    HarnessSpec parentSpec;
    parentSpec.loop.set = true;
    parentSpec.loop.sameCallLimit = 9;
    parentSpec.context.set = true;
    parentSpec.context.keepLastImages = 4;
    QVERIFY(pm.setAgentProfileSpec(parentId, parentSpec.toJson().toVariantMap()));

    const QString childId = pm.addAgentProfile(QStringLiteral("Hijo"));
    HarnessSpec childSpec;
    childSpec.extends = parentId;
    childSpec.context.set = true;
    childSpec.context.keepLastImages = 0;    // pisa sólo este módulo
    QVERIFY(pm.setAgentProfileSpec(childId, childSpec.toJson().toVariantMap()));

    const HarnessSpec resolved = pm.resolveHarnessSpecById(childId);
    QCOMPARE(resolved.loop.sameCallLimit, 9);      // heredado del padre
    QCOMPARE(resolved.context.keepLastImages, 0);  // pisado por el hijo
}

void HarnessSpecTests::chain_cycleDoesNotHang()
{
    ProfileManager pm;
    const QString a = pm.addAgentProfile(QStringLiteral("A"));
    const QString b = pm.addAgentProfile(QStringLiteral("B"));
    HarnessSpec sa; sa.extends = b; sa.loop.set = true; sa.loop.credits = 5;
    HarnessSpec sb; sb.extends = a; sb.loop.set = true; sb.loop.credits = 6;
    QVERIFY(pm.setAgentProfileSpec(a, sa.toJson().toVariantMap()));
    QVERIFY(pm.setAgentProfileSpec(b, sb.toJson().toVariantMap()));
    // No cuelga y resuelve algo válido: el perfil degrada, no rompe el arranque.
    const HarnessSpec r = pm.resolveHarnessSpecById(a);
    QVERIFY(r.loop.credits == 5 || r.loop.credits == 6);
}

void HarnessSpecTests::packs_expandIncludeExcludeAndOrder()
{
    HarnessToolsModule m;
    m.set = true;
    m.packs = {QStringLiteral("core")};
    m.include = {QStringLiteral("web_fetch")};
    m.exclude = {QStringLiteral("run_shell")};
    const QStringList tools = HarnessTools::resolve(m);
    QVERIFY(tools.contains(QStringLiteral("read_file")));
    QVERIFY(tools.contains(QStringLiteral("web_fetch")));
    QVERIFY(!tools.contains(QStringLiteral("run_shell")));   // exclude gana

    // Orden estable = orden del catálogo (la UI y el diff dependen de esto).
    QStringList catalogOrder;
    for (const QVariant &v : LlamaAgentBackend::toolCatalog())
        catalogOrder << v.toMap().value(QStringLiteral("name")).toString();
    QStringList filtered;
    for (const QString &n : catalogOrder)
        if (tools.contains(n)) filtered << n;
    QCOMPARE(tools, filtered);

    // "*" y el pack "all" son equivalentes y cubren todo el catálogo.
    HarnessToolsModule star; star.set = true; star.include = {QStringLiteral("*")};
    QCOMPARE(HarnessTools::resolve(star).size(), catalogOrder.size());
    HarnessToolsModule all; all.set = true; all.packs = {QStringLiteral("all")};
    QCOMPARE(HarnessTools::resolve(all).size(), catalogOrder.size());
    QVERIFY(HarnessTools::disabledFrom(HarnessTools::resolve(all)).isEmpty());
}

void HarnessSpecTests::packs_budgetAndDependencyWarnings()
{
    const int oneTool = HarnessTools::approxTokens({QStringLiteral("read_file")});
    QVERIFY(oneTool > 0);
    const int two = HarnessTools::approxTokens(
        {QStringLiteral("read_file"), QStringLiteral("list_dir")});
    QVERIFY(two > oneTool);

    HarnessTools::Environment env;
    env.hasGit = false;
    env.hasEmbeddings = false;
    const QStringList warns = HarnessTools::dependencyWarnings(
        {QStringLiteral("task"), QStringLiteral("hybrid_search"), QStringLiteral("read_file")},
        env);
    QCOMPARE(warns.size(), 2);
    QVERIFY(warns.join(QLatin1Char(' ')).contains(QStringLiteral("task")));
    QVERIFY(warns.join(QLatin1Char(' ')).contains(QStringLiteral("hybrid_search")));

    // Entorno completo: sin advertencias para el mismo set.
    QVERIFY(HarnessTools::dependencyWarnings(
                {QStringLiteral("task"), QStringLiteral("hybrid_search")},
                HarnessTools::Environment{}).isEmpty());
}

// Un perfil no puede desactivar el guardrail Zero-Autonomy "de costado": sólo
// declarándose explícitamente en modo super.
void HarnessSpecTests::permissions_guardrailOnlyDroppableInSuper()
{
    QJsonObject sneaky{{QStringLiteral("approvalMode"), QStringLiteral("auto")},
                       {QStringLiteral("hitlDestructive"), false}};
    QVERIFY(HarnessPermissionsModule::fromJson(sneaky).hitlDestructive);

    QJsonObject superMode{{QStringLiteral("approvalMode"), QStringLiteral("super")},
                          {QStringLiteral("hitlDestructive"), false}};
    QVERIFY(!HarnessPermissionsModule::fromJson(superMode).hitlDestructive);
}

void HarnessSpecTests::permissions_scopeNeverWidens()
{
    using namespace HarnessPolicy;
    QCOMPARE(narrowerScope(QStringLiteral("full"), QStringLiteral("project")),
             QStringLiteral("project"));
    QCOMPARE(narrowerScope(QStringLiteral("folder"), QStringLiteral("full")),
             QStringLiteral("folder"));
    QCOMPARE(narrowerScope(QStringLiteral("project"), QStringLiteral("project")),
             QStringLiteral("project"));

    // Un perfil legacy (spec derivado) no declara alcance: no debe estrechar el
    // de una Task con permisos de carpeta o disco completo.
    AgentProfile legacy;
    legacy.id = QStringLiteral("l");
    QVERIFY(!legacy.toSpec().permissions.fsScopeDeclared);
    QJsonObject declared{{QStringLiteral("fsScope"), QStringLiteral("folder")}};
    QVERIFY(HarnessPermissionsModule::fromJson(declared).fsScopeDeclared);

    const QStringList a{QStringLiteral("C:/a"), QStringLiteral("C:/b")};
    const QStringList b{QStringLiteral("C:/b"), QStringLiteral("C:/c")};
    QCOMPARE(intersectFolders(QStringLiteral("folder"), a, QStringLiteral("folder"), b),
             QStringList{QStringLiteral("C:/b")});
    // "full" del otro lado no restringe: manda la lista concreta.
    QCOMPARE(intersectFolders(QStringLiteral("folder"), a, QStringLiteral("full"), {}), a);
}

void HarnessSpecTests::phases_patchOverridesResolvedSpec()
{
    HarnessSpec s;
    s.permissions.set = true;
    s.permissions.approvalMode = QStringLiteral("auto");
    s.tools.set = true;
    s.tools.packs = {QStringLiteral("core")};

    QJsonObject planPatch;
    QJsonObject perms;
    perms[QStringLiteral("approvalMode")] = QStringLiteral("plan");
    planPatch[QStringLiteral("permissions")] = perms;
    s.phases.insert(QStringLiteral("plan"), planPatch);

    const HarnessSpec plan = HarnessSpec::forPhase(s, QStringLiteral("plan"));
    QCOMPARE(plan.permissions.approvalMode, QStringLiteral("plan"));
    QCOMPARE(plan.tools.packs, QStringList{QStringLiteral("core")});  // no tocado

    // Fase sin override = el spec base, sin sorpresas.
    const HarnessSpec exec = HarnessSpec::forPhase(s, QStringLiteral("exec"));
    QCOMPARE(exec.permissions.approvalMode, QStringLiteral("auto"));
}

void HarnessSpecTests::diff_listsOnlyChangedFields()
{
    HarnessSpec base;
    HarnessSpec mine = base;
    mine.loop.sameCallLimit = 2;
    mine.context.keepLastImages = 0;

    const QVariantList d = mine.diff(base);
    QCOMPARE(d.size(), 2);
    QStringList fields;
    for (const QVariant &v : d) fields << v.toMap().value(QStringLiteral("field")).toString();
    QVERIFY(fields.contains(QStringLiteral("sameCallLimit")));
    QVERIFY(fields.contains(QStringLiteral("keepLastImages")));
    QVERIFY(base.diff(base).isEmpty());
}

void HarnessSpecTests::presets_minimalAndRpaExist()
{
    QMap<QString, AgentProfile> byId;
    for (const AgentProfile &p : AgentProfile::systemPresets()) byId.insert(p.id, p);
    QVERIFY(byId.contains(QStringLiteral("agent-minimal")));
    QVERIFY(byId.contains(QStringLiteral("agent-rpa")));

    const AgentProfile minimal = byId.value(QStringLiteral("agent-minimal"));
    QVERIFY(minimal.system);
    QVERIFY(!minimal.mcpEnabled);                  // local-first: MCP off
    const HarnessSpec ms = minimal.toSpec();
    QCOMPARE(ms.context.keepLastImages, 0);
    QCOMPARE(ms.loop.sameCallLimit, 2);
    QVERIFY(ms.prompt.maxChars <= 8000);

    const AgentProfile rpa = byId.value(QStringLiteral("agent-rpa"));
    const QStringList rpaTools = HarnessTools::resolve(rpa.toSpec().tools);
    QVERIFY(rpaTools.contains(QStringLiteral("desktop_click_element")));
    QVERIFY(rpaTools.contains(QStringLiteral("read_file")));
    QVERIFY(rpa.toSpec().permissions.hitlDestructive);
}

QTEST_MAIN(HarnessSpecTests)
#include "test_harness_spec.moc"
