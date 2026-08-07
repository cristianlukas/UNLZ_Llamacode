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
#include <QRegularExpression>
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
    void bundle_ultraQ48gbIsDualGpuVariantOfUltraQ();
    void controller_launchMenuGatesByTotalVramAcrossGpus();
    void bundle_48gbFamilyIsBenchmarkableAndDualGpu();
    void controller_duplicateBakesResolvedBinary();

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
    QCOMPARE(sys, 61); // tiers base + extras + familia 48GB (18) + DSpark externo + 26 variantes bench
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
    // La visión intencional se declara con "vision": true en el bundle, no por el
    // texto del displayName: un perfil puede llamarse como el usuario quiera
    // ("ThinkingCap+MTP-7-8-26") y seguir cargando mmproj a propósito. El chequeo
    // sigue existiendo para lo que importa — que nadie arrastre un mmproj sin
    // querer, porque cuesta VRAM.
    QSet<QString> declaresVision;
    {
        QFile bundle(bundlePath());
        QVERIFY(bundle.open(QIODevice::ReadOnly));
        for (const QJsonValue &v : QJsonDocument::fromJson(bundle.readAll()).array()) {
            const QJsonObject o = v.toObject();
            if (o.value(QStringLiteral("vision")).toBool())
                declaresVision.insert(o.value(QStringLiteral("id")).toString());
        }
    }

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
                                     || name.contains(QStringLiteral("vision"))
                                     || declaresVision.contains(launchId);
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

