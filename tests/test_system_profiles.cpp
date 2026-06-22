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
#include <QStandardPaths>
#include <QUuid>
#include <QCoreApplication>
#include "core/profiles/ProfileManager.h"
#include "AppController.h"

static const char *kBundle =
    "C:/Users/cristian/Documents/LlamaCode/assets/system_profiles.json";

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
    void controller_recommendsCpuWhenNoGpu();
    void controller_noneWhenBelowMinimum();

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
    QVERIFY2(QFile::exists(QString::fromLatin1(kBundle)), "falta assets/system_profiles.json");
    qputenv("LLAMACODE_SYSTEM_PROFILES", QByteArray(kBundle));
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
    QCOMPARE(sys, 8);                        // 16/12-MoE/8-Gemma/4/2/0 + MAX Q + FAST GEMMA
    QVERIFY(pm.isSystemLaunch("sys-vram-16"));
    QVERIFY(!anySysId.isEmpty());
    // Visión: el tier 16GB lleva mmproj (multimodal); el 4GB no (VRAM ajustada).
    const QString mp16 = pm.getLaunchProfile("sys-vram-16").value("modelProfileId").toString();
    QVERIFY(!pm.getModelProfile(mp16).value("mmprojId").toString().isEmpty());
    const QString mp4 = pm.getLaunchProfile("sys-vram-4").value("modelProfileId").toString();
    QVERIFY(pm.getModelProfile(mp4).value("mmprojId").toString().isEmpty());
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
    QCOMPARE(mp.value("specType").toString(), QStringLiteral("dflash"));
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
    app.setHardwareSummaryForTest(24.0, 128.0, QStringLiteral("NVIDIA GeForce RTX 3090"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-16"));
    app.setHardwareSummaryForTest(10.0, 32.0, QStringLiteral("NVIDIA"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-8-gemma"));
    app.setHardwareSummaryForTest(5.0, 16.0, QStringLiteral("NVIDIA"));
    QCOMPARE(app.recommendedSystemProfile().value("launchId").toString(),
             QStringLiteral("sys-vram-4"));
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

QTEST_MAIN(SystemProfilesTests)
#include "test_system_profiles.moc"
