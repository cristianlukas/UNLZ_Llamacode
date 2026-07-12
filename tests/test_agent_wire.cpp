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
    void forceTextToolsSkipsNativeToolAttempt();
    void restartRepublishesPersistedMessages();
    void taskSessionIsEphemeralAndRestoresPrevious();
    void mergeToolCallDelta_assemblesAcrossChunks();
    void mergeToolCallDelta_parallelCallsByIndex();
    void visibleAnswer_stripsThinkButSalvagesWhenEmpty();
    void buildWarmupPayload_prefillsWithoutGenerating();
    void trimStaleImages_keepsOnlyLatestCapture();
    void buildObservationMessage_wrapsImagesAsUserMultimodal();
    void buildObservationMessage_emptyWhenNoImages();
    void developmentDisciplineSection_coversRegressionGuards();
    void testSafetyNetSection_coversRunnerDetectionAndQuality();
    void projectContextSection_coversIntentAndMemory();
    void desktopPlaybookSection_coversKeyboardPathAndTextVerify();
    void desktopConfirmKeyBlockedAfterTypeEquals();
    void parsesNativeToolCallLeakFallback();
    void textToolsModeDoesNotDoubleReserveToolBudget();
    void compactionStallCounterTracksProgress();
    void textToolPayloadCapsGenerationAndStopsAtToolCall();
    void adaptiveSubagentLimit_respectsProfileContextAndVram();
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

void AgentWireTests::parsesNativeToolCallLeakFallback()
{
    // Regresión del bug "sumar 2+2": modelos como Gemma filtran su formato NATIVO
    // de tool-call como texto (<|tool_call>call:NAME{args}<tool_call|>). El nombre
    // va en call:NAME y los args en un objeto JSON aparte (puede ser {}). El parser
    // debe reconocerlo; antes veía el {} vacío, no encontraba "name" y la tool
    // nunca se ejecutaba (la Task terminaba "ok" sin operar la app).

    // Args vacíos: desktop_windows sin parámetros.
    {
        const QString content = QStringLiteral("<|tool_call>call:desktop_windows{}<tool_call|>");
        const QJsonObject call = LlamaAgentBackend::textToolCallFromContent(content);
        QVERIFY(!call.isEmpty());
        const QJsonObject fn = call.value(QStringLiteral("function")).toObject();
        QCOMPARE(fn.value(QStringLiteral("name")).toString(), QStringLiteral("desktop_windows"));
    }

    // Con args: desktop_type con texto.
    {
        const QString content = QStringLiteral(
            "<|tool_call>call:desktop_type{\"text\":\"2+2\"}<tool_call|>");
        const QJsonObject call = LlamaAgentBackend::textToolCallFromContent(content);
        QVERIFY(!call.isEmpty());
        const QJsonObject fn = call.value(QStringLiteral("function")).toObject();
        QCOMPARE(fn.value(QStringLiteral("name")).toString(), QStringLiteral("desktop_type"));
        const QJsonObject args = QJsonDocument::fromJson(
            fn.value(QStringLiteral("arguments")).toString().toUtf8()).object();
        QCOMPARE(args.value(QStringLiteral("text")).toString(), QStringLiteral("2+2"));
    }

    // Prosa con "call:" pero sin el token nativo → NO debe disparar tool call.
    {
        const QString content = QStringLiteral("Ya hice la call: desktop_windows manualmente.");
        QVERIFY(LlamaAgentBackend::textToolCallFromContent(content).isEmpty());
    }
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

// Server que NUNCA acepta tools nativas: si llega un body con "tools" es un bug
// (con forceTextTools el backend no debe intentar el path nativo). Responde el
// protocolo textual directamente.
class FakeTextOnlyServer : public QTcpServer
{
public:
    int nativeRequests = 0;
    int textRequests = 0;

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
                ++nativeRequests;
                writeRaw(sock, QByteArrayLiteral(
                    "HTTP/1.1 400 Bad Request\r\nContent-Length: 4\r\nConnection: close\r\n\r\nnope"));
                return;
            }
            ++textRequests;
            if (textRequests == 1)
                writeSse(sock, QStringLiteral(
                    "TOOL_CALL {\"name\":\"read_file\",\"arguments\":{\"path\":\"marker.txt\"}}"));
            else
                writeSse(sock, QStringLiteral("FINAL: read_file ejecutado correctamente"));
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

void AgentWireTests::forceTextToolsSkipsNativeToolAttempt()
{
    QTemporaryDir cwd;
    QVERIFY(cwd.isValid());
    QFile marker(cwd.path() + QStringLiteral("/marker.txt"));
    QVERIFY(marker.open(QIODevice::WriteOnly));
    marker.write("ok");
    marker.close();

    FakeTextOnlyServer server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));

    AgentContext ctx;
    ctx.adapter = QStringLiteral("llamaagent");
    ctx.cwd = cwd.path();
    ctx.serverBaseUrl = QStringLiteral("http://127.0.0.1:%1").arg(server.serverPort());
    ctx.modelId = QStringLiteral("gemma-sin-tools");
    ctx.ctxOverride = 4096;

    LlamaAgentBackend backend;
    backend.setEphemeralSessions(true);
    backend.setForceTextTools(true);   // modelo "unsupported" → texto desde el primer request
    backend.start(ctx);
    QSignalSpy finished(&backend, &LlamaAgentBackend::turnFinished);
    backend.sendMessage(QStringLiteral("Leé marker.txt usando tools."));

    QTRY_VERIFY_WITH_TIMEOUT(finished.count() == 1, 10000);
    QCOMPARE(server.nativeRequests, 0);   // nunca intentó el payload de tools nativas
    QVERIFY(server.textRequests >= 2);

    bool sawTool = false, sawFinal = false;
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

