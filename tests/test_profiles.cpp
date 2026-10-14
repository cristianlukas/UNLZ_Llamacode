// Unit tests de perfiles:
//   - ProfileTypes: serialización JSON ida/vuelta de cada struct de perfil.
//   - ProfileManager: CRUD de backends/modelProfiles/runtimes/harness/launch,
//     getters, favoritos/alias y persistencia a disco (aislada vía
//     LLAMACODE_PROFILES_DIR).
//
// NOTA: ProfileManager::storagePath cachea la raíz en un 'static' la primera
// vez que se llama, así que el env var DEBE setearse antes de construir el
// primer ProfileManager del proceso (lo hacemos en initTestCase).

#include <QtTest>
#include <QTemporaryDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QFileInfo>
#include <QDir>
#include <QDateTime>
#include <algorithm>
#include "core/profiles/ProfileTypes.h"
#include "core/profiles/ProfileManager.h"
#include "core/profiles/ManagedServerCapabilities.h"
#include "core/profiles/PortablePaths.h"

class ProfilesTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();

    void strataVisionCapabilityRequiresConfiguredExistingAssets();
    void strataUsesFixedConfigOutsideLlamaMemoryLadder();

    void backendProfile_jsonRoundTrip();
    void modelProfile_jsonRoundTrip();
    void runtimePreset_jsonRoundTrip();
    void launchProfile_jsonRoundTrip();
    void solLinuxProfileUsesVllmBackend();
    void agentProfile_thinkingLeakGuardRoundTripAndDefault();
    void masterConfig_jsonRoundTrip();
    void masterConfig_legacyMigration();

    void manager_addGetRemoveBackend();
    void manager_updateBackendPort();
    void manager_setBackendCloud();
    void manager_addModelProfile();
    void manager_favoriteAndAlias();
    void manager_menuOrderPrecedesRecentUsage();
    void manager_benchmarkQueue();
    void manager_profileSearchFiltersNameAliasAndId();
    void manager_tagsAndLastUsed();
    void manager_profileTemplatesRoundTrip();
    void manager_harnessArgsEnvRoundTrip();
    void manager_reasoningControlsRoundTrip();
    void manager_deprecatedIsProfilesOnly();
    void manager_browserAutomationOverride();
    void manager_systemProfilesReloadIdempotent();
    void manager_persistsAcrossInstances();
    void portablePaths_roundTripIsStable();
    void portablePaths_repairsAccumulatedSlashes();
    void portablePaths_respectsRootBoundaries();
    void manager_sharedConfigSaveDoesNotGrowSlashes();
    void manager_exportImportBundle();
    void manager_profileChangeHistory();
    void manager_saveSkipsUnchangedAndLogsOnlyChanges();

private:
    QTemporaryDir m_dir;
};

void ProfilesTests::initTestCase()
{
    QVERIFY(m_dir.isValid());
    qputenv("LLAMACODE_PROFILES_DIR", m_dir.path().toLocal8Bit());
}

void ProfilesTests::backendProfile_jsonRoundTrip()
{
    BackendProfile b;
    b.id = "b1"; b.name = "cuda-8080"; b.binaryId = "bin1";
    b.host = "0.0.0.0"; b.port = 9090;
    b.baseArgs = QStringList{"--ctx", "8192"};
    b.envOverrides.insert("CUDA_VISIBLE_DEVICES", "0");
    const BackendProfile r = BackendProfile::fromJson(b.toJson());
    QCOMPARE(r.id, b.id);
    QCOMPARE(r.name, b.name);
    QCOMPARE(r.binaryId, b.binaryId);
    QCOMPARE(r.host, b.host);
    QCOMPARE(r.port, b.port);
    QCOMPARE(r.baseArgs, b.baseArgs);
    QCOMPARE(r.envOverrides.value("CUDA_VISIBLE_DEVICES"), QStringLiteral("0"));
    // default kind = local, sin campos cloud
    QCOMPARE(r.kind, QStringLiteral("local"));
    QVERIFY(!r.isCloud());

    // provider cloud round-trip
    BackendProfile c;
    c.id = "c1"; c.kind = "cloud";
    c.cloudBaseUrl = "https://api.openai.com";
    c.cloudKeyRef = "OPENAI_API_KEY"; c.cloudModel = "gpt-4o"; c.cloudCtx = 16384;
    c.managedServer = QJsonObject{{"type", "docker-compose"},
                                  {"composeFiles", QJsonArray{
                                       "~/models/compose.yml", "~/models/override.yml"}},
                                  {"project", "sol"}, {"service", "vllm"}};
    const QJsonObject cj = c.toJson();
    // El secreto NUNCA se serializa: sólo la referencia (nombre).
    QVERIFY(!cj.contains("cloudApiKey"));
    QCOMPARE(cj.value("cloudKeyRef").toString(), QStringLiteral("OPENAI_API_KEY"));
    const BackendProfile rc = BackendProfile::fromJson(cj);
    QVERIFY(rc.isCloud());
    QCOMPARE(rc.cloudBaseUrl, c.cloudBaseUrl);
    QCOMPARE(rc.cloudKeyRef, c.cloudKeyRef);
    QCOMPARE(rc.cloudModel, c.cloudModel);
    QCOMPARE(rc.cloudCtx, 16384);
    QCOMPARE(rc.managedServer, c.managedServer);
}