// El perfil de 48 GB (2x RTX 3090) reusa los mismos shards que ULTRA-Q y solo
// cambia lo que la VRAM extra habilita: KV q8_0, menos expertos en RAM, batch
// ganador del barrido y reparto explicito entre las dos placas.
void SystemProfilesTests::bundle_ultraQ48gbIsDualGpuVariantOfUltraQ()
{
    QFile bundle(bundlePath());
    QVERIFY(bundle.open(QIODevice::ReadOnly));
    const QJsonArray profiles = QJsonDocument::fromJson(bundle.readAll()).array();
    QJsonObject ultra, dual;
    for (const QJsonValue &value : profiles) {
        const QJsonObject profile = value.toObject();
        const QString id = profile.value("id").toString();
        if (id == QLatin1String("sys-ultraq-dsv4-0731-iq3s")) ultra = profile;
        if (id == QLatin1String("sys-ultraq-dsv4-0731-iq3s-48gb")) dual = profile;
    }
    QVERIFY(!dual.isEmpty());
    QVERIFY(dual.value("extra").toBool());
    QVERIFY(!dual.value("autoCompanion").toBool());
    QCOMPARE(dual.value("minVramGb").toInt(), 48);
    QCOMPARE(dual.value("minRamGb").toInt(), 120);
    QCOMPARE(dual.value("minimumBinaryBuild").toInt(), 10228);
    QCOMPARE(dual.value("model").toObject(), ultra.value("model").toObject());

    // Valores medidos contra el server real: ver el comment del perfil. Cambiarlos
    // sin volver a medir es lo que hacia crashear al server (OOM o illegal memory
    // access), asi que el test los clava.
    const QJsonObject rt = dual.value("runtime").toObject();
    QCOMPARE(rt.value("batch").toInt(), 4096);
    QCOMPARE(rt.value("ubatch").toInt(), 1024);
    QCOMPARE(rt.value("kv").toString(), QStringLiteral("q4_0")); // q8_0 deja CUDA0 al borde
    QVERIFY(rt.value("mmap").toBool());     // --no-mmap => OOM (116 GB en 128 de RAM)
    QVERIFY(!rt.value("mlock").toBool());   // mlock crashea

    QStringList args;
    for (const QJsonValue &v : dual.value("extraArgs").toArray()) args << v.toString();
    QCOMPARE(args.value(args.indexOf("--cache-type-k") + 1), QStringLiteral("q4_0"));
    QCOMPARE(args.value(args.indexOf("--cache-type-v") + 1), QStringLiteral("q4_0"));
    QCOMPARE(args.value(args.indexOf("--threads-batch") + 1), QStringLiteral("16"));
    QCOMPARE(args.value(args.indexOf("--spec-type") + 1), QStringLiteral("draft-dspark"));
    QCOMPARE(args.value(args.indexOf("--spec-draft-n-max") + 1), QStringLiteral("5"));

    // El reparto va con -ot explicito, NO con --n-cpu-moe: en multi-GPU el
    // n-cpu-moe manda todas las capas pesadas a una placa (OOM) y, aun
    // balanceado, mata la inferencia con illegal memory access.
    QVERIFY(!args.contains(QStringLiteral("--n-cpu-moe")));
    QCOMPARE(args.value(args.indexOf("--split-mode") + 1), QStringLiteral("layer"));
    // --fit off, no --fit-target: con el target el server muere en el primer prefill.
    QCOMPARE(args.value(args.indexOf("--fit") + 1), QStringLiteral("off"));
    QVERIFY(!args.contains(QStringLiteral("--fit-target")));

    // CLAVADO A PROPOSITO: --tensor-split 1,0, o sea las 44 capas base enteras en
    // CUDA0 y sólo expertos en CUDA1. Con 1,1 (repartir también las capas base)
    // este modelo devuelve TEXTO CORRUPTO — a "cuál es la capital de Francia"
    // contesta ".#/!)". No crashea: responde basura con métricas perfectas, así que
    // ningún test de arranque lo agarra. Sólo pasa con DeepSeek (expertos en RAM +
    // capas base repartidas); ThinkingCap y KAT con 1,1 responden bien.
    QCOMPARE(args.value(args.indexOf("--tensor-split") + 1), QStringLiteral("1,0"));
    const QStringList ot = args.filter(QStringLiteral("_exps"));
    QCOMPARE(ot.size(), 2);
    QVERIFY(ot.at(0).endsWith(QStringLiteral("=CUDA1")));   // sólo expertos cruzan
    QVERIFY(!ot.at(0).contains(QStringLiteral("=CUDA0")));
    QVERIFY(ot.at(1).endsWith(QStringLiteral("=CPU")));     // -ot es first-match-wins:
                                                            // el catch-all va ULTIMO
    // El regex tiene que nombrar el tensor exacto: con ffn_.*_exps arrastra tensores
    // que no deben moverse y el server muere con illegal memory access.
    for (const QString &rule : ot)
        QVERIFY(rule.contains(QStringLiteral("ffn_(gate|up|down)_exps\\.weight")));

    // El launch derivado tiene que llegar con esos valores, no solo el bundle.
    ProfileManager pm;
    const QVariantMap launch =
        pm.getLaunchProfile(QStringLiteral("sys-ultraq-dsv4-0731-iq3s-48gb"));
    QVERIFY(launch.value("system").toBool());
    const QVariantMap preset = pm.getRuntimePreset(launch.value("runtimePresetId").toString());
    QCOMPARE(preset.value("batch").toInt(), 4096);
    QCOMPARE(preset.value("ubatch").toInt(), 1024);
    const QStringList launchArgs = launch.value("extraArgs").toStringList();
    QCOMPARE(launchArgs.filter(QStringLiteral("_exps")).size(), 2);
    QVERIFY(!launchArgs.contains(QStringLiteral("--n-cpu-moe")));
    QCOMPARE(launchArgs.value(launchArgs.indexOf("--tensor-split") + 1), QStringLiteral("1,0"));

    // Mismo modelo fisico que ULTRA-Q: no re-descarga los 116 GB de shards.
    const QVariantMap ultraLaunch =
        pm.getLaunchProfile(QStringLiteral("sys-ultraq-dsv4-0731-iq3s"));
    QCOMPARE(pm.getModelProfile(launch.value("modelProfileId").toString()).value("modelId"),
             pm.getModelProfile(ultraLaunch.value("modelProfileId").toString()).value("modelId"));
}

