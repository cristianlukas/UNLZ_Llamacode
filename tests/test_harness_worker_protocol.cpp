#include <QtTest>

#include "core/agent/HarnessWorkerProtocol.h"

class HarnessWorkerProtocolTests final : public QObject {
    Q_OBJECT

private slots:
    void framesCanBeChunkedAndCoalesced();
    void frameBoundsAndProtocolAreStrict();
    void sessionRejectsReuseAndStaleResults();
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

QTEST_MAIN(HarnessWorkerProtocolTests)
#include "test_harness_worker_protocol.moc"
