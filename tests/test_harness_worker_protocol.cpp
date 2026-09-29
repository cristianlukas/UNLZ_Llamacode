#include <QtTest>
#include <QJsonArray>
#include <QFileInfo>
#include <QDir>
#include <QSignalSpy>
#include <QStandardPaths>
#include <QProcess>
#include <QTemporaryFile>

#include "core/agent/HarnessWorkerProtocol.h"
#include "core/agent/LlamaAgentBackend.h"
#include "core/profiles/HarnessSpec.h"

class HarnessWorkerProtocolTests final : public QObject {
    Q_OBJECT

private slots:
    void framesCanBeChunkedAndCoalesced();
    void frameBoundsAndProtocolAreStrict();
    void sessionRejectsReuseAndStaleResults();
    void workerModuleRoundTripsAndClamps();
    void sandboxRejectsEmptyProgramAndKeepsLegacyNone();
    void strongSandboxStartsWithWorkspaceUnderTmpfs();
    void strongSandboxCanHideHostUserData();
    void strongSandboxCanApplyOptionalCgroupLimits();
    void factoryAdmitsOnlyRequestedCapabilities();
    void workerCallsAreClassifiedAsDestructive();
    void nodeWorkerDriverRoundTripsWhenAvailable();
    void pythonWorkerDriverRoundTripsWhenAvailable();
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
        {"hideHostUserData", true}, {"enforceResourceLimits", true},
        {"cpuQuotaPercent", 1500},
        {"requestedCapabilities", QJsonArray{"fs.read"}}});
    QCOMPARE(module.lane, QStringLiteral("python"));
    QCOMPARE(module.sandbox, QStringLiteral("process"));
    QCOMPARE(module.maxFrameBytes, 1024);
    QCOMPARE(module.startupTimeoutMs, 100);
    QCOMPARE(module.callTimeoutMs, 100);
    QCOMPARE(module.memoryLimitMb, 0);
    QCOMPARE(module.processLimit, 1);
    QCOMPARE(module.cpuTimeLimitSec, 7);
    QVERIFY(module.hideHostUserData);
    QVERIFY(module.enforceResourceLimits);
    QCOMPARE(module.cpuQuotaPercent, 1000);
    QCOMPARE(module.arguments, QStringList({QStringLiteral("--profile"), QStringLiteral("safe")}));
    QCOMPARE(module.requestedCapabilities, QStringList{QStringLiteral("fs.read")});
    const HarnessSpec spec = HarnessSpec::fromJson({{"worker", module.toJson()}});
    QVERIFY(spec.worker.set);
    QCOMPARE(HarnessSpec::fromJson(spec.toJson()).worker.lane, QStringLiteral("python"));
    const HarnessWorkerModule roundTrip = HarnessSpec::fromJson(spec.toJson()).worker;
    QVERIFY(roundTrip.hideHostUserData);
    QVERIFY(roundTrip.enforceResourceLimits);
    QCOMPARE(roundTrip.cpuQuotaPercent, 1000);
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

    HarnessSandboxPolicy uncontainedLimits;
    uncontainedLimits.enforceResourceLimits = true;
    const HarnessSandboxPlan refused = HarnessSandbox::plan(
        QStringLiteral("node"), {}, QString(), uncontainedLimits);
    QVERIFY(!refused.supported);
    QVERIFY(refused.error.contains(QStringLiteral("resource limits")));
}

void HarnessWorkerProtocolTests::strongSandboxStartsWithWorkspaceUnderTmpfs()
{
#ifdef Q_OS_WIN
    QSKIP("bubblewrap strong sandbox is Unix-only");
#else
    HarnessSandboxPolicy policy;
    policy.mode = QStringLiteral("strong");
    const QString workspace = QDir::currentPath();
    const HarnessSandboxPlan plan = HarnessSandbox::plan(
        QStringLiteral("/bin/sh"), {QStringLiteral("-c"),
                                    QStringLiteral("test -r README.md && test \"$PWD\" = /tmp/llamacode-workspace")},
        workspace, policy);
    if (!plan.supported) QSKIP(qPrintable(plan.error));

    QVERIFY(plan.arguments.contains(QStringLiteral("--tmpfs")));
    QVERIFY(plan.arguments.contains(QStringLiteral("--dir")));
    QVERIFY(plan.arguments.contains(QStringLiteral("/tmp/llamacode-workspace")));

    QProcess process;
    process.setProgram(plan.program);
    process.setArguments(plan.arguments);
    process.start();
    if (!process.waitForStarted(5000)) {
        QSKIP(qPrintable(QStringLiteral("bubblewrap could not start: %1")
                             .arg(process.errorString())));
    }
    QVERIFY2(process.waitForFinished(10000), "bubblewrap sandbox did not finish");
    QCOMPARE(process.exitStatus(), QProcess::NormalExit);
    QVERIFY2(process.exitCode() == 0, process.readAllStandardError().constData());
#endif
}

