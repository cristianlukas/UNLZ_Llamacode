#include <QtTest>

#include "core/google/GoogleWorkspaceSecurity.h"

#include <QUrlQuery>

using namespace GoogleWorkspaceSecurity;

class GoogleWorkspaceSecurityTests : public QObject
{
    Q_OBJECT
private slots:
    void scopesAreNarrowAndDeduplicated();
    void writesAlwaysNeedApproval();
    void pkceUsesS256AndRejectsBadVerifiers();
    void authorizationRequestIsScopedAndLoopbackOnly();
    void callbackRequiresMatchingStateAndRedirect();
    void callbackRejectsDuplicatesAndNonGoogleIssuer();
    void approvalFingerprintBindsExactPayload();
    void googleDraftToolAlwaysNeedsExplicitApproval();
};

void GoogleWorkspaceSecurityTests::scopesAreNarrowAndDeduplicated()
{
    const QStringList gmailRead = scopesFor(Capability::GmailRead);
    QCOMPARE(gmailRead, QStringList{
        QStringLiteral("https://www.googleapis.com/auth/gmail.readonly")});
    QVERIFY(!gmailRead.contains(QStringLiteral("https://www.googleapis.com/auth/gmail.modify")));
    QVERIFY(!scopesFor({Capability::CalendarEventsRead}).contains(
        QStringLiteral("https://www.googleapis.com/auth/calendar")));
    QCOMPARE(scopesFor(Capability::CalendarFreeBusy),
             QStringList{QStringLiteral("https://www.googleapis.com/auth/calendar.events.freebusy")});
    QVERIFY(!grantsCapability(Capability::CalendarFreeBusy,
                              scopesFor(Capability::CalendarEventsRead)));
    QVERIFY(grantsCapability(Capability::CalendarFreeBusy,
                             scopesFor(Capability::CalendarFreeBusy)));
    QCOMPARE(scopesFor({Capability::TasksRead, Capability::TasksRead}).size(), 1);
    QVERIFY(grantsCapability(Capability::TasksRead, scopesFor(Capability::TasksRead)));
    QVERIFY(!grantsCapability(Capability::TasksWrite, scopesFor(Capability::TasksRead)));
    QCOMPARE(scopesFor(Capability::TasksWrite), QStringList{
        QStringLiteral("https://www.googleapis.com/auth/tasks")});
}

void GoogleWorkspaceSecurityTests::writesAlwaysNeedApproval()
{
    QVERIFY(!requiresExplicitApproval(Capability::GmailRead));
    QVERIFY(requiresExplicitApproval(Capability::GmailDraft));
    QVERIFY(requiresExplicitApproval(Capability::GmailSend));
    QVERIFY(requiresExplicitApproval(Capability::CalendarEventWrite));
    QVERIFY(requiresExplicitApproval(Capability::TasksWrite));
    QVERIFY(requiresExplicitApproval(Capability::CalendarEventWrite));
}

