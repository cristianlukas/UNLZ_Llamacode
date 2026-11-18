#include <QtTest>

#include "core/google/GoogleWorkspaceApi.h"

#include <QHostAddress>
#include <QStandardPaths>
#include <QTimer>
#include <QElapsedTimer>
#include <QTcpServer>
#include <QTcpSocket>
#include <atomic>

using namespace GoogleWorkspaceSecurity;

class ApiEndpointStub : public QTcpServer
{
    Q_OBJECT
public:
    explicit ApiEndpointStub(QObject *parent = nullptr) : QTcpServer(parent)
    {
        connect(this, &QTcpServer::newConnection, this, [this]() {
            while (hasPendingConnections()) {
                QTcpSocket *socket = nextPendingConnection();
                connect(socket, &QTcpSocket::readyRead, this, [this, socket]() {
                    if (socket->property("responded").toBool()) return;
                    QByteArray request = socket->property("requestData").toByteArray();
                    request += socket->readAll();
                    socket->setProperty("requestData", request);
                    const qsizetype headerEnd = request.indexOf(QByteArrayLiteral("\r\n\r\n"));
                    if (headerEnd < 0) return;
                    int contentLength = 0;
                    const QList<QByteArray> headers = request.left(headerEnd).split('\n');
                    for (QByteArray header : headers) {
                        header = header.trimmed();
                        if (header.toLower().startsWith(QByteArrayLiteral("content-length:"))) {
                            contentLength = header.mid(header.indexOf(':') + 1).trimmed().toInt();
                            break;
                        }
                    }
                    const qsizetype fullLength = headerEnd + 4 + contentLength;
                    if (request.size() < fullLength) return;
                    socket->setProperty("responded", true);
                    m_lastRequest = request.left(fullLength);
                    const int responseIndex = m_responseIndex++;
                    const int lastResponseIndex = static_cast<int>(m_responses.size()) - 1;
                    const QPair<int, QByteArray> selected = m_responses.isEmpty()
                        ? qMakePair(m_status, m_response)
                        : m_responses.at(qMin(responseIndex, lastResponseIndex));
                    const int status = selected.first;
                    const QByteArray responseBody = selected.second;
                    const QByteArray reason = status == 200 ? QByteArrayLiteral("OK")
                        : status == 503 ? QByteArrayLiteral("Service Unavailable")
                        : status == 429 ? QByteArrayLiteral("Too Many Requests")
                                        : QByteArrayLiteral("Unauthorized");
                    const QByteArray response = QByteArrayLiteral("HTTP/1.1 ")
                        + QByteArray::number(status) + ' ' + reason
                        + QByteArrayLiteral("\r\nContent-Type: application/json")
                        + (m_retryAfter.isEmpty() ? QByteArray{}
                           : QByteArrayLiteral("\r\nRetry-After: ") + m_retryAfter)
                        + QByteArrayLiteral("\r\nConnection: close\r\nContent-Length: ")
                        + QByteArray::number(responseBody.size()) + QByteArrayLiteral("\r\n\r\n") + responseBody;
                    ++m_requestCount;
                    const auto respond = [this, socket, response]() {
                        if (!socket || socket->state() == QAbstractSocket::UnconnectedState) return;
                        socket->write(response);
                        socket->disconnectFromHost();
                        emit requestReceived();
                    };
                    if (m_responseDelayMs > 0)
                        QTimer::singleShot(m_responseDelayMs, socket, respond);
                    else
                        respond();
                });
                connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
            }
        });
    }

    void setResponse(int status, const QByteArray &body)
    { m_status = status; m_response = body; m_responses.clear(); m_responseIndex = 0; m_requestCount = 0; }
    void setRetryAfter(const QByteArray &value) { m_retryAfter = value; }
    void setResponseSequence(const QList<QPair<int, QByteArray>> &responses)
    { m_responses = responses; m_responseIndex = 0; m_requestCount = 0; }
    void setResponseDelay(int milliseconds) { m_responseDelayMs = milliseconds; }
    QByteArray lastRequest() const { return m_lastRequest; }
    int requestCount() const { return m_requestCount; }

signals:
    void requestReceived();

private:
    int m_status = 200;
    int m_responseDelayMs = 0;
    QByteArray m_response = QByteArrayLiteral("{}");
    QByteArray m_retryAfter;
    QList<QPair<int, QByteArray>> m_responses;
    int m_responseIndex = 0;
    int m_requestCount = 0;
    QByteArray m_lastRequest;
};

class GoogleWorkspaceApiTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void scopesAreCheckedBeforeNetworkRequest();
    void gmailSearchUsesSafeRequestAndPagination();
    void calendarAndTasksBuildReadOnlyRequests();
    void freeBusyUsesLeastPrivilegeAndPostsBoundedRequest();
    void apiRequestCanBeCancelled();
    void retriesTransientReadFailuresOnceAndCanCancelBackoff();
    void rejectsUnsafeIdsAndUnzonedTimes();
    void mapsAuthorizationErrorsWithoutReturningBody();

private:
    static QUrl baseFor(const ApiEndpointStub &server);
};

void GoogleWorkspaceApiTests::initTestCase()
{
    QStandardPaths::setTestModeEnabled(true);
}

QUrl GoogleWorkspaceApiTests::baseFor(const ApiEndpointStub &server)
{
    return QUrl(QStringLiteral("http://127.0.0.1:%1").arg(server.serverPort()));
}

void GoogleWorkspaceApiTests::scopesAreCheckedBeforeNetworkRequest()
{
    ApiEndpointStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));
    GoogleWorkspaceApi api;
    QVERIFY(api.setApiBaseForTests(baseFor(server)));

    const ApiResult result = api.searchGmail(QStringLiteral("access-token"),
        scopesFor(Capability::TasksRead), QStringLiteral("is:unread"));
    QVERIFY(!result.ok);
    QVERIFY(result.error.contains(QStringLiteral("permiso")));
    QVERIFY(server.lastRequest().isEmpty());
}

void GoogleWorkspaceApiTests::gmailSearchUsesSafeRequestAndPagination()
{
    ApiEndpointStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));
    server.setResponse(200, QByteArrayLiteral("{\"messages\":[{\"id\":\"m-1\"}],\"nextPageToken\":\"p/2==\"}"));
    GoogleWorkspaceApi api;
    QVERIFY(api.setApiBaseForTests(baseFor(server)));

    const ApiResult result = api.searchGmail(QStringLiteral("access-token"),
        scopesFor(Capability::GmailRead), QStringLiteral("from:ada@example.com newer_than:7d"),
        QStringLiteral("p/1=="), 10);
    QVERIFY2(result.ok, qPrintable(result.error));
    QCOMPARE(result.data.value(QStringLiteral("messages")).toArray().size(), 1);
    QVERIFY(result.data.value(QStringLiteral("nextPageToken")).toString().contains(QLatin1Char('/')));
    const QByteArray request = server.lastRequest();
    const QByteArray normalizedRequest = request.toLower();
    QVERIFY(request.startsWith(QByteArrayLiteral("GET /gmail/v1/users/me/messages?")));
    QVERIFY(normalizedRequest.contains(QByteArrayLiteral("authorization: bearer access-token")));
    const QByteArray requestLine = request.left(request.indexOf(QByteArrayLiteral("\r\n")));
    const QList<QByteArray> requestParts = requestLine.split(' ');
    QVERIFY(requestParts.size() >= 2);
    const QUrl requestUrl(QStringLiteral("http://localhost")
                          + QString::fromLatin1(requestParts.at(1)));
    const QUrlQuery query(requestUrl);
    QCOMPARE(query.queryItemValue(QStringLiteral("q")),
             QStringLiteral("from:ada@example.com newer_than:7d"));
    QCOMPARE(query.queryItemValue(QStringLiteral("pageToken")), QStringLiteral("p/1=="));
}

