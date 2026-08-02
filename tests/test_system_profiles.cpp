// Tests de perfiles de SISTEMA (bundled, fast-start por hardware):
//   - ProfileManager: carga del bundle, inmutabilidad (no borrar/editar/fav),
//     no-persistencia, duplicar a copia editable, modelId determinista por ruta.
//   - AppController: recommendedSystemProfile elige el tier ≤ hardware correcto.
//
// Aislamiento: LLAMACODE_PROFILES_DIR (temp) + LLAMACODE_SYSTEM_PROFILES (bundle
// del repo) seteados en initTestCase ANTES de construir el primer ProfileManager
// (storagePath cachea la raíz en un static). QStandardPaths en modo test.

#include <QtTest>
#include <QTemporaryDir>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QUuid>
#include <QCoreApplication>
#include <algorithm>
#include "core/profiles/ProfileManager.h"
#include "core/profiles/MtpDetection.h"
#include "AppController.h"

// Bundle resuelto relativo al repo (ctest corre con WORKING_DIRECTORY = source dir).
static QString bundlePath()
{
    const QStringList candidates = {
        QDir::current().absoluteFilePath(QStringLiteral("assets/system_profiles.json")),
        QDir::current().absoluteFilePath(QStringLiteral("../assets/system_profiles.json")),
        QDir(QCoreApplication::applicationDirPath())
            .absoluteFilePath(QStringLiteral("../../assets/system_profiles.json")),
    };
    for (const QString &c : candidates)
        if (QFile::exists(c))
            return c;
    return candidates.first();
}

class SystemProfilesTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();

    void manager_loadsSystemProfiles();
    void manager_systemNotPersisted();
    void manager_immutable();
    void manager_duplicateMakesEditableCopy();
    void manager_modelIdIsDeterministic();
    void manager_fastGemmaDflashWired();
    void manager_systemProfilesAvoidAccidentalVisionAndMtp();
    void bundle_draftMtpAlwaysDeclaresDraftModel();
    void bundle_gemma4TemplateKeepsLlamaCppMarkers();
    void manager_smallProfilesAreConservative();
    void manager_defaultCodingProfileUsesKatCoder();
    void manager_16gbCodingProfileUsesBenchmarkedKatCoder();
    void manager_24gbPremiumPromotesThinkingCapAndKeepsMaxCtx();

    void controller_recommendsClosestTier();
    void controller_recommendedTierIncludesDisplayName();
    void controller_recommendsCpuWhenNoGpu();
    void controller_noneWhenBelowMinimum();
    void controller_showcase8gbOffersGemmaAndQwen();
    void controller_showcase24gbUnchanged();
    void controller_showcaseEmptyWhenNoSiblings();
    void bundle_lagunaIsOptInAndHardwareGated();
    void bundle_ultraQAndHybridAreWiredAndOptIn();

private:
    QTemporaryDir m_dir;
};

void SystemProfilesTests::initTestCase()
{
    QStandardPaths::setTestModeEnabled(true);
    QCoreApplication::setOrganizationName(QStringLiteral("LlamaCode"));
    QCoreApplication::setApplicationName(QStringLiteral("LlamaCode"));
    QVERIFY(m_dir.isValid());
    qputenv("LLAMACODE_PROFILES_DIR", m_dir.path().toLocal8Bit());
    const QString bundle = bundlePath();
    QVERIFY2(QFile::exists(bundle), "falta assets/system_profiles.json");
    qputenv("LLAMACODE_SYSTEM_PROFILES", bundle.toLocal8Bit());
}

void SystemProfilesTests::manager_loadsSystemProfiles()
{
    ProfileManager pm;
    auto *m = pm.launchProfiles();
    int sys = 0;
    QString anySysId;
    for (int r = 0; r < m->rowCount(); ++r) {
        if (m->data(m->index(r), ProfileListModel<LaunchProfile>::SystemRole).toBool()) {
            ++sys;
            anySysId = m->data(m->index(r), ProfileListModel<LaunchProfile>::IdRole).toString();
        }
    }
    QCOMPARE(sys, 29); // tiers base + extras + ULTRA-Q/híbrido + DSpark externo + 12 variantes bench
    QVERIFY(pm.isSystemLaunch("sys-vram-16"));
    QVERIFY(!anySysId.isEmpty());
    // Visión: solo los perfiles Gemma vision dedicados llevan mmproj. Los perfiles
    // Qwen/coding y Gemma chicos no deben cargar projector para una automatización
    // textual: aumenta memoria/prompt y no ayuda a desktop_controls.
    const QString mp16 = pm.getLaunchProfile("sys-vram-16").value("modelProfileId").toString();
    QVERIFY(pm.getModelProfile(mp16).value("mmprojId").toString().isEmpty());
    const QString mp4 = pm.getLaunchProfile("sys-vram-4").value("modelProfileId").toString();
    QVERIFY(pm.getModelProfile(mp4).value("mmprojId").toString().isEmpty());
    // El tier 8GB Gemma tiene visión (gemma4uv): mmproj presente, offload a CPU via
    // --no-mmproj-offload. Requiere llama-server b9496+ en runtime. Q3_K_XL deja
    // margen para MTP self-draft (mtp-gemma-4-12b-it.gguf, --spec-type draft-mtp).
    const QString mp8 = pm.getLaunchProfile("sys-vram-8-gemma").value("modelProfileId").toString();
    const QVariantMap m8 = pm.getModelProfile(mp8);
    QVERIFY(!m8.value("mmprojId").toString().isEmpty());
    QCOMPARE(m8.value("specType").toString(), QStringLiteral("draft-mtp"));
    QVERIFY(!m8.value("draftModelId").toString().isEmpty());
}

