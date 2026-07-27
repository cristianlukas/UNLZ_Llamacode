#include <QtTest>
#include "core/EngineCatalog.h"

class EngineCatalogTests : public QObject
{
    Q_OBJECT
private slots:
    void catalogIncludesSourceForks();
    void variantCompatibilityReportsReason();
    void versionComparisonHandlesBuildTagsAndSemver();
    void sourceUpdateComparesShortSha();
    void repoNormalizationAndBuildDirAreStable();
};

void EngineCatalogTests::catalogIncludesSourceForks()
{
    const EngineCatalogEntry ik = EngineCatalog::entry(QStringLiteral("ik_llama.cpp"));
    QCOMPARE(ik.repo, QStringLiteral("ikawrakow/ik_llama.cpp"));
    QVERIFY(!ik.variants.isEmpty());
    QVERIFY(ik.variants.first().buildFromSource);

    const EngineCatalogEntry official = EngineCatalog::entry(QStringLiteral("llama.cpp"));
    QVERIFY(official.variants.size() >= 3);

    const EngineCatalogEntry nanbeige = EngineCatalog::entry(QStringLiteral("nanbeige42"));
    QCOMPARE(nanbeige.repo, QStringLiteral("Nanbeige/llama.cpp"));
    QCOMPARE(nanbeige.sourceBranch, QStringLiteral("nanbeige42"));
    QVERIFY(!nanbeige.variants.isEmpty());
    QVERIFY(nanbeige.variants.first().buildFromSource);
    QCOMPARE(nanbeige.variants.first().gpuVendors, QStringList{QStringLiteral("nvidia")});
}

void EngineCatalogTests::variantCompatibilityReportsReason()
{
    const EngineCatalogEntry beellama = EngineCatalog::entry(QStringLiteral("beellama"));
    HardwareSignals hw;
    hw.platform = QStringLiteral("windows");
    hw.arch = QStringLiteral("x64");
    hw.gpuVendor = QStringLiteral("unknown");

    QString reason;
    QVERIFY(!EngineCatalog::isVariantCompatible(beellama.variants.first(), hw, &reason));
    QVERIFY(reason.contains(QStringLiteral("nvidia"), Qt::CaseInsensitive));
}

void EngineCatalogTests::versionComparisonHandlesBuildTagsAndSemver()
{
    QCOMPARE(EngineCatalog::parseBuildTag(QStringLiteral("b9608")), 9608);
    QVERIFY(EngineCatalog::compareVersions(QStringLiteral("b9608"), QStringLiteral("b9761")) < 0);
    QVERIFY(EngineCatalog::compareVersions(QStringLiteral("v1.115.1"), QStringLiteral("v1.115.2")) < 0);
    QCOMPARE(EngineCatalog::compareVersions(QStringLiteral("0.11"), QStringLiteral("0.11.0")), 0);
}

void EngineCatalogTests::sourceUpdateComparesShortSha()
{
    EngineUpdateStatus st = EngineCatalog::computeUpdateStatus(
        QStringLiteral("0a635dc"), QStringLiteral("9f42aaa123456"), true);
    QVERIFY(st.rebuild);
    QVERIFY(st.comparable);
    QVERIFY(st.hasUpdate);

    st = EngineCatalog::computeUpdateStatus(QString(), QStringLiteral("9f42aaa"), true);
    QVERIFY(st.rebuild);
    QVERIFY(!st.comparable);
    QCOMPARE(st.error, QStringLiteral("no_source"));
}

void EngineCatalogTests::repoNormalizationAndBuildDirAreStable()
{
    QCOMPARE(EngineCatalog::normalizeRepo(QStringLiteral("https://github.com/ikawrakow/ik_llama.cpp.git")),
             QStringLiteral("ikawrakow/ik_llama.cpp"));
    QCOMPARE(EngineCatalog::buildDirName(QStringLiteral("https://github.com/a/repo.git"), QStringLiteral("feature/x")),
             QStringLiteral("repo-feature-x"));
}

QTEST_MAIN(EngineCatalogTests)
#include "test_engine_catalog.moc"
