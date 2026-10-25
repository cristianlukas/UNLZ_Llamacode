#include "AstraStrataConfig.h"

#include <QJsonArray>
#include <QJsonValue>

QJsonObject AstraStrataConfig::withMaxContext(const QJsonObject &config,
                                               int contextTokens,
                                               QString *error)
{
    auto fail = [error](const QString &message) {
        if (error) *error = message;
        return QJsonObject{};
    };
    if (contextTokens <= 0)
        return fail(QStringLiteral("El contexto debe ser mayor que cero."));

    QJsonArray args = config.value(QStringLiteral("args")).toArray();
    if (args.isEmpty())
        return fail(QStringLiteral("El JSON de Strata no contiene argumentos."));

    int matches = 0;
    for (qsizetype i = 0; i < args.size(); ++i) {
        const QString arg = args.at(i).toString();
        if (arg == QLatin1String("--max-context")) {
            if (i + 1 >= args.size() || args.at(i + 1).toString().toInt() <= 0)
                return fail(QStringLiteral("El argumento --max-context no tiene un valor válido."));
            args[i + 1] = QString::number(contextTokens);
            ++matches;
        } else if (arg.startsWith(QStringLiteral("--max-context="))) {
            if (arg.mid(QStringLiteral("--max-context=").size()).toInt() <= 0)
                return fail(QStringLiteral("El argumento --max-context no tiene un valor válido."));
            args[i] = QStringLiteral("--max-context=%1").arg(contextTokens);
            ++matches;
        }
    }
    if (matches != 1)
        return fail(matches == 0
            ? QStringLiteral("El JSON de Strata no declara --max-context.")
            : QStringLiteral("El JSON de Strata declara --max-context más de una vez."));

    QJsonObject result = config;
    result.insert(QStringLiteral("args"), args);
    if (error) error->clear();
    return result;
}
