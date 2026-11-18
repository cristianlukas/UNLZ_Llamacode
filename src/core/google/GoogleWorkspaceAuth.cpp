#include "GoogleWorkspaceAuth.h"

#include <QHostAddress>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTimer>
#include <QUrlQuery>

namespace GoogleWorkspaceSecurity {
namespace {

const QUrl kGoogleTokenEndpoint(QStringLiteral("https://oauth2.googleapis.com/token"));
const QUrl kGoogleRevocationEndpoint(QStringLiteral("https://oauth2.googleapis.com/revoke"));

bool isLoopbackHttp(const QUrl &url)
{
    return url.scheme() == QLatin1String("http")
        && (url.host() == QLatin1String("127.0.0.1")
            || url.host() == QLatin1String("localhost")
            || url.host() == QLatin1String("::1"))
        && url.port(-1) > 0;
}

} // namespace

GoogleWorkspaceAuth::GoogleWorkspaceAuth(QObject *parent)
    : QObject(parent),
      m_server(new QTcpServer(this)),
      m_network(new QNetworkAccessManager(this)),
      m_timeout(new QTimer(this)),
      m_tokenEndpoint(kGoogleTokenEndpoint),
      m_revocationEndpoint(kGoogleRevocationEndpoint)
{
    m_timeout->setSingleShot(true);
    connect(m_server, &QTcpServer::newConnection,
            this, &GoogleWorkspaceAuth::acceptConnections);
    connect(m_timeout, &QTimer::timeout, this, [this]() {
        if (m_revoking)
            finishRevocation(false);
        else
            finishWithError(QStringLiteral("El intento OAuth de Google venció por tiempo."));
    });
}

GoogleWorkspaceAuth::~GoogleWorkspaceAuth()
{
    cancel();
}

bool GoogleWorkspaceAuth::start(const QString &clientId,
                                const QList<Capability> &capabilities)
{
    if (m_busy) return false;
    if (clientId.trimmed().isEmpty()) {
        emit operationFailed(QStringLiteral("Configurá el client ID OAuth de Google."));
        return false;
    }
    if (!m_server->listen(QHostAddress::LocalHost, 0)) {
        emit operationFailed(QStringLiteral("No se pudo abrir el callback OAuth loopback."));
        return false;
    }

    m_clientId = clientId.trimmed();
    m_redirectUri = QUrl(QStringLiteral("http://127.0.0.1:%1/oauth2callback")
                             .arg(m_server->serverPort()));
    const AuthorizationRequest request = createAuthorizationRequest(
        m_clientId, m_redirectUri, capabilities);
    if (!request.isValid()) {
        closeListener();
        emit operationFailed(request.error);
        return false;
    }

    m_state = request.state;
    m_codeVerifier = request.codeVerifier;
    m_requestedScopes = scopesFor(capabilities);
    m_refreshToken.clear();
    m_fallbackScopes.clear();
    setBusy(true);
    m_timeout->start(180000);
    emit authorizationUrlReady(request.url);
    return true;
}

bool GoogleWorkspaceAuth::refresh(const QString &clientId, const QString &refreshToken,
                                  const QStringList &previouslyGrantedScopes)
{
    if (m_busy) return false;
    if (clientId.trimmed().isEmpty() || refreshToken.trimmed().isEmpty()) {
        emit operationFailed(QStringLiteral("Falta client ID o refresh token para renovar Google."));
        return false;
    }
    m_clientId = clientId.trimmed();
    m_refreshToken = refreshToken;
    m_fallbackScopes = previouslyGrantedScopes;
    m_requestedScopes.clear();
    QUrlQuery form;
    form.addQueryItem(QStringLiteral("client_id"), m_clientId);
    form.addQueryItem(QStringLiteral("refresh_token"), refreshToken);
    form.addQueryItem(QStringLiteral("grant_type"), QStringLiteral("refresh_token"));
    setBusy(true);
    postTokenRequest(form, refreshToken, previouslyGrantedScopes);
    return true;
}

bool GoogleWorkspaceAuth::revoke(const QString &token)
{
    if (m_busy || token.trimmed().isEmpty()) return false;
    QUrlQuery form;
    form.addQueryItem(QStringLiteral("token"), token);
    QNetworkRequest request(m_revocationEndpoint);
    request.setHeader(QNetworkRequest::ContentTypeHeader,
                      QStringLiteral("application/x-www-form-urlencoded"));
    request.setRawHeader(QByteArrayLiteral("Accept"), QByteArrayLiteral("application/json"));
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute,
                         QNetworkRequest::ManualRedirectPolicy);
    m_revoking = true;
    setBusy(true);
    m_reply = m_network->post(request, form.toString(QUrl::FullyEncoded).toUtf8());
    m_timeout->start(15000);
    connect(m_reply, &QNetworkReply::finished, this, [this]() {
        QNetworkReply *reply = m_reply;
        if (!reply) return;
        m_reply = nullptr;
        m_timeout->stop();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const bool success = reply->error() == QNetworkReply::NoError
            && status >= 200 && status < 300;
        reply->readAll(); // discard provider body; it may contain token diagnostics
        reply->deleteLater();
        finishRevocation(success);
    });
    return true;
}