void HarnessWorkerProtocolTests::strongSandboxCanHideHostUserData()
{
#ifdef Q_OS_WIN
    QSKIP("bubblewrap strong sandbox is Unix-only");
#else
    QTemporaryFile canary(QDir::home().filePath(QStringLiteral(".llamacode-canary-XXXXXX")));
    QVERIFY(canary.open());
    const QString canaryPath = canary.fileName();
    canary.close();

    HarnessSandboxPolicy policy;
    policy.mode = QStringLiteral("strong");
    policy.hideHostUserData = true;
    const HarnessSandboxPlan plan = HarnessSandbox::plan(
        QStringLiteral("/bin/sh"),
        {QStringLiteral("-c"), QStringLiteral("test ! -e \"$1\" && test -r README.md"),
         QStringLiteral("worker-test"), canaryPath},
        QDir::currentPath(), policy);
    if (!plan.supported) QSKIP(qPrintable(plan.error));
    QVERIFY(plan.arguments.contains(QStringLiteral("--tmpfs")));
    QVERIFY(plan.arguments.contains(QDir::homePath()));

    QProcess process;
    process.setProgram(plan.program);
    process.setArguments(plan.arguments);
    process.start();
    if (!process.waitForStarted(5000))
        QSKIP(qPrintable(QStringLiteral("bubblewrap could not start: %1")
                             .arg(process.errorString())));
    QVERIFY2(process.waitForFinished(10000), "isolated worker did not finish");
    QCOMPARE(process.exitStatus(), QProcess::NormalExit);
    QVERIFY2(process.exitCode() == 0, process.readAllStandardError().constData());
#endif
}

void HarnessWorkerProtocolTests::strongSandboxCanApplyOptionalCgroupLimits()
{
#ifdef Q_OS_WIN
    QSKIP("systemd user scopes are Linux-only");
#else
    if (QStandardPaths::findExecutable(QStringLiteral("systemd-run")).isEmpty())
        QSKIP("systemd-run is not installed");
    HarnessSandboxPolicy policy;
    policy.mode = QStringLiteral("strong");
    policy.enforceResourceLimits = true;
    policy.memoryLimitMb = 128;
    policy.processLimit = 16;
    policy.cpuQuotaPercent = 50;
    const HarnessSandboxPlan plan = HarnessSandbox::plan(
        QStringLiteral("/bin/true"), {}, QDir::currentPath(), policy);
    QVERIFY2(plan.supported, qPrintable(plan.error));
    QCOMPARE(QFileInfo(plan.program).fileName(), QStringLiteral("systemd-run"));
    QVERIFY(plan.arguments.contains(QStringLiteral("--property=MemoryMax=128M")));
    QVERIFY(plan.arguments.contains(QStringLiteral("--property=TasksMax=16")));
    QVERIFY(plan.arguments.contains(QStringLiteral("--property=CPUQuota=50%")));
    QVERIFY(plan.arguments.contains(QStringLiteral("--")));

    QProcess process;
    process.setProgram(plan.program);
    process.setArguments(plan.arguments);
    process.start();
    if (!process.waitForStarted(5000))
        QSKIP(qPrintable(QStringLiteral("systemd-run could not start: %1")
                             .arg(process.errorString())));
    QVERIFY2(process.waitForFinished(15000), "resource-limited worker did not finish");
    if (process.exitCode() != 0 && process.readAllStandardError().contains("Failed to connect"))
        QSKIP("systemd user manager is not available in this session");
    QCOMPARE(process.exitStatus(), QProcess::NormalExit);
    QVERIFY2(process.exitCode() == 0, process.readAllStandardError().constData());
#endif
}

