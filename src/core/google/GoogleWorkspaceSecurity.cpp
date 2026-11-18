#include "GoogleWorkspaceSecurity.h"

#include "core/agent/ToolExecutionSafety.h"

#include <QCryptographicHash>
#include <QRandomGenerator>
#include <QRegularExpression>
#include <QSet>
#include <QUrlQuery>
#include <algorithm>

namespace GoogleWorkspaceSecurity {
namespace {

const QString kGmailRead = QStringLiteral("https://www.googleapis.com/auth/gmail.readonly");
const QString kGmailCompose = QStringLiteral("https://www.googleapis.com/auth/gmail.compose");
const QString kCalendarFreeBusy = QStringLiteral("https://www.googleapis.com/auth/calendar.events.freebusy");
const QString kCalendarEventsRead = QStringLiteral("https://www.googleapis.com/auth/calendar.events.readonly");
const QString kCalendarEventsWrite = QStringLiteral("https://www.googleapis.com/auth/calendar.events");
const QString kTasksRead = QStringLiteral("https://www.googleapis.com/auth/tasks.readonly");
const QString kTasksWrite = QStringLiteral("https://www.googleapis.com/auth/tasks");

QByteArray randomBytes(int count)
{
    QByteArray bytes(count, '\0');
    QRandomGenerator *generator = QRandomGenerator::system();
    for (int offset = 0; offset < count; offset += static_cast<int>(sizeof(quint32))) {
        const quint32 value = generator->generate();
        const int amount = qMin(static_cast<int>(sizeof(value)), count - offset);
        for (int i = 0; i < amount; ++i)
            bytes[offset + i] = static_cast<char>((value >> (8 * i)) & 0xff);
    }
    return bytes;
}

QString randomUrlToken()
{
    return QString::fromLatin1(randomBytes(32).toBase64(
        QByteArray::Base64UrlEncoding | QByteArray::OmitTrailingEquals));
}

bool isLoopbackRedirect(const QUrl &url)
{
    if (!url.isValid() || url.scheme() != QLatin1String("http")
        || url.port(-1) < 1024 || url.port(-1) > 65535
        || !url.userName().isEmpty() || !url.password().isEmpty()
        || url.hasQuery() || url.hasFragment())
        return false;
    const QString host = url.host().toLower();
    return host == QLatin1String("127.0.0.1") || host == QLatin1String("localhost")
        || host == QLatin1String("::1");
}

bool sameRedirect(const QUrl &callback, const QUrl &redirect)
{
    return isLoopbackRedirect(redirect) && callback.isValid()
        && callback.scheme() == redirect.scheme()
        && callback.host().compare(redirect.host(), Qt::CaseInsensitive) == 0
        && callback.port(-1) == redirect.port(-1)
        && callback.path() == redirect.path()
        && callback.userName().isEmpty() && callback.password().isEmpty()
        && callback.fragment().isEmpty();
}

QString singleQueryValue(const QUrlQuery &query, const QString &key, bool *valid)
{
    QStringList values;
    for (const auto &item : query.queryItems(QUrl::FullyDecoded))
        if (item.first == key) values.append(item.second);
    if (values.size() > 1) *valid = false;
    return values.size() == 1 ? values.constFirst() : QString();
}

bool constantTimeEqual(const QString &left, const QString &right)
{
    const QByteArray a = left.toUtf8();
    const QByteArray b = right.toUtf8();
    const int maxSize = qMax(a.size(), b.size());
    unsigned char difference = static_cast<unsigned char>(a.size() ^ b.size());
    for (int i = 0; i < maxSize; ++i) {
        const unsigned char ac = i < a.size() ? static_cast<unsigned char>(a.at(i)) : 0;
        const unsigned char bc = i < b.size() ? static_cast<unsigned char>(b.at(i)) : 0;
        difference |= static_cast<unsigned char>(ac ^ bc);
    }
    return difference == 0;
}

} // namespace

QStringList scopesFor(Capability capability)
{
    switch (capability) {
    case Capability::GmailRead: return {kGmailRead};
    case Capability::GmailDraft:
    case Capability::GmailSend: return {kGmailCompose};
    case Capability::CalendarFreeBusy: return {kCalendarFreeBusy};
    case Capability::CalendarEventsRead: return {kCalendarEventsRead};
    case Capability::CalendarEventWrite: return {kCalendarEventsWrite};
    case Capability::TasksRead: return {kTasksRead};
    case Capability::TasksWrite: return {kTasksWrite};
    }
    return {};
}

QStringList scopesFor(const QList<Capability> &capabilities)
{
    QStringList result;
    for (Capability capability : capabilities) {
        for (const QString &scope : scopesFor(capability))
            if (!result.contains(scope)) result.append(scope);
    }
    return result;
}

QStringList knownScopes()
{
    return {kGmailRead, kGmailCompose, kCalendarFreeBusy, kCalendarEventsRead,
            kCalendarEventsWrite, kTasksRead, kTasksWrite};
}

bool grantsCapability(Capability capability, const QStringList &grantedScopes)
{
    const QStringList required = scopesFor(capability);
    return !required.isEmpty()
        && std::all_of(required.cbegin(), required.cend(), [&grantedScopes](const QString &scope) {
               return grantedScopes.contains(scope);
           });
}

bool requiresExplicitApproval(Capability capability)
{
    switch (capability) {
    case Capability::GmailDraft:
    case Capability::GmailSend:
    case Capability::CalendarEventWrite:
    case Capability::TasksWrite:
        return true;
    case Capability::GmailRead:
    case Capability::CalendarFreeBusy:
    case Capability::CalendarEventsRead:
    case Capability::TasksRead:
        return false;
    }
    return true;
}

bool requiresExplicitApproval(const QString &toolName)
{
    return toolName == QLatin1String("google_gmail_create_draft")
        || toolName == QLatin1String("google_tasks_create")
        || toolName == QLatin1String("google_tasks_update")
        || toolName == QLatin1String("google_tasks_complete")
        || toolName == QLatin1String("google_calendar_create_event");
}

QString capabilityName(Capability capability)
{
    switch (capability) {
    case Capability::GmailRead: return QStringLiteral("gmail.read");
    case Capability::GmailDraft: return QStringLiteral("gmail.draft");
    case Capability::GmailSend: return QStringLiteral("gmail.send");
    case Capability::CalendarFreeBusy: return QStringLiteral("calendar.freebusy");
    case Capability::CalendarEventsRead: return QStringLiteral("calendar.events.read");
    case Capability::CalendarEventWrite: return QStringLiteral("calendar.events.write");
    case Capability::TasksRead: return QStringLiteral("tasks.read");
    case Capability::TasksWrite: return QStringLiteral("tasks.write");
    }
    return QStringLiteral("unknown");
}

QString codeChallengeForVerifier(const QString &verifier)
{
    static const QRegularExpression valid(QStringLiteral("^[A-Za-z0-9._~-]{43,128}$"));
    if (!valid.match(verifier).hasMatch()) return {};
    const QByteArray digest = QCryptographicHash::hash(verifier.toLatin1(),
                                                       QCryptographicHash::Sha256);
    return QString::fromLatin1(digest.toBase64(
        QByteArray::Base64UrlEncoding | QByteArray::OmitTrailingEquals));
}

AuthorizationRequest createAuthorizationRequest(const QString &clientId,
                                                const QUrl &redirectUri,
                                                const QList<Capability> &capabilities)
{
    AuthorizationRequest result;
    if (clientId.trimmed().isEmpty() || clientId.contains(QRegularExpression(QStringLiteral("\\s")))) {
        result.error = QStringLiteral("Falta un client ID válido de Google.");
        return result;
    }
    if (!isLoopbackRedirect(redirectUri)) {
        result.error = QStringLiteral("El callback OAuth debe ser HTTP loopback en localhost con puerto explícito.");
        return result;
    }
    const QStringList scopes = scopesFor(capabilities);
    if (scopes.isEmpty()) {
        result.error = QStringLiteral("No se solicitó ninguna capacidad Google válida.");
        return result;
    }

    result.state = randomUrlToken();
    result.codeVerifier = randomUrlToken();
    const QString challenge = codeChallengeForVerifier(result.codeVerifier);
    if (result.state.isEmpty() || challenge.isEmpty()) {
        result.error = QStringLiteral("No se pudo preparar PKCE.");
        return result;
    }

    result.url = QUrl(QStringLiteral("https://accounts.google.com/o/oauth2/v2/auth"));
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("client_id"), clientId.trimmed());
    query.addQueryItem(QStringLiteral("redirect_uri"), redirectUri.toString(QUrl::FullyEncoded));
    query.addQueryItem(QStringLiteral("response_type"), QStringLiteral("code"));
    query.addQueryItem(QStringLiteral("scope"), scopes.join(QLatin1Char(' ')));
    query.addQueryItem(QStringLiteral("state"), result.state);
    query.addQueryItem(QStringLiteral("code_challenge"), challenge);
    query.addQueryItem(QStringLiteral("code_challenge_method"), QStringLiteral("S256"));
    query.addQueryItem(QStringLiteral("access_type"), QStringLiteral("offline"));
    query.addQueryItem(QStringLiteral("include_granted_scopes"), QStringLiteral("true"));
    query.addQueryItem(QStringLiteral("prompt"), QStringLiteral("consent"));
    result.url.setQuery(query);
    return result;
}