void ProfilesTests::modelProfile_jsonRoundTrip()
{
    ModelProfile m;
    m.id = "m1"; m.name = "qwen"; m.modelId = "cat1";
    m.mmprojId = "mm1"; m.draftModelId = "d1";
    m.specType = "draft-dspark"; m.specDraftNMax = 3; m.specDraftNMin = 2;
    m.specDraftAdaptive = true; m.specDraftConfMin = 0.6;
    m.specDraftNgl = "all";
    m.specDraftTypeK = "q8_0"; m.specDraftTypeV = "q8_0";
    const ModelProfile r = ModelProfile::fromJson(m.toJson());
    QCOMPARE(r.name, m.name);
    QCOMPARE(r.modelId, m.modelId);
    QCOMPARE(r.mmprojId, m.mmprojId);
    QCOMPARE(r.draftModelId, m.draftModelId);
    QCOMPARE(r.specType, m.specType);
    QCOMPARE(r.specDraftNMax, m.specDraftNMax);
    QCOMPARE(r.specDraftNMin, m.specDraftNMin);
    QCOMPARE(r.specDraftAdaptive, m.specDraftAdaptive);
    QCOMPARE(r.specDraftConfMin, m.specDraftConfMin);
    QCOMPARE(r.specDraftNgl, m.specDraftNgl);
    QCOMPARE(r.specDraftTypeK, m.specDraftTypeK);
    QCOMPARE(r.specDraftTypeV, m.specDraftTypeV);

    // Perfiles anteriores no tienen los campos nuevos y deben seguir siendo
    // speculative fijo, sin activar adaptive por defecto.
    const ModelProfile legacy = ModelProfile::fromJson(QJsonObject{
        {QStringLiteral("specType"), QStringLiteral("draft-mtp")},
        {QStringLiteral("specDraftNMax"), 3}
    });
    QCOMPARE(legacy.specDraftNMin, 0);
    QVERIFY(!legacy.specDraftAdaptive);
}

void ProfilesTests::runtimePreset_jsonRoundTrip()
{
    RuntimePreset p;
    p.id = "r1"; p.name = "fast"; p.ctx = 16384; p.batch = 1024; p.ubatch = 256;
    p.threads = 8; p.gpuLayers = 99; p.flashAttention = true; p.mmap = false;
    p.mlock = true; p.contBatching = false; p.cacheType = "q8_0"; p.parallelSlots = 4;
    const RuntimePreset r = RuntimePreset::fromJson(p.toJson());
    QCOMPARE(r.ctx, p.ctx);
    QCOMPARE(r.batch, p.batch);
    QCOMPARE(r.ubatch, p.ubatch);
    QCOMPARE(r.threads, p.threads);
    QCOMPARE(r.gpuLayers, p.gpuLayers);
    QCOMPARE(r.flashAttention, p.flashAttention);
    QCOMPARE(r.mmap, p.mmap);
    QCOMPARE(r.mlock, p.mlock);
    QCOMPARE(r.contBatching, p.contBatching);
    QCOMPARE(r.cacheType, p.cacheType);
    QCOMPARE(r.parallelSlots, p.parallelSlots);
}

void ProfilesTests::launchProfile_jsonRoundTrip()
{
    LaunchProfile l;
    l.id = "l1"; l.name = "prod"; l.alias = "P"; l.best = true; l.favorite = true;
    l.systemBadge = true; l.benchmark = true; l.deprecated = true;
    l.backendProfileId = "b1"; l.modelProfileId = "m1"; l.runtimePresetId = "r1";
    l.extraArgs = QStringList{"--verbose"};
    l.chatTemplate = QStringLiteral("ling3-tools.jinja");
    l.platformArgs.insert(QStringLiteral("linux"), QStringList{"--moe-expert-cache", "188"});
    l.platformArgs.insert(QStringLiteral("windows"), QStringList{"--n-cpu-moe", "36"});
    l.platformBackendIds.insert(QStringLiteral("linux"), QStringLiteral("cuda-linux"));
    l.platformBackendIds.insert(QStringLiteral("windows"), QStringLiteral("windows-cuda"));
    l.platformModelProfileIds.insert(QStringLiteral("linux"), QStringLiteral("model-linux"));
    l.platformModelProfileIds.insert(QStringLiteral("windows"), QStringLiteral("model-windows"));
    MasterFallback mf; mf.type = "cli"; mf.cliName = "claude";
    l.master.fallbacks.append(mf);
    l.powerLimitW = 280;
    l.browserAutomation = "on";
    l.tags = QStringList{"coding", "local"};
    l.lastUsed = 123456789;
    l.plannerProfileId = "planner-maxq";
    l.hybridMode = "sequential";
    const LaunchProfile r = LaunchProfile::fromJson(l.toJson());
    QCOMPARE(r.browserAutomation, QStringLiteral("on"));
    QCOMPARE(r.name, l.name);
    QCOMPARE(r.alias, l.alias);
    QCOMPARE(r.best, l.best);
    QCOMPARE(r.favorite, l.favorite);
    QCOMPARE(r.systemBadge, l.systemBadge);
    QCOMPARE(r.benchmark, l.benchmark);
    QCOMPARE(r.deprecated, l.deprecated);
    QCOMPARE(r.backendProfileId, l.backendProfileId);
    QCOMPARE(r.modelProfileId, l.modelProfileId);
    QCOMPARE(r.extraArgs, l.extraArgs);
    QCOMPARE(r.chatTemplate, l.chatTemplate);
    QCOMPARE(r.platformArgs, l.platformArgs);
    QCOMPARE(r.platformBackendIds, l.platformBackendIds);
    QCOMPARE(r.platformModelProfileIds, l.platformModelProfileIds);
    QCOMPARE(r.master.fallbacks.size(), 1);
    QCOMPARE(r.master.fallbacks.first().type, QStringLiteral("cli"));
    QCOMPARE(r.master.fallbacks.first().cliName, QStringLiteral("claude"));
    QCOMPARE(r.powerLimitW, 280);
    QCOMPARE(r.plannerProfileId, QStringLiteral("planner-maxq"));
    QCOMPARE(r.hybridMode, QStringLiteral("sequential"));
    QCOMPARE(r.tags, l.tags);
    QCOMPARE(r.lastUsed, l.lastUsed);
    QCOMPARE(r.menuOrder, l.menuOrder);
    // Default (campo ausente) → 0 = sin override.
    LaunchProfile empty;
    QCOMPARE(LaunchProfile::fromJson(empty.toJson()).powerLimitW, 0);
    // browserAutomation ausente → default "inherit".
    QCOMPARE(LaunchProfile::fromJson(empty.toJson()).browserAutomation,
             QStringLiteral("inherit"));
    QCOMPARE(LaunchProfile::fromJson(QJsonObject{}).hybridMode,
             QStringLiteral("off"));
}

