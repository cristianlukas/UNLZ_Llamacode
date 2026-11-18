#pragma once

#include <QJsonObject>
#include <QString>
#include <QStringList>
#include <QUrl>

namespace GoogleWorkspaceSecurity {

enum class Capability {
    GmailRead,
    GmailDraft,
    GmailSend,
    CalendarFreeBusy,
    CalendarEventsRead,
    CalendarEventWrite,
    TasksRead,
    TasksWrite
};

struct AuthorizationRequest {
    QUrl url;
    QString state;
    QString codeVerifier;
    QString error;
    bool isValid() const { return url.isValid() && error.isEmpty(); }
};

struct CallbackResult {
    QString code;
    QString error;
    QString errorDescription;
    bool accepted = false;
    bool providerDenied = false;
};

// Scopes are grouped by the smallest API permission needed for one capability.
QStringList scopesFor(Capability capability);
QStringList scopesFor(const QList<Capability> &capabilities);
QStringList knownScopes();
bool grantsCapability(Capability capability, const QStringList &grantedScopes);
bool requiresExplicitApproval(Capability capability);
QString capabilityName(Capability capability);

// PKCE helpers are pure and usable in tests; authorization URLs always target
// Google's OAuth endpoint and redirect only to an explicit loopback listener.
QString codeChallengeForVerifier(const QString &verifier);
AuthorizationRequest createAuthorizationRequest(const QString &clientId,
                                                const QUrl &redirectUri,
                                                const QList<Capability> &capabilities);
CallbackResult validateAuthorizationCallback(const QUrl &callbackUrl,
                                            const QUrl &redirectUri,
                                            const QString &expectedState);

// Binds a one-time approval to the account, exact capability and full payload.
QString approvalFingerprint(Capability capability, const QString &account,
                            const QJsonObject &arguments);

} // namespace GoogleWorkspaceSecurity
