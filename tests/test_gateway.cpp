// Tests de LlmGateway (funciones puras): traducción Anthropic↔OpenAI, resolución
// de modelo, LRU keepN, salida estructurada. + decisión de idle auto-stop.

#include <QtTest>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonDocument>
#include "core/gateway/LlmGateway.h"
#include "AppController.h"

class GatewayTests : public QObject
{
    Q_OBJECT
private slots:
    void anthropicToOpenAIMapsSystemAndMessages();
    void anthropicToolsMapToOpenAI();
    void openAIToAnthropicMapsContentAndStop();
    void resolveModelMatches();
    void lruEvictsBeyondKeepN();
    void structuredOutputInjection();
    void idleStopDecision();
};

void GatewayTests::anthropicToOpenAIMapsSystemAndMessages()
{
    const QJsonObject a{
        {"model", "qwen"},
        {"system", "be terse"},
        {"max_tokens", 256},
        {"temperature", 0.4},
        {"stop_sequences", QJsonArray{"STOP"}},
        {"messages", QJsonArray{
            QJsonObject{{"role","user"}, {"content","hi"}},
            QJsonObject{{"role","assistant"}, {"content", QJsonArray{
                QJsonObject{{"type","text"},{"text","hello"}}}}}
        }}
    };
    const QJsonObject o = LlmGateway::anthropicToOpenAI(a);
    QCOMPARE(o.value("model").toString(), QStringLiteral("qwen"));
    QCOMPARE(o.value("max_tokens").toInt(), 256);
    const QJsonArray msgs = o.value("messages").toArray();
    QCOMPARE(msgs.size(), 3);   // system + user + assistant
    QCOMPARE(msgs.at(0).toObject().value("role").toString(), QStringLiteral("system"));
    QCOMPARE(msgs.at(0).toObject().value("content").toString(), QStringLiteral("be terse"));
    QCOMPARE(msgs.at(2).toObject().value("content").toString(), QStringLiteral("hello"));
    QCOMPARE(o.value("stop").toArray().first().toString(), QStringLiteral("STOP"));
}

void GatewayTests::anthropicToolsMapToOpenAI()
{
    const QJsonObject a{
        {"model","m"},
        {"messages", QJsonArray{}},
        {"tools", QJsonArray{ QJsonObject{
            {"name","get_weather"},
            {"description","weather"},
            {"input_schema", QJsonObject{{"type","object"}}}
        }}}
    };
    const QJsonObject o = LlmGateway::anthropicToOpenAI(a);
    const QJsonArray tools = o.value("tools").toArray();
    QCOMPARE(tools.size(), 1);
    const QJsonObject fn = tools.first().toObject().value("function").toObject();
    QCOMPARE(fn.value("name").toString(), QStringLiteral("get_weather"));
    QCOMPARE(fn.value("parameters").toObject().value("type").toString(), QStringLiteral("object"));
}

void GatewayTests::openAIToAnthropicMapsContentAndStop()
{
    const QJsonObject o{
        {"id","cmpl-1"},
        {"model","m"},
        {"choices", QJsonArray{ QJsonObject{
            {"finish_reason","stop"},
            {"message", QJsonObject{{"role","assistant"},{"content","hi there"}}}
        }}},
        {"usage", QJsonObject{{"prompt_tokens",10},{"completion_tokens",5}}}
    };
    const QJsonObject a = LlmGateway::openAIToAnthropic(o);
    QCOMPARE(a.value("type").toString(), QStringLiteral("message"));
    QCOMPARE(a.value("role").toString(), QStringLiteral("assistant"));
    QCOMPARE(a.value("stop_reason").toString(), QStringLiteral("end_turn"));
    const QJsonArray content = a.value("content").toArray();
    QCOMPARE(content.first().toObject().value("text").toString(), QStringLiteral("hi there"));
    QCOMPARE(a.value("usage").toObject().value("input_tokens").toInt(), 10);

    // tool_calls → tool_use + stop_reason tool_use
    const QJsonObject ot{
        {"choices", QJsonArray{ QJsonObject{
            {"finish_reason","tool_calls"},
            {"message", QJsonObject{{"tool_calls", QJsonArray{ QJsonObject{
                {"id","call_1"},
                {"function", QJsonObject{{"name","f"},{"arguments","{\"x\":1}"}}}
            }}}}}
        }}}
    };
    const QJsonObject at = LlmGateway::openAIToAnthropic(ot);
    QCOMPARE(at.value("stop_reason").toString(), QStringLiteral("tool_use"));
    const QJsonObject block = at.value("content").toArray().first().toObject();
    QCOMPARE(block.value("type").toString(), QStringLiteral("tool_use"));
    QCOMPARE(block.value("input").toObject().value("x").toInt(), 1);
}

void GatewayTests::resolveModelMatches()
{
    const QStringList avail{"Qwen3-14B", "Gemma-2-9B", "Llama-3.1-8B"};
    QCOMPARE(LlmGateway::resolveModel("qwen3-14b", avail), QStringLiteral("Qwen3-14B"));   // exacto ci
    QCOMPARE(LlmGateway::resolveModel("gemma", avail), QStringLiteral("Gemma-2-9B"));      // substring
    QVERIFY(LlmGateway::resolveModel("nonexistent-xyz", avail).isEmpty());
    QVERIFY(LlmGateway::resolveModel("", avail).isEmpty());
}

void GatewayTests::lruEvictsBeyondKeepN()
{
    QStringList order;
    QVERIFY(LlmGateway::lruTouch(order, "a", 2).isEmpty());
    QVERIFY(LlmGateway::lruTouch(order, "b", 2).isEmpty());
    const QStringList ev = LlmGateway::lruTouch(order, "c", 2);   // expulsa "a"
    QCOMPARE(ev, QStringList{"a"});
    QCOMPARE(order, (QStringList{"c","b"}));
    // re-tocar "b" lo manda al frente, sin expulsar.
    QVERIFY(LlmGateway::lruTouch(order, "b", 2).isEmpty());
    QCOMPARE(order, (QStringList{"b","c"}));
}

void GatewayTests::structuredOutputInjection()
{
    QJsonObject g = LlmGateway::applyStructuredOutput(QJsonObject{{"model","m"}},
                                                      QStringLiteral("root ::= \"yes\""), {});
    QCOMPARE(g.value("grammar").toString(), QStringLiteral("root ::= \"yes\""));

    QJsonObject j = LlmGateway::applyStructuredOutput(QJsonObject{{"model","m"}}, QString(),
                                                      QJsonObject{{"type","object"}});
    QCOMPARE(j.value("response_format").toObject().value("type").toString(),
             QStringLiteral("json_schema"));
}

void GatewayTests::idleStopDecision()
{
    // off
    QVERIFY(!AppController::shouldIdleStop(true, false, 0, 999999999));
    // server parado
    QVERIFY(!AppController::shouldIdleStop(false, false, 5, 999999999));
    // ocupado
    QVERIFY(!AppController::shouldIdleStop(true, true, 5, 999999999));
    // todavía no llega al umbral (5 min = 300000 ms)
    QVERIFY(!AppController::shouldIdleStop(true, false, 5, 200000));
    // supera umbral
    QVERIFY(AppController::shouldIdleStop(true, false, 5, 300001));
}

QTEST_MAIN(GatewayTests)
#include "test_gateway.moc"