void ProfilesTests::strataVisionCapabilityRequiresConfiguredExistingAssets()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());
    QVERIFY(QDir().mkpath(root.filePath(QStringLiteral("engine"))));
    QVERIFY(QDir().mkpath(root.filePath(QStringLiteral("models"))));

    auto touch = [](const QString &path) {
        QFile file(path);
        return file.open(QIODevice::WriteOnly) && file.write("x") == 1;
    };
    QVERIFY(touch(root.filePath(QStringLiteral("engine/strata-vision"))));
    QVERIFY(touch(root.filePath(QStringLiteral("models/mmproj.gguf"))));

    const QString configPath = root.filePath(QStringLiteral("strata.json"));
    auto writeConfig = [&](const QJsonObject &object) {
        QFile file(configPath);
        if (!file.open(QIODevice::WriteOnly)) return false;
        return file.write(QJsonDocument(object).toJson()) > 0;
    };

    const QJsonObject vision{
        {QStringLiteral("exe"), QStringLiteral("engine/strata-vision")},
        {QStringLiteral("mmproj"), QStringLiteral("models/mmproj.gguf")}
    };
    QVERIFY(writeConfig(QJsonObject{
        {QStringLiteral("args"), QJsonArray{QStringLiteral("--vision")}},
        {QStringLiteral("vision"), vision}
    }));
    QVERIFY(ManagedServerCapabilities::strataVisionAvailable(configPath, root.path()));

    QVERIFY(writeConfig(QJsonObject{
        {QStringLiteral("args"), QJsonArray{}},
        {QStringLiteral("vision"), vision}
    }));
    QVERIFY(!ManagedServerCapabilities::strataVisionAvailable(configPath, root.path()));

    QVERIFY(writeConfig(QJsonObject{
        {QStringLiteral("args"), QJsonArray{QStringLiteral("--vision")}},
        {QStringLiteral("vision"), QJsonObject{
            {QStringLiteral("exe"), QStringLiteral("engine/strata-vision")},
            {QStringLiteral("mmproj"), QStringLiteral("models/missing.gguf")}
        }}
    }));
    QVERIFY(!ManagedServerCapabilities::strataVisionAvailable(configPath, root.path()));
}

void ProfilesTests::strataUsesFixedConfigOutsideLlamaMemoryLadder()
{
    BackendProfile backend;
    backend.managedServer.insert(QStringLiteral("type"), QStringLiteral("astra-strata"));
    QVERIFY(!ManagedServerCapabilities::supportsAdaptiveLlamaMemoryPolicy(backend));

    backend.managedServer.insert(QStringLiteral("type"), QStringLiteral("llama-cpp"));
    QVERIFY(ManagedServerCapabilities::supportsAdaptiveLlamaMemoryPolicy(backend));

    backend.managedServer = QJsonObject{};
    QVERIFY(ManagedServerCapabilities::supportsAdaptiveLlamaMemoryPolicy(backend));
}

void ProfilesTests::solLinuxProfileUsesVllmBackend()
{
    QFile file(QStringLiteral("profiles/launches.json"));
    QVERIFY2(file.open(QIODevice::ReadOnly), qPrintable(file.errorString()));
    const QJsonArray profiles = QJsonDocument::fromJson(file.readAll()).array();
    const QString solId = QStringLiteral("c8d4f1a7-2b69-4e80-95c3-7a1d6f8b2045");
    const QString vllmBackendId = QStringLiteral("2baf3292-033d-4a6c-9f84-ea13ae4aae3b");
    for (const QJsonValue &value : profiles) {
        const QJsonObject profile = value.toObject();
        if (profile.value(QStringLiteral("id")).toString() != solId)
            continue;

        QCOMPARE(profile.value(QStringLiteral("platformBackendIds")).toObject()
                     .value(QStringLiteral("linux")).toString(), vllmBackendId);
        return;
    }
    QFAIL("The SOL launch profile is missing from profiles/launches.json.");
}

void ProfilesTests::agentProfile_thinkingLeakGuardRoundTripAndDefault()
{
    AgentProfile profile;
    profile.id = QStringLiteral("nanbeige-agent");
    profile.name = QStringLiteral("Nanbeige compat");
    profile.thinkingLeakGuard = true;
    const AgentProfile restored = AgentProfile::fromJson(profile.toJson());
    QVERIFY(restored.thinkingLeakGuard);

    // Perfiles viejos y perfiles nuevos sin opt-in conservan el comportamiento
    // estándar del template/modelo.
    QVERIFY(!AgentProfile::fromJson(QJsonObject{}).thinkingLeakGuard);
    for (const AgentProfile &preset : AgentProfile::systemPresets())
        QVERIFY(!preset.thinkingLeakGuard);
}

void ProfilesTests::masterConfig_jsonRoundTrip()
{
    MasterConfig m;
    m.escalation = "auto"; m.autoAfterFails = 5;
    // Cadena de 3 fallbacks ordenados: http → profile → cli.
    MasterFallback f1; f1.type = "http"; f1.label = "GPT";
    f1.httpUrl = "https://api.openai.com"; f1.httpModel = "gpt-4o";
    f1.httpKeyRef = "master/openai"; f1.timeoutSec = 600;
    MasterFallback f2; f2.type = "profile"; f2.profileId = "lp-big"; f2.label = "Cloud profile";
    MasterFallback f3; f3.type = "cli"; f3.cliName = "claude"; f3.applyEdits = false;
    m.fallbacks << f1 << f2 << f3;
    QVERIFY(m.isConfigured());

    const MasterConfig r = MasterConfig::fromJson(m.toJson());
    QCOMPARE(r.escalation, QStringLiteral("auto"));
    QCOMPARE(r.autoAfterFails, 5);
    QCOMPARE(r.fallbacks.size(), 3);
    // Orden preservado.
    QCOMPARE(r.fallbacks[0].type, QStringLiteral("http"));
    QCOMPARE(r.fallbacks[0].httpKeyRef, QStringLiteral("master/openai"));
    QCOMPARE(r.fallbacks[0].timeoutSec, 600);
    QCOMPARE(r.fallbacks[1].type, QStringLiteral("profile"));
    QCOMPARE(r.fallbacks[1].profileId, QStringLiteral("lp-big"));
    QCOMPARE(r.fallbacks[2].type, QStringLiteral("cli"));
    QCOMPARE(r.fallbacks[2].cliName, QStringLiteral("claude"));
    QCOMPARE(r.fallbacks[2].applyEdits, false);

    QVERIFY(!MasterConfig{}.isConfigured());  // default: cadena vacía
}

