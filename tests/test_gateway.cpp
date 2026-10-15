// Tests de LlmGateway (funciones puras): traducción Anthropic↔OpenAI, resolución
// de modelo, LRU keepN, salida estructurada. + decisión de idle auto-stop.

#include <QtTest>
#include <QNetworkInterface>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonDocument>
#include <QEventLoop>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QTcpServer>
#include "core/gateway/LlmGateway.h"
#include "core/integrations/ClaudeDesktopIntegration.h"
#include "core/integrations/OpenCodeIntegration.h"
#include "AppController.h"

class GatewayTests : public QObject
{
    Q_OBJECT
private slots:
    void anthropicToOpenAIMapsSystemAndMessages();
    void anthropicToolHistoryMapsToOpenAI();
    void anthropicToolsMapToOpenAI();
    void openAIToAnthropicMapsContentAndStop();
    void resolveModelMatches();
    void stableModelCatalog();
    void discoveryNeverContainsCredentials();
    void discoveryListsProfilesBeforeFirstModelLoad();
    void lanHealthRequiresAuthentication();
    void lanHealthCanBeExplicitlyUnauthenticated();
    void claudeDesktopConfigUsesStableAliases();
    void openCodeConfigUsesEnvironmentSecret();
    void openCodeDesktopCandidates();
    void modelsEndpointServesStableIds();
    void preferredLanAddressSelectsPrivateIpv4();
    void lanActivationStartsRequestedProfile();
    void lanSwapPolicyAndPeerDetection();
    void lanClientCannotSwapLoadedModelWhenLocked();
    void requestHookReportsLoopbackAsLocal();
    void lanStatusReportsModelLoadProgress();
    void lanStatusWithoutTrackerFallsBackToReady();
    void lanClientWaitsForRequestedModel();
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

void GatewayTests::anthropicToolHistoryMapsToOpenAI()
{
    const QJsonObject a{
        {"model", "m"},
        {"messages", QJsonArray{
            QJsonObject{{"role", "assistant"}, {"content", QJsonArray{
                QJsonObject{{"type", "tool_use"}, {"id", "call_1"},
                             {"name", "read_file"},
                             {"input", QJsonObject{{"path", "main.cpp"}}}}
            }}},
            QJsonObject{{"role", "user"}, {"content", QJsonArray{
                QJsonObject{{"type", "tool_result"}, {"tool_use_id", "call_1"},
                             {"content", "file contents"}}
            }}}
        }}
    };
    const QJsonArray messages = LlmGateway::anthropicToOpenAI(a)
                                    .value("messages").toArray();
    QCOMPARE(messages.size(), 2);
    const QJsonObject assistant = messages.at(0).toObject();
    QCOMPARE(assistant.value("tool_calls").toArray().first().toObject()
                 .value("function").toObject().value("name").toString(),
             QStringLiteral("read_file"));
    QCOMPARE(assistant.value("tool_calls").toArray().first().toObject()
                 .value("function").toObject().value("arguments").toString(),
             QStringLiteral("{\"path\":\"main.cpp\"}"));
    const QJsonObject result = messages.at(1).toObject();
    QCOMPARE(result.value("role").toString(), QStringLiteral("tool"));
    QCOMPARE(result.value("tool_call_id").toString(), QStringLiteral("call_1"));
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
    QCOMPARE(data.size(), 4);
    QCOMPARE(data.first().toObject().value("id").toString(),
             QStringLiteral("launch-qwen"));
    QCOMPARE(data.first().toObject().value("owned_by").toString(),
             QStringLiteral("llamacode"));
    QCOMPARE(data.at(1).toObject().value("id").toString(),
             QStringLiteral("claude-llamacode-launch-qwen"));
    QCOMPARE(LlmGateway::resolveModelId("claude-llamacode-launch-qwen", models),
             QStringLiteral("launch-qwen"));
}

void GatewayTests::discoveryNeverContainsCredentials()
{
    const QJsonObject response = LlmGateway::discoveryResponse(
        QStringLiteral("devbox"), 8088, true, QStringLiteral("launch-qwen"),
        QJsonArray{QJsonObject{{"id", "launch-qwen"}}});
    QVERIFY(!response.contains(QStringLiteral("apiKey")));
    QVERIFY(!QJsonDocument(response).toJson(QJsonDocument::Compact)
                 .contains("secret"));
    QCOMPARE(response.value(QStringLiteral("protocol")).toString(),
             QStringLiteral("llamacode-lan-v1"));
}

void GatewayTests::discoveryListsProfilesBeforeFirstModelLoad()
{
    const QJsonArray profiles{
        QJsonObject{{"id", "sys-astra-strata-iq3s"}, {"name", "ASTRA IQ3_S"}},
        QJsonObject{{"id", "launch-sol"}, {"name", "SOL"}}
    };
    const QJsonObject response = LlmGateway::discoveryResponse(
        QStringLiteral("server-pc"), 8088, false, QString(), profiles);

    QVERIFY(!response.value(QStringLiteral("ready")).toBool());
    QVERIFY(response.value(QStringLiteral("currentModel")).toString().isEmpty());
    const QJsonArray published = response.value(QStringLiteral("profiles")).toArray();
    QCOMPARE(published.size(), 2);
    QCOMPARE(published.at(0).toObject().value(QStringLiteral("id")).toString(),
             QStringLiteral("sys-astra-strata-iq3s"));
    QCOMPARE(published.at(1).toObject().value(QStringLiteral("id")).toString(),
             QStringLiteral("launch-sol"));
}

void GatewayTests::lanHealthRequiresAuthentication()
{
    QTcpServer probe;
    QVERIFY(probe.listen(QHostAddress::AnyIPv4, 0));
    const quint16 port = probe.serverPort();
    probe.close();

    LlmGateway gateway;
    QVERIFY(gateway.start(port, QHostAddress::AnyIPv4));

    QNetworkAccessManager nam;
    QNetworkReply *unauthorized = nam.get(QNetworkRequest(
        QUrl(QStringLiteral("http://127.0.0.1:%1/health").arg(port))));
    QEventLoop unauthorizedLoop;
    connect(unauthorized, &QNetworkReply::finished,
            &unauthorizedLoop, &QEventLoop::quit);
    unauthorizedLoop.exec();
    QCOMPARE(unauthorized->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 401);
    unauthorized->deleteLater();

    gateway.setApiKey(QStringLiteral("secret"));
    QNetworkRequest authorizedRequest(
        QUrl(QStringLiteral("http://127.0.0.1:%1/health").arg(port)));
    authorizedRequest.setRawHeader("Authorization", QByteArrayLiteral("Bearer secret"));
    QNetworkReply *authorized = nam.get(authorizedRequest);
    QEventLoop authorizedLoop;
    connect(authorized, &QNetworkReply::finished,
            &authorizedLoop, &QEventLoop::quit);
    authorizedLoop.exec();
    QCOMPARE(authorized->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 200);
    authorized->deleteLater();
}

void GatewayTests::lanHealthCanBeExplicitlyUnauthenticated()
{
    QTcpServer probe;
    QVERIFY(probe.listen(QHostAddress::AnyIPv4, 0));
    const quint16 port = probe.serverPort();
    probe.close();

    LlmGateway gateway;
    QVERIFY(gateway.start(port, QHostAddress::AnyIPv4));

    QNetworkAccessManager nam;
    QNetworkReply *locked = nam.get(QNetworkRequest(
        QUrl(QStringLiteral("http://127.0.0.1:%1/health").arg(port))));
    QEventLoop lockedLoop;
    connect(locked, &QNetworkReply::finished, &lockedLoop, &QEventLoop::quit);
    lockedLoop.exec();
    QCOMPARE(locked->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 401);
    locked->deleteLater();

    // Even a previously saved key must not silently re-enable auth when the
    // host explicitly opts into password-free LAN mode.
    gateway.setApiKey(QStringLiteral("previously-saved-key"));
    gateway.setLanAuthEnabled(false);
    QNetworkReply *open = nam.get(QNetworkRequest(
        QUrl(QStringLiteral("http://127.0.0.1:%1/health").arg(port))));
    QEventLoop openLoop;
    connect(open, &QNetworkReply::finished, &openLoop, &QEventLoop::quit);
    openLoop.exec();
    QCOMPARE(open->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 200);
    open->deleteLater();
}

void GatewayTests::claudeDesktopConfigUsesStableAliases()
{
    const QJsonArray models{
        QJsonObject{{"id", "launch-qwen"}, {"name", "Qwen Coder"}},
        QJsonObject{{"id", "launch-gemma"}, {"name", "Gemma"}}
    };
    const QJsonObject config = ClaudeDesktopIntegration::gatewayConfig(
        QStringLiteral("http://127.0.0.1:8088/"), QStringLiteral("local"),
        models, QStringLiteral("launch-gemma"));
    QCOMPARE(config.value("inferenceProvider").toString(), QStringLiteral("gateway"));
    QCOMPARE(config.value("inferenceGatewayBaseUrl").toString(),
             QStringLiteral("http://127.0.0.1:8088"));
    const QJsonArray inferenceModels = config.value("inferenceModels").toArray();
    QCOMPARE(inferenceModels.size(), 2);
    QCOMPARE(inferenceModels.first().toObject().value("name").toString(),
             QStringLiteral("claude-llamacode-launch-gemma"));
    QCOMPARE(inferenceModels.first().toObject().value("labelOverride").toString(),
             QStringLiteral("LlamaCode · Gemma"));

    const QJsonObject mode = ClaudeDesktopIntegration::withDeploymentMode(
        QJsonObject{{"keep", true}}, QStringLiteral("3p"));
    QVERIFY(mode.value("keep").toBool());
    QCOMPARE(mode.value("deploymentMode").toString(), QStringLiteral("3p"));
    QCOMPARE(ClaudeDesktopIntegration::metaConfig(models, "launch-gemma")
                 .value("appliedId").toString(),
             ClaudeDesktopIntegration::configId());
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
    QCOMPARE(result.value("data").toArray().at(1).toObject().value("id").toString(),
             QStringLiteral("claude-llamacode-launch-qwen"));
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

void GatewayTests::lanActivationStartsRequestedProfile()
{
    QTcpServer probe;
    QVERIFY(probe.listen(QHostAddress::LocalHost, 0));
    const quint16 port = probe.serverPort();
    probe.close();
    QString activated;
    const QString astraId = QStringLiteral("sys-astra-strata-iq3s");
    LlmGateway gateway;
    LlmGateway::Hooks hooks;
    hooks.models = [] {
        return QJsonArray{QJsonObject{{"id","sys-astra-strata-iq3s"},
                                      {"name","ASTRA · Strata IQ3_S"}}};
    };
    hooks.ensureModel = [&activated](const QString &id) { activated = id; };
    gateway.setHooks(hooks);
    gateway.setApiKey(QStringLiteral("secret"));
    QVERIFY(gateway.start(port));
    QNetworkRequest request(QUrl(
        QStringLiteral("http://127.0.0.1:%1/llamacode/v1/activate").arg(port)));
    request.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));
    request.setRawHeader("Authorization", "Bearer secret");
    QNetworkAccessManager nam;
    QNetworkReply *reply = nam.post(request,
        QJsonDocument(QJsonObject{{"model", astraId}}).toJson(QJsonDocument::Compact));
    QEventLoop loop;
    connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    loop.exec();
    QCOMPARE(reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 200);
    QCOMPARE(activated, astraId);
    reply->deleteLater();
}

