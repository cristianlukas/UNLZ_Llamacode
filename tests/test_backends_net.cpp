// Integration tests del RawChatBackend (chat directo a llama-server). Cubrimos:
//  - ciclo de sesiones y PERSISTENCIA a disco (sin red),
//  - stream SSE real de /v1/chat/completions contra un stub HTTP local
//    (SseStubServer) → acumulación de deltas y manejo de error HTTP.
// Almacenamiento aislado vía test mode. Server y client viven en el mismo hilo:
// se bombea el event loop con QSignalSpy::wait (NO waitForReadyRead).

#include <QtTest>
#include <QTemporaryDir>
#include <QStandardPaths>
#include <QSignalSpy>
#include <QTcpServer>
#include <QTcpSocket>
#include <QJsonArray>
#include <QJsonObject>
#include "core/agent/RawChatBackend.h"
#include "core/agent/AgentTypes.h"

// Stub HTTP mínimo para /v1/chat/completions. Responde a la primera request con
// un cuerpo fijo (SSE u otro) y un status configurable, luego cierra. Suficiente
// para ejercitar el parser de stream del backend sin un llama-server real.
class SseStubServer : public QObject
{
    Q_OBJECT
public:
    explicit SseStubServer(QObject *parent = nullptr) : QObject(parent) {}

    // Arranca en un puerto libre de loopback. `body` se manda tal cual tras los
    // headers; `status`/`reason` controlan la línea de estado.
    bool start(const QByteArray &body, int status = 200,
               const QByteArray &reason = "OK",
               const QByteArray &contentType = "text/event-stream")
    {
        m_body = body; m_status = status; m_reason = reason; m_ctype = contentType;
        connect(&m_srv, &QTcpServer::newConnection, this, &SseStubServer::onConn);
        return m_srv.listen(QHostAddress::LocalHost);
    }
    QString baseUrl() const
    {
        return QStringLiteral("http://127.0.0.1:%1").arg(m_srv.serverPort());
    }

private slots:
    void onConn()
    {
        QTcpSocket *sock = m_srv.nextPendingConnection();
        connect(sock, &QTcpSocket::readyRead, this, [this, sock]() {
            m_req.append(sock->readAll());
            // Esperar fin de headers de la request antes de responder.
            if (!m_req.contains("\r\n\r\n")) return;
            QByteArray resp;
            resp += "HTTP/1.1 " + QByteArray::number(m_status) + " " + m_reason + "\r\n";
            resp += "Content-Type: " + m_ctype + "\r\n";
            resp += "Content-Length: " + QByteArray::number(m_body.size()) + "\r\n";
            resp += "Connection: close\r\n\r\n";
            resp += m_body;
            sock->write(resp);
            sock->flush();
            sock->disconnectFromHost();
        });
        connect(sock, &QTcpSocket::disconnected, sock, &QObject::deleteLater);
    }

private:
    QTcpServer m_srv;
    QByteArray m_req, m_body, m_reason, m_ctype;
    int m_status = 200;
};

class BackendsNetTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase() { QStandardPaths::setTestModeEnabled(true); }

    void start_createsInitialSession();
    void newSession_addsSession();
    void renameSession_updatesTitle();
    void switchSession_changesCurrent();
    void deleteSession_removes();
    void persistsAcrossRestart();
    void stream_accumulatesAssistantContent();
    void stream_reportsErrorOnHttp500();
    void preamble_emptyWhenThinkingNoPersona();
    void preamble_thinkingOffAddsNoThinkSystem();
    void preamble_designerAddsPersonaFirst();
    void designerPrompt_mentionsArtifactFences();

private:
    AgentContext ctx(const QString &cwd);
    static QString lastAssistant(const RawChatBackend &be);
};

QString BackendsNetTests::lastAssistant(const RawChatBackend &be)
{
    const QVariantList msgs = be.messages();
    for (int i = msgs.size() - 1; i >= 0; --i) {
        const QVariantMap m = msgs.at(i).toMap();
        if (m.value("role").toString() == QLatin1String("assistant"))
            return m.value("content").toString();
    }
    return {};
}

AgentContext BackendsNetTests::ctx(const QString &cwd)
{
    AgentContext c;
    c.adapter = "raw";
    c.cwd = cwd;
    c.serverBaseUrl = "http://127.0.0.1:1";  // nunca se contacta en estos tests
    c.modelId = "test-model";
    return c;
}

void BackendsNetTests::start_createsInitialSession()
{
    QTemporaryDir dir;
    RawChatBackend be;
    be.start(ctx(dir.path()));
    QVERIFY(be.running());
    QVERIFY(!be.currentSessionId().isEmpty());
    QVERIFY(!be.sessions().isEmpty());
}

void BackendsNetTests::newSession_addsSession()
{
    QTemporaryDir dir;
    RawChatBackend be;
    be.start(ctx(dir.path()));
    const int before = be.sessions().size();
    be.newSession();
    QCOMPARE(be.sessions().size(), before + 1);
}

void BackendsNetTests::renameSession_updatesTitle()
{
    QTemporaryDir dir;
    RawChatBackend be;
    be.start(ctx(dir.path()));
    const QString id = be.currentSessionId();
    QSignalSpy spy(&be, &RawChatBackend::sessionsChanged);
    be.renameSession(id, "Mi sesión");
    QCOMPARE(be.currentSessionTitle(), QStringLiteral("Mi sesión"));
    QVERIFY(spy.count() >= 1);
}