// La familia 48GB son pares comparables para benchmarkear (DeepSeek con y sin
// DSpark, ThinkingCap 131k/196k, KAT 131k/262k). Todos reparten entre las dos
// placas y todos declaran 48 GB, así que el menú los muestra o los esconde juntos.
void SystemProfilesTests::bundle_48gbFamilyIsBenchmarkableAndDualGpu()
{
    QFile bundle(bundlePath());
    QVERIFY(bundle.open(QIODevice::ReadOnly));
    const QJsonArray profiles = QJsonDocument::fromJson(bundle.readAll()).array();

    const QStringList expected{
        QStringLiteral("sys-ultraq-dsv4-0731-iq3s-48gb"),   // DeepSeek + DSpark
        QStringLiteral("sys-48-dsv4-nospec"),               // DeepSeek sin DSpark
        QStringLiteral("sys-48-dsv4-iq2m"),                 // quant chico: mas expertos en VRAM
        QStringLiteral("sys-48-thinkingcap-131k"),
        QStringLiteral("sys-48-thinkingcap-196k"),
        QStringLiteral("sys-48-katcoder-262k"),
        QStringLiteral("sys-48-katcoder-131k"),
        QStringLiteral("sys-48-katcoder-393k-nographs"),
        QStringLiteral("sys-48-thinkingcap-mtp"),      // el ganador del barrido
        QStringLiteral("sys-48-hybrid-tc-kat"),        // planner TC+MTP, ejecutor KAT
    };
    QHash<QString, QJsonObject> found;
    for (const QJsonValue &v : profiles) {
        const QJsonObject o = v.toObject();
        if (expected.contains(o.value("id").toString()))
            found.insert(o.value("id").toString(), o);
    }
    QCOMPARE(found.size(), expected.size());

    for (const QString &id : expected) {
        const QJsonObject o = found.value(id);
        QCOMPARE(o.value("minVramGb").toInt(), 48);
        QVERIFY(o.value("extra").toBool());              // opt-in, no auto-recomendados
        QVERIFY(!o.value("autoCompanion").toBool());     // no arrastran descargas
        QVERIFY(!o.value("comment").toString().isEmpty());
        QStringList args;
        for (const QJsonValue &a : o.value("extraArgs").toArray()) args << a.toString();
        // Reparto entre las dos placas + el --fit off que evita el crash de prefill.
        QCOMPARE(args.value(args.indexOf("--split-mode") + 1), QStringLiteral("layer"));
        QCOMPARE(args.value(args.indexOf("--fit") + 1), QStringLiteral("off"));
        // DeepSeek va 1,0 (capas base enteras en CUDA0): con 1,1 devuelve texto
        // corrupto sin crashear. El resto entra entero en VRAM y reparte 1,1.
        const bool deepSeek = id.contains(QStringLiteral("dsv4"))
                           || id.contains(QStringLiteral("ultraq"));
        QCOMPARE(args.value(args.indexOf("--tensor-split") + 1),
                 deepSeek ? QStringLiteral("1,0") : QStringLiteral("1,1"));
        QVERIFY(o.value("runtime").toObject().value("flashAttn").toBool());
    }

    // Los que entran enteros en VRAM no llevan reparto de expertos (no hay offload
    // a RAM); los de DeepSeek sí, porque el modelo son ~116 GB.
    for (const QString &id : expected) {
        QStringList args;
        for (const QJsonValue &a : found.value(id).value("extraArgs").toArray())
            args << a.toString();
        const bool isDeepSeek = id.contains(QStringLiteral("dsv4"))
                             || id.contains(QStringLiteral("ultraq"));
        QCOMPARE(args.filter(QStringLiteral("_exps")).size(), isDeepSeek ? 2 : 0);
    }

    // ThinkingCap conserva la visión (mmproj) y KAT usa el KV fino que habilitan
    // los 48 GB — es justamente lo que el tier de 24 GB no puede pagar.
    QVERIFY(!found.value(QStringLiteral("sys-48-thinkingcap-196k"))
                 .value("model").toObject().value("mmprojFile").toString().isEmpty());
    QCOMPARE(found.value(QStringLiteral("sys-48-katcoder-262k"))
                 .value("runtime").toObject().value("kv").toString(),
             QStringLiteral("q8_0"));
    // 196k es el techo medido de ThinkingCap: a 262144 el server crashea.
    QCOMPARE(found.value(QStringLiteral("sys-48-thinkingcap-196k"))
                 .value("runtime").toObject().value("ctx").toInt(), 196608);

    // Ningún perfil de DeepSeek puede mandar expertos a CUDA0: con --tensor-split
    // 1,0 esa placa tiene las 44 capas base y el KV, y agregarle expertos la
    // desborda. CUDA1 recibe sólo expertos, y por eso sus capas van >= 22 (las de
    // la mitad de arriba), que es donde el reparto quedó verificado.
    for (const QString &id : expected) {
        if (!id.contains(QStringLiteral("dsv4")) && !id.contains(QStringLiteral("ultraq")))
            continue;
        QStringList args;
        for (const QJsonValue &a : found.value(id).value("extraArgs").toArray())
            args << a.toString();
        for (const QString &rule : args.filter(QStringLiteral("_exps"))) {
            QVERIFY2(!rule.endsWith(QStringLiteral("=CUDA0")), qPrintable(id));
            if (!rule.endsWith(QStringLiteral("=CUDA1"))) continue;  // catch-all a CPU
            // Sólo los números del selector de capas: el "=CUDA0"/"=CUDA1" del final
            // también tiene dígitos y no es una capa.
            const QString layers = rule.left(rule.indexOf(QStringLiteral(".ffn_")));
            static const QRegularExpression num(QStringLiteral("\\d+"));
            auto it = num.globalMatch(layers);
            while (it.hasNext()) {
                const int layer = it.next().captured().toInt();
                QVERIFY2(layer >= 22, qPrintable(id + QStringLiteral(": ") + rule));
            }
        }
    }

    // El perfil IQ2_M apunta a OTRO quant (90,9 GB contra 116), que es lo único que
    // puede bajar el tráfico a RAM — el cuello del decode. Si alguien lo hace
    // apuntar a los shards del IQ3_S deja de tener sentido: sería el perfil base
    // con más residencia de la que entra.
    const QJsonObject iq2 = found.value(QStringLiteral("sys-48-dsv4-iq2m"));
    QCOMPARE(iq2.value("model").toObject().value("quant").toString(),
             QStringLiteral("UD-IQ2_M"));
    QCOMPARE(iq2.value("model").toObject().value("files").toArray().size(), 3);
    QVERIFY(iq2.value("folder").toString().contains(QStringLiteral("IQ2_M")));
    // Y aprovecha el quant chico para residir más expertos que el base (16 vs 12).
    QStringList iq2Args;
    for (const QJsonValue &a : iq2.value("extraArgs").toArray()) iq2Args << a.toString();
    const QStringList iq2Ot = iq2Args.filter(QStringLiteral("=CUDA1"));
    QCOMPARE(iq2Ot.size(), 1);
    QStringList baseArgs;
    for (const QJsonValue &a : found.value(QStringLiteral("sys-ultraq-dsv4-0731-iq3s-48gb"))
                                  .value("extraArgs").toArray())
        baseArgs << a.toString();
    const QStringList baseOt = baseArgs.filter(QStringLiteral("=CUDA1"));
    QVERIFY(iq2Ot.at(0).count(u'|') > baseOt.at(0).count(u'|'));

    // Cada modelo trae su barrido de variantes para benchmarkear (heredan del base
    // y sólo cambian una palanca). Sin ellas el usuario no puede comparar nada.
    QCOMPARE(found.value(QStringLiteral("sys-48-thinkingcap-196k"))
                 .value("benchmarkVariants").toArray().size(), 4);
    QCOMPARE(found.value(QStringLiteral("sys-48-katcoder-262k"))
                 .value("benchmarkVariants").toArray().size(), 4);

    // Todos tienen que llegar al menú como perfiles de sistema lanzables, incluidas
    // las variantes expandidas.
    ProfileManager pm;
    QStringList launchable = expected;
    launchable << QStringLiteral("sys-bench-48-tc-mtp")
               << QStringLiteral("sys-bench-48-kat-f16")
               << QStringLiteral("sys-bench-48-kat-noreason");
    for (const QString &id : launchable) {
        const QVariantMap launch = pm.getLaunchProfile(id);
        QVERIFY2(launch.value("system").toBool(), qPrintable(id));
        QVERIFY2(!launch.value("modelProfileId").toString().isEmpty(), qPrintable(id));
    }

    // Los tres modelos medidos el 2026-08-07 quedan con nombre propio y fecha para
    // poder identificarlos después, y el híbrido junta a los dos ganadores:
    // ThinkingCap+MTP (10/10) planifica y KAT (9/10 pero a 110 t/s) ejecuta.
    QCOMPARE(found.value(QStringLiteral("sys-48-thinkingcap-mtp")).value("displayName").toString(),
             QStringLiteral("ThinkingCap+MTP-7-8-26"));
    QCOMPARE(found.value(QStringLiteral("sys-48-katcoder-262k")).value("displayName").toString(),
             QStringLiteral("KAT-Coder-7-8-26"));
    QCOMPARE(found.value(QStringLiteral("sys-48-dsv4-nospec")).value("displayName").toString(),
             QStringLiteral("DeepSeek V4-7-8-26"));

    const QJsonObject hyb = found.value(QStringLiteral("sys-48-hybrid-tc-kat"));
    QCOMPARE(hyb.value("plannerProfileId").toString(), QStringLiteral("sys-48-thinkingcap-mtp"));
    QCOMPARE(hyb.value("hybridMode").toString(), QStringLiteral("sequential"));
    // El ejecutor es KAT: mismo modelo que el perfil de KAT, no el de ThinkingCap.
    QCOMPARE(hyb.value("model").toObject().value("file").toString(),
             found.value(QStringLiteral("sys-48-katcoder-262k"))
                 .value("model").toObject().value("file").toString());
    // El planner tiene que existir y traer MTP, que es lo que lo hace rendir.
    QStringList mtpArgs2;
    for (const QJsonValue &a : found.value(QStringLiteral("sys-48-thinkingcap-mtp"))
                                   .value("extraArgs").toArray())
        mtpArgs2 << a.toString();
    QCOMPARE(mtpArgs2.value(mtpArgs2.indexOf("--spec-type") + 1), QStringLiteral("draft-mtp"));
    QVERIFY(!found.value(QStringLiteral("sys-48-thinkingcap-mtp"))
                 .value("model").toObject().value("mmprojFile").toString().isEmpty());

    // 393k sólo arranca con los CUDA graphs apagados, y eso viaja por env: si el
    // env se pierde, el server muere con "invalid program counter" en el primer
    // prompt. Es la única palanca del tier que no es un flag de línea de comandos.
    const QJsonObject k393 = found.value(QStringLiteral("sys-48-katcoder-393k-nographs"));
    QCOMPARE(k393.value("runtime").toObject().value("ctx").toInt(), 393216);
    QCOMPARE(k393.value("env").toObject().value("GGML_CUDA_DISABLE_GRAPHS").toString(),
             QStringLiteral("1"));
    const QVariantMap k393Launch =
        pm.getLaunchProfile(QStringLiteral("sys-48-katcoder-393k-nographs"));
    QCOMPARE(k393Launch.value("envOverrides").toMap()
                 .value(QStringLiteral("GGML_CUDA_DISABLE_GRAPHS")).toString(),
             QStringLiteral("1"));
    // Y nadie más lo lleva: apagar los graphs cuesta ~21% de decode.
    for (const QString &id : expected) {
        if (id == QStringLiteral("sys-48-katcoder-393k-nographs")) continue;
        QVERIFY2(found.value(id).value("env").toObject().isEmpty(), qPrintable(id));
    }

    // Las variantes tienen que llegar con la palanca aplicada, no sólo declarada.
    const QStringList mtpArgs =
        pm.getLaunchProfile(QStringLiteral("sys-bench-48-tc-mtp")).value("extraArgs").toStringList();
    QCOMPARE(mtpArgs.value(mtpArgs.indexOf("--spec-type") + 1), QStringLiteral("draft-mtp"));
    const QVariantMap f16 = pm.getLaunchProfile(QStringLiteral("sys-bench-48-kat-f16"));
    QCOMPARE(pm.getRuntimePreset(f16.value("runtimePresetId").toString())
                 .value("cacheType").toString(),
             QStringLiteral("f16"));
    const QStringList f16Args = f16.value("extraArgs").toStringList();
    QCOMPARE(f16Args.value(f16Args.indexOf("--cache-type-k") + 1), QStringLiteral("f16"));
}