void GatewayTests::lanSwapPolicyAndPeerDetection()
{
    QVERIFY(!LlmGateway::isLanPeer(QHostAddress(QStringLiteral("127.0.0.1"))));
    QVERIFY(!LlmGateway::isLanPeer(QHostAddress(QStringLiteral("::1"))));
    QVERIFY(!LlmGateway::isLanPeer(QHostAddress(QStringLiteral("::ffff:127.0.0.1"))));
    QVERIFY(LlmGateway::isLanPeer(QHostAddress(QStringLiteral("192.168.1.50"))));
    QVERIFY(LlmGateway::isLanPeer(QHostAddress(QStringLiteral("::ffff:192.168.1.50"))));

    // Loopback y "permitir" nunca se restringen.
    QVERIFY(LlmGateway::lanSwapAllowed(false, false, true, "astra", "other"));
    QVERIFY(LlmGateway::lanSwapAllowed(true, true, true, "astra", "other"));
    // Bloqueado: LAN no cambia el modelo cargado...
    QVERIFY(!LlmGateway::lanSwapAllowed(true, false, true, "astra", "other"));
    // ...pero sí usa el mismo, o carga uno si no hay nada.
    QVERIFY(LlmGateway::lanSwapAllowed(true, false, true, "astra", "ASTRA"));
    QVERIFY(LlmGateway::lanSwapAllowed(true, false, false, "astra", "other"));
    QVERIFY(LlmGateway::lanSwapAllowed(true, false, true, "astra", ""));
}

