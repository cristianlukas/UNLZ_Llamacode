#pragma once

#include <QHostAddress>
#include <QString>
#include <QUrl>

namespace WebSearchConfig {

inline QString plumbSearchUrl()
{
    return qEnvironmentVariable("LLAMACODE_PLUMBSEARCH_URL").trimmed();
}

inline QString searxngUrl()
{
    return qEnvironmentVariable("LLAMACODE_SEARXNG_URL").trimmed();
}

inline QString configuredEndpoint()
{
    const QString plumb = plumbSearchUrl();
    return plumb.isEmpty() ? searxngUrl() : plumb;
}

inline bool plumbSearchSelected()
{
    return !plumbSearchUrl().isEmpty();
}

inline bool hasInvalidMode()
{
    const QString mode = qEnvironmentVariable("LLAMACODE_WEB_SEARCH_MODE")
                             .trimmed().toLower();
    return !mode.isEmpty() && mode != QLatin1String("auto")
        && mode != QLatin1String("default") && mode != QLatin1String("local-only");
}

inline bool localOnly()
{
    const QString mode = qEnvironmentVariable("LLAMACODE_WEB_SEARCH_MODE")
                             .trimmed().toLower();
    // PlumbSearch is deliberately treated as a local-only provider: if it is
    // unavailable, a query must not silently escape to a public search engine.
    return mode == QLatin1String("local-only") || plumbSearchSelected();
}

inline bool isLoopbackEndpoint(const QString &endpoint)
{
    const QUrl url(endpoint.trimmed());
    if (!url.isValid() || (url.scheme() != QLatin1String("http")
                           && url.scheme() != QLatin1String("https"))
        || url.host().isEmpty() || !url.userInfo().isEmpty())
        return false;

    const QString host = url.host().toLower();
    if (host == QLatin1String("localhost") || host.endsWith(QLatin1String(".localhost")))
        return true;

    QHostAddress address;
    return address.setAddress(host) && address.isLoopback();
}

} // namespace WebSearchConfig
