// Unit tests de Perfiles de Agente:
//   - AgentProfile: serialización JSON ida/vuelta.
//   - systemPresets(): los 5 presets (Chat/Básico/Intermedio/Avanzado/Máximo), sus
//     ids estables, capas acumulativas de tools y el sentinel "*" de Máximo.
//   - LlamaAgentBackend::directiveCatalog() + setDirectives() → buildSystemPrompt
//     incluye/excluye cada sección (gating por directiva); default = todas.
//   - ProfileManager: CRUD + duplicado + persistencia de AgentProfile, presets de
//     sistema inmutables (aislado vía LLAMACODE_PROFILES_DIR).
//
// NOTA: storagePath cachea la raíz en un 'static' en la primera construcción de
// ProfileManager del proceso → el env var se setea en initTestCase.

#include <QtTest>
#include <QTemporaryDir>
#include <QJsonObject>
#include "core/profiles/ProfileTypes.h"
#include "core/profiles/ProfileManager.h"
#include "core/agent/LlamaAgentBackend.h"

class AgentProfilesTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();

    void agentProfile_jsonRoundTrip();
    void systemPresets_shape();
    void presets_levelsRestrictCapabilities();
    void directiveCatalog_hasAllKeys();
    void setDirectives_gatesSystemPrompt();
    void setDirectives_defaultIncludesAll();
    void honey_isOptInOnly();
    void antiBias_isOptInOnly();
    void mcpEnabled_roundTrips();
    void manager_crudAndPersistence();
    void manager_systemPresetsImmutable();

private:
    QTemporaryDir m_dir;
};

void AgentProfilesTests::initTestCase()
{
    QVERIFY(m_dir.isValid());
    qputenv("LLAMACODE_PROFILES_DIR", m_dir.path().toLocal8Bit());
}

void AgentProfilesTests::agentProfile_jsonRoundTrip()
{
    AgentProfile p;
    p.id = "ap1"; p.name = "Custom";
    p.enabledTools = QStringList{"read_file", "grep", "run_shell"};
    p.directives = QStringList{"discipline", "style"};
    p.approvalMode = "manual";
    p.thinking = true;
    p.temperature = 0.4;
    p.systemExtra = "sé conciso";
    const AgentProfile r = AgentProfile::fromJson(p.toJson());
    QCOMPARE(r.id, p.id);
    QCOMPARE(r.name, p.name);
    QCOMPARE(r.enabledTools, p.enabledTools);
    QCOMPARE(r.directives, p.directives);
    QCOMPARE(r.approvalMode, p.approvalMode);
    QCOMPARE(r.thinking, p.thinking);
    QCOMPARE(r.temperature, p.temperature);
    QCOMPARE(r.systemExtra, p.systemExtra);
}

