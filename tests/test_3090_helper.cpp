#include <QtTest>

#include "HealthStatus.h"

using namespace Gpu3090Helper;

class Gpu3090HelperTests final : public QObject
{
    Q_OBJECT
private slots:
    void greenRequiresAllThreeChecks();
    void faultyMemoryMustBeFullyHeldByEnabledWorker();
    void p2pMustWorkInBothDirectionsForExpectedCards();
    void gpuUnlockMustCoverBothCardsAtThisBoot();
};

namespace {
Inputs goodInputs()
{
    Inputs input;
    input.workerActive = true;
    input.workerEnabled = true;
    input.workerJson = QStringLiteral(
        R"({"uuid":"GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6","pci":"0000:01:00.0","driver":"615.71.09","built_for":"615.71.09","held":1636,"total":1636,"pending":0,"state":"protected"})");
    input.gpuInventory = QStringLiteral(
        "GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6, NVIDIA GeForce RTX 3090, 00000000:01:00.0\n"
        "GPU-5b9f385f-6a8e-b802-f69c-e62a71c91049, NVIDIA GeForce RTX 3090, 00000000:03:00.0");
    input.p2pRead = QStringLiteral("\tGPU0\tGPU1\n GPU0\tX\tOK\n GPU1\tOK\tX");
    input.p2pWrite = input.p2pRead;
    input.kernelCommandLine = QStringLiteral("quiet gpu_unlock.targets=0000:01:00.0,0000:03:00.0");
    input.unlockModuleTargets = QStringLiteral("0000:01:00.0,0000:03:00.0");
    input.unlockModulePresent = true;
    input.unlockKernelLog = QStringLiteral(
        "nvidia 0000:01:00.0: gpu_unlock: unlocked\n"
        "nvidia 0000:03:00.0: gpu_unlock: unlocked");
    return input;
}
} // namespace

void Gpu3090HelperTests::greenRequiresAllThreeChecks()
{
    const Snapshot snapshot = evaluate(goodInputs());
    QVERIFY(snapshot.vramQuarantine.ok);
    QVERIFY(snapshot.p2p.ok);
    QVERIFY(snapshot.gpuUnlock.ok);
    QVERIFY(snapshot.healthy());
    QVERIFY(snapshot.report().contains(QStringLiteral("VERDE")));
}

void Gpu3090HelperTests::faultyMemoryMustBeFullyHeldByEnabledWorker()
{
    Inputs input = goodInputs();
    input.workerJson.replace(QStringLiteral("\"pending\":0"), QStringLiteral("\"pending\":1"));
    QVERIFY(!evaluate(input).vramQuarantine.ok);
    input = goodInputs();
    input.workerEnabled = false;
    QVERIFY(!evaluate(input).vramQuarantine.ok);
}

void Gpu3090HelperTests::p2pMustWorkInBothDirectionsForExpectedCards()
{
    Inputs input = goodInputs();
    input.p2pWrite.replace(QStringLiteral("GPU1\tOK\tX"), QStringLiteral("GPU1\tGNS\tX"));
    QVERIFY(!evaluate(input).p2p.ok);
    input = goodInputs();
    input.gpuInventory.replace(QStringLiteral("RTX 3090"), QStringLiteral("RTX 4090"));
    QVERIFY(!evaluate(input).p2p.ok);
}

void Gpu3090HelperTests::gpuUnlockMustCoverBothCardsAtThisBoot()
{
    Inputs input = goodInputs();
    input.unlockKernelLog.remove(QStringLiteral("0000:03:00.0: gpu_unlock: unlocked"));
    QVERIFY(!evaluate(input).gpuUnlock.ok);
    input = goodInputs();
    input.kernelCommandLine = QStringLiteral("quiet gpu_unlock.targets=0000:01:00.0");
    QVERIFY(!evaluate(input).gpuUnlock.ok);
}

QTEST_APPLESS_MAIN(Gpu3090HelperTests)
#include "test_3090_helper.moc"
