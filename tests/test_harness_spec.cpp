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
#include <QJsonArray>
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
    void context_indexPolicyRoundTripsAndBounds();
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
    void phases_canOverridePromptDirectives();
    void phases_canOverrideTemperatureAndExtra();
    void escalation_masterChainAndRouterThresholds();
    void diff_listsOnlyChangedFields();
    void memoryAndChat_defaultsAndInheritance();
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

void HarnessSpecTests::context_indexPolicyRoundTripsAndBounds()
{
    HarnessContextModule context;
    context.indexPolicy = QStringLiteral("eager");
    context.scoutBudget = 1200;
    context.scoutK = 12;
    context.graphExpansion = false;

    const HarnessContextModule roundTrip =
        HarnessContextModule::fromJson(context.toJson());
    QCOMPARE(roundTrip.indexPolicy, QStringLiteral("eager"));
    QCOMPARE(roundTrip.scoutBudget, 1200);
    QCOMPARE(roundTrip.scoutK, 12);
    QVERIFY(!roundTrip.graphExpansion);

    QJsonObject invalid{{QStringLiteral("indexPolicy"), QStringLiteral("unknown")},
                        {QStringLiteral("scoutBudget"), 999999},
                        {QStringLiteral("scoutK"), -4}};
    const HarnessContextModule bounded = HarnessContextModule::fromJson(invalid);
    QCOMPARE(bounded.indexPolicy, QStringLiteral("lazy"));
    QCOMPARE(bounded.scoutBudget, 16000);
    QCOMPARE(bounded.scoutK, 1);
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

// Una fase puede pisar las directivas built-in: es lo que permite que "plan"
// entregue un prompt distinto al de "exec" sin duplicar el perfil.
void HarnessSpecTests::phases_canOverridePromptDirectives()
{
    HarnessSpec s;
    s.prompt.set = true;
    s.prompt.builtin = {QStringLiteral("discipline"), QStringLiteral("testNet")};

    QJsonObject promptPatch;
    promptPatch[QStringLiteral("builtin")] =
        QJsonArray{QStringLiteral("efficiency")};
    QJsonObject patch;
    patch[QStringLiteral("prompt")] = promptPatch;
    s.phases.insert(QStringLiteral("plan"), patch);

    const HarnessSpec plan = HarnessSpec::forPhase(s, QStringLiteral("plan"));
    QCOMPARE(plan.prompt.builtin, QStringList{QStringLiteral("efficiency")});
    // El spec base no se toca: la fase es una vista, no una mutación.
    QCOMPARE(s.prompt.builtin.size(), 2);
}

// Temperatura e instrucciones extra por fase: una fase de verificacion puede
// querer temperatura 0 sin duplicar el perfil entero.
void HarnessSpecTests::phases_canOverrideTemperatureAndExtra()
{
    HarnessSpec s;
    s.protocol.set = true;
    s.protocol.temperature = 0.7;
    s.prompt.set = true;
    s.prompt.systemExtra = QStringLiteral("base");

    QJsonObject proto;
    proto[QStringLiteral("temperature")] = 0.0;
    QJsonObject prompt;
    prompt[QStringLiteral("systemExtra")] = QStringLiteral("verificá con evidencia");
    QJsonObject patch;
    patch[QStringLiteral("protocol")] = proto;
    patch[QStringLiteral("prompt")] = prompt;
    s.phases.insert(QStringLiteral("verify"), patch);

    const HarnessSpec verify = HarnessSpec::forPhase(s, QStringLiteral("verify"));
    QCOMPARE(verify.protocol.temperature, 0.0);
    QCOMPARE(verify.prompt.systemExtra, QStringLiteral("verificá con evidencia"));
    QCOMPARE(s.protocol.temperature, 0.7);   // el spec base no se muta
}

// La cadena de maestros y los umbrales del router viajan en el spec: son lo que
// hace que "escalation" sea un módulo y no sólo dos flags.
void HarnessSpecTests::escalation_masterChainAndRouterThresholds()
{
    QJsonObject esc;
    esc[QStringLiteral("routerFilesAffected")] = 3;
    esc[QStringLiteral("routerContextTokens")] = 9000;
    esc[QStringLiteral("masterEscalation")] = QStringLiteral("auto");
    esc[QStringLiteral("masterAutoAfterFails")] = 2;
    QJsonArray chain;
    chain.append(QJsonObject{{QStringLiteral("type"), QStringLiteral("cli")},
                             {QStringLiteral("cliName"), QStringLiteral("claude")}});
    esc[QStringLiteral("masterFallbacks")] = chain;

    const HarnessEscalationModule m = HarnessEscalationModule::fromJson(esc);
    QCOMPARE(m.routerFilesAffected, 3);
    QCOMPARE(m.routerContextTokens, 9000);
    QCOMPARE(m.masterEscalation, QStringLiteral("auto"));
    QCOMPARE(m.masterAutoAfterFails, 2);
    QCOMPARE(m.masterFallbacks.size(), 1);
    QCOMPARE(m.masterFallbacks.first().toObject().value(QStringLiteral("cliName")).toString(),
             QStringLiteral("claude"));

    // Round-trip: la cadena sobrevive a guardar/cargar el perfil.
    const HarnessEscalationModule back = HarnessEscalationModule::fromJson(m.toJson());
    QCOMPARE(back.masterFallbacks.size(), 1);
    // Sin cadena declarada no se serializa la clave: el LaunchProfile sigue mandando.
    QVERIFY(!HarnessEscalationModule().toJson().contains(QStringLiteral("masterFallbacks")));
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

// Los modulos nuevos (memoria/RAG y modo Chat) siguen las MISMAS reglas que el
// resto: defaults iguales al comportamiento historico y herencia por modulo.
void HarnessSpecTests::memoryAndChat_defaultsAndInheritance()
{
    const HarnessSpec def;
    // Defaults = lo que estaba hardcodeado en buildSystemPrompt.
    QVERIFY(def.memory.structuredEnabled);
    QCOMPARE(def.memory.structuredFacts, 12);
    QVERIFY(def.memory.projectMemory);
    QCOMPARE(def.memory.projectMemoryMaxChars, 64 * 1024);
    QVERIFY(def.memory.consolidateOnLeave);
    QVERIFY(!def.chat.thinking);
    QCOMPARE(def.chat.temperature, -1.0);
    QVERIFY(def.chat.systemExtra.isEmpty());
    QVERIFY(def.isEmpty());          // declarar nada sigue siendo "spec vacio"

    // Round-trip: sin declarar, los modulos no viajan al JSON.
    HarnessSpec s;
    s.memory.set = true;
    s.memory.structuredFacts = 3;
    s.memory.projectMemory = false;
    s.chat.set = true;
    s.chat.systemExtra = QStringLiteral("respondé en una línea");
    s.chat.temperature = 0.2;
    const QJsonObject json = s.toJson();
    QVERIFY(json.contains(QStringLiteral("memory")));
    QVERIFY(json.contains(QStringLiteral("chat")));
    QVERIFY(!json.contains(QStringLiteral("tools")));

    const HarnessSpec back = HarnessSpec::fromJson(json);
    QCOMPARE(back.memory.structuredFacts, 3);
    QVERIFY(!back.memory.projectMemory);
    QCOMPARE(back.chat.systemExtra, QStringLiteral("respondé en una línea"));
    QCOMPARE(back.chat.temperature, 0.2);

    // Herencia por modulo: el hijo que declara `chat` no toca `memory`.
    HarnessSpec child;
    child.chat.set = true;
    child.chat.thinking = true;
    const HarnessSpec r = HarnessSpec::resolve(s, child);
    QCOMPARE(r.memory.structuredFacts, 3);        // heredado
    QVERIFY(r.chat.thinking);                     // pisado
    QVERIFY(r.chat.systemExtra.isEmpty());        // el modulo se reemplaza entero

    // El diff los reporta como cualquier otro modulo.
    QVariantList d = s.diff(HarnessSpec());
    QStringList mods;
    for (const QVariant &v : d) mods << v.toMap().value(QStringLiteral("module")).toString();
    QVERIFY(mods.contains(QStringLiteral("memory")));
    QVERIFY(mods.contains(QStringLiteral("chat")));
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
