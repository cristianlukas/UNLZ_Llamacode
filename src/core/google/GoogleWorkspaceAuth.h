#pragma once

#include "GoogleWorkspaceSecurity.h"

#include <QObject>
#include <QPointer>
#include <QStringList>
#include <QUrl>
#include <QUrlQuery>

class QNetworkAccessManager;
class QNetworkReply;
class QTcpServer;
class QTcpSocket;
class QTimer;

namespace GoogleWorkspaceSecurity {

struct TokenSet {
    QString accessToken;
    QString refreshToken;
    QString tokenType;
    qint64 expiresInSeconds = 0;
    QStringList grantedScopes;
};

// Desktop OAuth Authorization Code + PKCE (S256) with a short-lived loopback
// listener. Tokens are returned in memory; persistence policy belongs to the
// caller and must use an OS-protected SecretStore backend.
class GoogleWorkspaceAuth : public QObject
{
    Q_OBJECT
public:
    explicit GoogleWorkspaceAuth(QObject *parent = nullptr);
    ~GoogleWorkspaceAuth() override;

    bool busy() const { return m_busy; }
    bool revoking() const { return m_revoking; }
    bool start(const QString &clientId, const QList<Capability> &capabilities);
    bool refresh(const QString &clientId, const QString &refreshToken,
                 const QStringList &previouslyGrantedScopes);
    bool revoke(const QString &token);
    void cancel();

    // Test-only loopback token endpoint; refuses use outside Qt test mode.
    bool setTokenEndpointForTests(const QUrl &url);
    bool setRevocationEndpointForTests(const QUrl &url);

signals:
    void authorizationUrlReady(const QUrl &url);
    void tokensReady(const GoogleWorkspaceSecurity::TokenSet &tokens);
    void operationFailed(const QString &message);
    void revocationFinished(bool success);
    void busyChanged(bool busy);

private slots:
    void acceptConnections();

private:
    void setBusy(bool busy);
    void receiveCallback(QTcpSocket *socket);
    void answerCallback(QTcpSocket *socket, int status, const QByteArray &body);
    void exchangeAuthorizationCode(const QString &code);
    void postTokenRequest(const QUrlQuery &form, const QString &fallbackRefreshToken,
                          const QStringList &fallbackScopes);
    void finishWithError(const QString &message);
    void finishRevocation(bool success);
    void closeListener();

    QTcpServer *m_server = nullptr;
    QNetworkAccessManager *m_network = nullptr;
    QTimer *m_timeout = nullptr;
    QPointer<QNetworkReply> m_reply;
    QUrl m_tokenEndpoint;
    QUrl m_revocationEndpoint;
    QUrl m_redirectUri;
    QString m_clientId;
    QString m_state;
    QString m_codeVerifier;
    QString m_refreshToken;
    QStringList m_requestedScopes;
    QStringList m_fallbackScopes;
    bool m_busy = false;
    bool m_revoking = false;
};

} // namespace GoogleWorkspaceSecurity

Q_DECLARE_METATYPE(GoogleWorkspaceSecurity::TokenSet)