void SystemProfilesTests::manager_systemNotPersisted()
{
    { ProfileManager pm; pm.saveProfiles(); }   // fuerza save con system en memoria
    // El launches.json en disco NO debe contener perfiles de sistema.
    QFile f(m_dir.path() + "/launches.json");
    if (f.open(QIODevice::ReadOnly)) {
        const QByteArray raw = f.readAll();
        QVERIFY(!raw.contains("sys-vram-16"));
    }
    // Y al reconstruir, los de sistema reaparecen del bundle.
    ProfileManager pm2;
    QVERIFY(pm2.isSystemLaunch("sys-vram-16"));
}

void SystemProfilesTests::manager_immutable()
{
    ProfileManager pm;
    QVERIFY(!pm.removeLaunchProfile("sys-vram-12-moe"));
    QVERIFY(!pm.updateLaunchProfile(QVariantMap{{"id", "sys-vram-12-moe"}, {"name", "hack"}}));
    pm.setLaunchFavorite("sys-vram-12-moe", true);
    QVERIFY(!pm.getLaunchProfile("sys-vram-12-moe").value("favorite").toBool());
    pm.setLaunchAlias("sys-vram-12-moe", "hack");
    QCOMPARE(pm.getLaunchProfile("sys-vram-12-moe").value("alias").toString(), QStringLiteral("12GB"));
}

void SystemProfilesTests::manager_duplicateMakesEditableCopy()
{
    ProfileManager pm;
    const QString dup = pm.duplicateLaunchProfile("sys-vram-12-moe");
    QVERIFY(!dup.isEmpty());
    QVERIFY(!pm.isSystemLaunch(dup));
    // La copia ES editable (rename/fav OK).
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id", dup}, {"name", "mio"}}));
    // backing clonado: ids distintos a los del perfil de sistema.
    const QVariantMap src = pm.getLaunchProfile("sys-vram-12-moe");
    const QVariantMap cp = pm.getLaunchProfile(dup);
    QVERIFY(cp.value("modelProfileId").toString() != src.value("modelProfileId").toString());
    QVERIFY(cp.value("runtimePresetId").toString() != src.value("runtimePresetId").toString());
}

void SystemProfilesTests::manager_modelIdIsDeterministic()
{
    ProfileManager pm;
    const QString mpId = pm.getLaunchProfile("sys-vram-4").value("modelProfileId").toString();
    const QString modelId = pm.getModelProfile(mpId).value("modelId").toString();
    const QString modelsDir =
        QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/models";
    const QUuid ns(QStringLiteral("a1b2c3d4-e5f6-4a5b-8c7d-0e1f2a3b4c5d"));
    const QString expect = QUuid::createUuidV5(
        ns, QString(modelsDir + "/Qwen3.5-4B/Qwen3.5-4B-Q4_K_M.gguf").toUtf8()).toString(QUuid::WithoutBraces);
    QCOMPARE(modelId, expect);
}

void SystemProfilesTests::manager_fastGemmaDflashWired()
{
    ProfileManager pm;
    // FAST GEMMA: DFlash = target + draft + specType "dflash" (inmutable).
    const QString mpId = pm.getLaunchProfile("sys-fastgemma").value("modelProfileId").toString();
    const QVariantMap mp = pm.getModelProfile(mpId);
    QCOMPARE(mp.value("specType").toString(), QStringLiteral("draft-mtp"));
    QVERIFY(!mp.value("draftModelId").toString().isEmpty());
    QVERIFY(!mp.value("modelId").toString().isEmpty());
    // No se puede editar el original; sí su duplicado (copia editable).
    QVERIFY(!pm.updateLaunchProfile(QVariantMap{{"id","sys-fastgemma"},{"name","x"}}));
    const QString dup = pm.duplicateLaunchProfile("sys-fastgemma");
    QVERIFY(!dup.isEmpty());
    QVERIFY(!pm.isSystemLaunch(dup));
    QVERIFY(pm.updateLaunchProfile(QVariantMap{{"id",dup},{"name","mi-gemma"}}));
}

void SystemProfilesTests::manager_systemProfilesAvoidAccidentalVisionAndMtp()
{
    ProfileManager pm;
    auto *m = pm.launchProfiles();
    for (int r = 0; r < m->rowCount(); ++r) {
        const QModelIndex idx = m->index(r);
        if (!m->data(idx, ProfileListModel<LaunchProfile>::SystemRole).toBool())
            continue;
        const QString launchId = m->data(idx, ProfileListModel<LaunchProfile>::IdRole).toString();
        const QVariantMap launch = pm.getLaunchProfile(launchId);
        const QVariantMap model = pm.getModelProfile(launch.value("modelProfileId").toString());
        const QString name = launch.value("name").toString().toLower();
        const bool isVisionProfile = name.contains(QStringLiteral("visión"))
                                     || name.contains(QStringLiteral("vision"));
        if (!isVisionProfile) {
            QVERIFY2(model.value("mmprojId").toString().isEmpty(),
                     qPrintable(QStringLiteral("%1 carga mmproj sin ser perfil de visión")
                                    .arg(launchId)));
        }

        const bool hasSpec = !model.value("specType").toString().isEmpty()
                             || model.value("specDraftNMax").toInt() > 0;
        if (hasSpec) {
            QVERIFY2(!model.value("draftModelId").toString().isEmpty(),
                     qPrintable(QStringLiteral("%1 declara speculative/MTP sin draftModel")
                                    .arg(launchId)));
        }
    }
}

