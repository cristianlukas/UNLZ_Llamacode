#include <QtTest>

#include "core/google/GoogleWorkspaceAuth.h"

#include <QHostAddress>
#include <QElapsedTimer>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTcpSocket>
#include <QUrlQuery>

using namespace GoogleWorkspaceSecurity;

class TokenEndpointStub : public QTcpServer
{
    Q_OBJECT
public:
    explicit TokenEndpointStub(QObject *parent = nullptr) : QTcpServer(parent)
    {
        connect(this, &QTcpServer::newConnection, this, [this]() {
            while (hasPendingConnections()) {
                QTcpSocket *socket = nextPendingConnection();
                connect(socket, &QTcpSocket::readyRead, this, [this, socket]() {
                    QByteArray &buffer = m_buffers[socket];
                    buffer += socket->readAll();
                    const int headerEnd = buffer.indexOf("\r\n\r\n");
                    if (headerEnd < 0) return;
                    int contentLength = 0;
                    for (const QByteArray &line : buffer.left(headerEnd).split('\n')) {
                        const int colon = line.indexOf(':');
                        if (colon > 0 && line.left(colon).trimmed().compare("Content-Length", Qt::CaseInsensitive) == 0)
                            contentLength = line.mid(colon + 1).trimmed().toInt();
                    }
                    if (buffer.size() < headerEnd + 4 + contentLength) return;
                    m_lastRequest = buffer;
                    const QByteArray body = m_response;
                    const QByteArray reason = m_status == 200 ? QByteArrayLiteral("OK")
                        : m_status == 503 ? QByteArrayLiteral("Service Unavailable")
                                          : QByteArrayLiteral("Bad Request");
                    const QByteArray response = QByteArrayLiteral("HTTP/1.1 ")
                        + QByteArray::number(m_status) + ' ' + reason
                        + QByteArrayLiteral("\r\nContent-Type: application/json\r\n")
                        + QByteArrayLiteral("Connection: close\r\nContent-Length: ")
                        + QByteArray::number(body.size()) + QByteArrayLiteral("\r\n\r\n") + body;
                    socket->write(response);
                    socket->disconnectFromHost();
                    emit requestReceived();
                });
                connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
            }
        });
    }

    void setResponse(const QByteArray &response) { m_response = response; }
    void setStatus(int status) { m_status = status; }
    QByteArray lastRequest() const { return m_lastRequest; }

signals:
    void requestReceived();

private:
    QHash<QTcpSocket *, QByteArray> m_buffers;
    QByteArray m_response;
    int m_status = 200;
    QByteArray m_lastRequest;
};

class GoogleWorkspaceAuthTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void authorizationCodeUsesPkceAndNoClientSecret();
    void draftScopeCanBeRequestedIncrementally();
    void wrongStateIsRejectedAndCanRetry();
    void refreshKeepsExistingRefreshToken();
    void revokeUsesFormAndReportsServerFailure();

private:
    static bool deliverCallback(const QUrl &redirect, const QString &state,
                                const QString &code);
    static QByteArray tokenJson(const QString &scopes, const QString &refresh = QString());
};

void GoogleWorkspaceAuthTests::initTestCase()
{
    QStandardPaths::setTestModeEnabled(true);
    qRegisterMetaType<TokenSet>();
}

QByteArray GoogleWorkspaceAuthTests::tokenJson(const QString &scopes, const QString &refresh)
{
    QJsonObject json{{QStringLiteral("access_token"), QStringLiteral("access-test-123")},
                     {QStringLiteral("token_type"), QStringLiteral("Bearer")},
                     {QStringLiteral("expires_in"), 3600}};
    if (!scopes.isEmpty()) json.insert(QStringLiteral("scope"), scopes);
    if (!refresh.isEmpty()) json.insert(QStringLiteral("refresh_token"), refresh);
    return QJsonDocument(json).toJson(QJsonDocument::Compact);
}