void AgentWireTests::buildWarmupPayload_prefillsWithoutGenerating()
{
    const QJsonArray msgs{
        msg(QStringLiteral("system"), QStringLiteral("sys prompt")),
        msg(QStringLiteral("user"), QStringLiteral("turno previo"))
    };
    const QJsonArray tools{QJsonObject{{QStringLiteral("type"), QStringLiteral("function")}}};

    const QJsonObject p = LlamaAgentBackend::buildWarmupPayload(
        msgs, tools, QStringLiteral("local"), 0.7, true);

    // Prefijo idéntico al turno real: messages+tools+kwargs de template.
    QCOMPARE(p.value(QStringLiteral("messages")).toArray(), msgs);
    QCOMPARE(p.value(QStringLiteral("tools")).toArray(), tools);
    QCOMPARE(p.value(QStringLiteral("temperature")).toDouble(), 0.7);
    QCOMPARE(p.value(QStringLiteral("chat_template_kwargs")).toObject()
                 .value(QStringLiteral("enable_thinking")).toBool(), true);
    // Pero SIN generar: 1 token, sin stream, y con cache_prompt para el KV.
    QCOMPARE(p.value(QStringLiteral("max_tokens")).toInt(), 1);
    QCOMPARE(p.value(QStringLiteral("stream")).toBool(), false);
    QCOMPARE(p.value(QStringLiteral("cache_prompt")).toBool(), true);

    // Temperatura negativa (no seteada) → no se manda; thinking off → budget 0.
    const QJsonObject p2 = LlamaAgentBackend::buildWarmupPayload(
        msgs, tools, QStringLiteral("local"), -1.0, false);
    QVERIFY(!p2.contains(QStringLiteral("temperature")));
    QCOMPARE(p2.value(QStringLiteral("reasoning_budget")).toInt(), 0);
}

