#pragma once

#include "GoogleWorkspaceSecurity.h"

#include <QJsonObject>
#include <QString>
#include <QUrl>
#include <atomic>

namespace GoogleWorkspaceSecurity {

struct ApiResult {
    bool ok = false;
    int httpStatus = 0;
    QJsonObject data;
    QString error;
    int retryAfterMs = 0;
};

// Google Workspace REST client. Mutations have a separate no-retry path and
// never log bearer tokens or returned content.
class GoogleWorkspaceApi
{
public:
    GoogleWorkspaceApi();

    ApiResult searchGmail(const QString &accessToken, const QStringList &grantedScopes,
                          const QString &query, const QString &pageToken = QString(),
                          int maxResults = 20) const;
    ApiResult readGmailMessage(const QString &accessToken, const QStringList &grantedScopes,
                               const QString &messageId) const;
    ApiResult createGmailDraft(const QString &accessToken, const QStringList &grantedScopes,
                               const QStringList &recipients, const QStringList &ccRecipients,
                               const QString &subject, const QString &body) const;
    ApiResult createTask(const QString &accessToken, const QStringList &grantedScopes,
                         const QString &taskListId, const QString &title,
                         const QString &notes, const QString &dueDate) const;
    ApiResult updateTask(const QString &accessToken, const QStringList &grantedScopes,
                         const QString &taskListId, const QString &taskId,
                         const QJsonObject &fields) const;
    ApiResult completeTask(const QString &accessToken, const QStringList &grantedScopes,
                           const QString &taskListId, const QString &taskId) const;
    ApiResult createCalendarEvent(const QString &accessToken,
                                  const QStringList &grantedScopes,
                                  const QString &calendarId, const QString &summary,
                                  const QString &description, const QString &startDateTime,
                                  const QString &endDateTime, const QString &timeZone) const;
    ApiResult listCalendarEvents(const QString &accessToken, const QStringList &grantedScopes,
                                 const QString &calendarId, const QString &timeMin,
                                 const QString &timeMax, int maxResults = 25) const;
    ApiResult queryCalendarFreeBusy(const QString &accessToken, const QStringList &grantedScopes,
                                    const QStringList &calendarIds, const QString &timeMin,
                                    const QString &timeMax) const;
    ApiResult listTaskLists(const QString &accessToken, const QStringList &grantedScopes,
                            int maxResults = 50) const;
    ApiResult listTasks(const QString &accessToken, const QStringList &grantedScopes,
                        const QString &taskListId, int maxResults = 50) const;

    // Test-only base URL; production instances remain pinned to Google APIs.
    bool setApiBaseForTests(const QUrl &url);
    void setCancellationFlag(const std::atomic_bool *flag) { m_cancellationFlag = flag; }

private:
    ApiResult get(Capability capability, const QString &accessToken,
                  const QStringList &grantedScopes, const QString &path,
                  const QUrlQuery &query) const;
    ApiResult post(Capability capability, const QString &accessToken,
                   const QStringList &grantedScopes, const QString &path,
                   const QJsonObject &body) const;
    ApiResult postMutation(Capability capability, const QString &accessToken,
                           const QStringList &grantedScopes, const QString &path,
                           const QJsonObject &body) const;
    ApiResult patchMutation(Capability capability, const QString &accessToken,
                            const QStringList &grantedScopes, const QString &path,
                            const QJsonObject &body) const;
    ApiResult send(Capability capability, const QString &accessToken,
                   const QStringList &grantedScopes, const QByteArray &method,
                   const QString &path, const QUrlQuery &query,
                   const QByteArray &body) const;
    ApiResult sendOnce(Capability capability, const QString &accessToken,
                       const QStringList &grantedScopes, const QByteArray &method,
                       const QString &path, const QUrlQuery &query,
                       const QByteArray &body, bool externalMutation = false) const;
    QUrl m_apiBase;
    const std::atomic_bool *m_cancellationFlag = nullptr;
};

} // namespace GoogleWorkspaceSecurity