void GoogleWorkspaceApiTests::calendarAndTasksBuildReadOnlyRequests()
{
    ApiEndpointStub calendarServer;
    QVERIFY(calendarServer.listen(QHostAddress::LocalHost, 0));
    calendarServer.setResponse(200, QByteArrayLiteral("{\"items\":[]}"));
    GoogleWorkspaceApi calendarApi;
    QVERIFY(calendarApi.setApiBaseForTests(baseFor(calendarServer)));
    const ApiResult events = calendarApi.listCalendarEvents(
        QStringLiteral("calendar-token"), scopesFor(Capability::CalendarEventsRead),
        QStringLiteral("primary"), QStringLiteral("2026-11-17T00:00:00-03:00"),
        QStringLiteral("2026-11-18T00:00:00-03:00"));
    QVERIFY2(events.ok, qPrintable(events.error));
    QVERIFY(calendarServer.lastRequest().startsWith(
        QByteArrayLiteral("GET /calendar/v3/calendars/primary/events?")));
    QVERIFY(calendarServer.lastRequest().contains(QByteArrayLiteral("singleEvents=true")));
    QVERIFY(calendarServer.lastRequest().toLower().contains(
        QByteArrayLiteral("authorization: bearer calendar-token")));

    ApiEndpointStub tasksServer;
    QVERIFY(tasksServer.listen(QHostAddress::LocalHost, 0));
    tasksServer.setResponse(200, QByteArrayLiteral("{\"items\":[{\"id\":\"t1\"}]}"));
    GoogleWorkspaceApi tasksApi;
    QVERIFY(tasksApi.setApiBaseForTests(baseFor(tasksServer)));
    const ApiResult tasks = tasksApi.listTasks(QStringLiteral("tasks-token"),
        scopesFor(Capability::TasksRead), QStringLiteral("list_1"));
    QVERIFY2(tasks.ok, qPrintable(tasks.error));
    QVERIFY(tasksServer.lastRequest().startsWith(QByteArrayLiteral("GET /tasks/v1/lists/list_1/tasks?")));
    QVERIFY(tasksServer.lastRequest().contains(QByteArrayLiteral("showCompleted=true")));
}

void GoogleWorkspaceApiTests::freeBusyUsesLeastPrivilegeAndPostsBoundedRequest()
{
    ApiEndpointStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));
    server.setResponse(200, QByteArrayLiteral(
        "{\"calendars\":{\"primary\":{\"busy\":[{\"start\":\"2026-11-18T10:00:00-03:00\","
        "\"end\":\"2026-11-18T11:00:00-03:00\"}]},\"team@example.com\":{\"busy\":[]}}}"));
    GoogleWorkspaceApi api;
    QVERIFY(api.setApiBaseForTests(baseFor(server)));
    const ApiResult result = api.queryCalendarFreeBusy(
        QStringLiteral("calendar-token"), scopesFor(Capability::CalendarFreeBusy),
        {QStringLiteral("primary"), QStringLiteral("team@example.com")},
        QStringLiteral("2026-11-18T09:00:00-03:00"),
        QStringLiteral("2026-11-18T12:00:00-03:00"));
    QVERIFY2(result.ok, qPrintable(result.error));
    QCOMPARE(result.data.value(QStringLiteral("calendars")).toObject()
                 .value(QStringLiteral("primary")).toObject()
                 .value(QStringLiteral("busy")).toArray().size(), 1);
    const QByteArray request = server.lastRequest();
    QVERIFY(request.startsWith(QByteArrayLiteral("POST /calendar/v3/freeBusy ")));
    QVERIFY(request.toLower().contains(QByteArrayLiteral("authorization: bearer calendar-token")));
    QVERIFY(request.toLower().contains(QByteArrayLiteral("content-type: application/json")));
    const qsizetype bodyStart = request.indexOf(QByteArrayLiteral("\r\n\r\n")) + 4;
    const QJsonObject body = QJsonDocument::fromJson(request.mid(bodyStart)).object();
    QCOMPARE(body.value(QStringLiteral("timeMin")).toString(),
             QStringLiteral("2026-11-18T09:00:00-03:00"));
    QCOMPARE(body.value(QStringLiteral("timeMax")).toString(),
             QStringLiteral("2026-11-18T12:00:00-03:00"));
    QCOMPARE(body.value(QStringLiteral("calendarExpansionMax")).toInt(), 2);
    QCOMPARE(body.value(QStringLiteral("items")).toArray().at(1).toObject()
                 .value(QStringLiteral("id")).toString(), QStringLiteral("team@example.com"));

    ApiEndpointStub deniedServer;
    QVERIFY(deniedServer.listen(QHostAddress::LocalHost, 0));
    GoogleWorkspaceApi deniedApi;
    QVERIFY(deniedApi.setApiBaseForTests(baseFor(deniedServer)));
    const ApiResult denied = deniedApi.queryCalendarFreeBusy(
        QStringLiteral("calendar-token"), scopesFor(Capability::CalendarEventsRead),
        {QStringLiteral("primary")}, QStringLiteral("2026-11-18T09:00:00Z"),
        QStringLiteral("2026-11-18T10:00:00Z"));
    QVERIFY(!denied.ok);
    QVERIFY(deniedServer.lastRequest().isEmpty());
}