// El cliente LAN pidió un perfil Compose y después ASTRA: el anfitrión cambió de
// modelo dos veces sin que el usuario lo viera. Con la opción bloqueada, el
// cliente recibe 409 y el modelo cargado no se toca. Requiere una IP de LAN.
void GatewayTests::lanClientCannotSwapLoadedModelWhenLocked()
{
    const QHostAddress lanIp = LlmGateway::preferredLanAddress(QNetworkInterface::allAddresses());
    if (lanIp.isNull())
        QSKIP("sin IPv4 de LAN: no se puede simular un cliente no-loopback");
    QTcpServer probe;
    QVERIFY(probe.listen(QHostAddress::AnyIPv4, 0));
    const quint16 port = probe.serverPort();
    probe.close();

    QStringList ensured;
    QList<QJsonObject> logged;
    LlmGateway gateway;
    LlmGateway::Hooks hooks;
    hooks.models = [] {
        return QJsonArray{QJsonObject{{"id", "astra"}, {"name", "ASTRA"}},
                          QJsonObject{{"id", "compose"}, {"name", "Compose"}}};
    };
    hooks.currentModel = [] { return QStringLiteral("astra"); };
    hooks.running = [] { return true; };
    hooks.ensureModel = [&ensured](const QString &id) { ensured << id; };
    hooks.request = [&logged](const QJsonObject &r) { logged << r; };
    gateway.setHooks(hooks);
    gateway.setApiKey(QStringLiteral("secret"));
    gateway.setLanMayLoadModels(false);
    QVERIFY(gateway.start(port, QHostAddress::AnyIPv4));

    QNetworkAccessManager nam;
    auto activate = [&](const QString &model) {
        QNetworkRequest request(QUrl(QStringLiteral("http://%1:%2/llamacode/v1/activate")
                                         .arg(lanIp.toString()).arg(port)));
        request.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));
        request.setRawHeader("Authorization", "Bearer secret");
        QNetworkReply *reply = nam.post(request,
            QJsonDocument(QJsonObject{{"model", model}}).toJson(QJsonDocument::Compact));
        QEventLoop loop;
        connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
        loop.exec();
        const int code = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        reply->deleteLater();
        return code;
    };

    QCOMPARE(activate(QStringLiteral("compose")), 409);
    QVERIFY(ensured.isEmpty());                      // el modelo cargado no se tocó
    QCOMPARE(activate(QStringLiteral("astra")), 200);   // el mismo modelo, sí
    // (activate siempre avisa; AppController ignora el pedido del modelo ya activo)
    QCOMPARE(ensured, QStringList{QStringLiteral("astra")});

    QTRY_COMPARE(logged.size(), 2);
    QVERIFY(logged[0].value("lan").toBool());
    QCOMPARE(logged[0].value("peer").toString(), lanIp.toString());
    QCOMPARE(logged[0].value("status").toInt(), 409);
    QCOMPARE(logged[0].value("model").toString(), QStringLiteral("compose"));
    QCOMPARE(logged[1].value("status").toInt(), 200);

    gateway.setLanMayLoadModels(true);              // por defecto: como antes
    QCOMPARE(activate(QStringLiteral("compose")), 200);
    QCOMPARE(ensured, (QStringList{QStringLiteral("astra"), QStringLiteral("compose")}));
    gateway.stop();
}

