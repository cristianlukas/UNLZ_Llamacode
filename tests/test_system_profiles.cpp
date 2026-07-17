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
#include "core/profiles/ProfileManager.h"
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

    void controller_recommendsClosestTier();
    void controller_recommendedTierIncludesDisplayName();
    void controller_recommendsCpuWhenNoGpu();
    void controller_noneWhenBelowMinimum();
    void controller_showcase8gbOffersGemmaAndQwen();
    void controller_showcase24gbUnchanged();
    void controller_showcaseEmptyWhenNoSiblings();

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
    QCOMPARE(sys, 12);                       // 20/16/12-MoE/8-Gemma/8-QwenAgent/4/4-Gemma/2/2-Gemma/0 + MAX Q + FAST GEMMA
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
        QVERIFY2(!draft.value(QStringLiteral("repo")).toString().isEmpty()
                     && !draft.value(QStringLiteral("file")).toString().isEmpty(),
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

void SystemProfilesTests::controller_recommendsClosestTier()
{
    AppController app;
    // 24GB: maxq/fastgemma son extra (showcase), así que el mejor tier no-extra
    // ≤VRAM es el de 20GB (Qwen3.6-27B dense).
    app.setHardwareSummaryForTest(24.0, 128.0, QStringLiteral("NVIDIA GeForce RTX 3090"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-20"));
    // RTX 3080 20GB: tier dedicado 27B dense.
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
}

QTEST_MAIN(SystemProfilesTests)
#include "test_system_profiles.moc"
