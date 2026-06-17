#include <QtTest>
#include <QJsonArray>
#include <QJsonObject>
#include "core/agent/LlamaAgentBackend.h"

class AgentWireTests : public QObject
{
    Q_OBJECT
private slots:
    void dropsOrphanToolAndDemotesNonInitialSystem();
    void dropsDanglingAssistantAndAnchorsFirstUser();
};

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

QTEST_MAIN(AgentWireTests)
#include "test_agent_wire.moc"