void GatewayTests::requestHookReportsLoopbackAsLocal()
{
    QTcpServer probe;
    QVERIFY(probe.listen(QHostAddress::LocalHost, 0));
    const quint16 port = probe.serverPort();
    probe.close();
    QList<QJsonObject> logged;
    LlmGateway gateway;
    LlmGateway::Hooks hooks;
    hooks.models = [] { return QJsonArray{QJsonObject{{"id", "m"}, {"name", "M"}}}; };
    hooks.request = [&logged](const QJsonObject &r) { logged << r; };
    gateway.setHooks(hooks);
    QVERIFY(gateway.start(port));
    QNetworkAccessManager nam;
    QNetworkReply *reply = nam.get(QNetworkRequest(QUrl(
        QStringLiteral("http://127.0.0.1:%1/v1/models").arg(port))));
    QEventLoop loop;
    connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    loop.exec();
    reply->deleteLater();
    QTRY_COMPARE(logged.size(), 1);
    QVERIFY(!logged[0].value("lan").toBool());
    QCOMPARE(logged[0].value("path").toString(), QStringLiteral("/v1/models"));
    QCOMPARE(logged[0].value("status").toInt(), 200);
}

void GatewayTests::lanStatusReportsModelLoadProgress()
{
    QTcpServer probe;
    QVERIFY(probe.listen(QHostAddress::LocalHost, 0));
    const quint16 port = probe.serverPort();
    probe.close();
    LlmGateway gateway;
    LlmGateway::Hooks hooks;
    hooks.ready = [] { return false; };
    hooks.currentModel = [] { return QStringLiteral("big-model"); };
    hooks.loadStatus = [] {
        return QJsonObject{{"state", "loading"}, {"progress", 42},
                           {"estimated", true}, {"model", "big-model"}};
    };
    gateway.setHooks(hooks);
    gateway.setApiKey(QStringLiteral("secret"));
    QVERIFY(gateway.start(port));
    QNetworkAccessManager nam;
    auto get = [&](const QByteArray &auth) {
        QNetworkRequest request(QUrl(
            QStringLiteral("http://127.0.0.1:%1/llamacode/v1/status").arg(port)));
        if (!auth.isEmpty()) request.setRawHeader("Authorization", auth);
        QNetworkReply *reply = nam.get(request);
        QEventLoop loop;
        connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
        loop.exec();
        reply->deleteLater();
        return reply;
    };
    // Mismas reglas de auth que el resto del gateway.
    QCOMPARE(get({})->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 401);
    QNetworkReply *ok = get("Bearer secret");
    QCOMPARE(ok->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt(), 200);
    const QJsonObject body = QJsonDocument::fromJson(ok->readAll()).object();
    QCOMPARE(body.value("ready").toBool(), false);
    const QJsonObject load = body.value("load").toObject();
    QCOMPARE(load.value("state").toString(), QStringLiteral("loading"));
    QCOMPARE(load.value("progress").toInt(), 42);
    QCOMPARE(load.value("model").toString(), QStringLiteral("big-model"));
}