void SystemProfilesTests::bundle_draftMtpAlwaysDeclaresDraftModel()
{
    QFile f(bundlePath());
    QVERIFY(f.open(QIODevice::ReadOnly));
    const QJsonArray arr = QJsonDocument::fromJson(f.readAll()).array();
    QVERIFY(!arr.isEmpty());
    for (const QJsonValue &value : arr) {
        const QJsonObject entry = value.toObject();
        const QString id = entry.value(QStringLiteral("id")).toString();
        QStringList specTokens;
        const QJsonObject mtp = entry.value(QStringLiteral("mtp")).toObject();
        if (mtp.value(QStringLiteral("enabled")).toBool()) {
            for (const QJsonValue &arg : mtp.value(QStringLiteral("args")).toArray())
                specTokens << arg.toString();
        }
        for (const QJsonValue &arg : entry.value(QStringLiteral("extraArgs")).toArray())
            specTokens << arg.toString();
        const QJsonObject spec = entry.value(QStringLiteral("spec")).toObject();
        const bool declaresDraftMtp =
            spec.value(QStringLiteral("type")).toString().contains(QStringLiteral("draft"), Qt::CaseInsensitive)
            || specTokens.contains(QStringLiteral("draft-mtp"), Qt::CaseInsensitive);
        if (!declaresDraftMtp)
            continue;
        const QJsonObject draft = entry.value(QStringLiteral("draftModel")).toObject();
        const QString modelFile =
            entry.value(QStringLiteral("model")).toObject().value(QStringLiteral("file")).toString();
        const bool selfContained = MtpDetection::isSelfContained(modelFile);
        QVERIFY2(selfContained
                     || (!draft.value(QStringLiteral("repo")).toString().isEmpty()
                         && !draft.value(QStringLiteral("file")).toString().isEmpty()),
                 qPrintable(QStringLiteral("%1 declara draft-mtp pero no draftModel repo/file")
                                .arg(id)));
    }
}

void SystemProfilesTests::manager_smallProfilesAreConservative()
{
    ProfileManager pm;
    const auto assertRt = [&](const QString &launchId, int expectedCtx, int maxBatch, int maxLayers) {
        const QVariantMap launch = pm.getLaunchProfile(launchId);
        const QVariantMap rt = pm.getRuntimePreset(launch.value("runtimePresetId").toString());
        QCOMPARE(rt.value("ctx").toInt(), expectedCtx);
        QVERIFY2(rt.value("ctx").toInt() >= 8192,
                 qPrintable(QStringLiteral("%1 ctx=%2").arg(launchId).arg(rt.value("ctx").toInt())));
        QVERIFY2(rt.value("batch").toInt() <= maxBatch,
                 qPrintable(QStringLiteral("%1 batch=%2").arg(launchId).arg(rt.value("batch").toInt())));
        QVERIFY2(rt.value("ubatch").toInt() <= maxBatch,
                 qPrintable(QStringLiteral("%1 ubatch=%2").arg(launchId).arg(rt.value("ubatch").toInt())));
        QVERIFY2(rt.value("gpuLayers").toInt() <= maxLayers,
                 qPrintable(QStringLiteral("%1 gpuLayers=%2")
                                .arg(launchId).arg(rt.value("gpuLayers").toInt())));
    };
    assertRt(QStringLiteral("sys-vram-4-gemma"), 8192, 128, 12);
    assertRt(QStringLiteral("sys-vram-2-gemma"), 8192, 64, 8);
    assertRt(QStringLiteral("sys-vram-2"), 8192, 64, 8);
    assertRt(QStringLiteral("sys-vram-0"), 8192, 128, 0);

    const QVariantMap cpuLaunch = pm.getLaunchProfile(QStringLiteral("sys-vram-0"));
    const QVariantMap cpuRt = pm.getRuntimePreset(cpuLaunch.value("runtimePresetId").toString());
    const QVariantMap cpuModel = pm.getModelProfile(cpuLaunch.value("modelProfileId").toString());
    const QString modelsDir =
        QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/models";
    const QUuid ns(QStringLiteral("a1b2c3d4-e5f6-4a5b-8c7d-0e1f2a3b4c5d"));
    const QString expect = QUuid::createUuidV5(
        ns, QString(modelsDir + "/Qwen3.5-4B/Qwen3.5-4B-Q4_K_M.gguf").toUtf8()).toString(QUuid::WithoutBraces);
    QCOMPARE(cpuModel.value("modelId").toString(), expect);
    QCOMPARE(cpuRt.value("gpuLayers").toInt(), 0);
    QVERIFY2(!cpuRt.value("flashAttention").toBool(),
             "El fallback CPU no debe depender de flash-attn");

    QFile bundle(bundlePath());
    QVERIFY(bundle.open(QIODevice::ReadOnly));
    bool sawCpuKind = false;
    for (const QJsonValue &v : QJsonDocument::fromJson(bundle.readAll()).array()) {
        const QJsonObject o = v.toObject();
        if (o.value(QStringLiteral("id")).toString() != QStringLiteral("sys-vram-0"))
            continue;
        sawCpuKind = true;
        QCOMPARE(o.value(QStringLiteral("binaryKind")).toString(), QStringLiteral("cpu"));
    }
    QVERIFY(sawCpuKind);
}