void ProfilesTests::masterConfig_legacyMigration()
{
    // Perfil viejo: un solo maestro http con key en claro, sin array fallbacks.
    QJsonObject o;
    o["kind"] = "http"; o["httpUrl"] = "http://x"; o["httpModel"] = "big";
    o["httpKey"] = "secret-k"; o["escalation"] = "both"; o["autoAfterFails"] = 4;
    const MasterConfig r = MasterConfig::fromJson(o);
    QCOMPARE(r.fallbacks.size(), 1);
    QCOMPARE(r.fallbacks.first().type, QStringLiteral("http"));
    QCOMPARE(r.fallbacks.first().httpUrl, QStringLiteral("http://x"));
    QCOMPARE(r.fallbacks.first().httpKeyRef, QStringLiteral("secret-k"));
    QCOMPARE(r.escalation, QStringLiteral("both"));
    QCOMPARE(r.autoAfterFails, 4);

    // Legacy CLI.
    QJsonObject c; c["kind"] = "cli"; c["cliName"] = "codex";
    const MasterConfig rc = MasterConfig::fromJson(c);
    QCOMPARE(rc.fallbacks.size(), 1);
    QCOMPARE(rc.fallbacks.first().type, QStringLiteral("cli"));
    QCOMPARE(rc.fallbacks.first().cliName, QStringLiteral("codex"));

    // Legacy none → cadena vacía.
    QJsonObject n; n["kind"] = "none";
    QVERIFY(!MasterConfig::fromJson(n).isConfigured());
}

void ProfilesTests::manager_addGetRemoveBackend()
{
    ProfileManager pm;
    const QString id = pm.addBackend("be", "bin1", "127.0.0.1", 8080);
    QVERIFY(!id.isEmpty());
    const QVariantMap got = pm.getBackend(id);
    QCOMPARE(got.value("name").toString(), QStringLiteral("be"));
    QCOMPARE(got.value("port").toInt(), 8080);
    QVERIFY(pm.updateBackend(id, "be2", "bin1", "0.0.0.0", 9000, QStringList{"--x"}));
    QCOMPARE(pm.getBackend(id).value("name").toString(), QStringLiteral("be2"));
    QVERIFY(pm.removeBackend(id));
    QVERIFY(pm.getBackend(id).isEmpty());
    QVERIFY(!pm.removeBackend("nope"));
}

void ProfilesTests::manager_updateBackendPort()
{
    ProfileManager pm;
    const QString id = pm.addBackend("be", "bin1", "127.0.0.1", 8080);
    QVERIFY(!id.isEmpty());
    QVERIFY(pm.updateBackendPort(id, 8082));
    QCOMPARE(pm.getBackend(id).value("port").toInt(), 8082);
    QCOMPARE(pm.resolveBackend(id).port, 8082);
    QVERIFY(!pm.updateBackendPort(id, 0));
    QVERIFY(!pm.updateBackendPort(id, 70000));
    QVERIFY(!pm.updateBackendPort("nope", 8083));
}

void ProfilesTests::manager_setBackendCloud()
{
    ProfileManager pm;
    const QString id = pm.addBackend("be", "bin1", "127.0.0.1", 8080);
    QVERIFY(pm.setBackendCloud(id, "cloud", "https://openrouter.ai/api", "OPENROUTER_KEY",
                               "anthropic/claude-sonnet-4", 200000));
    const QVariantMap got = pm.getBackend(id);
    QCOMPARE(got.value("kind").toString(), QStringLiteral("cloud"));
    QCOMPARE(got.value("cloudKeyRef").toString(), QStringLiteral("OPENROUTER_KEY"));
    QCOMPARE(got.value("cloudBaseUrl").toString(), QStringLiteral("https://openrouter.ai/api"));
    QCOMPARE(got.value("cloudModel").toString(), QStringLiteral("anthropic/claude-sonnet-4"));
    QCOMPARE(got.value("cloudCtx").toInt(), 200000);
    // volver a local limpia el flag
    QVERIFY(pm.setBackendCloud(id, "local", "", "", "", 0));
    QCOMPARE(pm.getBackend(id).value("kind").toString(), QStringLiteral("local"));
    QVERIFY(!pm.setBackendCloud("nope", "cloud", "", "", "", 0));
}

void ProfilesTests::manager_addModelProfile()
{
    ProfileManager pm;
    const QString id = pm.addModelProfile("qwen", "cat1", "", "");
    QVERIFY(!id.isEmpty());
    QCOMPARE(pm.getModelProfile(id).value("modelId").toString(), QStringLiteral("cat1"));

    // setModelSpec persiste la configuración DSpark y getModelProfile la expone.
    QVERIFY(pm.setModelSpec(id, "draft-dspark", 3, "all", "q8_0", "q8_0", 0.6, 2, true));
    const QVariantMap m = pm.getModelProfile(id);
    QCOMPARE(m.value("specType").toString(), QStringLiteral("draft-dspark"));
    QCOMPARE(m.value("specDraftNMax").toInt(), 3);
    QCOMPARE(m.value("specDraftNMin").toInt(), 2);
    QVERIFY(m.value("specDraftAdaptive").toBool());
    QCOMPARE(m.value("specDraftConfMin").toDouble(), 0.6);
    QCOMPARE(m.value("specDraftTypeK").toString(), QStringLiteral("q8_0"));

    QVERIFY(pm.removeModelProfile(id));
}