void GoogleWorkspaceApiTests::apiRequestCanBeCancelled()
{
    ApiEndpointStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));
    server.setResponseDelay(2000);
    GoogleWorkspaceApi api;
    QVERIFY(api.setApiBaseForTests(baseFor(server)));
    std::atomic_bool cancelled{false};
    api.setCancellationFlag(&cancelled);
    QTimer::singleShot(100, [&cancelled]() {
        cancelled.store(true, std::memory_order_relaxed);
    });
    QElapsedTimer elapsed;
    elapsed.start();
    const ApiResult result = api.searchGmail(QStringLiteral("calendar-token"),
        scopesFor(Capability::GmailRead), QStringLiteral("is:unread"));
    QVERIFY(!result.ok);
    QVERIFY(result.error.contains(QStringLiteral("cancelada")));
    QVERIFY(!server.lastRequest().isEmpty());
    QVERIFY2(elapsed.elapsed() < 1000, "The API call waited for its delayed response instead of cancelling");
}

void GoogleWorkspaceApiTests::retriesTransientReadFailuresOnceAndCanCancelBackoff()
{
    ApiEndpointStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));
    server.setResponseSequence({
        {503, QByteArrayLiteral("{}")},
        {200, QByteArrayLiteral("{\"messages\":[]}")}});
    GoogleWorkspaceApi api;
    QVERIFY(api.setApiBaseForTests(baseFor(server)));
    const ApiResult result = api.searchGmail(QStringLiteral("token"),
        scopesFor(Capability::GmailRead), QStringLiteral("is:unread"));
    QVERIFY2(result.ok, qPrintable(result.error));
    QCOMPARE(server.requestCount(), 2);

    ApiEndpointStub cancelledServer;
    QVERIFY(cancelledServer.listen(QHostAddress::LocalHost, 0));
    cancelledServer.setResponseSequence({
        {503, QByteArrayLiteral("{}")},
        {200, QByteArrayLiteral("{\"messages\":[]}")}});
    GoogleWorkspaceApi cancelledApi;
    QVERIFY(cancelledApi.setApiBaseForTests(baseFor(cancelledServer)));
    std::atomic_bool cancelled{false};
    cancelledApi.setCancellationFlag(&cancelled);
    QTimer::singleShot(100, [&cancelled]() {
        cancelled.store(true, std::memory_order_relaxed);
    });
    const ApiResult cancelledResult = cancelledApi.searchGmail(QStringLiteral("token"),
        scopesFor(Capability::GmailRead), QStringLiteral("is:unread"));
    QVERIFY(!cancelledResult.ok);
    QVERIFY(cancelledResult.error.contains(QStringLiteral("cancelada")));
    QCOMPARE(cancelledServer.requestCount(), 1);

    ApiEndpointStub exhaustedServer;
    QVERIFY(exhaustedServer.listen(QHostAddress::LocalHost, 0));
    exhaustedServer.setResponse(503, QByteArrayLiteral("{}"));
    GoogleWorkspaceApi exhaustedApi;
    QVERIFY(exhaustedApi.setApiBaseForTests(baseFor(exhaustedServer)));
    const ApiResult exhausted = exhaustedApi.searchGmail(QStringLiteral("token"),
        scopesFor(Capability::GmailRead), QStringLiteral("is:unread"));
    QVERIFY(!exhausted.ok);
    QCOMPARE(exhausted.httpStatus, 503);
    QCOMPARE(exhaustedServer.requestCount(), 2);

    ApiEndpointStub deferredServer;
    QVERIFY(deferredServer.listen(QHostAddress::LocalHost, 0));
    deferredServer.setResponse(503, QByteArrayLiteral("{}"));
    deferredServer.setRetryAfter(QByteArrayLiteral("2"));
    GoogleWorkspaceApi deferredApi;
    QVERIFY(deferredApi.setApiBaseForTests(baseFor(deferredServer)));
    const ApiResult deferred = deferredApi.searchGmail(QStringLiteral("token"),
        scopesFor(Capability::GmailRead), QStringLiteral("is:unread"));
    QVERIFY(!deferred.ok);
    QCOMPARE(deferred.httpStatus, 503);
    QCOMPARE(deferredServer.requestCount(), 1);
}

