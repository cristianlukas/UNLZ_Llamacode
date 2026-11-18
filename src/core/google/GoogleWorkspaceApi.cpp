#include "GoogleWorkspaceApi.h"

#include <QEventLoop>
#include <QDate>
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
#include <QTimeZone>
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

bool validDraftAddress(const QString &raw)
{
    const QString address = raw.trimmed();
    if (address.isEmpty() || address.size() > 254 || address.contains(QRegularExpression(
            QStringLiteral("\\s|[\\x00-\\x1f\\x7f]"))))
        return false;
    const int at = address.indexOf(QLatin1Char('@'));
    if (at <= 0 || at != address.lastIndexOf(QLatin1Char('@')) || at > 64)
        return false;
    const QString local = address.left(at);
    if (local.startsWith(QLatin1Char('.')) || local.endsWith(QLatin1Char('.'))
        || local.contains(QStringLiteral("..")))
        return false;
    static const QRegularExpression localPart(QStringLiteral(
        "^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*$"));
    if (!localPart.match(local).hasMatch()) return false;

    const QString domain = address.mid(at + 1);
    if (domain.size() > 253 || !domain.contains(QLatin1Char('.'))) return false;
    static const QRegularExpression label(QStringLiteral(
        "^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"));
    const QStringList labels = domain.split(QLatin1Char('.'));
    if (labels.size() < 2) return false;
    for (const QString &part : labels)
        if (!label.match(part).hasMatch()) return false;
    return true;
}

bool validDraftAddresses(const QStringList &addresses, bool required)
{
    if (addresses.size() > 5 || (required && addresses.isEmpty())) return false;
    QSet<QString> seen;
    for (const QString &address : addresses) {
        if (!validDraftAddress(address)) return false;
        const QString normalized = address.trimmed().toLower();
        if (seen.contains(normalized)) return false;
        seen.insert(normalized);
    }
    return true;
}

QString foldedHeader(const QString &name, const QStringList &values,
                     const QString &separator = QStringLiteral(", "))
{
    QString result = name + QStringLiteral(": ");
    QString line = result;
    for (int i = 0; i < values.size(); ++i) {
        const QString delimiter = i == 0 ? QString() : separator;
        const QString item = delimiter + values.at(i);
        if (line.size() + item.size() > 78) {
            if (i > 0 && separator == QLatin1String(", ")) result += QLatin1Char(',');
            result += QStringLiteral("\r\n ");
            line = QStringLiteral(" ");
            result += values.at(i);
            line += values.at(i);
        } else {
            result += item;
            line += item;
        }
    }
    return result + QStringLiteral("\r\n");
}

QString encodedSubject(const QString &subject)
{
    QStringList words;
    QByteArray chunk;
    for (qsizetype offset = 0; offset < subject.size();) {
        const qsizetype count = subject.at(offset).isHighSurrogate()
            && offset + 1 < subject.size() ? 2 : 1;
        const QByteArray encoded = subject.mid(offset, count).toUtf8();
        if (!chunk.isEmpty() && chunk.size() + encoded.size() > 42) {
            words.append(QStringLiteral("=?UTF-8?B?%1?=")
                .arg(QString::fromLatin1(chunk.toBase64())));
            chunk.clear();
        }
        chunk += encoded;
        offset += count;
    }
    if (!chunk.isEmpty())
        words.append(QStringLiteral("=?UTF-8?B?%1?=")
            .arg(QString::fromLatin1(chunk.toBase64())));
    return words.join(QLatin1Char(' '));
}

QString foldedBase64Body(const QByteArray &body)
{
    const QByteArray encoded = body.toBase64();
    QString result;
    for (qsizetype offset = 0; offset < encoded.size(); offset += 76) {
        if (!result.isEmpty()) result += QStringLiteral("\r\n");
        result += QString::fromLatin1(encoded.mid(offset, 76));
    }
    return result;
}

QString uncertainDraftError()
{
    return QStringLiteral("No se pudo confirmar si Google guardó el borrador. Revisá la carpeta Borradores antes de volver a crearlo.");
}