// El menú de Lanzar gatea por VRAM TOTAL, no por la placa más grande: llama.cpp
// reparte por capas, asi que 2x24 GB habilita un perfil que pide 48.
void SystemProfilesTests::controller_launchMenuGatesByTotalVramAcrossGpus()
{
    const QString id = QStringLiteral("sys-ultraq-dsv4-0731-iq3s-48gb");
    auto idsOf = [](const QVariantList &menu) {
        QStringList out;
        for (const QVariant &v : menu) out << v.toMap().value("id").toString();
        return out;
    };

    AppController single;
    single.setHardwareSummaryForTest(24.0, 128.0, QStringLiteral("NVIDIA GeForce RTX 3090"));
    const QStringList singleIds = idsOf(single.launchMenu());
    QVERIFY(singleIds.contains(QStringLiteral("sys-ultraq-dsv4-0731-iq3s")));
    QVERIFY(!singleIds.contains(id));

    AppController dual;
    dual.setHardwareSummaryForTest(24.0, 128.0, QStringLiteral("NVIDIA GeForce RTX 3090"), 48.0, 2);
    const QVariantList dualMenu = dual.launchMenu();
    QVERIFY(idsOf(dualMenu).contains(id));
    for (const QVariant &v : dualMenu) {
        const QVariantMap m = v.toMap();
        if (m.value("id").toString() != id) continue;
        QCOMPARE(m.value("minVram").toDouble(), 48.0);
    }
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
    QCOMPARE(ultra.value("benchmarkVariants").toArray().size(), 26);

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
        pm.getLaunchProfile(QStringLiteral("sys-bench-ultraq-b8192-u2048-ds5"));
    QVERIFY(balanced.value("system").toBool());
    const QVariantMap balancedRt =
        pm.getRuntimePreset(balanced.value("runtimePresetId").toString());
    QCOMPARE(balancedRt.value("batch").toInt(), 8192);
    QCOMPARE(balancedRt.value("ubatch").toInt(), 2048);
    QCOMPARE(balanced.value("modelProfileId").toString(),
             QStringLiteral("sysmodel-sys-bench-ultraq-b8192-u2048-ds5"));
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

    const QVariantMap moe43 =
        pm.getLaunchProfile(QStringLiteral("sys-bench-ultraq-b4096-u1024-moe43"));
    const QStringList moeArgs = moe43.value("extraArgs").toStringList();
    QCOMPARE(moeArgs.value(moeArgs.indexOf("--n-cpu-moe") + 1), QStringLiteral("43"));

    // Variantes de investigación de DSpark sobre el batch ganador (B8192·U2048).
    auto argsOf = [&pm](const char *id) {
        return pm.getLaunchProfile(QString::fromLatin1(id)).value("extraArgs").toStringList();
    };
    // Control: el batch ganador debe quedar SIN speculative, o no mide nada.
    const QStringList wideNoSpec = argsOf("sys-bench-ultraq-b8192-u2048-nospec");
    QVERIFY(!wideNoSpec.isEmpty());
    QVERIFY(!wideNoSpec.contains(QStringLiteral("--spec-type")));
    QVERIFY(!wideNoSpec.contains(QStringLiteral("--spec-draft-n-max")));
    // El corte por confianza se agrega sin perder el resto de la config de DSpark.
    const QStringList pmin = argsOf("sys-bench-ultraq-b8192-u2048-ds5-pmin05");
    QCOMPARE(pmin.value(pmin.indexOf("--spec-type") + 1), QStringLiteral("draft-dspark"));
    QCOMPARE(pmin.value(pmin.indexOf("--spec-draft-n-max") + 1), QStringLiteral("5"));
    QCOMPARE(pmin.value(pmin.indexOf("--spec-draft-p-min") + 1), QStringLiteral("0.5"));
    // El offload del draft es independiente del offload del target.
    const QStringList draftGpu = argsOf("sys-bench-ultraq-b8192-u2048-ds5-draftgpu");
    QCOMPARE(draftGpu.value(draftGpu.indexOf("--n-cpu-moe") + 1), QStringLiteral("39"));
    QCOMPARE(draftGpu.value(draftGpu.indexOf("--spec-draft-n-cpu-moe") + 1), QStringLiteral("0"));
    // Cambiar de tipo de speculative reemplaza el valor, no agrega un segundo flag.
    const QStringList ngram = argsOf("sys-bench-ultraq-b8192-u2048-ngrammod");
    QCOMPARE(ngram.count(QStringLiteral("--spec-type")), 1);
    QCOMPARE(ngram.value(ngram.indexOf("--spec-type") + 1), QStringLiteral("ngram-mod"));

    // El control del hallazgo KV q8_0 debe quedar sin speculative, o no controla nada.
    const QStringList kv8NoSpec = argsOf("sys-bench-ultraq-b8192-u2048-kv8-nospec");
    QVERIFY(!kv8NoSpec.isEmpty());
    QVERIFY(!kv8NoSpec.contains(QStringLiteral("--spec-type")));
    QCOMPARE(kv8NoSpec.value(kv8NoSpec.indexOf("--cache-type-k") + 1), QStringLiteral("q8_0"));
    // Asimétrico: K en q8_0 y V en q4_0, no los dos iguales.
    const QStringList k8v4 = argsOf("sys-bench-ultraq-b8192-u2048-kv-k8v4");
    QCOMPARE(k8v4.value(k8v4.indexOf("--cache-type-k") + 1), QStringLiteral("q8_0"));
    QCOMPARE(k8v4.value(k8v4.indexOf("--cache-type-v") + 1), QStringLiteral("q4_0"));

    // Greedy: temp/top-k/top-p/min-p en 0. Con sampling estocástico el verificador
    // rechaza drafts que el greedy aceptaría, y el draft se paga igual.
    const QStringList greedy = argsOf("sys-bench-ultraq-b8192-u2048-ds5-temp0");
    QCOMPARE(greedy.count(QStringLiteral("--temp")), 1);
    QCOMPARE(greedy.value(greedy.indexOf("--temp") + 1), QStringLiteral("0"));
    QCOMPARE(greedy.value(greedy.indexOf("--top-k") + 1), QStringLiteral("0"));
    QCOMPARE(greedy.value(greedy.indexOf("--top-p") + 1), QStringLiteral("0"));
    // Pinear el modelo sólo funciona con archivo de paginación: sin él el commit
    // limit de Windows es la RAM física, VirtualLock falla a mitad de camino y el
    // server muere con GGML_ASSERT(ctx->mem_buffer != NULL). Los perfiles que lo
    // usan tienen que avisarlo en el NOMBRE, que es lo único que se ve al elegir
    // qué correr en el benchmark.
    int pinning = 0;
    auto *launches = pm.launchProfiles();
    for (int r = 0; r < launches->rowCount(); ++r) {
        const QModelIndex idx = launches->index(r);
        if (!launches->data(idx, ProfileListModel<LaunchProfile>::SystemRole).toBool()) continue;
        const QString id = launches->data(idx, ProfileListModel<LaunchProfile>::IdRole).toString();
        if (!id.startsWith(QStringLiteral("sys-bench-ultraq"))) continue;
        const QVariantMap lp = pm.getLaunchProfile(id);
        const QStringList a = lp.value("extraArgs").toStringList();
        const int lm = a.indexOf(QStringLiteral("--load-mode"));
        const bool pins = a.contains(QStringLiteral("--mlock"))
                          || (lm >= 0 && a.value(lm + 1).contains(QStringLiteral("mlock")));
        if (!pins) continue;
        ++pinning;
        QVERIFY2(lp.value("name").toString().contains(QStringLiteral("REQUIERE PAGEFILE")),
                 qPrintable(QStringLiteral("%1 pinea el modelo pero su nombre no avisa").arg(id)));
    }
    QCOMPARE(pinning, 2);
    // ngram-mod trae su propia ventana y no arrastra el n-max de DSpark.
    const QStringList ngramMod = argsOf("sys-bench-ultraq-b8192-u2048-ngrammod");
    QCOMPARE(ngramMod.value(ngramMod.indexOf("--spec-type") + 1), QStringLiteral("ngram-mod"));
    QVERIFY(!ngramMod.contains(QStringLiteral("--spec-draft-n-max")));
    QCOMPARE(ngramMod.value(ngramMod.indexOf("--spec-ngram-mod-n-match") + 1), QStringLiteral("32"));
    QCOMPARE(ngramMod.value(ngramMod.indexOf("--spec-ngram-mod-n-max") + 1), QStringLiteral("64"));
    // El KV del perfil se sube sin duplicar el flag.
    const QStringList kv8 = argsOf("sys-bench-ultraq-b8192-u2048-ds5-kv8");
    QCOMPARE(kv8.count(QStringLiteral("--cache-type-k")), 1);
    QCOMPARE(kv8.value(kv8.indexOf("--cache-type-k") + 1), QStringLiteral("q8_0"));
    QCOMPARE(kv8.value(kv8.indexOf("--cache-type-v") + 1), QStringLiteral("q8_0"));

    // Las variantes descartadas por resultados ya no se ofrecen.
    for (const char *gone : {"sys-bench-ultraq-b2048-u512-ds5", "sys-bench-ultraq-b8192-u512-ds5",
                             "sys-bench-ultraq-b4096-u1024-moe35", "sys-bench-ultraq-b4096-u1024-ds1",
                             "sys-bench-ultraq-b4096-u1024-ds3"})
        QVERIFY2(pm.getLaunchProfile(QString::fromLatin1(gone)).isEmpty(), gone);
}