void GoogleWorkspaceAuth::cancel()
{
    if (!m_busy && !m_server->isListening() && !m_reply) return;
    const bool wasRevoking = m_revoking;
    m_revoking = false;
    m_timeout->stop();
    if (m_reply) {
        QNetworkReply *reply = m_reply;
        m_reply = nullptr;
        reply->abort();
    }
    closeListener();
    m_state.clear();
    m_codeVerifier.clear();
    m_refreshToken.clear();
    m_requestedScopes.clear();
    m_fallbackScopes.clear();
    setBusy(false);
    if (wasRevoking) emit revocationFinished(false);
}

bool GoogleWorkspaceAuth::setTokenEndpointForTests(const QUrl &url)
{
    if (!QStandardPaths::isTestModeEnabled() || !isLoopbackHttp(url)
        || m_busy || m_server->isListening())
        return false;
    m_tokenEndpoint = url;
    return true;
}

bool GoogleWorkspaceAuth::setRevocationEndpointForTests(const QUrl &url)
{
    if (!QStandardPaths::isTestModeEnabled() || !isLoopbackHttp(url)
        || m_busy || m_server->isListening())
        return false;
    m_revocationEndpoint = url;
    return true;
}

void GoogleWorkspaceAuth::acceptConnections()
{
    while (m_server->hasPendingConnections()) {
        QTcpSocket *socket = m_server->nextPendingConnection();
        connect(socket, &QTcpSocket::readyRead, this, [this, socket]() {
            receiveCallback(socket);
        });
        connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
        if (socket->bytesAvailable() > 0) receiveCallback(socket);
    }
}

void GoogleWorkspaceAuth::receiveCallback(QTcpSocket *socket)
{
    if (!socket || socket->property("lc_callback_handled").toBool()) return;
    const QByteArray request = socket->peek(16384);
    if (request.size() > 8192) {
        socket->setProperty("lc_callback_handled", true);
        answerCallback(socket, 400, QByteArrayLiteral("Solicitud OAuth inválida."));
        return;
    }
    const int headerEnd = request.indexOf(QByteArrayLiteral("\r\n\r\n"));
    if (headerEnd < 0) return;
    socket->setProperty("lc_callback_handled", true);

    const QList<QByteArray> lines = request.left(headerEnd).split('\n');
    const QList<QByteArray> first = lines.isEmpty()
        ? QList<QByteArray>{} : lines.first().trimmed().split(' ');
    if (first.size() < 2 || first.at(0) != QByteArrayLiteral("GET")) {
        answerCallback(socket, 405, QByteArrayLiteral("Usá el navegador para completar OAuth."));
        return;
    }
    const QUrl target = QUrl::fromEncoded(first.at(1));
    QByteArray hostHeader;
    for (const QByteArray &line : lines) {
        const int colon = line.indexOf(':');
        if (colon > 0 && line.left(colon).trimmed().compare("Host", Qt::CaseInsensitive) == 0) {
            hostHeader = line.mid(colon + 1).trimmed();
            break;
        }
    }
    const QByteArray expectedHost = m_redirectUri.authority(QUrl::FullyEncoded).toLatin1();
    if (!target.isValid() || !target.isRelative() || target.path() != m_redirectUri.path()
        || target.hasFragment() || !target.userInfo().isEmpty()
        || hostHeader.compare(expectedHost, Qt::CaseInsensitive) != 0) {
        answerCallback(socket, 400, QByteArrayLiteral("Callback OAuth inválido."));
        return;
    }

    QUrl callback = m_redirectUri;
    callback.setQuery(target.query(QUrl::FullyEncoded));
    const CallbackResult result = validateAuthorizationCallback(callback, m_redirectUri, m_state);
    if (!result.accepted) {
        answerCallback(socket, 400, QByteArrayLiteral("Callback OAuth rechazado. Volvé a LlamaCode."));
        if (result.providerDenied) {
            finishWithError(QStringLiteral("Google rechazó la autorización (%1).")
                                .arg(result.error.left(80)));
        }
        return;
    }

    answerCallback(socket, 200, QByteArrayLiteral("Cuenta Google conectada. Podés volver a LlamaCode."));
    m_timeout->stop();
    closeListener();
    exchangeAuthorizationCode(result.code);
}

void GoogleWorkspaceAuth::answerCallback(QTcpSocket *socket, int status,
                                         const QByteArray &body)
{
    if (!socket) return;
    const QByteArray reason = status == 200 ? QByteArrayLiteral("OK")
        : status == 405 ? QByteArrayLiteral("Method Not Allowed")
                        : QByteArrayLiteral("Bad Request");
    const QByteArray response = QByteArrayLiteral("HTTP/1.1 ") + QByteArray::number(status)
        + ' ' + reason + QByteArrayLiteral("\r\nContent-Type: text/plain; charset=utf-8\r\n")
        + QByteArrayLiteral("Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n")
        + QByteArrayLiteral("Connection: close\r\nContent-Length: ")
        + QByteArray::number(body.size()) + QByteArrayLiteral("\r\n\r\n") + body;
    socket->write(response);
    socket->disconnectFromHost();
}