bool GoogleWorkspaceAuthTests::deliverCallback(const QUrl &redirect,
                                              const QString &state,
                                              const QString &code)
{
    QTcpSocket browser;
    browser.connectToHost(QHostAddress(QStringLiteral("127.0.0.1")),
                          static_cast<quint16>(redirect.port()));
    QElapsedTimer timer;
    timer.start();
    while (browser.state() != QAbstractSocket::ConnectedState && timer.elapsed() < 2000)
        QTest::qWait(10); // lets the QTcpServer in the same event loop accept the callback
    if (browser.state() != QAbstractSocket::ConnectedState) return false;
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("state"), state);
    if (!code.isEmpty()) query.addQueryItem(QStringLiteral("code"), code);
    const QByteArray request = QByteArrayLiteral("GET ") + redirect.path().toUtf8()
        + '?' + query.toString(QUrl::FullyEncoded).toUtf8()
        + QByteArrayLiteral(" HTTP/1.1\r\nHost: ")
        + redirect.authority(QUrl::FullyEncoded).toLatin1()
        + QByteArrayLiteral("\r\nConnection: close\r\n\r\n");
    if (browser.write(request) != request.size()) return false;
    browser.flush();
    timer.restart();
    while (browser.bytesAvailable() == 0 && timer.elapsed() < 2000)
        QTest::qWait(10);
    if (browser.bytesAvailable() == 0) return false;
    const QByteArray response = browser.readAll();
    if (!response.startsWith(QByteArrayLiteral("HTTP/1.1 200")))
        qWarning().noquote() << "OAuth test callback response:" << response;
    return response.startsWith(QByteArrayLiteral("HTTP/1.1 200"));
}

void GoogleWorkspaceAuthTests::authorizationCodeUsesPkceAndNoClientSecret()
{
    const QStringList requestedScopes = scopesFor(
        {Capability::GmailRead, Capability::TasksRead});
    TokenEndpointStub endpoint;
    QVERIFY(endpoint.listen(QHostAddress::LocalHost, 0));
    endpoint.setResponse(tokenJson(requestedScopes.join(QLatin1Char(' ')),
                                   QStringLiteral("refresh-test-456")));

    GoogleWorkspaceAuth auth;
    QVERIFY(auth.setTokenEndpointForTests(QUrl(QStringLiteral("http://127.0.0.1:%1/token")
                                                   .arg(endpoint.serverPort()))));
    QSignalSpy urlSpy(&auth, &GoogleWorkspaceAuth::authorizationUrlReady);
    QSignalSpy tokenSpy(&auth, &GoogleWorkspaceAuth::tokensReady);
    QSignalSpy failureSpy(&auth, &GoogleWorkspaceAuth::operationFailed);
    QVERIFY(auth.start(QStringLiteral("client.apps.googleusercontent.com"),
                       {Capability::GmailRead, Capability::TasksRead}));
    QCOMPARE(urlSpy.size(), 1);

    const QUrl authorizationUrl = urlSpy.constFirst().at(0).toUrl();
    const QUrlQuery authorizationQuery(authorizationUrl);
    const QUrl redirect(authorizationQuery.queryItemValue(QStringLiteral("redirect_uri")));
    const QString state = authorizationQuery.queryItemValue(QStringLiteral("state"));
    QVERIFY(!state.isEmpty());
    QVERIFY(!authorizationQuery.hasQueryItem(QStringLiteral("code_verifier")));
    QCOMPARE(authorizationQuery.queryItemValue(QStringLiteral("code_challenge_method")),
             QStringLiteral("S256"));
    QCOMPARE(authorizationQuery.queryItemValue(QStringLiteral("include_granted_scopes")),
             QStringLiteral("true"));

    QSignalSpy endpointSpy(&endpoint, &TokenEndpointStub::requestReceived);
    QVERIFY(deliverCallback(redirect, state, QStringLiteral("auth-code")));
    QTRY_COMPARE_WITH_TIMEOUT(tokenSpy.size(), 1, 3000);
    QCOMPARE(failureSpy.size(), 0);
    QVERIFY(!auth.busy());
    const TokenSet tokens = qvariant_cast<TokenSet>(tokenSpy.constFirst().at(0));
    QCOMPARE(tokens.accessToken, QStringLiteral("access-test-123"));
    QCOMPARE(tokens.refreshToken, QStringLiteral("refresh-test-456"));
    QCOMPARE(tokens.grantedScopes, requestedScopes);

    QTRY_COMPARE_WITH_TIMEOUT(endpointSpy.size(), 1, 2000);
    const QByteArray request = endpoint.lastRequest();
    QVERIFY(request.startsWith(QByteArrayLiteral("POST /token HTTP/1.1")));
    const int headerEnd = request.indexOf("\r\n\r\n");
    const QUrlQuery form(QString::fromUtf8(request.mid(headerEnd + 4)));
    QCOMPARE(form.queryItemValue(QStringLiteral("client_id")),
             QStringLiteral("client.apps.googleusercontent.com"));
    QCOMPARE(form.queryItemValue(QStringLiteral("code")), QStringLiteral("auth-code"));
    QCOMPARE(form.queryItemValue(QStringLiteral("grant_type")), QStringLiteral("authorization_code"));
    QVERIFY(form.queryItemValue(QStringLiteral("code_verifier")).size() >= 43);
    QVERIFY(!form.hasQueryItem(QStringLiteral("client_secret")));
}