void SystemProfilesTests::manager_defaultCodingProfileUsesKatCoder()
{
    ProfileManager pm;
    const QVariantMap launch = pm.getLaunchProfile(QStringLiteral("sys-vram-20"));
    QCOMPARE(launch.value(QStringLiteral("name")).toString(),
             QStringLiteral("[coding] 20GB · KAT Coder 2.5 35B-A3B Q4_K_M"));

    const QVariantMap model =
        pm.getModelProfile(launch.value(QStringLiteral("modelProfileId")).toString());
    const QString modelsDir =
        QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/models";
    const QUuid ns(QStringLiteral("a1b2c3d4-e5f6-4a5b-8c7d-0e1f2a3b4c5d"));
    const QString expectedModelId = QUuid::createUuidV5(
        ns, QString(modelsDir
                    + "/KAT-Coder-V2.5-Dev-Q4_K_M-GGUF/"
                      "Kwaipilot_KAT-Coder-V2.5-Dev-Q4_K_M.gguf").toUtf8())
                                        .toString(QUuid::WithoutBraces);
    QCOMPARE(model.value(QStringLiteral("modelId")).toString(), expectedModelId);

    const QVariantMap runtime =
        pm.getRuntimePreset(launch.value(QStringLiteral("runtimePresetId")).toString());
    QCOMPARE(runtime.value(QStringLiteral("ctx")).toInt(), 32768);
    QCOMPARE(runtime.value(QStringLiteral("gpuLayers")).toInt(), 30);
    QCOMPARE(runtime.value(QStringLiteral("batch")).toInt(), 2048);
    QCOMPARE(runtime.value(QStringLiteral("ubatch")).toInt(), 512);
    QCOMPARE(runtime.value(QStringLiteral("cacheType")).toString(), QStringLiteral("q4_0"));

    const QStringList args = launch.value(QStringLiteral("extraArgs")).toStringList();
    const auto valueAfter = [&args](const QString &flag) {
        const int index = args.indexOf(flag);
        return index >= 0 && index + 1 < args.size() ? args.at(index + 1) : QString();
    };
    QCOMPARE(valueAfter(QStringLiteral("--temp")), QStringLiteral("0.60"));
    QCOMPARE(valueAfter(QStringLiteral("--top-p")), QStringLiteral("0.95"));
    QCOMPARE(valueAfter(QStringLiteral("--top-k")), QStringLiteral("20"));
    QCOMPARE(valueAfter(QStringLiteral("--repeat-penalty")), QStringLiteral("1.0"));
    QCOMPARE(valueAfter(QStringLiteral("--presence-penalty")), QStringLiteral("0.0"));
    QCOMPARE(valueAfter(QStringLiteral("--reasoning")), QStringLiteral("on"));
}

void SystemProfilesTests::manager_16gbCodingProfileUsesBenchmarkedKatCoder()
{
    ProfileManager pm;
    const QVariantMap launch = pm.getLaunchProfile(QStringLiteral("sys-vram-16"));
    QCOMPARE(launch.value(QStringLiteral("name")).toString(),
             QStringLiteral("[coding] 16GB · KAT Coder 2.5 35B-A3B Q4_K_M"));

    const QVariantMap model =
        pm.getModelProfile(launch.value(QStringLiteral("modelProfileId")).toString());
    const QString modelsDir =
        QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/models";
    const QUuid ns(QStringLiteral("a1b2c3d4-e5f6-4a5b-8c7d-0e1f2a3b4c5d"));
    const QString expectedModelId = QUuid::createUuidV5(
        ns, QString(modelsDir
                    + "/KAT-Coder-V2.5-Dev-Q4_K_M-GGUF/"
                      "Kwaipilot_KAT-Coder-V2.5-Dev-Q4_K_M.gguf").toUtf8())
                                        .toString(QUuid::WithoutBraces);
    QCOMPARE(model.value(QStringLiteral("modelId")).toString(), expectedModelId);

    const QVariantMap runtime =
        pm.getRuntimePreset(launch.value(QStringLiteral("runtimePresetId")).toString());
    QCOMPARE(runtime.value(QStringLiteral("ctx")).toInt(), 32768);
    QCOMPARE(runtime.value(QStringLiteral("gpuLayers")).toInt(), 999);
    QCOMPARE(runtime.value(QStringLiteral("batch")).toInt(), 512);
    QCOMPARE(runtime.value(QStringLiteral("cacheType")).toString(), QStringLiteral("q4_0"));

    const QStringList args = launch.value(QStringLiteral("extraArgs")).toStringList();
    QVERIFY(args.contains(QStringLiteral("--n-cpu-moe")));
    QCOMPARE(args.value(args.indexOf(QStringLiteral("--n-cpu-moe")) + 1),
             QStringLiteral("18"));
    QCOMPARE(args.value(args.indexOf(QStringLiteral("--reasoning")) + 1),
             QStringLiteral("on"));
}