// Regresión: duplicar un perfil de sistema debe FIJAR en la copia lo que el
// original resolvía dinámicamente sólo por ser system.
//   - binario por minimumBinaryBuild: antes la copia quedaba con backend.binaryId
//     vacío y la UI la ataba al primer binario de la lista — que puede ser un build
//     viejo sin los flags del perfil (p.ej. --spec-type draft-dspark) y el server
//     moría al arrancar.
//   - modelo: el ModelProfile de sistema lleva un id determinista por la ruta
//     administrada; el religado por nombre de archivo también es system-only.
void SystemProfilesTests::controller_duplicateBakesResolvedBinary()
{
    // Dos binarios "instalados": uno viejo (primero de la lista, el que se colaba)
    // y uno que cumple el mínimo del perfil ULTRA-Q (build 10228).
    const QString oldExe = m_dir.path() + QStringLiteral("/b9045/llama-server.exe");
    const QString newExe = m_dir.path() + QStringLiteral("/b10228-cuda12.4/llama-server.exe");
    for (const QString &p : {oldExe, newExe}) {
        QVERIFY(QDir().mkpath(QFileInfo(p).absolutePath()));
        QFile f(p);
        QVERIFY(f.open(QIODevice::WriteOnly));
        f.write("stub");
    }

    AppController app;
    const QString oldId = app.binaryRegistry()->add(oldExe, QStringLiteral("b9045 (cuda)"),
                                                    QStringLiteral("official"),
                                                    QStringLiteral("cuda"), QStringLiteral("b9045"));
    const QString newId = app.binaryRegistry()->add(newExe, QStringLiteral("b10228 CUDA 12.4"),
                                                    QStringLiteral("official"),
                                                    QStringLiteral("cuda"), QStringLiteral("b10228"));
    QVERIFY(!oldId.isEmpty() && !newId.isEmpty());

    const QString sysId = QStringLiteral("sys-bench-ultraq-b8192-u2048-ds5");
    QCOMPARE(app.systemProfileMinimumBinaryBuild(sysId), 10228);

    const QString dup = app.duplicateLaunchProfile(sysId);
    QVERIFY(!dup.isEmpty());

    ProfileManager *pm = app.profileManager();
    QVERIFY(!pm->isSystemLaunch(dup));
    const QVariantMap backend =
        pm->getBackend(pm->getLaunchProfile(dup).value("backendProfileId").toString());
    // Fijado, y al binario correcto — no al primero de la lista.
    QCOMPARE(backend.value("binaryId").toString(), newId);
    QVERIFY(backend.value("binaryId").toString() != oldId);

    // El original sigue sin binario fijado: resuelve en cada arranque.
    const QVariantMap sysBackend =
        pm->getBackend(pm->getLaunchProfile(sysId).value("backendProfileId").toString());
    QVERIFY(sysBackend.value("binaryId").toString().isEmpty());

    // El modelo de la copia nunca queda vacío: o mantiene el id determinista del
    // original, o el que el religado del original resolvió contra el catálogo.
    const QVariantMap sysModel =
        pm->getModelProfile(pm->getLaunchProfile(sysId).value("modelProfileId").toString());
    const QVariantMap dupModel =
        pm->getModelProfile(pm->getLaunchProfile(dup).value("modelProfileId").toString());
    QVERIFY(!dupModel.value("modelId").toString().isEmpty());
    // Sin catálogo escaneado en el test no hay religado, así que debe coincidir.
    QCOMPARE(dupModel.value("modelId").toString(), sysModel.value("modelId").toString());
}

QTEST_MAIN(SystemProfilesTests)
#include "test_system_profiles.moc"
