#include <QtTest>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTcpSocket>
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
    void parsesTextToolCallFallback();
    void fallsBackToTextToolsWhenServerRejectsNativeTools();
    void restartRepublishesPersistedMessages();
    void taskSessionIsEphemeralAndRestoresPrevious();
    void mergeToolCallDelta_assemblesAcrossChunks();
    void mergeToolCallDelta_parallelCallsByIndex();
    void visibleAnswer_stripsThinkButSalvagesWhenEmpty();
    void buildObservationMessage_wrapsImagesAsUserMultimodal();
    void buildObservationMessage_emptyWhenNoImages();
    void developmentDisciplineSection_coversRegressionGuards();
    void testSafetyNetSection_coversRunnerDetectionAndQuality();
    void projectContextSection_coversIntentAndMemory();
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

void AgentWireTests::parsesTextToolCallFallback()
{
    const QString content = QStringLiteral(
        "TOOL_CALL {\"name\":\"web_fetch\",\"arguments\":{\"url\":\"https://dolarhoy.com/\"}}");

    const QJsonObject call = LlamaAgentBackend::textToolCallFromContent(content);
    QVERIFY(!call.isEmpty());
    QVERIFY(call.value(QStringLiteral("id")).toString().startsWith(QStringLiteral("textcall_")));
    QCOMPARE(call.value(QStringLiteral("type")).toString(), QStringLiteral("function"));

    const QJsonObject fn = call.value(QStringLiteral("function")).toObject();
    QCOMPARE(fn.value(QStringLiteral("name")).toString(), QStringLiteral("web_fetch"));

    const QJsonObject args = QJsonDocument::fromJson(
        fn.value(QStringLiteral("arguments")).toString().toUtf8()).object();
    QCOMPARE(args.value(QStringLiteral("url")).toString(), QStringLiteral("https://dolarhoy.com/"));
}

class FakeToolRejectingServer : public QTcpServer
{
public:
    int nativeRejects = 0;
    int textRequests = 0;
    int secondTextBodySize = 0;
    bool secondTextBodyWasTruncated = false;

protected:
    void incomingConnection(qintptr socketDescriptor) override
    {
        auto *sock = new QTcpSocket(this);
        sock->setSocketDescriptor(socketDescriptor);
        auto *buf = new QByteArray;
        connect(sock, &QTcpSocket::readyRead, this, [this, sock, buf]() {
            buf->append(sock->readAll());
            const int headerEnd = buf->indexOf("\r\n\r\n");
            if (headerEnd < 0) return;
            const QByteArray headers = buf->left(headerEnd);
            int contentLength = 0;
            for (const QByteArray &line : headers.split('\n')) {
                const QByteArray trimmed = line.trimmed();
                if (trimmed.toLower().startsWith("content-length:"))
                    contentLength = trimmed.mid(15).trimmed().toInt();
            }
            if (buf->size() < headerEnd + 4 + contentLength) return;

            const QByteArray firstLine = headers.split('\n').value(0).trimmed();
            const QByteArray body = buf->mid(headerEnd + 4, contentLength);
            if (firstLine.startsWith("GET /props")) {
                writeJson(sock, QByteArrayLiteral("{\"n_ctx\":4096}"));
                return;
            }
            if (body.contains("\"tools\"")) {
                ++nativeRejects;
                writeRaw(sock, QByteArrayLiteral(
                    "HTTP/1.1 400 Bad Request\r\nContent-Length: 23\r\nConnection: close\r\n\r\nnative tools rejected"));
                return;
            }

            ++textRequests;
            if (textRequests == 1) {
                writeSse(sock, QStringLiteral(
                    "TOOL_CALL {\"name\":\"read_file\",\"arguments\":{\"path\":\"big.txt\"}}"));
            } else {
                QVERIFY(body.contains("TOOL_RESULT"));
                secondTextBodySize = body.size();
                secondTextBodyWasTruncated = body.contains("TOOL_RESULT truncado");
                writeSse(sock, QStringLiteral("FINAL: read_file ejecutado correctamente"));
            }
        });
        connect(sock, &QTcpSocket::disconnected, sock, &QObject::deleteLater);
    }

private:
    static void writeJson(QTcpSocket *sock, const QByteArray &json)
    {
        writeRaw(sock, QByteArrayLiteral("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ")
                       + QByteArray::number(json.size())
                       + QByteArrayLiteral("\r\nConnection: close\r\n\r\n") + json);
    }