void ProfilesTests::manager_favoriteAndAlias()
{
    ProfileManager pm;
    const QString id = pm.addLaunchProfile("L", "b", "m", "r");
    QVERIFY(!id.isEmpty());
    pm.setLaunchFavorite(id, true);
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", id}, {"best", true}}));
    pm.setLaunchAlias(id, "Alias");
    const QVariantList menu = pm.launchProfilesForMenu();
    QVERIFY(!menu.isEmpty());
    const auto it = std::find_if(menu.cbegin(), menu.cend(), [&](const QVariant &value) {
        return value.toMap().value("id").toString() == id;
    });
    QVERIFY(it != menu.cend());
    const QVariantMap row = it->toMap();
    QCOMPARE(row.value("alias").toString(), QStringLiteral("Alias"));
    QVERIFY(row.value("favorite").toBool());
    // displayName antepone la estrella a los favoritos y muestra alias + nombre.
    QCOMPARE(row.value("displayName").toString(), QStringLiteral("⚡ ★ Alias - 1_L"));
    QVERIFY(row.value("best").toBool());
    QCOMPARE(pm.getLaunchProfile(id).value("displayName").toString(),
             QStringLiteral("Alias - 1_L"));
}

void ProfilesTests::manager_menuOrderPrecedesRecentUsage()
{
    ProfileManager pm;
    const QString first = pm.addLaunchProfile(QStringLiteral("First"), "b", "m", "r");
    const QString second = pm.addLaunchProfile(QStringLiteral("Second"), "b", "m", "r");
    QVERIFY(!first.isEmpty());
    QVERIFY(!second.isEmpty());
    pm.markLaunchUsed(second);
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", first}, {"menuOrder", 1}}));
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", second}, {"menuOrder", 2}}));

    const QVariantList menu = pm.launchProfilesForMenu();
    const auto pos = [&](const QString &id) {
        for (int i = 0; i < menu.size(); ++i)
            if (menu.at(i).toMap().value("id").toString() == id) return i;
        return static_cast<int>(menu.size());
    };
    QVERIFY(pos(first) < pos(second));
    QCOMPARE(pm.getLaunchProfile(first).value("menuOrder").toInt(), 1);
    QCOMPARE(pm.getLaunchProfile(second).value("menuOrder").toInt(), 2);
}

void ProfilesTests::manager_benchmarkQueue()
{
    ProfileManager pm;
    const QString id = pm.addLaunchProfile(QStringLiteral("Pendiente"), "b", "m", "r");
    QVERIFY(!id.isEmpty());

    pm.setLaunchBenchmark(id, true);
    const QVariantMap queued = pm.getLaunchProfile(id);
    QVERIFY(queued.value(QStringLiteral("benchmark")).toBool());

    const QVariantList menu = pm.launchProfilesForMenu();
    QVERIFY(std::any_of(menu.cbegin(), menu.cend(), [&](const QVariant &value) {
        const QVariantMap row = value.toMap();
        return row.value(QStringLiteral("id")).toString() == id
            && row.value(QStringLiteral("benchmark")).toBool()
            && row.value(QStringLiteral("displayName")).toString().contains(QStringLiteral("🏆"));
    }));

    {
        ProfileManager reloaded;
        QVERIFY(reloaded.getLaunchProfile(id).value(QStringLiteral("benchmark")).toBool());
    }

    pm.setLaunchBenchmark(id, false);
    QVERIFY(!pm.getLaunchProfile(id).value(QStringLiteral("benchmark")).toBool());
}

void ProfilesTests::manager_profileSearchFiltersNameAliasAndId()
{
    ProfileManager pm;
    const QString id = pm.addLaunchProfile(QStringLiteral("Qwen análisis"), {}, {}, {});
    QVERIFY(!id.isEmpty());
    pm.setLaunchAlias(id, QStringLiteral("Documentos"));

    const QVariantList byName = pm.launchProfilesForProfilesPage(QStringLiteral("ANÁLISIS"));
    QVERIFY(std::any_of(byName.cbegin(), byName.cend(), [&](const QVariant &v) {
        return v.toMap().value(QStringLiteral("id")).toString() == id;
    }));
    const QVariantList byAlias = pm.launchProfilesForProfilesPage(QStringLiteral("documentos"));
    QCOMPARE(byAlias.size(), 1);
    QCOMPARE(byAlias.first().toMap().value(QStringLiteral("id")).toString(), id);
    const QVariantList byId = pm.launchProfilesForProfilesPage(id.left(8));
    QVERIFY(std::any_of(byId.cbegin(), byId.cend(), [&](const QVariant &v) {
        return v.toMap().value(QStringLiteral("id")).toString() == id;
    }));
    QVERIFY(pm.launchProfilesForProfilesPage(QStringLiteral("no existe")).isEmpty());
}

void ProfilesTests::manager_tagsAndLastUsed()
{
    ProfileManager pm;
    const QString id = pm.addLaunchProfile(QStringLiteral("Tagged"), {}, {}, {});
    QVERIFY(!id.isEmpty());
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", id}, {"tags", QStringList{" coding ", "local", "CODING"}}}));
    const QVariantMap before = pm.getLaunchProfile(id);
    QCOMPARE(before.value("tags").toStringList(), QStringList({"coding", "local"}));
    QCOMPARE(before.value("lastUsed").toLongLong(), 0);

    pm.markLaunchUsed(id);
    const QVariantMap after = pm.getLaunchProfile(id);
    QVERIFY(after.value("lastUsed").toLongLong() > 0);
    const QVariantList byTag = pm.launchProfilesForProfilesPage(QStringLiteral("LOCAL"));
    QVERIFY(std::any_of(byTag.cbegin(), byTag.cend(), [&](const QVariant &value) {
        return value.toMap().value("id").toString() == id;
    }));
}