void GatewayTests::lanStatusWithoutTrackerFallsBackToReady()
{
    const QJsonObject ready = LlmGateway::statusResponse(true, QStringLiteral("m"), {});
    QCOMPARE(ready.value("load").toObject().value("state").toString(), QStringLiteral("ready"));
    QCOMPARE(ready.value("load").toObject().value("progress").toInt(), 100);
    QCOMPARE(ready.value("load").toObject().value("model").toString(), QStringLiteral("m"));
    const QJsonObject idle = LlmGateway::statusResponse(false, QString(), {});
    QCOMPARE(idle.value("load").toObject().value("state").toString(), QStringLiteral("idle"));
}

void GatewayTests::lanClientWaitsForRequestedModel()
{
    auto body = [](const QString &state, const QString &model, int progress) {
        return QJsonObject{{"load", QJsonObject{{"state", state}, {"model", model},
                                                {"progress", progress}}}};
    };
    // Listo con el modelo pedido: deja de seguir.
    QVERIFY(AppController::remoteLoadFromStatus(body("ready", "new", 100), "new").isEmpty());
    // "ready" del modelo VIEJO = el swap todavía no arrancó: sigue en "starting".
    const QJsonObject swapping = AppController::remoteLoadFromStatus(body("ready", "old", 100), "new");
    QCOMPARE(swapping.value("state").toString(), QStringLiteral("starting"));
    QCOMPARE(swapping.value("progress").toInt(), 0);
    // "idle" (el anfitrión bajó el viejo y aún no levantó el nuevo) tampoco es listo.
    QCOMPARE(AppController::remoteLoadFromStatus(body("idle", "", -1), "new")
                 .value("state").toString(), QStringLiteral("starting"));
    // Cargando: se muestra tal cual.
    QCOMPARE(AppController::remoteLoadFromStatus(body("loading", "new", 37), "new")
                 .value("progress").toInt(), 37);
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