void GoogleWorkspaceAuthTests::draftScopeCanBeRequestedIncrementally()
{
    GoogleWorkspaceAuth auth;
    QSignalSpy urlSpy(&auth, &GoogleWorkspaceAuth::authorizationUrlReady);
    const QList<Capability> requested{Capability::GmailDraft};
    QVERIFY(auth.start(QStringLiteral("client.apps.googleusercontent.com"), requested));
    QCOMPARE(urlSpy.size(), 1);
    const QUrlQuery query(urlSpy.constFirst().at(0).toUrl());
    QCOMPARE(query.queryItemValue(QStringLiteral("scope")), scopesFor(Capability::GmailDraft).join(QLatin1Char(' ')));
    QCOMPARE(query.queryItemValue(QStringLiteral("include_granted_scopes")), QStringLiteral("true"));
    auth.cancel();
}

void GoogleWorkspaceAuthTests::wrongStateIsRejectedAndCanRetry()
{
    TokenEndpointStub endpoint;
    QVERIFY(endpoint.listen(QHostAddress::LocalHost, 0));
    endpoint.setResponse(tokenJson(scopesFor(Capability::GmailRead).join(QLatin1Char(' '))));

    GoogleWorkspaceAuth auth;
    QVERIFY(auth.setTokenEndpointForTests(QUrl(QStringLiteral("http://127.0.0.1:%1/token")
                                                   .arg(endpoint.serverPort()))));
    QSignalSpy urlSpy(&auth, &GoogleWorkspaceAuth::authorizationUrlReady);
    QSignalSpy tokenSpy(&auth, &GoogleWorkspaceAuth::tokensReady);
    QVERIFY(auth.start(QStringLiteral("client.apps.googleusercontent.com"),
                       {Capability::GmailRead}));
    const QUrlQuery query(urlSpy.constFirst().at(0).toUrl());
    const QUrl redirect(query.queryItemValue(QStringLiteral("redirect_uri")));
    const QString state = query.queryItemValue(QStringLiteral("state"));

    QVERIFY(!deliverCallback(redirect, QStringLiteral("wrong-state"), QStringLiteral("bad-code")));
    QVERIFY(auth.busy());
    QVERIFY(deliverCallback(redirect, state, QStringLiteral("good-code")));
    QTRY_COMPARE_WITH_TIMEOUT(tokenSpy.size(), 1, 3000);
}