void ProfilesTests::manager_profileTemplatesRoundTrip()
{
    ProfileManager pm;
    const QString launch = pm.addLaunchProfile(QStringLiteral("Template source"), "be", "mo", "rt");
    QVERIFY(!launch.isEmpty());
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", launch}, {"tags", QStringList{"coding"}},
                                               {"extraArgs", QStringList{"--temp", "0.6"}},
                                               {"envOverrides", QVariantMap{{"TEST_TEMPLATE", "1"}}}}));
    const QString tid = pm.saveLaunchAsTemplate(launch, QStringLiteral("Coding local"));
    QVERIFY(!tid.isEmpty());
    const QVariantList templates = pm.profileTemplates();
    QVERIFY(std::any_of(templates.cbegin(), templates.cend(), [&](const QVariant &v) {
        return v.toMap().value(QStringLiteral("id")).toString() == tid;
    }));
    const QString copy = pm.createLaunchFromTemplate(tid, QStringLiteral("From template"));
    QVERIFY(!copy.isEmpty());
    const QVariantMap restored = pm.getLaunchProfile(copy);
    QCOMPARE(restored.value(QStringLiteral("tags")).toStringList(), QStringList{"coding"});
    const QStringList expectedArgs{"--temp", "0.6"};
    QCOMPARE(restored.value(QStringLiteral("extraArgs")).toStringList(), expectedArgs);
    QCOMPARE(restored.value(QStringLiteral("envOverrides")).toMap().value(QStringLiteral("TEST_TEMPLATE")).toString(), QStringLiteral("1"));
    QVERIFY(pm.removeProfileTemplate(tid));
}

void ProfilesTests::manager_harnessArgsEnvRoundTrip()
{
    ProfileManager pm;
    const QString id = pm.addHarness(QStringLiteral("Harness"), QStringLiteral("llamaagent"));
    QVERIFY(pm.updateHarness(QVariantMap{{"id", id}, {"args", QStringList{"--quiet"}},
                                         {"env", QVariantMap{{"HARNESS_MODE", "test"}}}}));
    const QVariantMap got = pm.getHarness(id);
    QCOMPARE(got.value(QStringLiteral("args")).toStringList(), QStringList{"--quiet"});
    QCOMPARE(got.value(QStringLiteral("env")).toMap().value(QStringLiteral("HARNESS_MODE")).toString(), QStringLiteral("test"));
}

void ProfilesTests::manager_reasoningControlsRoundTrip()
{
    ProfileManager pm;
    const QString id = pm.addLaunchProfile(QStringLiteral("Reasoning controls"), {}, {}, {});
    QVERIFY(!id.isEmpty());

    QVERIFY(pm.updateLaunchProfile(QVariantMap{
        {"id", id}, {"reasoningBudget", 0}, {"reasoningEffort", "low"}}));
    const QVariantMap disabled = pm.getLaunchProfile(id);
    QCOMPARE(disabled.value("reasoningBudget").toInt(), 0);
    QCOMPARE(disabled.value("reasoningEffort").toString(), QStringLiteral("low"));

    // -1 means inherit the app-level setting; negative values below -1 are
    // clamped instead of producing an invalid launch profile.
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", id}, {"reasoningBudget", -9},
                                                {"reasoningEffort", ""}}));
    const QVariantMap inherited = pm.getLaunchProfile(id);
    QCOMPARE(inherited.value("reasoningBudget").toInt(), -1);
    QVERIFY(inherited.value("reasoningEffort").toString().isEmpty());
}

void ProfilesTests::manager_browserAutomationOverride()
{
    ProfileManager pm;
    const QString id = pm.addLaunchProfile("BA", "b", "m", "r");
    QVERIFY(!id.isEmpty());
    // Default: campo ausente → "inherit".
    QCOMPARE(pm.getLaunchProfile(id).value("browserAutomation").toString(),
             QStringLiteral("inherit"));
    // update/get round-trip del override.
    QVERIFY(pm.updateLaunchProfile(QVariantMap{
        {"id", id}, {"browserAutomation", "off"}}));
    QCOMPARE(pm.getLaunchProfile(id).value("browserAutomation").toString(),
             QStringLiteral("off"));
}

void ProfilesTests::manager_deprecatedIsProfilesOnly()
{
    ProfileManager pm;
    const QString id = pm.addLaunchProfile("Deprecated", "b", "m", "r");
    QVERIFY(!id.isEmpty());
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", id}, {"deprecated", true},
                                                {"systemBadge", true}, {"benchmark", true}}));
    QCOMPARE(pm.getLaunchProfile(id).value("deprecated").toBool(), true);
    QCOMPARE(pm.getLaunchProfile(id).value("systemBadge").toBool(), true);
    QCOMPARE(pm.getLaunchProfile(id).value("benchmark").toBool(), true);
    const QVariantList menu = pm.launchProfilesForMenu();
    for (const QVariant &v : menu)
        QVERIFY(v.toMap().value("id").toString() != id);
    const QVariantList profiles = pm.launchProfilesForProfilesPage();
    bool found = false;
    for (const QVariant &v : profiles) {
        if (v.toMap().value("id").toString() == id) {
            found = true;
            QCOMPARE(v.toMap().value("deprecated").toBool(), true);
            QVERIFY(v.toMap().value("displayName").toString().startsWith(QStringLiteral("⚙ 🏆 ⚠ ")));
        }
    }
    QVERIFY(found);
}

