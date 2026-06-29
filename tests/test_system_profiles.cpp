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
    // Visión: el tier 16GB lleva mmproj (multimodal); el 4GB no (VRAM ajustada).
    const QString mp16 = pm.getLaunchProfile("sys-vram-16").value("modelProfileId").toString();
    QVERIFY(!pm.getModelProfile(mp16).value("mmprojId").toString().isEmpty());
    const QString mp4 = pm.getLaunchProfile("sys-vram-4").value("modelProfileId").toString();
    QVERIFY(pm.getModelProfile(mp4).value("mmprojId").toString().isEmpty());
    // El tier 8GB Gemma tiene visión (gemma4uv): mmproj presente, offload a CPU via
    // --no-mmproj-offload. Requiere llama-server b9496+ en runtime.
    const QString mp8 = pm.getLaunchProfile("sys-vram-8-gemma").value("modelProfileId").toString();
    QVERIFY(!pm.getModelProfile(mp8).value("mmprojId").toString().isEmpty());
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
             QStringLiteral("[general] 8GB · Gemma 4 12B Q4 (visión)"));
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
    app.setHardwareSummaryForTest(0.0, 4.0, QStringLiteral("sin GPU"));   // 4GB RAM < 32 del CPU tier
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

QTEST_MAIN(SystemProfilesTests)
#include "test_system_profiles.moc"