void AgentProfilesTests::systemPresets_shape()
{
    const QList<AgentProfile> ps = AgentProfile::systemPresets();
    QCOMPARE(ps.size(), 5);

    // Orden: Chat liviano → Básico → Intermedio → Avanzado → Máximo.
    QCOMPARE(ps[0].id, QStringLiteral("agent-chat"));
    QCOMPARE(ps[1].id, QStringLiteral("agent-basico"));
    QCOMPARE(ps[2].id, QStringLiteral("agent-intermedio"));
    QCOMPARE(ps[3].id, QStringLiteral("agent-avanzado"));
    QCOMPARE(ps[4].id, QStringLiteral("agent-maximo"));
    QCOMPARE(AgentProfile::defaultPresetId(), QStringLiteral("agent-intermedio"));

    for (const AgentProfile &p : ps) QVERIFY(p.system);

    auto byId = [&](const QString &id) {
        for (const AgentProfile &p : ps) if (p.id == id) return p;
        return AgentProfile{};
    };
    const AgentProfile chat   = byId(QStringLiteral("agent-chat"));
    const AgentProfile basico = byId(QStringLiteral("agent-basico"));
    const AgentProfile inter  = byId(QStringLiteral("agent-intermedio"));
    const AgentProfile avanz  = byId(QStringLiteral("agent-avanzado"));
    const AgentProfile maximo = byId(QStringLiteral("agent-maximo"));

    // Chat liviano: set mínimo, SIN directivas y SIN MCP (presupuesto chico). Es el
    // único preset con mcpEnabled=false; todos los demás traen MCP (default true).
    QVERIFY(chat.enabledTools.contains(QStringLiteral("read_file")));
    QVERIFY(chat.enabledTools.contains(QStringLiteral("edit_file")));
    QVERIFY(chat.directives.isEmpty());
    QVERIFY(!chat.mcpEnabled);
    QVERIFY(chat.enabledTools.size() < basico.enabledTools.size());
    for (const AgentProfile &p : {basico, inter, avanz, maximo})
        QVERIFY2(p.mcpEnabled, qPrintable(p.id + " debería traer MCP"));

    // Básico: core de archivos/código, sin directivas.
    QVERIFY(basico.enabledTools.contains(QStringLiteral("read_file")));
    QVERIFY(basico.enabledTools.contains(QStringLiteral("run_shell")));
    QVERIFY(basico.directives.isEmpty());

    // Capas acumulativas: Intermedio ⊇ Básico; Avanzado ⊇ Intermedio.
    for (const QString &t : basico.enabledTools) QVERIFY(inter.enabledTools.contains(t));
    for (const QString &t : inter.enabledTools) QVERIFY(avanz.enabledTools.contains(t));
    QVERIFY(inter.directives.contains(QStringLiteral("discipline")));
    QVERIFY(avanz.directives.contains(QStringLiteral("testNet")));
    QVERIFY(avanz.thinking);

    // Máximo: sentinel "*" = todo el catálogo, super + thinking.
    QCOMPARE(maximo.enabledTools, QStringList{QStringLiteral("*")});
    QCOMPARE(maximo.directives, QStringList{QStringLiteral("*")});
    QCOMPARE(maximo.approvalMode, QStringLiteral("super"));
    QVERIFY(maximo.thinking);
}

// Garantía clave para el benchmark por NIVEL: distintos niveles = distintas
// capacidades, así una comparación a "Básico" está realmente más restringida que
// a "Máximo". Si un preset deja de restringir, la comparación deja de ser justa.
void AgentProfilesTests::presets_levelsRestrictCapabilities()
{
    const QList<AgentProfile> ps = AgentProfile::systemPresets();
    auto byId = [&](const QString &id) {
        for (const AgentProfile &p : ps) if (p.id == id) return p;
        return AgentProfile{};
    };
    const AgentProfile basico = byId(QStringLiteral("agent-basico"));
    const AgentProfile avanzado = byId(QStringLiteral("agent-avanzado"));
    const AgentProfile maximo = byId(QStringLiteral("agent-maximo"));

    // Básico NO trae web ni búsqueda avanzada (debe estar acotado).
    QVERIFY(!basico.enabledTools.contains(QStringLiteral("web_search")));
    QVERIFY(!basico.enabledTools.contains(QStringLiteral("hybrid_search")));
    QVERIFY(!basico.enabledTools.contains(QStringLiteral("*")));

    // Avanzado SÍ las trae → estrictamente más capaz que Básico.
    QVERIFY(avanzado.enabledTools.contains(QStringLiteral("web_search")));
    QVERIFY(avanzado.enabledTools.size() > basico.enabledTools.size());

    // Máximo = "*" (todo el catálogo): cubre cualquier tool built-in.
    QVERIFY(maximo.enabledTools.contains(QStringLiteral("*")));
    QVERIFY(!LlamaAgentBackend::toolCatalog().isEmpty());
}

void AgentProfilesTests::directiveCatalog_hasAllKeys()
{
    const QVariantList cat = LlamaAgentBackend::directiveCatalog();
    QStringList keys;
    for (const QVariant &v : cat) keys << v.toMap().value("key").toString();
    for (const QString &k : {"discipline", "testNet", "projectContext",
                             "efficiency", "style", "honey", "antiBias"})
        QVERIFY2(keys.contains(k), qPrintable("falta directiva " + k));
    // Cada item tiene name + description no vacíos (para la UI de toggles).
    for (const QVariant &v : cat) {
        const QVariantMap m = v.toMap();
        QVERIFY(!m.value("name").toString().isEmpty());
        QVERIFY(!m.value("description").toString().isEmpty());
    }
}