void GoogleWorkspaceSecurityTests::pkceUsesS256AndRejectsBadVerifiers()
{
    const QString verifier = QStringLiteral("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
    QCOMPARE(codeChallengeForVerifier(verifier),
             QStringLiteral("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"));
    QVERIFY(codeChallengeForVerifier(QStringLiteral("short")).isEmpty());
    QVERIFY(codeChallengeForVerifier(QString(129, QLatin1Char('a'))).isEmpty());
}

void GoogleWorkspaceSecurityTests::authorizationRequestIsScopedAndLoopbackOnly()
{
    const QUrl redirect(QStringLiteral("http://127.0.0.1:49152/oauth2callback"));
    const AuthorizationRequest request = createAuthorizationRequest(
        QStringLiteral("test-client.apps.googleusercontent.com"), redirect,
        {Capability::GmailRead, Capability::CalendarFreeBusy, Capability::TasksRead});
    QVERIFY2(request.isValid(), qPrintable(request.error));
    QCOMPARE(request.url.host(), QStringLiteral("accounts.google.com"));
    QCOMPARE(request.url.scheme(), QStringLiteral("https"));
    QVERIFY(request.state.size() >= 40);
    QVERIFY(request.codeVerifier.size() >= 43);

    const QUrlQuery query(request.url);
    QCOMPARE(query.queryItemValue(QStringLiteral("code_challenge_method")), QStringLiteral("S256"));
    QCOMPARE(query.queryItemValue(QStringLiteral("response_type")), QStringLiteral("code"));
    QCOMPARE(query.queryItemValue(QStringLiteral("access_type")), QStringLiteral("offline"));
    QCOMPARE(query.queryItemValue(QStringLiteral("prompt")), QStringLiteral("consent"));
    QCOMPARE(query.queryItemValue(QStringLiteral("redirect_uri")), redirect.toString());
    QVERIFY(!query.queryItemValue(QStringLiteral("scope")).contains(
        QStringLiteral("gmail.compose")));
    QVERIFY(query.queryItemValue(QStringLiteral("scope")).contains(
        QStringLiteral("calendar.events.freebusy")));
    QVERIFY(!createAuthorizationRequest(QStringLiteral("client"),
        QUrl(QStringLiteral("https://attacker.example/callback")),
        {Capability::GmailRead}).isValid());
    QVERIFY(!createAuthorizationRequest(QStringLiteral("client"), redirect, {}).isValid());
}

void GoogleWorkspaceSecurityTests::callbackRequiresMatchingStateAndRedirect()
{
    const QUrl redirect(QStringLiteral("http://localhost:49152/oauth2callback"));
    const QUrl callback(QStringLiteral(
        "http://localhost:49152/oauth2callback?code=auth-code&state=random-state&iss=https%3A%2F%2Faccounts.google.com"));
    const CallbackResult result = validateAuthorizationCallback(callback, redirect,
                                                                QStringLiteral("random-state"));
    QVERIFY(result.accepted);
    QCOMPARE(result.code, QStringLiteral("auth-code"));
    QVERIFY(validateAuthorizationCallback(callback, redirect,
        QStringLiteral("attacker-state")).code.isEmpty());

    const QUrl otherPort(QStringLiteral(
        "http://localhost:49153/oauth2callback?code=auth-code&state=random-state"));
    QVERIFY(!validateAuthorizationCallback(otherPort, redirect,
        QStringLiteral("random-state")).accepted);
    const QUrl otherPath(QStringLiteral(
        "http://localhost:49152/other?code=auth-code&state=random-state"));
    QVERIFY(!validateAuthorizationCallback(otherPath, redirect,
        QStringLiteral("random-state")).accepted);
}

void GoogleWorkspaceSecurityTests::callbackRejectsDuplicatesAndNonGoogleIssuer()
{
    const QUrl redirect(QStringLiteral("http://127.0.0.1:49152/oauth2callback"));
    const QUrl duplicate(QStringLiteral(
        "http://127.0.0.1:49152/oauth2callback?code=a&code=b&state=s"));
    QVERIFY(!validateAuthorizationCallback(duplicate, redirect, QStringLiteral("s")).accepted);
    const QUrl wrongIssuer(QStringLiteral(
        "http://127.0.0.1:49152/oauth2callback?code=a&state=s&iss=https%3A%2F%2Fevil.example"));
    QVERIFY(!validateAuthorizationCallback(wrongIssuer, redirect, QStringLiteral("s")).accepted);
    const QUrl denied(QStringLiteral(
        "http://127.0.0.1:49152/oauth2callback?error=access_denied&error_description=cancelled&state=s"));
    const CallbackResult result = validateAuthorizationCallback(denied, redirect, QStringLiteral("s"));
    QVERIFY(!result.accepted);
    QCOMPARE(result.error, QStringLiteral("access_denied"));
    QVERIFY(result.code.isEmpty());
    const QUrl ambiguous(QStringLiteral(
        "http://127.0.0.1:49152/oauth2callback?error=access_denied&code=a&state=s"));
    QVERIFY(!validateAuthorizationCallback(ambiguous, redirect, QStringLiteral("s")).accepted);
}

void GoogleWorkspaceSecurityTests::approvalFingerprintBindsExactPayload()
{
    const QJsonObject first{{QStringLiteral("to"), QStringLiteral("test@example.com")},
                            {QStringLiteral("subject"), QStringLiteral("Hola")}};
    const QJsonObject sameDifferentKeyOrder{{QStringLiteral("subject"), QStringLiteral("Hola")},
                                            {QStringLiteral("to"), QStringLiteral("test@example.com")}};
    const QJsonObject altered{{QStringLiteral("to"), QStringLiteral("other@example.com")},
                              {QStringLiteral("subject"), QStringLiteral("Hola")}};
    const QString approved = approvalFingerprint(Capability::GmailSend,
                                                  QStringLiteral("Me@Example.com"), first);
    QCOMPARE(approved, approvalFingerprint(Capability::GmailSend,
                                           QStringLiteral("me@example.com"), sameDifferentKeyOrder));
    QVERIFY(approved != approvalFingerprint(Capability::GmailSend,
                                           QStringLiteral("me@example.com"), altered));
    QVERIFY(approved != approvalFingerprint(Capability::GmailDraft,
                                           QStringLiteral("me@example.com"), first));
}

void GoogleWorkspaceSecurityTests::googleDraftToolAlwaysNeedsExplicitApproval()
{
    QVERIFY(requiresExplicitApproval(QStringLiteral("google_gmail_create_draft")));
    QVERIFY(requiresExplicitApproval(QStringLiteral("google_tasks_create")));
    QVERIFY(requiresExplicitApproval(QStringLiteral("google_calendar_create_event")));
    QVERIFY(!requiresExplicitApproval(QStringLiteral("google_gmail_search")));
    QVERIFY(!requiresExplicitApproval(QStringLiteral("google_tasks_list")));
    QVERIFY(!requiresExplicitApproval(QStringLiteral("google_calendar_events")));
}

QTEST_MAIN(GoogleWorkspaceSecurityTests)
#include "test_google_workspace_security.moc"
