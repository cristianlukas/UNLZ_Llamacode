#include <QtTest>

#include "core/HardwareDiagnostics.h"
#include "core/PerformanceMatrix.h"

class HardwareDiagnosticsTests : public QObject
{
    Q_OBJECT
private slots:
    void parsesGpuTopology();
    void parsesP2pTopologyMatrix();
    void parsesNvlinkStatus();
    void enrichmentFeedsRecommendation();
    void weakPciePrefersLayer();
    void fastPcieAllowsTensor();
    void fingerprintIsStable();
    void scoreRespectsObjectiveAndStability();
    void scoresRealBenchmarkArtifact();
    void performanceMatrixIsHeadless();
};

void HardwareDiagnosticsTests::parsesGpuTopology()
{
    const QString csv = QStringLiteral(
        "0, NVIDIA GeForce RTX 3090, 24576, 23000, 00000000:01:00.0, 4, 16, 55, 120, 350\n"
        "1, NVIDIA GeForce RTX 3090, 24576, 22000, 00000000:09:00.0, 3, 4, 60, 130, 350\n");
    const QVariantList gpus = HardwareDiagnostics::parseNvidiaSmiCsv(csv);
    QCOMPARE(gpus.size(), 2);
    QCOMPARE(gpus.at(1).toMap().value(QStringLiteral("pcieGeneration")).toDouble(), 3.0);
    QCOMPARE(gpus.at(1).toMap().value(QStringLiteral("pcieLanes")).toDouble(), 4.0);
}

void HardwareDiagnosticsTests::parsesP2pTopologyMatrix()
{
    const QString topo = QStringLiteral(
        "        GPU0 GPU1 CPU Affinity\n"
        "GPU0     X   NV1 0-15\n"
        "GPU1    NV1   X  0-15\n");
    const QVariantMap parsed = HardwareDiagnostics::parseTopologyMatrix(topo);
    QVERIFY(parsed.value(QStringLiteral("p2pAvailable")).toBool());
    QCOMPARE(parsed.value(QStringLiteral("links")).toList().size(), 2);
}

void HardwareDiagnosticsTests::parsesNvlinkStatus()
{
    QVERIFY(HardwareDiagnostics::parseNvlinkActive("Link 0: Active"));
    QVERIFY(!HardwareDiagnostics::parseNvlinkActive("Link 0: Inactive"));
    QVERIFY(!HardwareDiagnostics::parseNvlinkActive("No NVLink support"));
}

void HardwareDiagnosticsTests::enrichmentFeedsRecommendation()
{
    const QVariantMap base{{QStringLiteral("gpus"), QVariantList{
        QVariantMap{{QStringLiteral("pcieGeneration"), 3.0}, {QStringLiteral("pcieLanes"), 4.0}},
        QVariantMap{{QStringLiteral("pcieGeneration"), 4.0}, {QStringLiteral("pcieLanes"), 16.0}}}}};
    const QVariantMap enriched = HardwareDiagnostics::enrichTopology(
        base, "GPU0 GPU1 CPU\nGPU0 X NV1 0-3\nGPU1 NV1 X 0-3\n", "Link 0: Active");
    QVERIFY(enriched.value(QStringLiteral("p2pAvailable")).toBool());
    QVERIFY(enriched.value(QStringLiteral("nvlinkAvailable")).toBool());
    QCOMPARE(HardwareDiagnostics::recommendedSplitMode(enriched), QStringLiteral("layer"));
}

void HardwareDiagnosticsTests::weakPciePrefersLayer()
{
    const QVariantList gpus{
        QVariantMap{{QStringLiteral("name"), QStringLiteral("A")},
                     {QStringLiteral("totalMb"), 24576},
                     {QStringLiteral("pcieGeneration"), 4.0},
                     {QStringLiteral("pcieLanes"), 16.0}},
        QVariantMap{{QStringLiteral("name"), QStringLiteral("B")},
                     {QStringLiteral("totalMb"), 24576},
                     {QStringLiteral("pcieGeneration"), 3.0},
                     {QStringLiteral("pcieLanes"), 4.0}}};
    const QVariantMap hw{{QStringLiteral("gpus"), gpus}};
    QCOMPARE(HardwareDiagnostics::recommendedSplitMode(hw), QStringLiteral("layer"));
    QCOMPARE(HardwareDiagnostics::performanceRecommendation(hw).value(QStringLiteral("kvCache")),
             QVariant(QStringLiteral("q8_0")));
}