void SystemProfilesTests::manager_24gbPremiumPromotesThinkingCapAndKeepsMaxCtx()
{
    ProfileManager pm;
    const QVariantMap launch = pm.getLaunchProfile(QStringLiteral("sys-maxq"));
    QCOMPARE(launch.value(QStringLiteral("name")).toString(),
             QStringLiteral("[coding] MAX-Q · ThinkingCap Qwen3.6-27B 131k (visión)"));

    const QVariantMap model =
        pm.getModelProfile(launch.value(QStringLiteral("modelProfileId")).toString());
    const QString modelsDir =
        QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/models";
    const QUuid ns(QStringLiteral("a1b2c3d4-e5f6-4a5b-8c7d-0e1f2a3b4c5d"));
    const QString modelBase = modelsDir + "/ThinkingCap-Qwen3.6-27B-GGUF/";
    QCOMPARE(model.value(QStringLiteral("modelId")).toString(),
             QUuid::createUuidV5(
                 ns, QString(modelBase + "ThinkingCap-Qwen3.6-27B-Q4_K_M.gguf").toUtf8())
                 .toString(QUuid::WithoutBraces));
    QVERIFY(!model.value(QStringLiteral("mmprojId")).toString().isEmpty());

    const QVariantMap runtime =
        pm.getRuntimePreset(launch.value(QStringLiteral("runtimePresetId")).toString());
    QCOMPARE(runtime.value(QStringLiteral("ctx")).toInt(), 131000);
    QCOMPARE(runtime.value(QStringLiteral("gpuLayers")).toInt(), 999);
    QCOMPARE(runtime.value(QStringLiteral("batch")).toInt(), 512);
    QCOMPARE(runtime.value(QStringLiteral("ubatch")).toInt(), 64);
    QCOMPARE(runtime.value(QStringLiteral("cacheType")).toString(), QStringLiteral("q4_0"));

    const QStringList args = launch.value(QStringLiteral("extraArgs")).toStringList();
    const auto valueAfter = [&args](const QString &flag) {
        const int index = args.indexOf(flag);
        return index >= 0 && index + 1 < args.size() ? args.at(index + 1) : QString();
    };
    QCOMPARE(valueAfter(QStringLiteral("--spec-type")), QStringLiteral("draft-mtp"));
    QCOMPARE(valueAfter(QStringLiteral("--spec-draft-n-max")), QStringLiteral("4"));
    QCOMPARE(valueAfter(QStringLiteral("--reasoning")), QStringLiteral("off"));

    const QVariantMap maxCtx = pm.getLaunchProfile(QStringLiteral("sys-maxctx"));
    QCOMPARE(maxCtx.value(QStringLiteral("name")).toString(),
             QStringLiteral("[coding] MAX-CTX · Qwen3.6-27B 262k"));
    const QVariantMap maxCtxRuntime =
        pm.getRuntimePreset(maxCtx.value(QStringLiteral("runtimePresetId")).toString());
    QCOMPARE(maxCtxRuntime.value(QStringLiteral("ctx")).toInt(), 262000);
    const QVariantMap maxCtxModel =
        pm.getModelProfile(maxCtx.value(QStringLiteral("modelProfileId")).toString());
    QVERIFY(maxCtxModel.value(QStringLiteral("mmprojId")).toString().isEmpty());
}

