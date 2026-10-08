#pragma once

#include <QJsonObject>
#include <QString>

namespace StartupDiagnostics {

// Call as the first operation in main(), before constructing QApplication.
void initializeEarly(const QString &executablePath = {}, bool forceExpanded = false);
bool expandedEnabled();
void setExpandedEnabled(bool enabled);
QString expandedLogPath();
qint64 elapsedMs();
void record(const QString &event, const QJsonObject &details = {});

} // namespace StartupDiagnostics