    static void writeSse(QTcpSocket *sock, const QString &content)
    {
        const QByteArray escaped = QString(content).replace("\\", "\\\\").replace("\"", "\\\"").toUtf8();
        const QByteArray payload = QByteArrayLiteral("data: {\"choices\":[{\"delta\":{\"content\":\"")
                                   + escaped + QByteArrayLiteral("\"}}]}\n\n")
                                   + QByteArrayLiteral("data: [DONE]\n\n");
        writeRaw(sock, QByteArrayLiteral("HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: ")
                       + QByteArray::number(payload.size())
                       + QByteArrayLiteral("\r\nConnection: close\r\n\r\n") + payload);
    }

    static void writeRaw(QTcpSocket *sock, const QByteArray &data)
    {
        sock->write(data);
        sock->flush();
        sock->disconnectFromHost();
    }
};

void AgentWireTests::fallsBackToTextToolsWhenServerRejectsNativeTools()
{
    QTemporaryDir cwd;
    QVERIFY(cwd.isValid());
    QFile marker(cwd.path() + QStringLiteral("/marker.txt"));
    QVERIFY(marker.open(QIODevice::WriteOnly));
    marker.write("ok");
    marker.close();
    QFile big(cwd.path() + QStringLiteral("/big.txt"));
    QVERIFY(big.open(QIODevice::WriteOnly));
    big.write(QByteArray(50000, 'x'));
    big.close();

    FakeToolRejectingServer server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));

    AgentContext ctx;
    ctx.adapter = QStringLiteral("llamaagent");
    ctx.cwd = cwd.path();
    ctx.serverBaseUrl = QStringLiteral("http://127.0.0.1:%1").arg(server.serverPort());
    ctx.modelId = QStringLiteral("test-model");
    ctx.ctxOverride = 4096;

    LlamaAgentBackend backend;
    backend.setEphemeralSessions(true);
    backend.start(ctx);
    QSignalSpy finished(&backend, &LlamaAgentBackend::turnFinished);
    backend.sendMessage(QStringLiteral("Listá el directorio actual usando tools."));

    QTRY_VERIFY_WITH_TIMEOUT(finished.count() == 1, 10000);
    QCOMPARE(server.nativeRejects, 2);
    QCOMPARE(server.textRequests, 2);
    QVERIFY(server.secondTextBodySize < 20000);
    QVERIFY(server.secondTextBodyWasTruncated);

    bool sawTool = false;
    bool sawFinal = false;
    for (const QVariant &v : backend.messages()) {
        const QVariantMap m = v.toMap();
        if (m.value(QStringLiteral("role")).toString() == QLatin1String("toolcall")
            && m.value(QStringLiteral("name")).toString() == QLatin1String("read_file"))
            sawTool = true;
        if (m.value(QStringLiteral("content")).toString().contains(QStringLiteral("read_file ejecutado")))
            sawFinal = true;
    }
    QVERIFY(sawTool);
    QVERIFY(sawFinal);
    backend.stop();
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