void GoogleWorkspaceAuth::exchangeAuthorizationCode(const QString &code)
{
    QUrlQuery form;
    form.addQueryItem(QStringLiteral("client_id"), m_clientId);
    form.addQueryItem(QStringLiteral("code"), code);
    form.addQueryItem(QStringLiteral("code_verifier"), m_codeVerifier);
    form.addQueryItem(QStringLiteral("grant_type"), QStringLiteral("authorization_code"));
    form.addQueryItem(QStringLiteral("redirect_uri"), m_redirectUri.toString(QUrl::FullyEncoded));
    postTokenRequest(form, QString(), m_requestedScopes);
}

void GoogleWorkspaceAuth::postTokenRequest(const QUrlQuery &form,
                                           const QString &fallbackRefreshToken,
                                           const QStringList &fallbackScopes)
{
    QNetworkRequest request(m_tokenEndpoint);
    request.setHeader(QNetworkRequest::ContentTypeHeader,
                      QStringLiteral("application/x-www-form-urlencoded"));
    request.setRawHeader(QByteArrayLiteral("Accept"), QByteArrayLiteral("application/json"));
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute,
                         QNetworkRequest::ManualRedirectPolicy);
    m_reply = m_network->post(request, form.toString(QUrl::FullyEncoded).toUtf8());
    m_timeout->start(20000);
    connect(m_reply, &QNetworkReply::finished, this,
            [this, fallbackRefreshToken, fallbackScopes]() {
        QNetworkReply *reply = m_reply;
        if (!reply) return;
        m_reply = nullptr;
        m_timeout->stop();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QNetworkReply::NetworkError networkError = reply->error();
        const QByteArray payload = reply->readAll();
        reply->deleteLater();
        if (networkError != QNetworkReply::NoError || status < 200 || status >= 300) {
            finishWithError(QStringLiteral("No se pudo completar OAuth con Google (HTTP %1).")
                                .arg(status));
            return;
        }

        QJsonParseError parseError;
        const QJsonDocument document = QJsonDocument::fromJson(payload, &parseError);
        const QJsonObject json = document.object();
        const QString accessToken = json.value(QStringLiteral("access_token")).toString();
        const QString tokenType = json.value(QStringLiteral("token_type")).toString();
        const qint64 expiresIn = json.value(QStringLiteral("expires_in")).toVariant().toLongLong();
        QStringList scopes;
        const QString scopeText = json.value(QStringLiteral("scope")).toString();
        if (!scopeText.isEmpty()) scopes = scopeText.split(QLatin1Char(' '), Qt::SkipEmptyParts);
        else scopes = fallbackScopes;

        if (parseError.error != QJsonParseError::NoError || !document.isObject()
            || accessToken.isEmpty() || tokenType.compare(QStringLiteral("Bearer"), Qt::CaseInsensitive) != 0
            || expiresIn <= 0 || scopes.isEmpty()) {
            finishWithError(QStringLiteral("Google devolvió una respuesta OAuth incompleta."));
            return;
        }
        for (const QString &scope : m_requestedScopes) {
            if (!scopes.contains(scope)) {
                finishWithError(QStringLiteral("La cuenta no concedió todos los permisos solicitados."));
                return;
            }
        }
        TokenSet tokens;
        tokens.accessToken = accessToken;
        tokens.refreshToken = json.value(QStringLiteral("refresh_token")).toString();
        if (tokens.refreshToken.isEmpty()) tokens.refreshToken = fallbackRefreshToken;
        tokens.tokenType = tokenType;
        tokens.expiresInSeconds = expiresIn;
        tokens.grantedScopes = scopes;

        m_timeout->stop();
        m_state.clear();
        m_codeVerifier.clear();
        m_refreshToken.clear();
        m_requestedScopes.clear();
        m_fallbackScopes.clear();
        setBusy(false);
        emit tokensReady(tokens);
    });
}

void GoogleWorkspaceAuth::finishWithError(const QString &message)
{
    if (m_revoking) {
        finishRevocation(false);
        return;
    }
    m_timeout->stop();
    closeListener();
    if (m_reply) {
        QNetworkReply *reply = m_reply;
        m_reply = nullptr;
        reply->abort();
    }
    m_state.clear();
    m_codeVerifier.clear();
    m_refreshToken.clear();
    m_requestedScopes.clear();
    m_fallbackScopes.clear();
    setBusy(false);
    emit operationFailed(message);
}

void GoogleWorkspaceAuth::finishRevocation(bool success)
{
    m_timeout->stop();
    m_revoking = false;
    closeListener();
    m_state.clear();
    m_codeVerifier.clear();
    m_refreshToken.clear();
    m_requestedScopes.clear();
    m_fallbackScopes.clear();
    setBusy(false);
    emit revocationFinished(success);
}

void GoogleWorkspaceAuth::closeListener()
{
    if (!m_server) return;
    m_server->close();
}

void GoogleWorkspaceAuth::setBusy(bool busy)
{
    if (m_busy == busy) return;
    m_busy = busy;
    emit busyChanged(busy);
}

} // namespace GoogleWorkspaceSecurity