QString uncertainMutationError(const QString &path)
{
    if (path.startsWith(QLatin1String("/gmail/"))) return uncertainDraftError();
    if (path.startsWith(QLatin1String("/tasks/")))
        return QStringLiteral("No se pudo confirmar si Google guardó la tarea. Revisá la lista de tareas antes de volver a crearla.");
    return QStringLiteral("No se pudo confirmar si Google creó el evento. Revisá el calendario antes de volver a crearlo.");
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

ApiResult GoogleWorkspaceApi::createGmailDraft(const QString &accessToken,
                                               const QStringList &grantedScopes,
                                               const QStringList &recipients,
                                               const QStringList &ccRecipients,
                                               const QString &subject,
                                               const QString &body) const
{
    static const QRegularExpression forbiddenHeaderCharacters(
        QStringLiteral("[\\r\\n\\x00-\\x1f\\x7f]"));
    static const QRegularExpression forbiddenBodyCharacters(
        QStringLiteral("[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]"));
    QStringList allRecipients = recipients;
    allRecipients.append(ccRecipients);
    QSet<QString> allRecipientIds;
    bool duplicateAcrossRecipientGroups = false;
    for (const QString &address : allRecipients) {
        const QString normalized = address.trimmed().toLower();
        if (allRecipientIds.contains(normalized)) duplicateAcrossRecipientGroups = true;
        allRecipientIds.insert(normalized);
    }
    if (!validDraftAddresses(recipients, true)
        || !validDraftAddresses(ccRecipients, false)
        || duplicateAcrossRecipientGroups
        || recipients.size() + ccRecipients.size() > 5
        || subject.trimmed().isEmpty() || subject.size() > 300
        || forbiddenHeaderCharacters.match(subject).hasMatch()
        || body.trimmed().isEmpty() || body.size() > 8000
        || forbiddenBodyCharacters.match(body).hasMatch())
        return {false, 0, {}, QStringLiteral("El borrador tiene destinatarios, asunto o cuerpo inválidos o demasiado largos.")};

    QByteArray mime;
    mime += foldedHeader(QStringLiteral("To"), recipients).toUtf8();
    if (!ccRecipients.isEmpty())
        mime += foldedHeader(QStringLiteral("Cc"), ccRecipients).toUtf8();
    mime += foldedHeader(QStringLiteral("Subject"), encodedSubject(subject).split(QLatin1Char(' ')),
                         QStringLiteral(" ")).toUtf8();
    mime += QByteArrayLiteral("MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n");
    mime += foldedBase64Body(body.toUtf8()).toUtf8();
    const QString raw = QString::fromLatin1(mime.toBase64(
        QByteArray::Base64UrlEncoding | QByteArray::OmitTrailingEquals));
    const QJsonObject payload{{QStringLiteral("message"),
                               QJsonObject{{QStringLiteral("raw"), raw}}}};
    return postMutation(Capability::GmailDraft, accessToken, grantedScopes,
                        QStringLiteral("/gmail/v1/users/me/drafts"), payload);
}

ApiResult GoogleWorkspaceApi::createTask(const QString &accessToken,
                                         const QStringList &grantedScopes,
                                         const QString &taskListId,
                                         const QString &title,
                                         const QString &notes,
                                         const QString &dueDate) const
{
    const QString normalizedTitle = title.trimmed();
    const QString normalizedNotes = notes;
    const QString normalizedDueDate = dueDate.trimmed();
    if (!safePathId(taskListId) || normalizedTitle.isEmpty() || normalizedTitle.size() > 1024
        || normalizedNotes.size() > 8192
        || (!normalizedDueDate.isEmpty()
            && (normalizedDueDate.size() != 10
                || !QDate::fromString(normalizedDueDate, Qt::ISODate).isValid()
                || QDate::fromString(normalizedDueDate, Qt::ISODate).toString(Qt::ISODate)
                    != normalizedDueDate)))
        return {false, 0, {}, QStringLiteral("La lista, el título, las notas o la fecha de la tarea son inválidos o demasiado largos.")};

    QJsonObject payload{{QStringLiteral("title"), normalizedTitle}};
    if (!normalizedNotes.trimmed().isEmpty()) payload.insert(QStringLiteral("notes"), normalizedNotes);
    // Google Tasks treats this as an all-day due date and discards the time.
    if (!normalizedDueDate.isEmpty())
        payload.insert(QStringLiteral("due"), normalizedDueDate + QStringLiteral("T00:00:00.000Z"));
    return postMutation(Capability::TasksWrite, accessToken, grantedScopes,
                        QStringLiteral("/tasks/v1/lists/") + taskListId
                            + QStringLiteral("/tasks"), payload);
}

ApiResult GoogleWorkspaceApi::updateTask(const QString &accessToken,
                                         const QStringList &grantedScopes,
                                         const QString &taskListId,
                                         const QString &taskId,
                                         const QJsonObject &fields) const
{
    static const QSet<QString> allowedFields{
        QStringLiteral("title"), QStringLiteral("notes"), QStringLiteral("due_date")};
    if (!safePathId(taskListId) || !safePathId(taskId) || fields.isEmpty())
        return {false, 0, {}, QStringLiteral("La lista, tarea o los campos a actualizar son inválidos.")};
    for (auto it = fields.constBegin(); it != fields.constEnd(); ++it)
        if (!allowedFields.contains(it.key()) || !it.value().isString())
            return {false, 0, {}, QStringLiteral("La actualización contiene un campo desconocido o inválido.")};

    QJsonObject payload;
    if (fields.contains(QStringLiteral("title"))) {
        const QString title = fields.value(QStringLiteral("title")).toString().trimmed();
        if (title.isEmpty() || title.size() > 1024)
            return {false, 0, {}, QStringLiteral("El título de la tarea está vacío o supera 1024 caracteres.")};
        payload.insert(QStringLiteral("title"), title);
    }
    if (fields.contains(QStringLiteral("notes"))) {
        const QString notes = fields.value(QStringLiteral("notes")).toString();
        if (notes.size() > 8192)
            return {false, 0, {}, QStringLiteral("Las notas de la tarea superan 8192 caracteres.")};
        payload.insert(QStringLiteral("notes"), notes);
    }
    if (fields.contains(QStringLiteral("due_date"))) {
        const QString dueDate = fields.value(QStringLiteral("due_date")).toString().trimmed();
        const QDate date = QDate::fromString(dueDate, Qt::ISODate);
        if (dueDate.size() != 10 || !date.isValid() || date.toString(Qt::ISODate) != dueDate)
            return {false, 0, {}, QStringLiteral("La fecha programada debe usar YYYY-MM-DD.")};
        payload.insert(QStringLiteral("due"), dueDate + QStringLiteral("T00:00:00.000Z"));
    }
    return patchMutation(Capability::TasksWrite, accessToken, grantedScopes,
                         QStringLiteral("/tasks/v1/lists/") + taskListId
                             + QStringLiteral("/tasks/") + taskId, payload);
}

ApiResult GoogleWorkspaceApi::completeTask(const QString &accessToken,
                                           const QStringList &grantedScopes,
                                           const QString &taskListId,
                                           const QString &taskId) const
{
    if (!safePathId(taskListId) || !safePathId(taskId))
        return {false, 0, {}, QStringLiteral("La lista o la tarea son inválidas.")};
    return patchMutation(Capability::TasksWrite, accessToken, grantedScopes,
                         QStringLiteral("/tasks/v1/lists/") + taskListId
                             + QStringLiteral("/tasks/") + taskId,
                         QJsonObject{{QStringLiteral("status"), QStringLiteral("completed")}});
}

ApiResult GoogleWorkspaceApi::createCalendarEvent(const QString &accessToken,
                                                  const QStringList &grantedScopes,
                                                  const QString &calendarId,
                                                  const QString &summary,
                                                  const QString &description,
                                                  const QString &startDateTime,
                                                  const QString &endDateTime,
                                                  const QString &timeZone) const
{
    const QString normalizedSummary = summary.trimmed();
    const QString normalizedTimeZone = timeZone.trimmed();
    const QDateTime start = parseDateTime(startDateTime);
    const QDateTime end = parseDateTime(endDateTime);
    const QTimeZone zone(normalizedTimeZone.toUtf8());
    const bool startOffsetMatchesZone = zone.isValid() && start.isValid()
        && start.toTimeZone(zone).offsetFromUtc() == start.offsetFromUtc();
    const bool endOffsetMatchesZone = zone.isValid() && end.isValid()
        && end.toTimeZone(zone).offsetFromUtc() == end.offsetFromUtc();
    if (!safePathId(calendarId) || normalizedSummary.isEmpty() || normalizedSummary.size() > 1024
        || description.size() > 8192 || startDateTime.size() > 64 || endDateTime.size() > 64
        || !explicitDateTime(startDateTime) || !explicitDateTime(endDateTime)
        || !start.isValid() || !end.isValid() || start >= end
        || normalizedTimeZone.isEmpty() || normalizedTimeZone.size() > 128 || !zone.isValid()
        || !startOffsetMatchesZone || !endOffsetMatchesZone)
        return {false, 0, {}, QStringLiteral("El calendario, título, intervalo o zona horaria del evento son inválidos o demasiado largos.")};

    const QJsonObject payload{
        {QStringLiteral("summary"), normalizedSummary},
        {QStringLiteral("description"), description},
        {QStringLiteral("start"), QJsonObject{
             {QStringLiteral("dateTime"), startDateTime},
             {QStringLiteral("timeZone"), normalizedTimeZone}}},
        {QStringLiteral("end"), QJsonObject{
             {QStringLiteral("dateTime"), endDateTime},
             {QStringLiteral("timeZone"), normalizedTimeZone}}}};
    return postMutation(Capability::CalendarEventWrite, accessToken, grantedScopes,
                        QStringLiteral("/calendar/v3/calendars/") + calendarId
                            + QStringLiteral("/events"), payload);
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

ApiResult GoogleWorkspaceApi::postMutation(Capability capability, const QString &accessToken,
                                           const QStringList &grantedScopes,
                                           const QString &path,
                                           const QJsonObject &body) const
{
    // Mutations intentionally never use the transient retry loop: a timeout or
    // 5xx may happen after Google has already committed the side effect.
    return sendOnce(capability, accessToken, grantedScopes, QByteArrayLiteral("POST"),
                    path, {}, QJsonDocument(body).toJson(QJsonDocument::Compact), true);
}

ApiResult GoogleWorkspaceApi::patchMutation(Capability capability, const QString &accessToken,
                                            const QStringList &grantedScopes,
                                            const QString &path,
                                            const QJsonObject &body) const
{
    // PATCH muta estado externo, por lo que un timeout/5xx queda incierto y
    // no se repite automáticamente.
    return sendOnce(capability, accessToken, grantedScopes, QByteArrayLiteral("PATCH"),
                    path, {}, QJsonDocument(body).toJson(QJsonDocument::Compact), true);
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
                                       const QByteArray &body, bool externalMutation) const
{
    if (m_cancellationFlag && m_cancellationFlag->load(std::memory_order_relaxed))
        return {false, 0, {}, QStringLiteral("La solicitud a Google fue cancelada.")};
    if (accessToken.trimmed().isEmpty())
        return {false, 0, {}, QStringLiteral("Conectá una cuenta Google antes de consultar.")};
    if (!grantsCapability(capability, grantedScopes))
        return {false, 0, {}, QStringLiteral("La cuenta Google no concedió el permiso requerido para esta función.")};

    QUrl url = m_apiBase;
    if (m_apiBase == kGoogleApiBase) {
        if (path.startsWith(QLatin1String("/gmail/")))
            url.setHost(QStringLiteral("gmail.googleapis.com"));
        else if (path.startsWith(QLatin1String("/tasks/")))
            url.setHost(QStringLiteral("tasks.googleapis.com"));
    }
    url.setPath(path);
    url.setQuery(query);
    QNetworkRequest request(url);
    request.setRawHeader(QByteArrayLiteral("Authorization"),
                         QByteArrayLiteral("Bearer ") + accessToken.toUtf8());
    request.setRawHeader(QByteArrayLiteral("Accept"), QByteArrayLiteral("application/json"));
    if (method != QByteArrayLiteral("GET"))
        request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute,
                         QNetworkRequest::ManualRedirectPolicy);
    request.setTransferTimeout(15000);

    QNetworkAccessManager manager;
    QNetworkReply *reply = method == QByteArrayLiteral("GET")
        ? manager.get(request)
        : method == QByteArrayLiteral("POST") ? manager.post(request, body)
                                                : manager.sendCustomRequest(request, method, body);
    QEventLoop loop;
    QTimer timeout;
    timeout.setSingleShot(true);
    QTimer cancellationCheck;
    cancellationCheck.setInterval(20);
    QByteArray payload;
    bool tooLarge = false;
    bool timedOut = false;
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
        timedOut = true;
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

    if (tooLarge && externalMutation && status >= 200 && status < 300)
        return {false, status, {}, uncertainMutationError(path)};
    if (tooLarge)
        return {false, status, {}, QStringLiteral("La respuesta de Google superó el límite de 4 MiB.")};
    if ((cancelled || timedOut
         || (networkError != QNetworkReply::NoError
             && (status == 0 || status >= 500))) && externalMutation)
        return {false, status, {}, uncertainMutationError(path)};
    if (cancelled)
        return {false, status, {}, QStringLiteral("La solicitud a Google fue cancelada.")};
    if (timedOut)
        return {false, status, {}, QStringLiteral("La solicitud a Google venció por tiempo.")};
    if (externalMutation && status >= 500 && status <= 599)
        return {false, status, {}, uncertainMutationError(path), retryAfterMs};
    if (timeout.isActive()) timeout.stop();
    if (status == 401 || status == 403 || status == 404 || status == 429 || status >= 500)
        return {false, status, {}, apiError(status), retryAfterMs};
    if (networkError != QNetworkReply::NoError)
        return {false, status, {}, QStringLiteral("No se pudo conectar con Google. Revisá la red y reintentá.")};
    if (status < 200 || status >= 300)
        return {false, status, {}, apiError(status)};

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(payload, &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        if (externalMutation && status >= 200 && status < 300)
            return {false, status, {}, uncertainMutationError(path)};
        return {false, status, {}, QStringLiteral("Google devolvió una respuesta JSON inválida.")};
    }
    return {true, status, document.object(), {}};
}

} // namespace GoogleWorkspaceSecurity