void BackendsNetTests::switchSession_changesCurrent()
{
    QTemporaryDir dir;
    RawChatBackend be;
    be.start(ctx(dir.path()));
    const QString first = be.currentSessionId();
    be.newSession();
    const QString second = be.currentSessionId();
    QVERIFY(first != second);
    be.switchSession(first);
    QCOMPARE(be.currentSessionId(), first);
}

void BackendsNetTests::deleteSession_removes()
{
    QTemporaryDir dir;
    RawChatBackend be;
    be.start(ctx(dir.path()));
    be.newSession();
    const QString toDelete = be.currentSessionId();
    const int before = be.sessions().size();
    be.deleteSession(toDelete);
    QCOMPARE(be.sessions().size(), before - 1);
}

void BackendsNetTests::persistsAcrossRestart()
{
    QTemporaryDir dir;
    QString id;
    {
        RawChatBackend be;
        be.start(ctx(dir.path()));
        be.renameSession(be.currentSessionId(), "Persistida");
        id = be.currentSessionId();
        be.stop();
    }
    {
        RawChatBackend be2;
        be2.start(ctx(dir.path()));
        bool found = false;
        for (const QVariant &v : be2.sessions())
            if (v.toMap().value("id").toString() == id) {
                QCOMPARE(v.toMap().value("title").toString(), QStringLiteral("Persistida"));
                found = true;
            }
        QVERIFY(found);
    }
}

void BackendsNetTests::stream_accumulatesAssistantContent()
{
    SseStubServer stub;
    const QByteArray body =
        "data: {\"choices\":[{\"delta\":{\"content\":\"Hola\"}}]}\n"
        "data: {\"choices\":[{\"delta\":{\"content\":\" mundo\"}}]}\n"
        "data: [DONE]\n";
    QVERIFY(stub.start(body));

    QTemporaryDir dir;
    RawChatBackend be;
    AgentContext c = ctx(dir.path());
    c.serverBaseUrl = stub.baseUrl();   // apuntar al stub, no a 127.0.0.1:1
    be.start(c);

    QSignalSpy spy(&be, &RawChatBackend::messagesChanged);
    be.sendMessage(QStringLiteral("hola"));

    // Bombear el event loop hasta que el turno cierre con el texto acumulado.
    for (int i = 0; i < 40 && !lastAssistant(be).contains(QStringLiteral("mundo")); ++i)
        spy.wait(100);

    QCOMPARE(lastAssistant(be), QStringLiteral("Hola mundo"));
}

void BackendsNetTests::stream_reportsErrorOnHttp500()
{
    SseStubServer stub;
    QVERIFY(stub.start(QByteArrayLiteral("internal boom"), 500, "Internal Server Error",
                       "text/plain"));

    QTemporaryDir dir;
    RawChatBackend be;
    AgentContext c = ctx(dir.path());
    c.serverBaseUrl = stub.baseUrl();
    be.start(c);

    QSignalSpy errSpy(&be, &RawChatBackend::errorOccurred);
    be.sendMessage(QStringLiteral("hola"));

    for (int i = 0; i < 40 && errSpy.isEmpty(); ++i)
        errSpy.wait(100);

    QVERIFY(!errSpy.isEmpty());
}

static QString sysContent(const QJsonArray &a, int i)
{ return a.at(i).toObject().value(QStringLiteral("content")).toString(); }

void BackendsNetTests::preamble_emptyWhenThinkingNoPersona()
{
    // thinking ON + sin persona → sin mensajes de sistema.
    const QJsonArray a = RawChatBackend::buildSystemPreamble(true, false);
    QCOMPARE(a.size(), 0);
}

void BackendsNetTests::preamble_thinkingOffAddsNoThinkSystem()
{
    const QJsonArray a = RawChatBackend::buildSystemPreamble(false, false);
    QCOMPARE(a.size(), 1);
    QCOMPARE(a.at(0).toObject().value(QStringLiteral("role")).toString(), QString("system"));
    QVERIFY(sysContent(a, 0).contains(QStringLiteral("<think>")));
}

void BackendsNetTests::preamble_designerAddsPersonaFirst()
{
    // persona + thinking OFF → 2 system; persona va PRIMERO.
    const QJsonArray a = RawChatBackend::buildSystemPreamble(false, true);
    QCOMPARE(a.size(), 2);
    QVERIFY(sysContent(a, 0).contains(QStringLiteral("DISEÑO")));
    QVERIFY(sysContent(a, 1).contains(QStringLiteral("<think>")));
    // persona + thinking ON → solo la persona.
    const QJsonArray b = RawChatBackend::buildSystemPreamble(true, true);
    QCOMPARE(b.size(), 1);
    QVERIFY(sysContent(b, 0).contains(QStringLiteral("DISEÑO")));
}

void BackendsNetTests::designerPrompt_mentionsArtifactFences()
{
    const QString p = RawChatBackend::designerSystemPrompt();
    QVERIFY(p.contains(QStringLiteral("```mermaid")));
    QVERIFY(p.contains(QStringLiteral("```svg")));
}

QTEST_MAIN(BackendsNetTests)
#include "test_backends_net.moc"