void GoogleWorkspaceApiTests::rejectsUnsafeIdsAndUnzonedTimes()
{
    GoogleWorkspaceApi api;
    const QStringList grants = scopesFor(Capability::CalendarEventsRead);
    QVERIFY(!api.listCalendarEvents(QStringLiteral("token"), grants, QStringLiteral("../other"),
        QStringLiteral("2026-11-17T00:00:00Z"), QStringLiteral("2026-11-18T00:00:00Z")).ok);
    QVERIFY(!api.listCalendarEvents(QStringLiteral("token"), grants, QStringLiteral("primary"),
        QStringLiteral("2026-11-17T00:00:00"), QStringLiteral("2026-11-18T00:00:00Z")).ok);
    QVERIFY(!api.listTasks(QStringLiteral("token"), scopesFor(Capability::TasksRead),
                           QStringLiteral("../../settings")).ok);
    QVERIFY(!api.readGmailMessage(QStringLiteral("token"), scopesFor(Capability::GmailRead),
                                  QStringLiteral("id/../../other")).ok);
    const QStringList validCalendars{QStringLiteral("primary")};
    const QString timeMin = QStringLiteral("2026-11-17T09:00:00Z");
    const QString timeMax = QStringLiteral("2026-11-17T10:00:00Z");
    const QStringList freeBusyGrants = scopesFor(Capability::CalendarFreeBusy);
    QVERIFY(!api.queryCalendarFreeBusy(QStringLiteral("token"), freeBusyGrants,
        {QStringLiteral("../other")}, timeMin, timeMax).ok);
    QVERIFY(!api.queryCalendarFreeBusy(QStringLiteral("token"), freeBusyGrants,
        {QStringLiteral("primary"), QStringLiteral("primary")}, timeMin, timeMax).ok);
    QVERIFY(!api.queryCalendarFreeBusy(QStringLiteral("token"), freeBusyGrants,
        validCalendars, timeMax, timeMin).ok);
    QVERIFY(!api.queryCalendarFreeBusy(QStringLiteral("token"), freeBusyGrants,
        {}, timeMin, timeMax).ok);
    QStringList tooManyCalendars;
    for (int i = 0; i < 51; ++i) tooManyCalendars << QStringLiteral("cal-%1").arg(i);
    QVERIFY(!api.queryCalendarFreeBusy(QStringLiteral("token"), freeBusyGrants,
        tooManyCalendars, timeMin, timeMax).ok);
}

void GoogleWorkspaceApiTests::mapsAuthorizationErrorsWithoutReturningBody()
{
    ApiEndpointStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost, 0));
    server.setResponse(401, QByteArrayLiteral("{\"error\":\"secret server detail\"}"));
    GoogleWorkspaceApi api;
    QVERIFY(api.setApiBaseForTests(baseFor(server)));
    const ApiResult result = api.searchGmail(QStringLiteral("expired-token"),
        scopesFor(Capability::GmailRead), QStringLiteral("is:unread"));
    QVERIFY(!result.ok);
    QCOMPARE(result.httpStatus, 401);
    QVERIFY(result.error.contains(QStringLiteral("venció")));
    QVERIFY(!result.error.contains(QStringLiteral("secret server detail")));
    QVERIFY(result.data.isEmpty());
}

QTEST_MAIN(GoogleWorkspaceApiTests)
#include "test_google_workspace_api.moc"