void SystemProfilesTests::controller_recommendsClosestTier()
{
    AppController app;
    // 24GB: maxq/fastgemma son extra (showcase), así que el mejor tier no-extra
    // ≤VRAM es el default coding KAT de 20GB.
    app.setHardwareSummaryForTest(24.0, 128.0, QStringLiteral("NVIDIA GeForce RTX 3090"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-20"));
    // RTX 3080 20GB: mismo tier KAT con offload parcial validado.
    app.setHardwareSummaryForTest(20.0, 64.0, QStringLiteral("NVIDIA GeForce RTX 3080"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-20"));
    app.setHardwareSummaryForTest(10.0, 32.0, QStringLiteral("NVIDIA"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-8-gemma"));
    app.setHardwareSummaryForTest(5.0, 16.0, QStringLiteral("NVIDIA"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-4"));
}

void SystemProfilesTests::controller_recommendedTierIncludesDisplayName()
{
    AppController app;
    app.setHardwareSummaryForTest(8.0, 32.0, QStringLiteral("NVIDIA GeForce RTX 3070"));
    const QVariantMap pick = app.recommendedSystemProfile();
    QCOMPARE(pick.value("launchId").toString(), QStringLiteral("sys-vram-8-gemma"));
    QCOMPARE(pick.value("displayName").toString(),
             QStringLiteral("[general] 8GB · Gemma 4 12B Q3 (visión, MTP)"));
}

void SystemProfilesTests::controller_recommendsCpuWhenNoGpu()
{
    AppController app;
    app.setHardwareSummaryForTest(0.0, 64.0, QStringLiteral("sin GPU"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-0"));
}

void SystemProfilesTests::controller_noneWhenBelowMinimum()
{
    AppController app;
    app.setHardwareSummaryForTest(0.0, 4.0, QStringLiteral("sin GPU"));   // 4GB RAM < 16 del CPU tier
    QVERIFY(app.recommendedSystemProfile().isEmpty());
}

// A 8GB el showcase ofrece elegir: Gemma 12B (visión) vs Qwen3.5 9B (agente),
// o ambos. recommendedSystemProfile sigue siendo el Gemma (default por orden).
void SystemProfilesTests::controller_showcase8gbOffersGemmaAndQwen()
{
    AppController app;
    app.setHardwareSummaryForTest(8.0, 32.0, QStringLiteral("NVIDIA GeForce RTX 3070"));

    // El recomendado único (tier ≤VRAM, no-extra, primero por orden) = Gemma.
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-8-gemma"));

    const QVariantList sc = app.recommendedShowcase();
    QCOMPARE(sc.size(), 2);
    QStringList ids, labels;
    for (const QVariant &v : sc) {
        ids   << v.toMap().value("launchId").toString();
        labels << v.toMap().value("label").toString();
    }
    QVERIFY(ids.contains("sys-vram-8-gemma"));
    QVERIFY(ids.contains("sys-vram-8-qwen-agent"));
    QVERIFY(labels.contains("Visión"));
    QVERIFY(labels.contains("Agente"));
}

// El showcase de 24GB (MAX-Q coding + FAST-GEMMA general) sigue intacto tras
// generalizar el mecanismo por showcaseGroup.
void SystemProfilesTests::controller_showcase24gbUnchanged()
{
    AppController app;
    app.setHardwareSummaryForTest(24.0, 64.0, QStringLiteral("NVIDIA GeForce RTX 4090"));
    const QVariantList sc = app.recommendedShowcase();
    QCOMPARE(sc.size(), 2);
    QStringList ids;
    for (const QVariant &v : sc) ids << v.toMap().value("launchId").toString();
    QVERIFY(ids.contains("sys-maxq"));
    QVERIFY(ids.contains("sys-fastgemma"));
}

void SystemProfilesTests::bundle_lagunaIsOptInAndHardwareGated()
{
    QFile f(bundlePath());
    QVERIFY(f.open(QIODevice::ReadOnly));
    const QJsonArray arr = QJsonDocument::fromJson(f.readAll()).array();
    QJsonObject laguna;
    for (const QJsonValue &v : arr) {
        const QJsonObject o = v.toObject();
        if (o.value(QStringLiteral("id")).toString()
            == QStringLiteral("sys-laguna-s-2-1-q2")) {
            laguna = o;
            break;
        }
    }
    QVERIFY2(!laguna.isEmpty(), "falta el perfil experimental Laguna");
    QVERIFY(laguna.value(QStringLiteral("extra")).toBool());
    QVERIFY(!laguna.value(QStringLiteral("autoCompanion")).toBool());
    QCOMPARE(laguna.value(QStringLiteral("minVramGb")).toInt(), 24);
    QCOMPARE(laguna.value(QStringLiteral("minRamGb")).toInt(), 120);
    QCOMPARE(laguna.value(QStringLiteral("binaryPin")).toString(),
             QStringLiteral("b10087"));

    const QJsonObject model = laguna.value(QStringLiteral("model")).toObject();
    QCOMPARE(model.value(QStringLiteral("file")).toString(),
             QStringLiteral("Laguna-S-2.1-UD-Q2_K_XL.gguf"));
    const QJsonObject runtime = laguna.value(QStringLiteral("runtime")).toObject();
    QCOMPARE(runtime.value(QStringLiteral("ctx")).toInt(), 100000);
    QCOMPARE(runtime.value(QStringLiteral("ubatch")).toInt(), 768);
    const QJsonArray args = laguna.value(QStringLiteral("extraArgs")).toArray();
    QStringList tokens;
    for (const QJsonValue &arg : args)
        tokens << arg.toString();
    const int cpuMoe = tokens.indexOf(QStringLiteral("--n-cpu-moe"));
    QVERIFY(cpuMoe >= 0 && cpuMoe + 1 < tokens.size());
    QCOMPARE(tokens.at(cpuMoe + 1), QStringLiteral("32"));

    // Sigue fuera del recomendado y del showcase premium: es opt-in incluso en
    // la máquina objetivo de 24GB VRAM + 128GB RAM.
    AppController app;
    app.setHardwareSummaryForTest(24.0, 128.0,
                                  QStringLiteral("NVIDIA GeForce RTX 3090"));
    QVERIFY(app.recommendedSystemProfile().value(QStringLiteral("launchId")).toString()
            != QStringLiteral("sys-laguna-s-2-1-q2"));
    const QVariantList showcase = app.recommendedShowcase();
    for (const QVariant &item : showcase)
        QVERIFY(item.toMap().value(QStringLiteral("launchId")).toString()
                != QStringLiteral("sys-laguna-s-2-1-q2"));
}

// Un tier sin grupo de showcase (ej. 4GB) no ofrece "uno/otro/ambos".
void SystemProfilesTests::controller_showcaseEmptyWhenNoSiblings()
{
    AppController app;
    app.setHardwareSummaryForTest(5.0, 16.0, QStringLiteral("NVIDIA"));
    QVERIFY(app.recommendedShowcase().isEmpty());
}

// El chat-template de Gemma4 no es un archivo cualquiera: llama.cpp lo clasifica
// leyendo su TEXTO. Busca "'<|tool_call>call:'" para tomar el path nativo
// (peg-gemma4) en vez del parseo genérico, y el comentario "OpenAI Chat
// Completions:" para decidir que NO es una versión vieja que necesite
// workarounds de compatibilidad. Un reemplazo desde upstream que pierda
// cualquiera de los dos degrada el tool-calling en silencio: el server arranca,
// responde 200, y sólo se nota porque el modelo llama peor a las tools.
// Además el archivo está duplicado (qrc bundle + copia versionada que usan los
// perfiles de usuario vía --chat-template-file): deben ser idénticos.
void SystemProfilesTests::bundle_gemma4TemplateKeepsLlamaCppMarkers()
{
    const QDir repo = QFileInfo(bundlePath()).dir();   // .../assets
    const QString bundled = repo.absoluteFilePath(
        QStringLiteral("chat-templates/gemma4-tools-fixed.jinja"));
    QFile f(bundled);
    QVERIFY2(f.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("no se pudo abrir %1").arg(bundled)));
    const QString tpl = QString::fromUtf8(f.readAll());
    f.close();

    QVERIFY2(tpl.contains(QStringLiteral("'<|tool_call>call:'")),
             "sin este literal llama.cpp no toma el path nativo peg-gemma4");
    QVERIFY2(tpl.contains(QStringLiteral("OpenAI Chat Completions:")),
             "sin este comentario llama.cpp trata el template como outdated");

    // La copia del repo root (a la que apuntan los perfiles de usuario) no puede
    // divergir de la bundleada en el qrc.
    const QString rootCopy = QDir(repo.absoluteFilePath(QStringLiteral("..")))
                                 .absoluteFilePath(QStringLiteral("chat-templates/gemma4-tools-fixed.jinja"));
    QFile g(rootCopy);
    QVERIFY2(g.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("no se pudo abrir %1").arg(rootCopy)));
    const QString rootTpl = QString::fromUtf8(g.readAll());
    g.close();
    QCOMPARE(rootTpl, tpl);

    // Todos los perfiles Gemma 4 deben forzar la plantilla canónica. Dejar que
    // alguno use sólo el metadata embebido hace que un GGUF descargado antes de
    // la corrección de Google conserve silenciosamente el tool-calling viejo.
    QFile bundle(bundlePath());
    QVERIFY2(bundle.open(QIODevice::ReadOnly), "no se pudo abrir system_profiles.json");
    const QJsonArray profiles = QJsonDocument::fromJson(bundle.readAll()).array();
    int gemmaProfiles = 0;
    bool promotedHeretic = false;
    for (const QJsonValue &value : profiles) {
        const QJsonObject profile = value.toObject();
        const QJsonObject model = profile.value(QStringLiteral("model")).toObject();
        const QString identity = model.value(QStringLiteral("repo")).toString()
                                 + QLatin1Char('/')
                                 + model.value(QStringLiteral("file")).toString();
        if (!identity.contains(QStringLiteral("gemma-4"), Qt::CaseInsensitive))
            continue;
        ++gemmaProfiles;
        QCOMPARE(profile.value(QStringLiteral("chatTemplate")).toString(),
                 QStringLiteral("gemma4-tools-fixed.jinja"));
        if (profile.value(QStringLiteral("id")).toString() == QStringLiteral("sys-vram-4-gemma")) {
            QCOMPARE(model.value(QStringLiteral("repo")).toString(),
                     QStringLiteral("SC117/gemma-4-E4B-it-heretic-QAT-GGUF"));
            QCOMPARE(model.value(QStringLiteral("file")).toString(),
                     QStringLiteral("gemma-4-E4B-it-heretic-QAT-UD-Q4_K_XL.gguf"));
            promotedHeretic = true;
        }
    }
    QCOMPARE(gemmaProfiles, 4);
    QVERIFY(promotedHeretic);
}

void SystemProfilesTests::bundle_ultraQAndHybridAreWiredAndOptIn()
{
    QFile bundle(bundlePath());
    QVERIFY(bundle.open(QIODevice::ReadOnly));
    const QJsonArray profiles = QJsonDocument::fromJson(bundle.readAll()).array();
    ProfileManager pm;
    QJsonObject ultra, ultraExternal, hybrid;
    for (const QJsonValue &value : profiles) {
        const QJsonObject profile = value.toObject();
        if (profile.value("id").toString() == QLatin1String("sys-ultraq-dsv4-0731-iq3s")) ultra = profile;
        if (profile.value("id").toString()
            == QLatin1String("sys-ultraq-dsv4-0731-iq3s-dspark-external"))
            ultraExternal = profile;
        if (profile.value("id").toString() == QLatin1String("sys-hybrid-ultraq-maxq")) hybrid = profile;
    }
    QVERIFY(!ultra.isEmpty());
    QVERIFY(ultra.value("extra").toBool());
    QVERIFY(!ultra.value("autoCompanion").toBool());
    QCOMPARE(ultra.value("minimumBinaryBuild").toInt(), 10228);
    QCOMPARE(ultra.value("reasoningEffort").toString(), QStringLiteral("high"));
    QCOMPARE(ultra.value("reasoningBudget").toInt(), 8192);
    QCOMPARE(ultra.value("contextPresets").toArray().size(), 5);
    QCOMPARE(ultra.value("minRamGb").toInt(), 120);
    const QJsonObject model = ultra.value("model").toObject();
    QCOMPARE(model.value("repo").toString(), QStringLiteral("unsloth/DeepSeek-V4-Flash-0731-GGUF"));
    QCOMPARE(model.value("files").toArray().size(), 4);
    QCOMPARE(model.value("file").toString(),
             QStringLiteral("DeepSeek-V4-Flash-0731-UD-IQ3_S-00001-of-00004.gguf"));
    QVERIFY(ultra.value("runtime").toObject().value("mmap").toBool());
    QStringList args;
    for (const QJsonValue &v : ultra.value("extraArgs").toArray()) args << v.toString();
    QCOMPARE(args.value(args.indexOf("--n-cpu-moe") + 1), QStringLiteral("39"));
    QCOMPARE(args.value(args.indexOf("--fit-target") + 1), QStringLiteral("512"));
    QCOMPARE(args.value(args.indexOf("--temp") + 1), QStringLiteral("0.60"));
    QCOMPARE(args.value(args.indexOf("--top-p") + 1), QStringLiteral("0.95"));
    QCOMPARE(args.value(args.indexOf("--top-k") + 1), QStringLiteral("20"));
    QCOMPARE(args.value(args.indexOf("--min-p") + 1), QStringLiteral("0.0"));
    QCOMPARE(args.value(args.indexOf("--repeat-penalty") + 1), QStringLiteral("1.0"));
    QCOMPARE(args.value(args.indexOf("--presence-penalty") + 1), QStringLiteral("0.0"));
    QVERIFY(args.contains(QStringLiteral("--no-warmup")));
    QCOMPARE(args.value(args.indexOf("--spec-type") + 1), QStringLiteral("draft-dspark"));
    QCOMPARE(args.value(args.indexOf("--spec-draft-n-max") + 1), QStringLiteral("5"));
    QCOMPARE(ultra.value("benchmarkVariants").toArray().size(), 12);

    QVERIFY(!ultraExternal.isEmpty());
    QVERIFY(ultraExternal.value("extra").toBool());
    QVERIFY(!ultraExternal.value("autoCompanion").toBool());
    QCOMPARE(ultraExternal.value("minimumBinaryBuild").toInt(), 10228);
    QCOMPARE(ultraExternal.value("model").toObject().value("file").toString(),
             model.value("file").toString());
    const QJsonObject externalDraft = ultraExternal.value("draftModel").toObject();
    QCOMPARE(externalDraft.value("repo").toString(),
             QStringLiteral("am17an/DeepseekV4-Flash-20260731-DSpark"));
    QCOMPARE(externalDraft.value("file").toString(),
             QStringLiteral("DeepseekV4-Flash-20260731-DSpark.gguf"));
    const QJsonObject externalSpec = ultraExternal.value("spec").toObject();
    QCOMPARE(externalSpec.value("type").toString(), QStringLiteral("draft-dspark"));
    QCOMPARE(externalSpec.value("draftNgl").toString(), QStringLiteral("auto"));
    QCOMPARE(externalSpec.value("draftNMax").toInt(), 5);
    QStringList externalArgs;
    for (const QJsonValue &v : ultraExternal.value("extraArgs").toArray())
        externalArgs << v.toString();
    QCOMPARE(externalArgs.value(externalArgs.indexOf("--spec-type") + 1),
             QStringLiteral("draft-dspark"));
    QVERIFY(!externalArgs.contains(QStringLiteral("--spec-draft-model")));

    const QVariantMap externalLaunch =
        pm.getLaunchProfile(QStringLiteral("sys-ultraq-dsv4-0731-iq3s-dspark-external"));
    const QVariantMap externalModel =
        pm.getModelProfile(externalLaunch.value("modelProfileId").toString());
    QVERIFY(!externalModel.value("draftModelId").toString().isEmpty());
    QCOMPARE(externalModel.value("specType").toString(), QStringLiteral("draft-dspark"));
    QCOMPARE(externalModel.value("specDraftNgl").toString(), QStringLiteral("auto"));
    QCOMPARE(externalModel.value("specDraftNMax").toInt(), 5);

    QVERIFY(!hybrid.isEmpty());
    QCOMPARE(hybrid.value("plannerProfileId").toString(),
             QStringLiteral("sys-ultraq-dsv4-0731-iq3s"));
    QCOMPARE(hybrid.value("hybridMode").toString(), QStringLiteral("sequential"));
    QCOMPARE(hybrid.value("binaryKind").toString(), QStringLiteral("official"));
    const QVariantMap launch = pm.getLaunchProfile(QStringLiteral("sys-hybrid-ultraq-maxq"));
    QCOMPARE(launch.value("plannerProfileId").toString(),
             QStringLiteral("sys-ultraq-dsv4-0731-iq3s"));
    QCOMPARE(launch.value("hybridMode").toString(), QStringLiteral("sequential"));

    const QVariantMap balanced =
        pm.getLaunchProfile(QStringLiteral("sys-bench-ultraq-b4096-u1024-ds5"));
    QVERIFY(balanced.value("system").toBool());
    const QVariantMap balancedRt =
        pm.getRuntimePreset(balanced.value("runtimePresetId").toString());
    QCOMPARE(balancedRt.value("batch").toInt(), 4096);
    QCOMPARE(balancedRt.value("ubatch").toInt(), 1024);
    QCOMPARE(balanced.value("modelProfileId").toString(),
             QStringLiteral("sysmodel-sys-bench-ultraq-b4096-u1024-ds5"));
    const QVariantMap balancedModel =
        pm.getModelProfile(balanced.value("modelProfileId").toString());
    const QVariantMap ultraLaunch =
        pm.getLaunchProfile(QStringLiteral("sys-ultraq-dsv4-0731-iq3s"));
    const QVariantMap ultraModel =
        pm.getModelProfile(ultraLaunch.value("modelProfileId").toString());
    QCOMPARE(balancedModel.value("modelId").toString(),
             ultraModel.value("modelId").toString());
    QCOMPARE(balanced.value("extraArgs").toStringList().value(
                 balanced.value("extraArgs").toStringList().indexOf("--spec-draft-n-max") + 1),
             QStringLiteral("5"));

    const QVariantMap noSpec =
        pm.getLaunchProfile(QStringLiteral("sys-bench-ultraq-b4096-u1024-nospec"));
    QVERIFY(!noSpec.value("extraArgs").toStringList().contains(QStringLiteral("--spec-type")));
    QVERIFY(!noSpec.value("extraArgs").toStringList().contains(
        QStringLiteral("--spec-draft-n-max")));

    const QVariantMap moe35 =
        pm.getLaunchProfile(QStringLiteral("sys-bench-ultraq-b4096-u1024-moe35"));
    const QStringList moeArgs = moe35.value("extraArgs").toStringList();
    QCOMPARE(moeArgs.value(moeArgs.indexOf("--n-cpu-moe") + 1), QStringLiteral("35"));
}

QTEST_MAIN(SystemProfilesTests)
#include "test_system_profiles.moc"