void ProfilesTests::manager_systemProfilesReloadIdempotent()
{
    ProfileManager pm;
    const int launchCount = pm.launchProfiles()->rowCount();
    const int modelCount = pm.modelProfiles()->rowCount();
    const int runtimeCount = pm.runtimePresets()->rowCount();
    const int backendCount = pm.backendProfiles()->rowCount();
    const int agentCount = pm.agentProfiles()->rowCount();

    pm.reloadFromDisk();
    QCOMPARE(pm.launchProfiles()->rowCount(), launchCount);
    QCOMPARE(pm.modelProfiles()->rowCount(), modelCount);
    QCOMPARE(pm.runtimePresets()->rowCount(), runtimeCount);
    QCOMPARE(pm.backendProfiles()->rowCount(), backendCount);
    QCOMPARE(pm.agentProfiles()->rowCount(), agentCount);
}

void ProfilesTests::manager_persistsAcrossInstances()
{
    QString id;
    {
        ProfileManager pm;
        id = pm.addBackend("persist", "bin1", "127.0.0.1", 7777);
        pm.saveProfiles();
    }
    {
        ProfileManager pm2;  // recarga de disco en el ctor
        QCOMPARE(pm2.getBackend(id).value("name").toString(), QStringLiteral("persist"));
    }
}

// Config compartida Windows/Linux: cada guardado convertía "D:/x" en "D://x"
// (launches.json llegó a "D:////////////Models"). La ida y vuelta tiene que
// devolver exactamente lo mismo, también repetida.
static const QString kCRoot = QStringLiteral("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian");
static const QString kDRoot = QStringLiteral("/media/cristian/Disco local");

void ProfilesTests::portablePaths_roundTripIsStable()
{
    const QStringList stored = {
        QStringLiteral("D:/Models/llamacpp/x.gguf"),
        QStringLiteral("C:/Users/cristian/Documents/LlamaCode/chat-templates/a.jinja"),
        QStringLiteral("--mmproj=D:/Models/BigBang/mmproj.gguf"),
        QStringLiteral("C:/Users/cristian"),
        QStringLiteral("D:/"),
        QStringLiteral("sin rutas"),
    };
    for (const QString &s : stored) {
        QString v = s;
        for (int i = 0; i < 5; ++i) {
            const QString runtime = PortablePaths::translate(v, true, kCRoot, kDRoot);
            QVERIFY2(!runtime.contains(QStringLiteral("D:/")) || s == QStringLiteral("sin rutas"),
                     qPrintable(runtime));
            v = PortablePaths::translate(runtime, false, kCRoot, kDRoot);
        }
        QCOMPARE(v, s);
    }
    QCOMPARE(PortablePaths::translate(QStringLiteral("D:/Models/x.gguf"), true, kCRoot, kDRoot),
             kDRoot + QStringLiteral("/Models/x.gguf"));
    // Raíces con '/' final: mismo resultado.
    QCOMPARE(PortablePaths::translate(kDRoot + QStringLiteral("/Models/x.gguf"), false,
                                      kCRoot + QLatin1Char('/'), kDRoot + QLatin1Char('/')),
             QStringLiteral("D:/Models/x.gguf"));
}

void ProfilesTests::portablePaths_repairsAccumulatedSlashes()
{
    const QString corrupt = QStringLiteral("D:////////////Models/llamacpp/x.gguf");
    const QString runtime = PortablePaths::translate(corrupt, true, kCRoot, kDRoot);
    QCOMPARE(runtime, kDRoot + QStringLiteral("/Models/llamacpp/x.gguf"));
    QCOMPARE(PortablePaths::translate(runtime, false, kCRoot, kDRoot),
             QStringLiteral("D:/Models/llamacpp/x.gguf"));
}

void ProfilesTests::portablePaths_respectsRootBoundaries()
{
    // Sólo D configurada: una ruta C: no se borra (antes se reemplazaba por "").
    QCOMPARE(PortablePaths::translate(QStringLiteral("C:/Users/cristian/a"), true, QString(), kDRoot),
             QStringLiteral("C:/Users/cristian/a"));
    // Un directorio hermano con el mismo prefijo no es la raíz.
    const QString sibling = QStringLiteral("/media/cristian/Disco locales/x");
    QCOMPARE(PortablePaths::translate(sibling, false, kCRoot, kDRoot), sibling);
    QCOMPARE(PortablePaths::translate(QStringLiteral("C:/Users/cristianX/a"), true, kCRoot, kDRoot),
             QStringLiteral("C:/Users/cristianX/a"));
    // Sin raíces no se toca nada.
    QCOMPARE(PortablePaths::translate(QStringLiteral("D:/x"), true, QString(), QString()),
             QStringLiteral("D:/x"));
}

