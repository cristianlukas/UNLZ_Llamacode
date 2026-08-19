#include <QtTest>
#include <QJsonArray>

#include "core/agent/HarnessWorkerProtocol.h"
#include "core/profiles/HarnessSpec.h"

class HarnessWorkerProtocolTests final : public QObject {
    Q_OBJECT

private slots:
    void framesCanBeChunkedAndCoalesced();
    void frameBoundsAndProtocolAreStrict();
    void sessionRejectsReuseAndStaleResults();
    void workerModuleRoundTripsAndClamps();
    void sandboxRejectsEmptyProgramAndKeepsLegacyNone();
    void factoryAdmitsOnlyRequestedCapabilities();
};

void HarnessWorkerProtocolTests::framesCanBeChunkedAndCoalesced()
{
    const QJsonObject hello{{"protocol", "llamacode-worker-v1"},
                            {"type", "hello"},
                            {"nonce", "n"}};
    const QJsonObject call{{"protocol", "llamacode-worker-v1"},
                           {"type", "call"},
                           {"callId", "c1"}};
    const QByteArray bytes = HarnessWorkerProtocol::encode(hello, 1024)
                             + HarnessWorkerProtocol::encode(call, 1024);
    QByteArray buffer;
    QJsonObject decoded;
    buffer += bytes.left(2);
    QVERIFY(!HarnessWorkerProtocol::take(buffer, 1024, &decoded));
    buffer += bytes.mid(2);
    QVERIFY(HarnessWorkerProtocol::take(buffer, 1024, &decoded));
    QCOMPARE(decoded.value("type").toString(), QStringLiteral("hello"));
    QVERIFY(HarnessWorkerProtocol::take(buffer, 1024, &decoded));
    QCOMPARE(decoded.value("callId").toString(), QStringLiteral("c1"));
    QVERIFY(buffer.isEmpty());
}

void HarnessWorkerProtocolTests::frameBoundsAndProtocolAreStrict()
{
    QString error;
    QVERIFY(HarnessWorkerProtocol::encode(
                QJsonObject{{"protocol", "wrong"}, {"type", "hello"}}, 1024, &error).isEmpty());
    QVERIFY(!error.isEmpty());

    QByteArray tooLarge;
    tooLarge.append(char(0));
    tooLarge.append(char(0));
    tooLarge.append(char(4));
    tooLarge.append(char(0));
    tooLarge.append("nope");
    QJsonObject body;
    error.clear();
    QVERIFY(!HarnessWorkerProtocol::take(tooLarge, 3, &body, &error));
    QVERIFY(!error.isEmpty());
}

void HarnessWorkerProtocolTests::sessionRejectsReuseAndStaleResults()
{
    HarnessWorkerSession session;
    QString error;
    QVERIFY(!session.beginCall(QStringLiteral("c1"), &error));
    QVERIFY(session.acceptHelloAck(
        QJsonObject{{"type", "hello_ack"}, {"nonce", "n"}}, QStringLiteral("n"), &error));
    QVERIFY(session.beginCall(QStringLiteral("c1"), &error));
    QVERIFY(!session.beginCall(QStringLiteral("c1"), &error));
    QVERIFY(!session.finishCall(QStringLiteral("stale"), &error));
    QVERIFY(session.finishCall(QStringLiteral("c1"), &error));
    QVERIFY(!session.finishCall(QStringLiteral("c1"), &error));
}

void HarnessWorkerProtocolTests::workerModuleRoundTripsAndClamps()
{
    const HarnessWorkerModule module = HarnessWorkerModule::fromJson({
        {"lane", "PYTHON"}, {"entrypoint", "worker.py"}, {"sandbox", "PROCESS"},
        {"arguments", QJsonArray{"--profile", "safe"}}, {"cpuTimeLimitSec", 7},
        {"maxFrameBytes", 1}, {"startupTimeoutMs", 1}, {"callTimeoutMs", 1},
        {"memoryLimitMb", -1}, {"processLimit", 0},
        {"requestedCapabilities", QJsonArray{"fs.read"}}});
    QCOMPARE(module.lane, QStringLiteral("python"));
    QCOMPARE(module.sandbox, QStringLiteral("process"));
    QCOMPARE(module.maxFrameBytes, 1024);
    QCOMPARE(module.startupTimeoutMs, 100);
    QCOMPARE(module.callTimeoutMs, 100);
    QCOMPARE(module.memoryLimitMb, 0);
    QCOMPARE(module.processLimit, 1);
    QCOMPARE(module.cpuTimeLimitSec, 7);
    QCOMPARE(module.arguments, QStringList({QStringLiteral("--profile"), QStringLiteral("safe")}));
    QCOMPARE(module.requestedCapabilities, QStringList{QStringLiteral("fs.read")});
    const HarnessSpec spec = HarnessSpec::fromJson({{"worker", module.toJson()}});
    QVERIFY(spec.worker.set);
    QCOMPARE(HarnessSpec::fromJson(spec.toJson()).worker.lane, QStringLiteral("python"));
}

void HarnessWorkerProtocolTests::sandboxRejectsEmptyProgramAndKeepsLegacyNone()
{
    const HarnessSandboxPlan empty = HarnessSandbox::plan(QString(), {}, QString(), {});
    QVERIFY(!empty.supported);
    QVERIFY(!empty.error.isEmpty());
    const HarnessSandboxPlan legacy = HarnessSandbox::plan(QStringLiteral("node"), {}, QString(), {});
    QVERIFY(legacy.supported);
    QCOMPARE(legacy.backend, QStringLiteral("none"));
    QCOMPARE(legacy.program, QStringLiteral("node"));
}

void HarnessWorkerProtocolTests::factoryAdmitsOnlyRequestedCapabilities()
{
    const HarnessWorkerModule module = HarnessWorkerModule::fromJson({
        {"lane", "node"}, {"entrypoint", "worker.mjs"},
        {"requestedCapabilities", QJsonArray{"fs.read", "network"}}});
    QString error;
    const HarnessWorkerLaunchSpec spec = HarnessWorkerFactory::build(
        module, QStringLiteral("."), QStringLiteral("a"), QStringLiteral("next"),
        QStringLiteral("p"), 3, {QStringLiteral("fs.read")}, &error);
    QVERIFY2(error.isEmpty(), qPrintable(error));
    QVERIFY(spec.policy.hasCapabilitySnapshot);
    QVERIFY(spec.policy.capabilities.canUse(QStringLiteral("fs.read")));
    QVERIFY(!spec.policy.capabilities.canUse(QStringLiteral("network")));
    QCOMPARE(spec.program, QStringLiteral("node"));
    QCOMPARE(spec.arguments.first(), QStringLiteral("worker.mjs"));
}

QTEST_MAIN(HarnessWorkerProtocolTests)
#include "test_harness_worker_protocol.moc"
