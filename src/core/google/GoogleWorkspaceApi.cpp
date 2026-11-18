#include "GoogleWorkspaceApi.h"

#include <QEventLoop>
#include <QDateTime>
#include <QJsonArray>
#include <QJsonDocument>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QRegularExpression>
#include <QSet>
#include <QStandardPaths>
#include <QTimer>
#include <QUrlQuery>

namespace GoogleWorkspaceSecurity {
namespace {

const QUrl kGoogleApiBase(QStringLiteral("https://www.googleapis.com"));
constexpr qsizetype kMaxResponseBytes = 4 * 1024 * 1024;

bool isLoopbackHttp(const QUrl &url)
{
    return url.scheme() == QLatin1String("http")
        && (url.host() == QLatin1String("127.0.0.1")
            || url.host() == QLatin1String("localhost")
            || url.host() == QLatin1String("::1"))
        && url.port(-1) > 0 && url.path().isEmpty() && !url.hasQuery()
        && !url.hasFragment() && url.userInfo().isEmpty();
}

bool safePathId(const QString &id)
{
    static const QRegularExpression safe(QStringLiteral("^[A-Za-z0-9._@+-]{1,256}$"));
    return safe.match(id).hasMatch();
}

bool safePageToken(const QString &token)
{
    static const QRegularExpression safe(QStringLiteral("^[A-Za-z0-9_./+=-]{1,2048}$"));
    return safe.match(token).hasMatch();
}

QDateTime parseDateTime(const QString &value)
{
    return QDateTime::fromString(value, Qt::ISODateWithMs).isValid()
        ? QDateTime::fromString(value, Qt::ISODateWithMs)
        : QDateTime::fromString(value, Qt::ISODate);
}

bool explicitDateTime(const QString &value)
{
    const QDateTime dateTime = parseDateTime(value);
    if (!dateTime.isValid()) return false;
    return value.endsWith(QLatin1Char('Z'))
        || value.contains(QLatin1Char('+'), Qt::CaseInsensitive)
        || value.lastIndexOf(QLatin1Char('-')) > 9;
}

QString apiError(int status)
{
    if (status == 401)
        return QStringLiteral("La autorización de Google venció; reconectá la cuenta.");
    if (status == 403)
        return QStringLiteral("Google denegó el acceso a esta función o a ese recurso.");
    if (status == 404)
        return QStringLiteral("Google no encontró el elemento solicitado.");
    if (status == 429 || status >= 500)
        return QStringLiteral("Google está temporalmente no disponible (HTTP %1). Querés reintentar más tarde.")
            .arg(status);
    return QStringLiteral("La solicitud a Google falló (HTTP %1). No se cambió ningún dato.")
        .arg(status);
}

} // namespace

GoogleWorkspaceApi::GoogleWorkspaceApi() : m_apiBase(kGoogleApiBase) {}

bool GoogleWorkspaceApi::setApiBaseForTests(const QUrl &url)
{
    if (!QStandardPaths::isTestModeEnabled() || !isLoopbackHttp(url)) return false;
    m_apiBase = url;
    return true;
}

ApiResult GoogleWorkspaceApi::searchGmail(const QString &accessToken,
                                          const QStringList &grantedScopes,
                                          const QString &query,
                                          const QString &pageToken,
                                          int maxResults) const
{
    if (query.trimmed().isEmpty() || query.size() > 4096
        || (!pageToken.isEmpty() && !safePageToken(pageToken)))
        return {false, 0, {}, QStringLiteral("La búsqueda de Gmail está vacía o es inválida.")};
    if (maxResults < 1 || maxResults > 50)
        return {false, 0, {}, QStringLiteral("Gmail permite pedir entre 1 y 50 resultados por página.")};
    QUrlQuery parameters;
    parameters.addQueryItem(QStringLiteral("q"), query);
    parameters.addQueryItem(QStringLiteral("maxResults"), QString::number(maxResults));
    if (!pageToken.isEmpty()) parameters.addQueryItem(QStringLiteral("pageToken"), pageToken);
    return get(Capability::GmailRead, accessToken, grantedScopes,
               QStringLiteral("/gmail/v1/users/me/messages"), parameters);
}

ApiResult GoogleWorkspaceApi::readGmailMessage(const QString &accessToken,
                                               const QStringList &grantedScopes,
                                               const QString &messageId) const
{
    if (!safePathId(messageId))
        return {false, 0, {}, QStringLiteral("El identificador del mensaje de Gmail es inválido.")};
    QUrlQuery parameters;
    parameters.addQueryItem(QStringLiteral("format"), QStringLiteral("full"));
    return get(Capability::GmailRead, accessToken, grantedScopes,
               QStringLiteral("/gmail/v1/users/me/messages/") + messageId, parameters);
}

ApiResult GoogleWorkspaceApi::listCalendarEvents(const QString &accessToken,
                                                 const QStringList &grantedScopes,
                                                 const QString &calendarId,
                                                 const QString &timeMin,
                                                 const QString &timeMax,
                                                 int maxResults) const
{
    if (!safePathId(calendarId) || !explicitDateTime(timeMin) || !explicitDateTime(timeMax)
        || maxResults < 1 || maxResults > 2500)
        return {false, 0, {}, QStringLiteral("Calendario, fechas u opciones de consulta inválidos.")};
    QUrlQuery parameters;
    parameters.addQueryItem(QStringLiteral("timeMin"), timeMin);
    parameters.addQueryItem(QStringLiteral("timeMax"), timeMax);
    parameters.addQueryItem(QStringLiteral("maxResults"), QString::number(maxResults));
    parameters.addQueryItem(QStringLiteral("singleEvents"), QStringLiteral("true"));
    parameters.addQueryItem(QStringLiteral("orderBy"), QStringLiteral("startTime"));
    return get(Capability::CalendarEventsRead, accessToken, grantedScopes,
               QStringLiteral("/calendar/v3/calendars/") + calendarId + QStringLiteral("/events"),
               parameters);
}

ApiResult GoogleWorkspaceApi::queryCalendarFreeBusy(const QString &accessToken,
                                                    const QStringList &grantedScopes,
                                                    const QStringList &calendarIds,
                                                    const QString &timeMin,
                                                    const QString &timeMax) const
{
    const QDateTime start = parseDateTime(timeMin);
    const QDateTime end = parseDateTime(timeMax);
    if (calendarIds.isEmpty() || calendarIds.size() > 50
        || timeMin.size() > 64 || timeMax.size() > 64
        || !explicitDateTime(timeMin) || !explicitDateTime(timeMax)
        || !start.isValid() || !end.isValid() || start >= end)
        return {false, 0, {}, QStringLiteral("Calendarios o intervalo de disponibilidad inválidos.")};

    QJsonArray items;
    QSet<QString> seen;
    for (const QString &id : calendarIds) {
        const QString calendarId = id.trimmed();
        if (!safePathId(calendarId) || seen.contains(calendarId))
            return {false, 0, {}, QStringLiteral("Hay un ID de calendario inválido o repetido.")};
        seen.insert(calendarId);
        items.append(QJsonObject{{QStringLiteral("id"), calendarId}});
    }
    const QJsonObject body{
        {QStringLiteral("timeMin"), timeMin},
        {QStringLiteral("timeMax"), timeMax},
        {QStringLiteral("calendarExpansionMax"), static_cast<int>(calendarIds.size())},
        {QStringLiteral("items"), items}};
    return post(Capability::CalendarFreeBusy, accessToken, grantedScopes,
                QStringLiteral("/calendar/v3/freeBusy"), body);
}

ApiResult GoogleWorkspaceApi::listTaskLists(const QString &accessToken,
                                            const QStringList &grantedScopes,
                                            int maxResults) const
{
    if (maxResults < 1 || maxResults > 100)
        return {false, 0, {}, QStringLiteral("Google Tasks permite entre 1 y 100 listas por página.")};
    QUrlQuery parameters;
    parameters.addQueryItem(QStringLiteral("maxResults"), QString::number(maxResults));
    return get(Capability::TasksRead, accessToken, grantedScopes,
               QStringLiteral("/tasks/v1/users/@me/lists"), parameters);
}

ApiResult GoogleWorkspaceApi::listTasks(const QString &accessToken,
                                        const QStringList &grantedScopes,
                                        const QString &taskListId,
                                        int maxResults) const
{
    if (!safePathId(taskListId) || maxResults < 1 || maxResults > 100)
        return {false, 0, {}, QStringLiteral("La lista o las opciones de Google Tasks son inválidas.")};
    QUrlQuery parameters;
    parameters.addQueryItem(QStringLiteral("maxResults"), QString::number(maxResults));
    parameters.addQueryItem(QStringLiteral("showCompleted"), QStringLiteral("true"));
    parameters.addQueryItem(QStringLiteral("showHidden"), QStringLiteral("false"));
    return get(Capability::TasksRead, accessToken, grantedScopes,
               QStringLiteral("/tasks/v1/lists/") + taskListId + QStringLiteral("/tasks"), parameters);
}

ApiResult GoogleWorkspaceApi::get(Capability capability, const QString &accessToken,
                                  const QStringList &grantedScopes, const QString &path,
                                  const QUrlQuery &query) const
{
    return send(capability, accessToken, grantedScopes, QByteArrayLiteral("GET"),
                path, query, {});
}

ApiResult GoogleWorkspaceApi::post(Capability capability, const QString &accessToken,
                                   const QStringList &grantedScopes, const QString &path,
                                   const QJsonObject &body) const
{
    return send(capability, accessToken, grantedScopes, QByteArrayLiteral("POST"), path, {},
                QJsonDocument(body).toJson(QJsonDocument::Compact));
}

ApiResult GoogleWorkspaceApi::send(Capability capability, const QString &accessToken,
                                   const QStringList &grantedScopes, const QByteArray &method,
                                   const QString &path, const QUrlQuery &query,
                                   const QByteArray &body) const
{
    // All current callers are read-only, including Calendar freeBusy's query
    // POST, so one bounded retry is safe. Future mutating requests must use a
    // separate transport path with an idempotency contract.
    ApiResult result;
    for (int attempt = 0; attempt < 2; ++attempt) {
        result = sendOnce(capability, accessToken, grantedScopes, method, path, query, body);
        const bool retryable = result.httpStatus == 429
            || (result.httpStatus >= 500 && result.httpStatus <= 599);
        if (!retryable || attempt != 0) return result;
        // Do not shorten a provider's Retry-After just to fit an interactive
        // wait budget. Return the transient error and let the caller retry later.
        if (result.retryAfterMs > 1000) return result;
        const int delayMs = qBound(250, result.retryAfterMs > 0 ? result.retryAfterMs : 250, 1000);
        if (m_cancellationFlag && m_cancellationFlag->load(std::memory_order_relaxed))
            return {false, result.httpStatus, {}, QStringLiteral("La solicitud a Google fue cancelada.")};
        QEventLoop backoffLoop;
        QTimer backoff;
        backoff.setSingleShot(true);
        QTimer cancellationCheck;
        cancellationCheck.setInterval(20);
        bool cancelled = false;
        QObject::connect(&backoff, &QTimer::timeout, &backoffLoop, &QEventLoop::quit);
        QObject::connect(&cancellationCheck, &QTimer::timeout, &backoffLoop, [&]() {
            if (!m_cancellationFlag || !m_cancellationFlag->load(std::memory_order_relaxed))
                return;
            cancelled = true;
            backoffLoop.quit();
        });
        cancellationCheck.start();
        backoff.start(delayMs);
        backoffLoop.exec();
        cancellationCheck.stop();
        if (cancelled)
            return {false, result.httpStatus, {}, QStringLiteral("La solicitud a Google fue cancelada.")};
    }
    return result;
}

ApiResult GoogleWorkspaceApi::sendOnce(Capability capability, const QString &accessToken,
                                       const QStringList &grantedScopes, const QByteArray &method,
                                       const QString &path, const QUrlQuery &query,
                                       const QByteArray &body) const
{
    if (m_cancellationFlag && m_cancellationFlag->load(std::memory_order_relaxed))
        return {false, 0, {}, QStringLiteral("La solicitud a Google fue cancelada.")};
    if (accessToken.trimmed().isEmpty())
        return {false, 0, {}, QStringLiteral("Conectá una cuenta Google antes de consultar.")};
    if (!grantsCapability(capability, grantedScopes))
        return {false, 0, {}, QStringLiteral("La cuenta Google no concedió el permiso de lectura requerido.")};

    QUrl url = m_apiBase;
    url.setPath(path);
    url.setQuery(query);
    QNetworkRequest request(url);
    request.setRawHeader(QByteArrayLiteral("Authorization"),
                         QByteArrayLiteral("Bearer ") + accessToken.toUtf8());
    request.setRawHeader(QByteArrayLiteral("Accept"), QByteArrayLiteral("application/json"));
    if (method == QByteArrayLiteral("POST"))
        request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute,
                         QNetworkRequest::ManualRedirectPolicy);
    request.setTransferTimeout(15000);