CallbackResult validateAuthorizationCallback(const QUrl &callbackUrl,
                                            const QUrl &redirectUri,
                                            const QString &expectedState)
{
    CallbackResult result;
    if (expectedState.isEmpty() || !sameRedirect(callbackUrl, redirectUri)) {
        result.error = QStringLiteral("El callback OAuth no coincide con el listener esperado.");
        return result;
    }

    const QUrlQuery query(callbackUrl);
    bool unique = true;
    const QString state = singleQueryValue(query, QStringLiteral("state"), &unique);
    const QString code = singleQueryValue(query, QStringLiteral("code"), &unique);
    const QString error = singleQueryValue(query, QStringLiteral("error"), &unique);
    const QString description = singleQueryValue(query, QStringLiteral("error_description"), &unique);
    const QString issuer = singleQueryValue(query, QStringLiteral("iss"), &unique);
    if (!unique || !constantTimeEqual(state, expectedState)) {
        result.error = QStringLiteral("El estado OAuth no coincide o está repetido.");
        return result;
    }
    if (!issuer.isEmpty() && issuer != QLatin1String("https://accounts.google.com")) {
        result.error = QStringLiteral("El emisor del callback OAuth no es Google.");
        return result;
    }
    if (!error.isEmpty() && !code.isEmpty()) {
        result.error = QStringLiteral("El callback OAuth no puede incluir código y error a la vez.");
        return result;
    }
    if (!error.isEmpty()) {
        result.error = error;
        result.errorDescription = description;
        result.providerDenied = true;
        return result;
    }
    if (code.isEmpty()) {
        result.error = QStringLiteral("El callback OAuth no incluye un código.");
        return result;
    }
    result.code = code;
    result.accepted = true;
    return result;
}

QString approvalFingerprint(Capability capability, const QString &account,
                            const QJsonObject &arguments)
{
    QJsonObject payload{
        {QStringLiteral("account"), account.trimmed().toLower()},
        {QStringLiteral("capability"), capabilityName(capability)},
        {QStringLiteral("arguments"), arguments}};
    return QString::fromLatin1(QCryptographicHash::hash(
        ToolExecutionSafety::canonicalJson(payload), QCryptographicHash::Sha256).toHex());
}

} // namespace GoogleWorkspaceSecurity