void AgentWireTests::taskSessionIsEphemeralAndRestoresPrevious()
{
    // Regresión: correr una Task/Automatización NO debe dejar su sesión en el
    // panel "Agente". La sesión de la Task es efímera (no listada, no persistida)
    // y al terminar se restaura la sesión del usuario.
    const QString store = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                          + QStringLiteral("/agent_llamaagent");
    QDir(store).removeRecursively();
    QVERIFY(QDir().mkpath(store));

    const QString sessionId = QStringLiteral("user-session");
    QFile indexFile(store + QStringLiteral("/index.json"));
    QVERIFY(indexFile.open(QIODevice::WriteOnly | QIODevice::Truncate));
    indexFile.write(QJsonDocument(QJsonArray{QJsonObject{
        {QStringLiteral("id"), sessionId},
        {QStringLiteral("title"), QStringLiteral("Del usuario")},
        {QStringLiteral("created"), 1.0}
    }}).toJson());
    indexFile.close();

    QFile sessionFile(store + QStringLiteral("/") + sessionId + QStringLiteral(".json"));
    QVERIFY(sessionFile.open(QIODevice::WriteOnly | QIODevice::Truncate));
    sessionFile.write(QJsonDocument(QJsonObject{
        {QStringLiteral("id"), sessionId},
        {QStringLiteral("title"), QStringLiteral("Del usuario")},
        {QStringLiteral("messages"), QJsonArray{QJsonObject{
            {QStringLiteral("role"), QStringLiteral("assistant")},
            {QStringLiteral("content"), QStringLiteral("mensaje del usuario")}
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
    const int listedBefore = backend.sessions().size();
    QCOMPARE(listedBefore, 1);

    // Arranca la sesión efímera de la Task: no debe sumarse al panel.
    backend.newTaskSession();
    QCOMPARE(backend.sessions().size(), listedBefore);

    // Termina la Task: se restaura la sesión del usuario con sus mensajes.
    backend.endTaskSession();
    QCOMPARE(backend.sessions().size(), listedBefore);
    QVERIFY(!backend.messages().isEmpty());
    QCOMPARE(backend.messages().first().toMap().value(QStringLiteral("content")).toString(),
             QStringLiteral("mensaje del usuario"));

    backend.stop();
    QDir(store).removeRecursively();
}

// Helper: arma un delta de tool_calls como el que manda el server en streaming.
static QJsonArray tcDelta(int index, const QJsonObject &fn,
                          const QString &id = QString())
{
    QJsonObject tc{{QStringLiteral("index"), index},
                   {QStringLiteral("function"), fn}};
    if (!id.isEmpty()) tc.insert(QStringLiteral("id"), id);
    return QJsonArray{tc};
}

void AgentWireTests::mergeToolCallDelta_assemblesAcrossChunks()
{
    QHash<int, QJsonObject> acc;
    // Chunk 1: id + name. Chunk 2 y 3: arguments parciales (se concatenan).
    LlamaAgentBackend::mergeToolCallDelta(acc,
        tcDelta(0, QJsonObject{{QStringLiteral("name"), QStringLiteral("read_file")}},
                QStringLiteral("call_1")));
    LlamaAgentBackend::mergeToolCallDelta(acc,
        tcDelta(0, QJsonObject{{QStringLiteral("arguments"), QStringLiteral("{\"path\":\"")}}));
    LlamaAgentBackend::mergeToolCallDelta(acc,
        tcDelta(0, QJsonObject{{QStringLiteral("arguments"), QStringLiteral("x.txt\"}")}}));

    QCOMPARE(acc.size(), 1);
    const QJsonObject call = acc.value(0);
    QCOMPARE(call.value(QStringLiteral("id")).toString(), QStringLiteral("call_1"));
    QCOMPARE(call.value(QStringLiteral("name")).toString(), QStringLiteral("read_file"));
    QCOMPARE(call.value(QStringLiteral("arguments")).toString(),
             QStringLiteral("{\"path\":\"x.txt\"}"));
    // Los arguments deben parsear a JSON válido tras el ensamblado.
    const QJsonDocument args = QJsonDocument::fromJson(
        call.value(QStringLiteral("arguments")).toString().toUtf8());
    QVERIFY(args.isObject());
    QCOMPARE(args.object().value(QStringLiteral("path")).toString(), QStringLiteral("x.txt"));
}

void AgentWireTests::mergeToolCallDelta_parallelCallsByIndex()
{
    QHash<int, QJsonObject> acc;
    // Dos tool_calls paralelas (index 0 y 1) intercaladas en el stream.
    LlamaAgentBackend::mergeToolCallDelta(acc,
        tcDelta(0, QJsonObject{{QStringLiteral("name"), QStringLiteral("grep")}}, QStringLiteral("a")));
    LlamaAgentBackend::mergeToolCallDelta(acc,
        tcDelta(1, QJsonObject{{QStringLiteral("name"), QStringLiteral("list_dir")}}, QStringLiteral("b")));
    LlamaAgentBackend::mergeToolCallDelta(acc,
        tcDelta(0, QJsonObject{{QStringLiteral("arguments"), QStringLiteral("{\"q\":1}")}}));
    LlamaAgentBackend::mergeToolCallDelta(acc,
        tcDelta(1, QJsonObject{{QStringLiteral("arguments"), QStringLiteral("{\"p\":2}")}}));

    QCOMPARE(acc.size(), 2);
    QCOMPARE(acc.value(0).value(QStringLiteral("name")).toString(), QStringLiteral("grep"));
    QCOMPARE(acc.value(0).value(QStringLiteral("arguments")).toString(), QStringLiteral("{\"q\":1}"));
    QCOMPARE(acc.value(1).value(QStringLiteral("name")).toString(), QStringLiteral("list_dir"));
    QCOMPARE(acc.value(1).value(QStringLiteral("arguments")).toString(), QStringLiteral("{\"p\":2}"));
}

// visibleAnswer: con Pensar OFF quita <think>…</think>, PERO si el modelo metió
// toda la respuesta dentro de <think> (Qwen con thinking off) rescata el interior
// en vez de devolver vacío — esa era la causa de los saludos sin respuesta.
void AgentWireTests::visibleAnswer_stripsThinkButSalvagesWhenEmpty()
{
    using B = LlamaAgentBackend;
    // Caso normal: think + respuesta afuera → queda sólo la respuesta.
    QCOMPARE(B::visibleAnswer(QStringLiteral("<think>razono</think>Hola!"), false),
             QStringLiteral("Hola!"));
    // Caso bug: TODO dentro de think, nada afuera → no devolver vacío, rescatar.
    QCOMPARE(B::visibleAnswer(QStringLiteral("<think>Hola, ¿qué tal?</think>"), false),
             QStringLiteral("Hola, ¿qué tal?"));
    // Think sin cerrar (cortado por n_predict) y sin texto afuera → rescatar interior.
    QCOMPARE(B::visibleAnswer(QStringLiteral("<think>respuesta cortada"), false),
             QStringLiteral("respuesta cortada"));
    // Pensar ON: deja el content tal cual (la UI muestra el <think>).
    QCOMPARE(B::visibleAnswer(QStringLiteral("<think>r</think>R"), true),
             QStringLiteral("<think>r</think>R"));
    // Texto sin think: intacto.
    QCOMPARE(B::visibleAnswer(QStringLiteral("respuesta directa"), false),
             QStringLiteral("respuesta directa"));
    // Realmente vacío (sólo etiquetas) → vacío, no inventa.
    QVERIFY(B::visibleAnswer(QStringLiteral("<think></think>"), false).isEmpty());
}

void AgentWireTests::buildObservationMessage_wrapsImagesAsUserMultimodal()
{
    // Una captura (desktop_observe) → mensaje role=user con content multimodal:
    // [texto, image_url]. El image_url lleva la data-URI tal cual.
    const QString uriA = QStringLiteral("data:image/jpeg;base64,AAAA");
    const QString uriB = QStringLiteral("data:image/png;base64,BBBB");
    const QJsonObject m = LlamaAgentBackend::buildObservationMessage({uriA, QString(), uriB});

    QCOMPARE(m.value(QStringLiteral("role")).toString(), QStringLiteral("user"));
    const QJsonArray content = m.value(QStringLiteral("content")).toArray();
    // 1 bloque de texto + 2 imágenes (el "" se descarta).
    QCOMPARE(content.size(), 3);
    QCOMPARE(content.at(0).toObject().value(QStringLiteral("type")).toString(),
             QStringLiteral("text"));
    QVERIFY(!content.at(0).toObject().value(QStringLiteral("text")).toString().isEmpty());

    QStringList urls;
    for (int i = 1; i < content.size(); ++i) {
        const QJsonObject part = content.at(i).toObject();
        QCOMPARE(part.value(QStringLiteral("type")).toString(), QStringLiteral("image_url"));
        urls << part.value(QStringLiteral("image_url")).toObject()
                    .value(QStringLiteral("url")).toString();
    }
    QCOMPARE(urls, QStringList({uriA, uriB}));   // orden preservado, "" omitido
}

void AgentWireTests::buildObservationMessage_emptyWhenNoImages()
{
    // Sin imágenes válidas → objeto vacío (el loop no inyecta nada).
    QVERIFY(LlamaAgentBackend::buildObservationMessage({}).isEmpty());
    QVERIFY(LlamaAgentBackend::buildObservationMessage({QString(), QString()}).isEmpty());
}

void AgentWireTests::developmentDisciplineSection_coversRegressionGuards()
{
    // Regresión: la guía anti-regresión debe seguir presente en el system prompt.
    // Si alguien la borra/vacía, este test cae. Verificamos los 4 pilares:
    // blast radius, cambio mínimo, preservar contratos, verificar/tests.
    const QString g = LlamaAgentBackend::developmentDisciplineSection();
    QVERIFY(!g.trimmed().isEmpty());

    // Pilar 1: conocer quién usa el código antes de tocarlo (blast radius).
    QVERIFY(g.contains(QStringLiteral("Blast radius"), Qt::CaseInsensitive));
    QVERIFY(g.contains(QStringLiteral("grep")));
    // Pilar 2: cambio mínimo, no tocar lo no relacionado.
    QVERIFY(g.contains(QStringLiteral("mínimo"), Qt::CaseInsensitive));
    // Pilar 3: preservar comportamiento/contratos existentes.
    QVERIFY(g.contains(QStringLiteral("comportamiento"), Qt::CaseInsensitive)
            || g.contains(QStringLiteral("contrato"), Qt::CaseInsensitive));
    // Pilar 4: correr tests/compilar al terminar.
    QVERIFY(g.contains(QStringLiteral("test"), Qt::CaseInsensitive));

    // Cableado: buildSystemPrompt() la incluye. No es accesible directo (privada),
    // pero la sección es lo que se concatena tal cual → testear la sección cubre
    // el contenido shippeado. El cableado se verifica por inspección de start().
    QVERIFY(g.endsWith(QStringLiteral("\n\n")));   // separador para no pegarse al ESTILO
}

void AgentWireTests::testSafetyNetSection_coversRunnerDetectionAndQuality()
{
    // Regresión: la guía de "red de tests" debe seguir en el system prompt y
    // cubrir sus pilares. Si se borra/vacía o pierde un pilar, este test cae.
    const QString g = LlamaAgentBackend::testSafetyNetSection();
    QVERIFY(!g.trimmed().isEmpty());

    // Pilar 1: detectar el runner que ya usa el proyecto (varios ecosistemas).
    QVERIFY(g.contains(QStringLiteral("runner"), Qt::CaseInsensitive));
    QVERIFY(g.contains(QStringLiteral("package.json")));
    QVERIFY(g.contains(QStringLiteral("ctest")));
    QVERIFY(g.contains(QStringLiteral("pytest")));
    // Pilar 2: test caja-negra, NO asserts triviales (el reclamo del thread).
    QVERIFY(g.contains(QStringLiteral("caja-negra"), Qt::CaseInsensitive)
            || g.contains(QStringLiteral("caja negra"), Qt::CaseInsensitive));
    QVERIFY(g.contains(QStringLiteral("trivial"), Qt::CaseInsensitive));
    // Pilar 3: registrar el test para que el runner lo levante solo.
    QVERIFY(g.contains(QStringLiteral("Registr"), Qt::CaseInsensitive));
    // Pilar 4: correr el suite y no entregar en rojo.
    QVERIFY(g.contains(QStringLiteral("suite"), Qt::CaseInsensitive));
    QVERIFY(g.contains(QStringLiteral("rojo"), Qt::CaseInsensitive));
    // Pilar 5: fallback cuando el proyecto no tiene tests (no meter framework pesado).
    QVERIFY(g.contains(QStringLiteral("smoke"), Qt::CaseInsensitive));

    QVERIFY(g.endsWith(QStringLiteral("\n\n")));   // separa de la sección siguiente
}

void AgentWireTests::projectContextSection_coversIntentAndMemory()
{
    // Regresión: la guía de contexto de proyecto debe seguir en el prompt y cubrir
    // sus pilares (entender el porqué, co-cambios por git, dejar memoria durable).
    const QString g = LlamaAgentBackend::projectContextSection();
    QVERIFY(!g.trimmed().isEmpty());

    // Pilar 1: entender el porqué via git history antes de tocar; no romper workarounds.
    QVERIFY(g.contains(QStringLiteral("git blame"))
            || g.contains(QStringLiteral("git log")));
    QVERIFY(g.contains(QStringLiteral("workaround"), Qt::CaseInsensitive));
    // Pilar 2: co-cambios / acoplamiento sin import visible.
    QVERIFY(g.contains(QStringLiteral("Co-cambios"), Qt::CaseInsensitive)
            || g.contains(QStringLiteral("acopl"), Qt::CaseInsensitive));
    // Pilar 3: dejar decisiones durables en el archivo de memoria del proyecto.
    QVERIFY(g.contains(QStringLiteral(".llamacode/memory.md")));
    QVERIFY(g.contains(QStringLiteral("durable"), Qt::CaseInsensitive));
    // El archivo citado debe coincidir con el real que carga buildSystemPrompt.
    QVERIFY(g.contains(LlamaAgentBackend::memoryFilePath(QStringLiteral("x"))
                       .section(QLatin1Char('/'), -2)));   // ".llamacode/memory.md"

    QVERIFY(g.endsWith(QStringLiteral("\n\n")));
}

QTEST_MAIN(AgentWireTests)
#include "test_agent_wire.moc"