    QNetworkAccessManager manager;
    QNetworkReply *reply = method == QByteArrayLiteral("POST")
        ? manager.post(request, body) : manager.get(request);
    QEventLoop loop;
    QTimer timeout;
    timeout.setSingleShot(true);
    QTimer cancellationCheck;
    cancellationCheck.setInterval(20);
    QByteArray payload;
    bool tooLarge = false;
    QObject::connect(reply, &QNetworkReply::readyRead, &loop, [&]() {
        const QByteArray chunk = reply->readAll();
        if (payload.size() + chunk.size() > kMaxResponseBytes) {
            tooLarge = true;
            reply->abort();
            return;
        }
        payload += chunk;
    });
    QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    QObject::connect(&timeout, &QTimer::timeout, &loop, [&]() {
        reply->abort();
        loop.quit();
    });
    bool cancelled = false;
    QObject::connect(&cancellationCheck, &QTimer::timeout, &loop, [&]() {
        if (!m_cancellationFlag || !m_cancellationFlag->load(std::memory_order_relaxed))
            return;
        cancelled = true;
        reply->abort();
        loop.quit();
    });
    timeout.start(16000);
    cancellationCheck.start();
    loop.exec();
    timeout.stop();
    cancellationCheck.stop();
    const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    const QNetworkReply::NetworkError networkError = reply->error();
    int retryAfterMs = 0;
    const QByteArray retryAfter = reply->rawHeader(QByteArrayLiteral("Retry-After")).trimmed();
    bool retryAfterSecondsValid = false;
    const qint64 retryAfterSeconds = retryAfter.toLongLong(&retryAfterSecondsValid);
    if (retryAfterSecondsValid) {
        retryAfterMs = static_cast<int>(qBound<qint64>(0, retryAfterSeconds, 5LL) * 1000);
    } else if (!retryAfter.isEmpty()) {
        const QDateTime retryAt = QDateTime::fromString(QString::fromLatin1(retryAfter),
                                                        Qt::RFC2822Date).toUTC();
        if (retryAt.isValid())
            retryAfterMs = static_cast<int>(qBound<qint64>(0,
                QDateTime::currentDateTimeUtc().msecsTo(retryAt), 5000LL));
    }
    const QByteArray finalChunk = reply->readAll();
    if (payload.size() + finalChunk.size() <= kMaxResponseBytes)
        payload += finalChunk;
    else
        tooLarge = true;
    reply->deleteLater();

    if (tooLarge)
        return {false, status, {}, QStringLiteral("La respuesta de Google superó el límite de 4 MiB.")};
    if (cancelled)
        return {false, status, {}, QStringLiteral("La solicitud a Google fue cancelada.")};
    if (timeout.isActive()) timeout.stop();
    if (status == 401 || status == 403 || status == 404 || status == 429 || status >= 500)
        return {false, status, {}, apiError(status), retryAfterMs};
    if (networkError != QNetworkReply::NoError)
        return {false, status, {}, QStringLiteral("No se pudo conectar con Google. Revisá la red y reintentá.")};
    if (status < 200 || status >= 300)
        return {false, status, {}, apiError(status)};

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(payload, &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject())
        return {false, status, {}, QStringLiteral("Google devolvió una respuesta JSON inválida.")};
    return {true, status, document.object(), {}};
}

} // namespace GoogleWorkspaceSecurity