void ProfilesTests::manager_sharedConfigSaveDoesNotGrowSlashes()
{
#ifdef Q_OS_WIN
    QSKIP("La traducción de config compartida sólo corre en Linux.");
#else
    const QString backendsPath = QDir(m_dir.path()).filePath(QStringLiteral("backends.json"));
    QString id;
    {
        ProfileManager pm;
        id = pm.addBackend(QStringLiteral("portable"), QStringLiteral("bin1"),
                           QStringLiteral("127.0.0.1"), 7001);
        pm.saveProfiles();
    }
    // Simular el archivo compartido de Windows con una ruta D: en baseArgs.
    QFile f(backendsPath);
    QVERIFY(f.open(QIODevice::ReadOnly));
    QByteArray raw = f.readAll();
    f.close();
    QVERIFY(raw.contains("\"portable\""));
    QJsonDocument doc = QJsonDocument::fromJson(raw);
    QJsonArray items = doc.isArray() ? doc.array()
                                     : doc.object().value(QStringLiteral("items")).toArray();
    QVERIFY(!items.isEmpty());
    for (int i = 0; i < items.size(); ++i) {
        QJsonObject o = items[i].toObject();
        if (o.value(QStringLiteral("id")).toString() != id) continue;
        o.insert(QStringLiteral("baseArgs"),
                 QJsonArray{QStringLiteral("--model"), QStringLiteral("D:/Models/x.gguf")});
        items[i] = o;
    }
    if (doc.isArray()) doc.setArray(items);
    else { QJsonObject root = doc.object(); root.insert(QStringLiteral("items"), items); doc.setObject(root); }
    QVERIFY(f.open(QIODevice::WriteOnly | QIODevice::Truncate));
    f.write(doc.toJson());
    f.close();

    // Se desarman aunque falle un QVERIFY: si no, contaminan los tests siguientes.
    struct EnvGuard {
        EnvGuard() {
            qputenv("LLAMACODE_SHARED_PORTABLE_CONFIG", "1");
            qputenv("LLAMACODE_WINDOWS_C_ROOT", kCRoot.toLocal8Bit());
            qputenv("LLAMACODE_WINDOWS_D_ROOT", kDRoot.toLocal8Bit());
        }
        ~EnvGuard() {
            qunsetenv("LLAMACODE_SHARED_PORTABLE_CONFIG");
            qunsetenv("LLAMACODE_WINDOWS_C_ROOT");
            qunsetenv("LLAMACODE_WINDOWS_D_ROOT");
        }
    };
    {
    EnvGuard env;
    for (int port = 7002; port < 7005; ++port) {   // varios ciclos cargar → guardar
        ProfileManager pm;
        QVERIFY(pm.getBackend(id).value(QStringLiteral("baseArgs")).toStringList()
                    .contains(kDRoot + QStringLiteral("/Models/x.gguf")));
        QVERIFY(pm.updateBackendPort(id, port));
        pm.saveProfiles();
    }
    }

    QVERIFY(f.open(QIODevice::ReadOnly));
    raw = f.readAll();
    QVERIFY2(raw.contains("\"D:/Models/x.gguf\""), raw.constData());
    QVERIFY(!raw.contains("D://"));
    QVERIFY(!raw.contains("Disco local"));
#endif
}

void ProfilesTests::manager_exportImportBundle()
{
    ProfileManager pm;
    const QString backendId = pm.addBackend("bundle-backend", "bin-bundle",
                                            "127.0.0.1", 9191);
    QVERIFY(!backendId.isEmpty());
    const QString launchId = pm.addLaunchProfile("bundle-launch", backendId, "model-missing",
                                                 "runtime-missing");
    QVERIFY(!launchId.isEmpty());
    const QString json = pm.exportProfilesBundle();
    QVERIFY(json.contains(QStringLiteral("schemaVersion")));
    QVERIFY(json.contains(QStringLiteral("bundle-backend")));

    QVERIFY(pm.removeBackend(backendId));
    QVERIFY(pm.removeLaunchProfile(launchId));
    const int imported = pm.importProfilesBundle(json);
    QVERIFY(imported >= 2);
    QCOMPARE(pm.getBackend(backendId).value(QStringLiteral("name")).toString(),
             QStringLiteral("bundle-backend"));
    QVERIFY(pm.getLaunchProfile(launchId).value(QStringLiteral("name")).toString()
            .endsWith(QStringLiteral("_bundle-launch")));
    QCOMPARE(pm.importProfilesBundle(QStringLiteral("not-json")), -1);
    QCOMPARE(pm.importProfilesBundle(QStringLiteral("{\"schemaVersion\":99}")), -1);
}

void ProfilesTests::manager_profileChangeHistory()
{
    ProfileManager pm;
    const QString id = pm.addBackend(QStringLiteral("history-a"), QStringLiteral("bin"),
                                     QStringLiteral("127.0.0.1"), 9911);
    QVERIFY(!id.isEmpty());
    QVERIFY(pm.updateBackendPort(id, 9912));
    const QVariantList history = pm.profileChangeHistory(QStringLiteral("backend"), id, 10);
    QVERIFY(history.size() >= 2);
    QCOMPARE(history.first().toMap().value(QStringLiteral("id")).toString(), id);
    QVERIFY(history.first().toMap().value(QStringLiteral("snapshot")).toMap()
                .value(QStringLiteral("name")).toString().contains(QStringLiteral("history-a")));
}

// save() se llama mucho (arranque, auto-sanado, cada setter). Sin cambios no
// debe tocar disco: ni reescribir launches.json ni apilar snapshots en el
// historial (antes sumaba uno por CADA perfil en cada save → 13 MB).
void ProfilesTests::manager_saveSkipsUnchangedAndLogsOnlyChanges()
{
    ProfileManager pm;
    const QString a = pm.addBackend(QStringLiteral("skip-a"), QStringLiteral("bin"),
                                    QStringLiteral("127.0.0.1"), 9921);
    const QString b = pm.addBackend(QStringLiteral("skip-b"), QStringLiteral("bin"),
                                    QStringLiteral("127.0.0.1"), 9922);
    QVERIFY(!a.isEmpty() && !b.isEmpty());

    const QString backends = m_dir.filePath(QStringLiteral("backends.json"));
    const QString historyPath = m_dir.filePath(QStringLiteral("profile_history.jsonl"));
    auto historyLines = [&]() {
        QFile f(historyPath);
        if (!f.open(QIODevice::ReadOnly)) return QList<QByteArray>{};
        QList<QByteArray> lines = f.readAll().split('\n');
        lines.removeAll(QByteArray());
        return lines;
    };
    const QDateTime mtimeBefore = QFileInfo(backends).lastModified();
    const qsizetype linesBefore = historyLines().size();

    QTest::qWait(30);   // que un rewrite se note en el mtime
    pm.saveProfiles();
    QCOMPARE(QFileInfo(backends).lastModified(), mtimeBefore);
    QCOMPARE(historyLines().size(), linesBefore);

    QVERIFY(pm.updateBackendPort(a, 9931));
    const QList<QByteArray> after = historyLines();
    QCOMPARE(after.size(), linesBefore + 1);
    const QJsonObject row = QJsonDocument::fromJson(after.last()).object();
    QCOMPARE(row.value(QStringLiteral("id")).toString(), a);
    QCOMPARE(row.value(QStringLiteral("entity")).toString(), QStringLiteral("backend"));
}

QTEST_MAIN(ProfilesTests)
#include "test_profiles.moc"