void AgentProfilesTests::setDirectives_gatesSystemPrompt()
{
    LlamaAgentBackend be;
    // Solo "discipline": presente; las otras secciones ausentes.
    be.setDirectives(QStringList{"discipline"});
    const QString only = be.systemPromptForTest();
    QVERIFY(only.contains(QStringLiteral("Blast radius"), Qt::CaseInsensitive));
    QVERIFY(!only.contains(QStringLiteral("RED DE TESTS")));        // testNet off
    QVERIFY(!only.contains(QStringLiteral("CONTEXTO DEL PROYECTO"))); // projectContext off
    QVERIFY(!only.contains(QStringLiteral("ESTILO:")));            // style off

    // Solo "style": presente; discipline ausente.
    be.setDirectives(QStringList{"style"});
    const QString styled = be.systemPromptForTest();
    QVERIFY(styled.contains(QStringLiteral("ESTILO:")));
    QVERIFY(!styled.contains(QStringLiteral("Blast radius"), Qt::CaseInsensitive));

    // Vacío: ninguna sección de directiva.
    be.setDirectives(QStringList{});
    const QString none = be.systemPromptForTest();
    QVERIFY(!none.contains(QStringLiteral("Blast radius"), Qt::CaseInsensitive));
    QVERIFY(!none.contains(QStringLiteral("RED DE TESTS")));
    QVERIFY(!none.contains(QStringLiteral("ESTILO:")));
}

void AgentProfilesTests::setDirectives_defaultIncludesAll()
{
    // Sin setDirectives() = comportamiento histórico: todas las secciones ON
    // (no regresiona los perfiles/usuarios que no aplican un perfil de agente).
    LlamaAgentBackend be;
    const QString sp = be.systemPromptForTest();
    QVERIFY(sp.contains(QStringLiteral("Blast radius"), Qt::CaseInsensitive));
    QVERIFY(sp.contains(QStringLiteral("RED DE TESTS")));
    QVERIFY(sp.contains(QStringLiteral("CONTEXTO DEL PROYECTO")));
    QVERIFY(sp.contains(QStringLiteral("ESTILO:")));
    QVERIFY(sp.contains(QStringLiteral("EFICIENCIA")));
}

// Honey (frugalidad) es opt-in PURO: a diferencia del resto, NO se incluye en el
// default "todas las directivas on" (sin setDirectives). Es agresiva y en modelos
// chicos locales puede recortar el razonamiento, así que sólo aparece si el perfil
// la elige explícitamente.
void AgentProfilesTests::honey_isOptInOnly()
{
    LlamaAgentBackend be;
    // Default (sin setDirectives): NINGUNA sección Honey, aunque el resto esté on.
    QVERIFY(!be.systemPromptForTest().contains(QStringLiteral("FRUGALIDAD (Honey)")));

    // Catálogo completo explícito tampoco la trae si no se nombra honey.
    be.setDirectives(QStringList{"discipline", "testNet", "projectContext",
                                 "efficiency", "style"});
    QVERIFY(!be.systemPromptForTest().contains(QStringLiteral("FRUGALIDAD (Honey)")));

    // El sentinel "*" (preset Máximo = todo el catálogo) TAMPOCO la trae: honey
    // se nombra o no está. Garantiza que ningún preset de sistema la incluya.
    be.setDirectives(QStringList{"*"});
    QVERIFY(!be.systemPromptForTest().contains(QStringLiteral("FRUGALIDAD (Honey)")));

    // Elegida explícitamente: presente.
    be.setDirectives(QStringList{"honey"});
    QVERIFY(be.systemPromptForTest().contains(QStringLiteral("FRUGALIDAD (Honey)")));
}

// Anti-sesgo es opt-in PURO como honey: endurece el razonamiento pero alarga el
// prompt y en modelos chicos puede inducir trap-paranoia, así que NO entra en el
// default "todas on" ni en el sentinel "*"; sólo si el perfil la nombra.
void AgentProfilesTests::antiBias_isOptInOnly()
{
    LlamaAgentBackend be;
    // Default (sin setDirectives): ausente, aunque el resto esté on.
    QVERIFY(!be.systemPromptForTest().contains(QStringLiteral("ANTI-SESGO")));

    // Catálogo completo explícito sin nombrarla: ausente.
    be.setDirectives(QStringList{"discipline", "testNet", "projectContext",
                                 "efficiency", "style"});
    QVERIFY(!be.systemPromptForTest().contains(QStringLiteral("ANTI-SESGO")));

    // Sentinel "*" (preset Máximo): tampoco la trae.
    be.setDirectives(QStringList{"*"});
    QVERIFY(!be.systemPromptForTest().contains(QStringLiteral("ANTI-SESGO")));

    // Elegida explícitamente: presente.
    be.setDirectives(QStringList{"antiBias"});
    QVERIFY(be.systemPromptForTest().contains(QStringLiteral("ANTI-SESGO")));
}