void HarnessWorkerProtocolTests::factoryAdmitsOnlyRequestedCapabilities()
{
    const HarnessWorkerModule module = HarnessWorkerModule::fromJson({
        {"lane", "node"}, {"entrypoint", "worker.mjs"},
        {"sandbox", "strong"}, {"hideHostUserData", true},
        {"enforceResourceLimits", true}, {"cpuQuotaPercent", 50},
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
    QVERIFY(spec.policy.sandbox.hideHostUserData);
    QVERIFY(spec.policy.sandbox.enforceResourceLimits);
    QCOMPARE(spec.policy.sandbox.cpuQuotaPercent, 50);
}

void HarnessWorkerProtocolTests::workerCallsAreClassifiedAsDestructive()
{
    QVERIFY(LlamaAgentBackend::isDestructiveAction(
        QStringLiteral("worker_call"),
        QJsonObject{{QStringLiteral("operation"), QStringLiteral("echo")},
                    {QStringLiteral("payload"), QJsonObject{}}}));
    QVERIFY(!LlamaAgentBackend::isDestructiveAction(
        QStringLiteral("read_file"),
        QJsonObject{{QStringLiteral("path"), QStringLiteral("README.md")}}));
}

void HarnessWorkerProtocolTests::nodeWorkerDriverRoundTripsWhenAvailable()
{
    const QString node = QStandardPaths::findExecutable(QStringLiteral("node"));
    const QString root = qEnvironmentVariable("QT_TESTCASE_SOURCEDIR");
    const QString entry = QDir(root).filePath(QStringLiteral("sdk/node/examples/echo-worker.mjs"));
    if (node.isEmpty() || root.isEmpty() || !QFileInfo::exists(entry))
        QSKIP("Node.js y el ejemplo del SDK no están disponibles en este entorno");

    HarnessWorkerDriver driver;
    HarnessWorkerPolicy policy;
    policy.startupTimeoutMs = 5000;
    policy.callTimeoutMs = 5000;
    QVERIFY2(driver.start(node, {entry}, root, policy),
             qPrintable(driver.lastError()));
    QTRY_VERIFY_WITH_TIMEOUT(driver.authenticated(), 5000);

    QSignalSpy results(&driver, &HarnessWorkerDriver::callResult);
    QVERIFY(driver.call(QStringLiteral("integration-1"),
                        QJsonObject{{QStringLiteral("operation"), QStringLiteral("echo")},
                                    {QStringLiteral("payload"),
                                     QJsonObject{{QStringLiteral("value"), QStringLiteral("ok")}}}}));
    QTRY_COMPARE_WITH_TIMEOUT(results.count(), 1, 5000);
    const QList<QVariant> emitted = results.takeFirst();
    QCOMPARE(emitted.at(0).toString(), QStringLiteral("integration-1"));
    QCOMPARE(emitted.at(1).toJsonObject().value(QStringLiteral("value")).toString(),
             QStringLiteral("ok"));
    driver.stop();
}

void HarnessWorkerProtocolTests::pythonWorkerDriverRoundTripsWhenAvailable()
{
    QString python = qEnvironmentVariable("LLAMACODE_PYTHON");
    if (python.isEmpty()) python = QStandardPaths::findExecutable(QStringLiteral("python"));
    const QString root = qEnvironmentVariable("QT_TESTCASE_SOURCEDIR");
    const QString entry = QDir(root).filePath(
        QStringLiteral("sdk/python/examples/echo_worker.py"));
    if (python.isEmpty() || root.isEmpty() || !QFileInfo::exists(entry))
        QSKIP("Python y el ejemplo del SDK no están disponibles en este entorno");

    HarnessWorkerDriver driver;
    HarnessWorkerPolicy policy;
    policy.startupTimeoutMs = 5000;
    policy.callTimeoutMs = 5000;
    QVERIFY2(driver.start(python, {entry}, root, policy), qPrintable(driver.lastError()));
    QTRY_VERIFY_WITH_TIMEOUT(driver.authenticated(), 5000);

    QSignalSpy results(&driver, &HarnessWorkerDriver::callResult);
    QVERIFY(driver.call(QStringLiteral("integration-python-1"),
                        QJsonObject{{QStringLiteral("operation"), QStringLiteral("echo")},
                                    {QStringLiteral("payload"),
                                     QJsonObject{{QStringLiteral("value"), QStringLiteral("ok")}}}}));
    QTRY_COMPARE_WITH_TIMEOUT(results.count(), 1, 5000);
    const QList<QVariant> emitted = results.takeFirst();
    QCOMPARE(emitted.at(0).toString(), QStringLiteral("integration-python-1"));
    QCOMPARE(emitted.at(1).toJsonObject().value(QStringLiteral("value")).toString(),
             QStringLiteral("ok"));
    driver.stop();
}

QTEST_MAIN(HarnessWorkerProtocolTests)
#include "test_harness_worker_protocol.moc"