void GoogleWorkspaceAuthTests::refreshKeepsExistingRefreshToken()
{
    const QStringList scopes = scopesFor(Capability::TasksRead);
    TokenEndpointStub endpoint;
    QVERIFY(endpoint.listen(QHostAddress::LocalHost, 0));
    endpoint.setResponse(tokenJson(QString()));

    GoogleWorkspaceAuth auth;
    QVERIFY(auth.setTokenEndpointForTests(QUrl(QStringLiteral("http://127.0.0.1:%1/token")
                                                   .arg(endpoint.serverPort()))));
    QSignalSpy tokenSpy(&auth, &GoogleWorkspaceAuth::tokensReady);
    QSignalSpy failureSpy(&auth, &GoogleWorkspaceAuth::operationFailed);
    QVERIFY(auth.refresh(QStringLiteral("client.apps.googleusercontent.com"),
                         QStringLiteral("old-refresh-token"), scopes));
    QTRY_COMPARE_WITH_TIMEOUT(tokenSpy.size(), 1, 3000);
    QCOMPARE(failureSpy.size(), 0);
    const TokenSet tokens = qvariant_cast<TokenSet>(tokenSpy.constFirst().at(0));
    QCOMPARE(tokens.refreshToken, QStringLiteral("old-refresh-token"));
    QCOMPARE(tokens.grantedScopes, scopes);
    QVERIFY(endpoint.lastRequest().contains(QByteArrayLiteral("grant_type=refresh_token")));
    QVERIFY(endpoint.lastRequest().contains(QByteArrayLiteral("old-refresh-token")));
}

void GoogleWorkspaceAuthTests::revokeUsesFormAndReportsServerFailure()
{
    TokenEndpointStub endpoint;
    QVERIFY(endpoint.listen(QHostAddress::LocalHost, 0));
    endpoint.setResponse(QByteArrayLiteral("{}"));
    GoogleWorkspaceAuth auth;
    const QUrl revokeUrl(QStringLiteral("http://127.0.0.1:%1/revoke").arg(endpoint.serverPort()));
    QVERIFY(auth.setRevocationEndpointForTests(revokeUrl));
    QSignalSpy revoked(&auth, &GoogleWorkspaceAuth::revocationFinished);
    QSignalSpy failed(&auth, &GoogleWorkspaceAuth::operationFailed);
    QVERIFY(auth.revoke(QStringLiteral("refresh-token-secret")));
    QVERIFY(auth.busy());
    QTRY_COMPARE_WITH_TIMEOUT(revoked.size(), 1, 3000);
    QVERIFY(revoked.constFirst().at(0).toBool());
    QVERIFY(!auth.busy());
    QCOMPARE(failed.size(), 0);
    QVERIFY(endpoint.lastRequest().startsWith(QByteArrayLiteral("POST /revoke ")));
    QVERIFY(endpoint.lastRequest().toLower().contains(
        QByteArrayLiteral("content-type: application/x-www-form-urlencoded")));
    const qsizetype bodyStart = endpoint.lastRequest().indexOf(QByteArrayLiteral("\r\n\r\n")) + 4;
    const QUrlQuery body(QString::fromLatin1(endpoint.lastRequest().mid(bodyStart)));
    QCOMPARE(body.queryItemValue(QStringLiteral("token")), QStringLiteral("refresh-token-secret"));

    TokenEndpointStub errorEndpoint;
    QVERIFY(errorEndpoint.listen(QHostAddress::LocalHost, 0));
    errorEndpoint.setStatus(503);
    GoogleWorkspaceAuth errorAuth;
    QVERIFY(errorAuth.setRevocationEndpointForTests(
        QUrl(QStringLiteral("http://127.0.0.1:%1/revoke").arg(errorEndpoint.serverPort()))));
    QSignalSpy revokeError(&errorAuth, &GoogleWorkspaceAuth::revocationFinished);
    QVERIFY(errorAuth.revoke(QStringLiteral("access-token")));
    QTRY_COMPARE_WITH_TIMEOUT(revokeError.size(), 1, 3000);
    QVERIFY(!revokeError.constFirst().at(0).toBool());
    QVERIFY(!errorAuth.busy());
}

QTEST_MAIN(GoogleWorkspaceAuthTests)
#include "test_google_workspace_auth.moc"