// mcpEnabled persiste por JSON y default es true para perfiles legacy (sin la
// clave) → no regresiona perfiles guardados antes de la feature.
void AgentProfilesTests::mcpEnabled_roundTrips()
{
    AgentProfile p;
    p.id = QStringLiteral("x"); p.name = QStringLiteral("X");
    p.mcpEnabled = false;
    const AgentProfile back = AgentProfile::fromJson(p.toJson());
    QVERIFY(!back.mcpEnabled);

    AgentProfile q;
    q.mcpEnabled = true;
    QVERIFY(AgentProfile::fromJson(q.toJson()).mcpEnabled);

    // Legacy: JSON sin la clave mcpEnabled → default true (MCP on, histórico).
    QJsonObject legacy{{"id", "y"}, {"name", "Y"}};
    QVERIFY(AgentProfile::fromJson(legacy).mcpEnabled);
}

void AgentProfilesTests::manager_crudAndPersistence()
{
    QString newId;
    {
        ProfileManager pm;
        newId = pm.addAgentProfile(QStringLiteral("Mi perfil"));
        QVERIFY(!newId.isEmpty());

        // Editar: tools/directivas/ajustes.
        QVariantMap upd{
            {"id", newId},
            {"name", "Mi perfil v2"},
            {"enabledTools", QStringList{"read_file", "grep"}},
            {"directives", QStringList{"discipline", "testNet"}},
            {"approvalMode", "manual"},
            {"thinking", true},
            {"temperature", 0.3},
            {"systemExtra", "extra"}};
        QVERIFY(pm.updateAgentProfile(upd));

        const QVariantMap got = pm.getAgentProfile(newId);
        QCOMPARE(got.value("name").toString(), QStringLiteral("Mi perfil v2"));
        QCOMPARE(got.value("enabledTools").toStringList(), (QStringList{"read_file", "grep"}));
        QCOMPARE(got.value("directives").toStringList(), (QStringList{"discipline", "testNet"}));
        QCOMPARE(got.value("approvalMode").toString(), QStringLiteral("manual"));
        QVERIFY(got.value("thinking").toBool());

        // Duplicar.
        const QString dupId = pm.duplicateAgentProfile(newId);
        QVERIFY(!dupId.isEmpty() && dupId != newId);
        QVERIFY(pm.getAgentProfile(dupId).value("name").toString().contains("copia"));
    }
    // Persistencia entre instancias.
    {
        ProfileManager pm2;
        const QVariantMap got = pm2.getAgentProfile(newId);
        QCOMPARE(got.value("name").toString(), QStringLiteral("Mi perfil v2"));
        QVERIFY(pm2.removeAgentProfile(newId));
        QVERIFY(pm2.getAgentProfile(newId).isEmpty());
    }
}

void AgentProfilesTests::manager_systemPresetsImmutable()
{
    ProfileManager pm;
    // Los 4 presets de sistema están presentes y son solo lectura.
    QVERIFY(pm.isSystemAgentProfile(QStringLiteral("agent-basico")));
    QVERIFY(pm.isSystemAgentProfile(QStringLiteral("agent-maximo")));
    QVERIFY(!pm.getAgentProfile(QStringLiteral("agent-intermedio")).isEmpty());

    // No se pueden editar ni borrar.
    QVERIFY(!pm.updateAgentProfile(QVariantMap{{"id", "agent-basico"}, {"name", "hack"}}));
    QVERIFY(!pm.removeAgentProfile(QStringLiteral("agent-basico")));
    QCOMPARE(pm.getAgentProfile(QStringLiteral("agent-basico")).value("name").toString(),
             QStringLiteral("Básico"));

    // Duplicar un preset de sistema produce una copia EDITABLE de usuario.
    const QString dupId = pm.duplicateAgentProfile(QStringLiteral("agent-avanzado"));
    QVERIFY(!dupId.isEmpty());
    QVERIFY(!pm.isSystemAgentProfile(dupId));
    QVERIFY(pm.updateAgentProfile(QVariantMap{{"id", dupId}, {"name", "editable"}}));
}

QTEST_MAIN(AgentProfilesTests)
#include "test_agent_profiles.moc"
