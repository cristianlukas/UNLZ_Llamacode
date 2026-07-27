// Tests de LlmGateway (funciones puras): traducción Anthropic↔OpenAI, resolución
// de modelo, LRU keepN, salida estructurada. + decisión de idle auto-stop.

#include <QtTest>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonDocument>
#include <QEventLoop>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QTcpServer>
#include "core/gateway/LlmGateway.h"
#include "core/integrations/OpenCodeIntegration.h"
#include "AppController.h"

class GatewayTests : public QObject
{
    Q_OBJECT
private slots:
    void anthropicToOpenAIMapsSystemAndMessages();
    void anthropicToolsMapToOpenAI();
    void openAIToAnthropicMapsContentAndStop();
    void resolveModelMatches();
    void stableModelCatalog();
    void openCodeConfigUsesEnvironmentSecret();
    void openCodeDesktopCandidates();
    void modelsEndpointServesStableIds();
    void preferredLanAddressSelectsPrivateIpv4();
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

void GatewayTests::stableModelCatalog()
{
    const QJsonArray models{
        QJsonObject{{"id","launch-qwen"}, {"name","Qwen Coder"},
                    {"context",32768}, {"output",8192}},
        QJsonObject{{"id","launch-gemma"}, {"name","Gemma"}}
    };
    QCOMPARE(LlmGateway::resolveModelId("launch-qwen", models),
             QStringLiteral("launch-qwen"));
    QCOMPARE(LlmGateway::resolveModelId("qwen coder", models),
             QStringLiteral("launch-qwen"));
    QVERIFY(LlmGateway::resolveModelId("qwen", models).isEmpty());

    const QJsonObject response = LlmGateway::modelsResponse(models);
    QCOMPARE(response.value("object").toString(), QStringLiteral("list"));
    const QJsonArray data = response.value("data").toArray();
    QCOMPARE(data.size(), 2);
    QCOMPARE(data.first().toObject().value("id").toString(),
             QStringLiteral("launch-qwen"));
    QCOMPARE(data.first().toObject().value("owned_by").toString(),
             QStringLiteral("llamacode"));
}

void GatewayTests::openCodeConfigUsesEnvironmentSecret()
{
    const QJsonArray models{
        QJsonObject{{"id","launch-qwen"}, {"name","Qwen Coder"},
                    {"context",32768}, {"output",8192}}
    };
    const QJsonObject config = OpenCodeIntegration::buildConfig(
        QStringLiteral("http://127.0.0.1:8088/v1"), models,
        QStringLiteral("launch-qwen"));
    QCOMPARE(config.value("model").toString(),
             QStringLiteral("llamacode/launch-qwen"));
    const QJsonObject provider = config.value("provider").toObject()
        .value("llamacode").toObject();
    QCOMPARE(provider.value("npm").toString(),
             QStringLiteral("@ai-sdk/openai-compatible"));
    const QJsonObject options = provider.value("options").toObject();
    QCOMPARE(options.value("baseURL").toString(),
             QStringLiteral("http://127.0.0.1:8088/v1"));
    QCOMPARE(options.value("apiKey").toString(),
             QStringLiteral("{env:LLAMACODE_GATEWAY_API_KEY}"));
    const QByteArray serialized = QJsonDocument(config).toJson();
    QVERIFY(!serialized.contains("sk-"));
    QCOMPARE(provider.value("models").toObject().value("launch-qwen").toObject()
                 .value("limit").toObject().value("context").toInt(), 32768);
    QVERIFY(provider.value("models").toObject().value("launch-qwen").toObject()
                .value("tool_call").toBool());
}

void GatewayTests::openCodeDesktopCandidates()
{
    const QStringList candidates =
        OpenCodeIntegration::windowsDesktopCandidates(QStringLiteral("C:/Users/Test/AppData/Local"));
    QCOMPARE(candidates.size(), 3);
    QCOMPARE(QDir::fromNativeSeparators(candidates.first()),
             QStringLiteral("C:/Users/Test/AppData/Local/Programs/"
                            "@opencode-aidesktop/OpenCode.exe"));
    QVERIFY(OpenCodeIntegration::windowsDesktopCandidates({}).isEmpty());
}

void GatewayTests::modelsEndpointServesStableIds()
{
    QTcpServer probe;
    QVERIFY(probe.listen(QHostAddress::LocalHost, 0));
    const quint16 port = probe.serverPort();
    probe.close();

    LlmGateway gateway;
    LlmGateway::Hooks hooks;
    hooks.models = [] {
        return QJsonArray{QJsonObject{{"id","launch-qwen"}, {"name","Qwen"}}};
    };
    gateway.setHooks(hooks);
    QVERIFY(gateway.start(port));

    QNetworkAccessManager nam;
    QNetworkReply *reply = nam.get(QNetworkRequest(
        QUrl(QStringLiteral("http://127.0.0.1:%1/v1/models").arg(port))));
    QEventLoop loop;
    connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    loop.exec();
    QCOMPARE(reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 200);
    const QJsonObject result = QJsonDocument::fromJson(reply->readAll()).object();
    QCOMPARE(result.value("data").toArray().first().toObject().value("id").toString(),
             QStringLiteral("launch-qwen"));
    reply->deleteLater();
}

void GatewayTests::preferredLanAddressSelectsPrivateIpv4()
{
    const QList<QHostAddress> addresses{
        QHostAddress(QStringLiteral("127.0.0.1")),
        QHostAddress(QStringLiteral("169.254.10.20")),
        QHostAddress(QStringLiteral("2001:db8::1")),
        QHostAddress(QStringLiteral("192.168.1.42")),
        QHostAddress(QStringLiteral("10.0.0.8"))
    };
    QCOMPARE(LlmGateway::preferredLanAddress(addresses).toString(),
             QStringLiteral("192.168.1.42"));
    QVERIFY(LlmGateway::preferredLanAddress({
        QHostAddress(QStringLiteral("127.0.0.1")),
        QHostAddress(QStringLiteral("169.254.1.2"))
    }).isNull());
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