void AgentWireTests::trimStaleImages_keepsOnlyLatestCapture()
{
    auto imgMsg = [](const QString &txt, const QString &uri) {
        return QJsonObject{
            {QStringLiteral("role"), QStringLiteral("user")},
            {QStringLiteral("content"), QJsonArray{
                QJsonObject{{QStringLiteral("type"), QStringLiteral("text")},
                            {QStringLiteral("text"), txt}},
                QJsonObject{{QStringLiteral("type"), QStringLiteral("image_url")},
                            {QStringLiteral("image_url"),
                             QJsonObject{{QStringLiteral("url"), uri}}}}}}};
    };
    const QJsonArray in{
        msg(QStringLiteral("system"), QStringLiteral("sys")),
        imgMsg(QStringLiteral("captura 1"), QStringLiteral("data:1")),
        msg(QStringLiteral("assistant"), QStringLiteral("veo la pantalla")),
        imgMsg(QStringLiteral("captura 2"), QStringLiteral("data:2")),
    };

    const QJsonArray out = LlamaAgentBackend::trimStaleImages(in, 1);
    QCOMPARE(out.size(), 4);
    // Captura vieja: image_url reemplazada por placeholder de texto.
    const QJsonArray parts1 = out[1].toObject().value(QStringLiteral("content")).toArray();
    for (const QJsonValue &p : parts1)
        QVERIFY(p.toObject().value(QStringLiteral("type")).toString() != QLatin1String("image_url"));
    QVERIFY(parts1.last().toObject().value(QStringLiteral("text")).toString()
                .contains(QStringLiteral("omitida")));
    // El texto original del mensaje se conserva.
    QCOMPARE(parts1.first().toObject().value(QStringLiteral("text")).toString(),
             QStringLiteral("captura 1"));
    // Última captura: intacta.
    const QJsonArray parts3 = out[3].toObject().value(QStringLiteral("content")).toArray();
    QCOMPARE(parts3.last().toObject().value(QStringLiteral("type")).toString(),
             QStringLiteral("image_url"));
    // Mensajes sin imagen: intactos (content string no se toca).
    QCOMPARE(out[2].toObject().value(QStringLiteral("content")).toString(),
             QStringLiteral("veo la pantalla"));

    // keepLast=0: ninguna imagen sobrevive (pre-append de una captura nueva).
    const QJsonArray none = LlamaAgentBackend::trimStaleImages(in, 0);
    const QJsonArray p3 = none[3].toObject().value(QStringLiteral("content")).toArray();
    for (const QJsonValue &p : p3)
        QVERIFY(p.toObject().value(QStringLiteral("type")).toString() != QLatin1String("image_url"));
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

void AgentWireTests::desktopPlaybookSection_coversKeyboardPathAndTextVerify()
{
    // Regresión: el playbook de escritorio debe guiar el camino rápido (teclado)
    // y la verificación por TEXTO sin visión, para no flailar con capturas ciegas
    // (bug: "sumar 2+2 en la calculadora" tardaba y nunca completaba).
    const QString novis = LlamaAgentBackend::desktopPlaybookSection(false);
    QVERIFY(!novis.trimmed().isEmpty());

    // Pilar 1: abrir con desktop_launch, no run_shell.
    QVERIFY(novis.contains(QStringLiteral("desktop_launch")));
    // Pilar 2: camino rápido por teclado generalizable para calculadora.
    QVERIFY(novis.contains(QStringLiteral("desktop_type")));
    QVERIFY(novis.contains(QStringLiteral("<expresión>=")));
    QVERIFY(novis.contains(QStringLiteral("desktop_key ESC")));
    // Pilar 3: verificar por texto vía desktop_controls (UIA), no por captura.
    QVERIFY(novis.contains(QStringLiteral("desktop_controls")));
    // Pilar 4: sin visión, NO usar desktop_observe (evita el loop ciego).
    QVERIFY(novis.contains(QStringLiteral("desktop_observe")));
    QVERIFY(novis.contains(QStringLiteral("loop"), Qt::CaseInsensitive));
    QVERIFY(novis.endsWith(QStringLiteral("\n\n")));

    // Con visión, sí se ofrece desktop_observe como recurso extra.
    const QString vis = LlamaAgentBackend::desktopPlaybookSection(true);
    QVERIFY(vis.contains(QStringLiteral("mmproj")));
    QVERIFY(vis.contains(QStringLiteral("desktop_observe")));
    // La variante sin visión debe advertir explícitamente que NO puede ver.
    QVERIFY(novis.contains(QStringLiteral("NO")) );
    QVERIFY(novis != vis);
}

void AgentWireTests::desktopConfirmKeyBlockedAfterTypeEquals()
{
    QVERIFY(LlamaAgentBackend::redundantDesktopConfirmKey(
        QStringLiteral("desktop_type"), QStringLiteral("2+2="), QStringLiteral("ENTER")));
    QVERIFY(LlamaAgentBackend::redundantDesktopConfirmKey(
        QStringLiteral("desktop_type"), QStringLiteral("2+2="), QStringLiteral("=")));
    QVERIFY(!LlamaAgentBackend::redundantDesktopConfirmKey(
        QStringLiteral("desktop_type"), QStringLiteral("2+2"), QStringLiteral("ENTER")));
    QVERIFY(!LlamaAgentBackend::redundantDesktopConfirmKey(
        QStringLiteral("desktop_focus"), QStringLiteral("2+2="), QStringLiteral("ENTER")));
    QVERIFY(!LlamaAgentBackend::redundantDesktopConfirmKey(
        QStringLiteral("desktop_type"), QStringLiteral("hola="), QStringLiteral("TAB")));
}

void AgentWireTests::textToolsModeDoesNotDoubleReserveToolBudget()
{
    // Regresión del bug "sumar 2+2": con n_ctx chico (8192) y en modo text-tools
    // (fallback headless), la compactación disparaba en CADA turno porque el budget
    // reservaba el esquema OpenAI completo de tools (~miles de tok) que en ese modo
    // NO se manda como payload (va embebido por nombre en el system prompt, ya
    // contado). Resultado: se resumía el historial cada 1-2 tools y la Task se
    // rompía tras 4-5 acciones. Con el fix, el mismo historial NO gatilla
    // compactación en modo text-tools, pero SÍ en modo nativo (donde el esquema
    // realmente ocupa contexto).
    auto buildHistory = []() {
        QJsonArray msgs;
        msgs.append(QJsonObject{{"role", "system"}, {"content", QString(400, 'x')}});
        msgs.append(QJsonObject{{"role", "user"}, {"content", QString(400, 'y')}});
        // ~3000 tokens de cuerpo (≈12k chars) repartidos en varios turnos.
        for (int i = 0; i < 6; ++i) {
            msgs.append(QJsonObject{{"role", "assistant"}, {"content", QString(1000, 'a')}});
            msgs.append(QJsonObject{{"role", "user"}, {"content", QString(1000, 'b')}});
        }
        return msgs;
    };

    int head = 0, keepFrom = 0;

    // Modo nativo: el esquema de tools SÍ reserva contexto → budget chico → compacta.
    LlamaAgentBackend nativeBe;
    nativeBe.setCtxLimitForTest(8192);
    nativeBe.setApiMessagesForTest(buildHistory());
    QVERIFY2(nativeBe.planCompactionForTest(head, keepFrom),
             "modo nativo: con el esquema de tools reservado, este historial debe compactar");

    // Modo text-tools: no se reserva el esquema → budget amplio → NO compacta.
    LlamaAgentBackend textBe;
    textBe.setForceTextTools(true);
    textBe.setCtxLimitForTest(8192);
    textBe.setApiMessagesForTest(buildHistory());
    QVERIFY2(!textBe.planCompactionForTest(head, keepFrom),
             "modo text-tools: el mismo historial NO debe disparar compactación");
}

void AgentWireTests::compactionStallCounterTracksProgress()
{
    // Regresión del loop infinito de compactación (12GB, n_ctx=16384): cuando el
    // tramo compactable es chico y lo pesado es el head protegido (system+objetivo),
    // el resumen no baja tokens (2678→2678) y runCompletion recompactaba sin fin.
    // El contador de estancamiento sube cuando un pase NO reduce y se resetea
    // cuando sí; runCompletion corta al llegar a 2 (no lo ejercitamos acá porque
    // requiere red, pero sí la contabilidad que lo gobierna).
    auto history = []() {
        QJsonArray m;
        m.append(QJsonObject{{"role", "system"}, {"content", QString(400, 'x')}});
        m.append(QJsonObject{{"role", "user"},   {"content", QString(400, 'y')}});
        m.append(QJsonObject{{"role", "assistant"}, {"content", QString(1000, 'a')}});
        m.append(QJsonObject{{"role", "user"},      {"content", QString(1000, 'b')}});
        return m;
    };
    LlamaAgentBackend be;
    be.setCtxLimitForTest(8192);

    // Resumen tan grande como lo removido → sin reducción → stall sube.
    be.setApiMessagesForTest(history());
    be.applyCompactionForTest(2, 4, QString(2000, 'z'));
    QCOMPARE(be.compactStallForTest(), 1);
    be.setApiMessagesForTest(history());
    be.applyCompactionForTest(2, 4, QString(2000, 'z'));
    QCOMPARE(be.compactStallForTest(), 2);   // 2 → runCompletion deja de compactar

    // Resumen chico → reduce de verdad → resetea el contador.
    be.setApiMessagesForTest(history());
    be.applyCompactionForTest(2, 4, QStringLiteral("ok"));
    QCOMPARE(be.compactStallForTest(), 0);
}

void AgentWireTests::textToolPayloadCapsGenerationAndStopsAtToolCall()
{
    // Regresión del bug "sumar 2+2": tras arreglar parser y compactación, la Task
    // avanzaba hasta desktop_focus pero el turno siguiente colgaba ~5 min. El
    // modelo (Gemma) escupía su formato nativo <|tool_call>...<tool_call|> y SEGUÍA
    // generando hasta max_tokens (ctx/4 = 2048 → ~5 min de decode local). El payload
    // text-tools debe (a) capar max_tokens y (b) traer stop en los marcadores de
    // cierre para cortar apenas se emite el tool-call.
    LlamaAgentBackend be;
    QJsonObject nativePayload{
        {QStringLiteral("model"), QStringLiteral("local")},
        {QStringLiteral("messages"), QJsonArray{
            QJsonObject{{QStringLiteral("role"), QStringLiteral("system")},
                        {QStringLiteral("content"), QStringLiteral("sys")}}}},
        {QStringLiteral("max_tokens"), 2048}};

    const QJsonObject p = be.buildTextToolPayloadForTest(nativePayload);

    // (a) max_tokens capado (no los 2048 originales que causaban el ramble largo).
    QVERIFY(p.value(QStringLiteral("max_tokens")).toInt() <= 1536);
    QVERIFY(p.value(QStringLiteral("max_tokens")).toInt() >= 256);

    // (b) stop cubre el marcador de cierre nativo que vimos en el log.
    const QJsonArray stop = p.value(QStringLiteral("stop")).toArray();
    QVERIFY(!stop.isEmpty());
    bool hasClose = false;
    for (const QJsonValue &v : stop)
        if (v.toString() == QStringLiteral("<tool_call|>")) hasClose = true;
    QVERIFY2(hasClose, "stop debe incluir el cierre <tool_call|>");

    // (c) el protocolo instruye NO razonar/usar <think> (evita el turno vacío que
    // rompía la Task 2+2 tras desktop_focus).
    const QString sysContent = p.value(QStringLiteral("messages")).toArray()
                                   .first().toObject().value(QStringLiteral("content")).toString();
    QVERIFY(sysContent.contains(QStringLiteral("<think>")));
    QVERIFY(sysContent.contains(QStringLiteral("Nunca respondas vacío")));
}

void AgentWireTests::adaptiveSubagentLimit_respectsProfileContextAndVram()
{
    using B = LlamaAgentBackend;
    QCOMPARE(B::adaptiveSubagentLimit(1, 8192, 24576), 1);
    QCOMPARE(B::adaptiveSubagentLimit(4, 8192, 24576), 4);
    QCOMPARE(B::adaptiveSubagentLimit(8, 8192, 49152), 5); // hard safety cap
    QCOMPARE(B::adaptiveSubagentLimit(4, 131072, 49152), 1);
    QCOMPARE(B::adaptiveSubagentLimit(4, 65536, 49152), 2);
    QCOMPARE(B::adaptiveSubagentLimit(4, 32768, 49152), 3);
    QCOMPARE(B::adaptiveSubagentLimit(4, 8192, 6144), 1);
    QCOMPARE(B::adaptiveSubagentLimit(4, 8192, 10240), 2);
    QCOMPARE(B::adaptiveSubagentLimit(4, 8192, 24576, 300), 1);
    QCOMPARE(B::adaptiveSubagentLimit(4, 8192, 24576, 700), 2);
    // Sin telemetría no inventa una restricción: manda el perfil configurado.
    QCOMPARE(B::adaptiveSubagentLimit(3, 8192, 0), 3);
}

QTEST_MAIN(AgentWireTests)
#include "test_agent_wire.moc"
