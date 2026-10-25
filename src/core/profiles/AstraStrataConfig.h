#pragma once

#include <QJsonObject>
#include <QString>

namespace AstraStrataConfig {

// Returns a copy with exactly one --max-context value changed. Invalid or
// ambiguous configurations are rejected so a context variant cannot silently
// keep running at the source profile's limit.
QJsonObject withMaxContext(const QJsonObject &config, int contextTokens,
                           QString *error = nullptr);

} // namespace AstraStrataConfig