void HardwareDiagnosticsTests::fastPcieAllowsTensor()
{
    const QVariantList gpus{
        QVariantMap{{QStringLiteral("name"), QStringLiteral("A")},
                     {QStringLiteral("pcieGeneration"), 4.0}, {QStringLiteral("pcieLanes"), 16.0}},
        QVariantMap{{QStringLiteral("name"), QStringLiteral("B")},
                     {QStringLiteral("pcieGeneration"), 4.0}, {QStringLiteral("pcieLanes"), 16.0}}};
    QCOMPARE(HardwareDiagnostics::recommendedSplitMode(QVariantMap{{QStringLiteral("gpus"), gpus}}),
             QStringLiteral("tensor"));
}

void HardwareDiagnosticsTests::fingerprintIsStable()
{
    const QVariantMap hw{{QStringLiteral("cpuModel"), QStringLiteral("CPU")},
                         {QStringLiteral("gpus"), QVariantList{QVariantMap{
                             {QStringLiteral("name"), QStringLiteral("GPU")},
                             {QStringLiteral("totalMb"), 24576},
                             {QStringLiteral("pcieGeneration"), 4.0},
                             {QStringLiteral("pcieLanes"), 16.0},
                             {QStringLiteral("busId"), QStringLiteral("01:00.0")}}}}};
    QCOMPARE(HardwareDiagnostics::hardwareFingerprint(hw), HardwareDiagnostics::hardwareFingerprint(hw));
    QVERIFY(HardwareDiagnostics::hardwareFingerprint(hw).startsWith(QStringLiteral("hw-")));
}

void HardwareDiagnosticsTests::scoreRespectsObjectiveAndStability()
{
    const QVariantMap stable{{QStringLiteral("promptTps"), 1000.0},
                             {QStringLiteral("generationTps"), 20.0},
                             {QStringLiteral("quality"), 1.0},
                             {QStringLiteral("stable"), true}};
    const QVariantMap unstable = QVariantMap{{QStringLiteral("promptTps"), 1000.0},
                                              {QStringLiteral("generationTps"), 20.0},
                                              {QStringLiteral("quality"), 1.0},
                                              {QStringLiteral("stable"), false}};
    QVERIFY(HardwareDiagnostics::performanceScore(stable, QStringLiteral("prefill")) >
            HardwareDiagnostics::performanceScore(stable, QStringLiteral("decode")));
    QVERIFY(HardwareDiagnostics::performanceScore(stable) >
            HardwareDiagnostics::performanceScore(unstable));
}

void HardwareDiagnosticsTests::scoresRealBenchmarkArtifact()
{
    const QVariantMap artifact{{QStringLiteral("avgTps"), 40.0},
                               {QStringLiteral("qualityScore"), 8},
                               {QStringLiteral("qualityTotal"), 10},
                               {QStringLiteral("failed"), false},
                               {QStringLiteral("timedOut"), false}};
    QVERIFY(HardwareDiagnostics::performanceScore(artifact, QStringLiteral("decode")) > 0.0);
    const QVariantMap candidate{{QStringLiteral("id"), QStringLiteral("layer-q8_0-32768")},
                                {QStringLiteral("target"), QStringLiteral("decode")}};
    const QVariantMap annotated = PerformanceMatrix::annotate(
        artifact, QVariantMap{{QStringLiteral("hardwareFingerprint"), QStringLiteral("hw-test")}},
        candidate);
    QCOMPARE(annotated.value(QStringLiteral("measurementStatus")).toString(),
             QStringLiteral("measured"));
}

void HardwareDiagnosticsTests::performanceMatrixIsHeadless()
{
    const QVariantMap hw{{QStringLiteral("gpuCount"), 2},
                         {QStringLiteral("p2pAvailable"), false},
                         {QStringLiteral("hardwareFingerprint"), QStringLiteral("hw-test")}};
    const QVariantList candidates = PerformanceMatrix::candidates(hw, QStringLiteral("decode"));
    QCOMPARE(candidates.size(), 6);
    QVariantMap sample = candidates.first().toMap();
    sample[QStringLiteral("performanceCandidate")] = candidates.first();
    sample[QStringLiteral("promptTps")] = 100.0;
    sample[QStringLiteral("generationTps")] = 30.0;
    sample[QStringLiteral("quality")] = 1.0;
    sample[QStringLiteral("stable")] = true;
    const QVariantList ranked = PerformanceMatrix::rank({sample}, QStringLiteral("decode"));
    QCOMPARE(ranked.first().toMap().value(QStringLiteral("rank")).toInt(), 1);
    QVERIFY(ranked.first().toMap().value(QStringLiteral("performanceScore")).toDouble() > 0.0);
}

QTEST_MAIN(HardwareDiagnosticsTests)
#include "test_hardware_diagnostics.moc"
