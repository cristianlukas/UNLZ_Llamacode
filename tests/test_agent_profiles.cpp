// Unit tests de Perfiles de Agente:
//   - AgentProfile: serialización JSON ida/vuelta.
//   - systemPresets(): los 4 presets (Básico/Intermedio/Avanzado/Máximo), sus
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
    void directiveCatalog_hasAllKeys();
    void setDirectives_gatesSystemPrompt();
    void setDirectives_defaultIncludesAll();
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
    QCOMPARE(ps.size(), 4);

    // ids estables y orden Básico → Intermedio → Avanzado → Máximo.
    QCOMPARE(ps[0].id, QStringLiteral("agent-basico"));
    QCOMPARE(ps[1].id, QStringLiteral("agent-intermedio"));
    QCOMPARE(ps[2].id, QStringLiteral("agent-avanzado"));
    QCOMPARE(ps[3].id, QStringLiteral("agent-maximo"));
    QCOMPARE(AgentProfile::defaultPresetId(), QStringLiteral("agent-intermedio"));

    for (const AgentProfile &p : ps) QVERIFY(p.system);

    // Básico: core de archivos/código, sin directivas.
    QVERIFY(ps[0].enabledTools.contains(QStringLiteral("read_file")));
    QVERIFY(ps[0].enabledTools.contains(QStringLiteral("run_shell")));
    QVERIFY(ps[0].directives.isEmpty());

    // Capas acumulativas: Intermedio ⊇ Básico; Avanzado ⊇ Intermedio.
    for (const QString &t : ps[0].enabledTools) QVERIFY(ps[1].enabledTools.contains(t));
    for (const QString &t : ps[1].enabledTools) QVERIFY(ps[2].enabledTools.contains(t));
    QVERIFY(ps[1].directives.contains(QStringLiteral("discipline")));
    QVERIFY(ps[2].directives.contains(QStringLiteral("testNet")));
    QVERIFY(ps[2].thinking);

    // Máximo: sentinel "*" = todo el catálogo, super + thinking.
    QCOMPARE(ps[3].enabledTools, QStringList{QStringLiteral("*")});
    QCOMPARE(ps[3].directives, QStringList{QStringLiteral("*")});
    QCOMPARE(ps[3].approvalMode, QStringLiteral("super"));
    QVERIFY(ps[3].thinking);
}

void AgentProfilesTests::directiveCatalog_hasAllKeys()
{
    const QVariantList cat = LlamaAgentBackend::directiveCatalog();
    QStringList keys;
    for (const QVariant &v : cat) keys << v.toMap().value("key").toString();
    for (const QString &k : {"discipline", "testNet", "projectContext",
                             "efficiency", "style"})
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
