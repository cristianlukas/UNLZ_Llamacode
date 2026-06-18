#include <QtTest>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTemporaryDir>
#include "core/agent/LlamaAgentBackend.h"

class AgentWireTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void dropsOrphanToolAndDemotesNonInitialSystem();
    void dropsDanglingAssistantAndAnchorsFirstUser();
    void dropsTransportErrorAssistantMessages();
    void restartRepublishesPersistedMessages();
};

void AgentWireTests::initTestCase()
{
    QStandardPaths::setTestModeEnabled(true);
}

static QJsonObject msg(const QString &role, const QString &content)
{
    return QJsonObject{{QStringLiteral("role"), role}, {QStringLiteral("content"), content}};
}

static QJsonObject assistantCall(const QString &id)
{
    return QJsonObject{
        {QStringLiteral("role"), QStringLiteral("assistant")},
        {QStringLiteral("content"), QString()},
        {QStringLiteral("tool_calls"), QJsonArray{QJsonObject{
            {QStringLiteral("id"), id},
            {QStringLiteral("type"), QStringLiteral("function")},
            {QStringLiteral("function"), QJsonObject{
                {QStringLiteral("name"), QStringLiteral("read_file")},
                {QStringLiteral("arguments"), QStringLiteral("{\"path\":\"a.txt\"")}
            }}
        }}}
    };
}

static QJsonObject toolResult(const QString &id)
{
    return QJsonObject{
        {QStringLiteral("role"), QStringLiteral("tool")},
        {QStringLiteral("tool_call_id"), id},
        {QStringLiteral("name"), QStringLiteral("read_file")},
        {QStringLiteral("content"), QStringLiteral("ok")}
    };
}

void AgentWireTests::dropsOrphanToolAndDemotesNonInitialSystem()
{
    QJsonArray in{
        msg(QStringLiteral("system"), QStringLiteral("base")),
        msg(QStringLiteral("user"), QStringLiteral("task")),
        toolResult(QStringLiteral("missing")),
        msg(QStringLiteral("system"), QStringLiteral("soft nudge"))
    };

    const QJsonArray out = LlamaAgentBackend::sanitizeApiMessagesForWire(in);
    QCOMPARE(out.size(), 3);
    QCOMPARE(out[0].toObject().value(QStringLiteral("role")).toString(), QStringLiteral("system"));
    QCOMPARE(out[1].toObject().value(QStringLiteral("role")).toString(), QStringLiteral("user"));
    QCOMPARE(out[2].toObject().value(QStringLiteral("role")).toString(), QStringLiteral("user"));
    QCOMPARE(out[2].toObject().value(QStringLiteral("content")).toString(), QStringLiteral("soft nudge"));
}

void AgentWireTests::dropsDanglingAssistantAndAnchorsFirstUser()
{
    QJsonArray in{
        msg(QStringLiteral("system"), QStringLiteral("base")),
        msg(QStringLiteral("user"), QStringLiteral("original task")),
        assistantCall(QStringLiteral("c1")),
        msg(QStringLiteral("assistant"), QStringLiteral("tail without user"))
    };

    const QJsonArray out = LlamaAgentBackend::sanitizeApiMessagesForWire(in);
    QCOMPARE(out.size(), 3);
    QCOMPARE(out[0].toObject().value(QStringLiteral("role")).toString(), QStringLiteral("system"));
    QCOMPARE(out[1].toObject().value(QStringLiteral("role")).toString(), QStringLiteral("user"));
    QCOMPARE(out[1].toObject().value(QStringLiteral("content")).toString(), QStringLiteral("original task"));
    QCOMPARE(out[2].toObject().value(QStringLiteral("role")).toString(), QStringLiteral("assistant"));
    QVERIFY(!out[2].toObject().contains(QStringLiteral("tool_calls")));
}

void AgentWireTests::dropsTransportErrorAssistantMessages()
{
    QJsonArray in{
        msg(QStringLiteral("system"), QStringLiteral("base")),
        msg(QStringLiteral("user"), QStringLiteral("Que hora es?")),
        msg(QStringLiteral("assistant"), QStringLiteral("[error: Error transferring http://127.0.0.1:8081/v1/chat/completions - server replied: Bad Request]")),
        msg(QStringLiteral("user"), QStringLiteral("Hola"))
    };

    const QJsonArray out = LlamaAgentBackend::sanitizeApiMessagesForWire(in);
    QCOMPARE(out.size(), 3);
    QCOMPARE(out[0].toObject().value(QStringLiteral("role")).toString(), QStringLiteral("system"));
    QCOMPARE(out[1].toObject().value(QStringLiteral("content")).toString(), QStringLiteral("Que hora es?"));
    QCOMPARE(out[2].toObject().value(QStringLiteral("content")).toString(), QStringLiteral("Hola"));
}

void AgentWireTests::restartRepublishesPersistedMessages()
{
    const QString store = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                          + QStringLiteral("/agent_llamaagent");
    QDir(store).removeRecursively();
    QVERIFY(QDir().mkpath(store));

    const QString sessionId = QStringLiteral("restart-regression");
    const QJsonObject sessionMeta{
        {QStringLiteral("id"), sessionId},
        {QStringLiteral("title"), QStringLiteral("Persistida")},
        {QStringLiteral("created"), 1.0}
    };
    QFile indexFile(store + QStringLiteral("/index.json"));
    QVERIFY(indexFile.open(QIODevice::WriteOnly | QIODevice::Truncate));
    indexFile.write(QJsonDocument(QJsonArray{sessionMeta}).toJson());
    indexFile.close();

    QFile sessionFile(store + QStringLiteral("/") + sessionId + QStringLiteral(".json"));
    QVERIFY(sessionFile.open(QIODevice::WriteOnly | QIODevice::Truncate));
    sessionFile.write(QJsonDocument(QJsonObject{
        {QStringLiteral("id"), sessionId},
        {QStringLiteral("title"), QStringLiteral("Persistida")},
        {QStringLiteral("messages"), QJsonArray{QJsonObject{
            {QStringLiteral("role"), QStringLiteral("assistant")},
            {QStringLiteral("content"), QStringLiteral("mensaje persistido")}
        }}},
        {QStringLiteral("api"), QJsonArray{}}
    }).toJson());
    sessionFile.close();

    QTemporaryDir cwd;
    QVERIFY(cwd.isValid());
    AgentContext ctx;
    ctx.adapter = QStringLiteral("llamaagent");
    ctx.cwd = cwd.path();
    ctx.serverBaseUrl = QStringLiteral("http://127.0.0.1:1");
    ctx.modelId = QStringLiteral("test-model");

    LlamaAgentBackend backend;
    backend.start(ctx);
    QCOMPARE(backend.messages().size(), 1);
    backend.stop();

    QSignalSpy messagesSpy(&backend, &LlamaAgentBackend::messagesChanged);
    QSignalSpy sessionsSpy(&backend, &LlamaAgentBackend::sessionsChanged);
    backend.start(ctx);

    QVERIFY(messagesSpy.count() >= 1);
    QVERIFY(sessionsSpy.count() >= 1);
    QCOMPARE(backend.messages().first().toMap().value(QStringLiteral("content")).toString(),
             QStringLiteral("mensaje persistido"));

    backend.stop();
    QDir(store).removeRecursively();
}

QTEST_MAIN(AgentWireTests)
#include "test_agent_wire.moc"
