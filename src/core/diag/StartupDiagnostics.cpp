#include "StartupDiagnostics.h"

#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QMutex>
#include <QMutexLocker>
#include <QSettings>
#include <QStandardPaths>
#include <QTextStream>
#include <QThread>
#include <QSysInfo>
#include <QElapsedTimer>
#include <QtMessageHandler>
#include <cstdio>
#include <cstdlib>
#include <atomic>

namespace {
QFile s_regularLog;
QFile s_expandedLog;
QTextStream s_regularStream;
QElapsedTimer s_clock;
QMutex s_mutex;
bool s_initialized = false;
std::atomic_bool s_expanded{false};
constexpr qint64 kExpandedLogMaxBytes = 16 * 1024 * 1024;

QString appDataDirectory()
{
    return QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
}

void rotateExpandedLog()
{
    const QString path = appDataDirectory() + QStringLiteral("/llamacode-expanded.jsonl");
    QFile current(path);
    if (current.exists() && current.size() >= kExpandedLogMaxBytes) {
        QFile::remove(path + QStringLiteral(".1"));
        current.rename(path + QStringLiteral(".1"));
    }
}

QJsonObject baseRecord(const QString &event)
{
    return {{QStringLiteral("timestampUtc"),
             QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
            {QStringLiteral("elapsedMs"), s_clock.isValid() ? s_clock.elapsed() : 0},
            {QStringLiteral("pid"), QCoreApplication::applicationPid()},
            {QStringLiteral("thread"), QString::number(
                 reinterpret_cast<quintptr>(QThread::currentThreadId()), 16)},
            {QStringLiteral("event"), event}};
}

void appendExpanded(QJsonObject record)
{
    if (!s_expanded || !s_expandedLog.isOpen())
        return;
    const QByteArray line = QJsonDocument(record).toJson(QJsonDocument::Compact) + '\n';
    s_expandedLog.write(line);
    s_expandedLog.flush();
}

void messageHandler(QtMsgType type, const QMessageLogContext &context, const QString &message)
{
    const char *level = "DEBUG";
    if (type == QtInfoMsg) level = "INFO";
    else if (type == QtWarningMsg) level = "WARN";
    else if (type == QtCriticalMsg) level = "ERROR";
    else if (type == QtFatalMsg) level = "FATAL";

    QMutexLocker locker(&s_mutex);
    const QString line = QStringLiteral("[%1] [+%2 ms] [%3] %4")
        .arg(QDateTime::currentDateTime().toString(Qt::ISODateWithMs))
        .arg(s_clock.isValid() ? s_clock.elapsed() : 0)
        .arg(QLatin1String(level), message);
    if (s_regularLog.isOpen()) {
        s_regularStream << line << '\n';
        s_regularStream.flush();
    }

    if (s_expanded && s_expandedLog.isOpen()) {
        QJsonObject record = baseRecord(QStringLiteral("qt_message"));
        record.insert(QStringLiteral("level"), QLatin1String(level));
        record.insert(QStringLiteral("message"), message);
        if (context.category && *context.category)
            record.insert(QStringLiteral("category"), QString::fromUtf8(context.category));
        if (context.file && *context.file)
            record.insert(QStringLiteral("file"), QString::fromUtf8(context.file));
        if (context.function && *context.function)
            record.insert(QStringLiteral("function"), QString::fromUtf8(context.function));
        if (context.line > 0)
            record.insert(QStringLiteral("line"), context.line);
        appendExpanded(std::move(record));
    }

    FILE *stream = type == QtWarningMsg || type == QtCriticalMsg || type == QtFatalMsg
        ? stderr : stdout;
    std::fprintf(stream, "%s\n", qPrintable(line));
    std::fflush(stream);
    if (type == QtFatalMsg)
        std::abort();
}

void openExpandedLog()
{
    if (s_expandedLog.isOpen())
        return;
    QDir().mkpath(appDataDirectory());
    rotateExpandedLog();
    s_expandedLog.setFileName(appDataDirectory() + QStringLiteral("/llamacode-expanded.jsonl"));
    s_expandedLog.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text);
}
} // namespace

namespace StartupDiagnostics {

void initializeEarly(const QString &executablePath, bool forceExpanded)
{
    QMutexLocker locker(&s_mutex);
    if (s_initialized)
        return;
    s_initialized = true;
    QCoreApplication::setApplicationName(QStringLiteral("LlamaCode"));
    QCoreApplication::setOrganizationName(QStringLiteral("LlamaCode"));
    s_clock.start();

    const QString logDir = appDataDirectory();
    QDir().mkpath(logDir);
    s_regularLog.setFileName(logDir + QStringLiteral("/llamacode.log"));
    if (s_regularLog.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text))
        s_regularStream.setDevice(&s_regularLog);
    const bool envEnabled = qEnvironmentVariableIntValue("LLAMACODE_EXPANDED_LOG") == 1;
    s_expanded = forceExpanded || envEnabled
        || QSettings().value(QStringLiteral("logging/expanded"), false).toBool();
    if (s_expanded)
        openExpandedLog();
    qInstallMessageHandler(messageHandler);

    QJsonObject start = baseRecord(QStringLiteral("process_start"));
    start.insert(QStringLiteral("version"), QCoreApplication::applicationVersion());
    start.insert(QStringLiteral("qtVersion"), QString::fromLatin1(qVersion()));
    start.insert(QStringLiteral("platform"), QSysInfo::prettyProductName());
    start.insert(QStringLiteral("executable"), executablePath);
    if (forceExpanded || envEnabled)
        start.insert(QStringLiteral("expandedLoggingSource"),
                     forceExpanded ? QStringLiteral("command_line") : QStringLiteral("environment"));
    appendExpanded(std::move(start));
}

bool expandedEnabled()
{
    return s_expanded;
}

void setExpandedEnabled(bool enabled)
{
    QMutexLocker locker(&s_mutex);
    if (!s_initialized) {
        s_expanded = enabled;
        QSettings().setValue(QStringLiteral("logging/expanded"), enabled);
        return;
    }
    if (s_expanded == enabled)
        return;
    QSettings().setValue(QStringLiteral("logging/expanded"), enabled);
    if (enabled) {
        s_expanded = true;
        openExpandedLog();
        appendExpanded(baseRecord(QStringLiteral("expanded_logging_enabled")));
    } else if (s_expandedLog.isOpen()) {
        appendExpanded(baseRecord(QStringLiteral("expanded_logging_disabled")));
        s_expanded = false;
        s_expandedLog.close();
    } else {
        s_expanded = false;
    }
}

QString expandedLogPath()
{
    return appDataDirectory() + QStringLiteral("/llamacode-expanded.jsonl");
}

qint64 elapsedMs()
{
    return s_clock.isValid() ? s_clock.elapsed() : 0;
}

void record(const QString &event, const QJsonObject &details)
{
    QMutexLocker locker(&s_mutex);
    if (!s_expanded || !s_expandedLog.isOpen())
        return;
    QJsonObject entry = baseRecord(event);
    for (auto it = details.constBegin(); it != details.constEnd(); ++it)
        entry.insert(it.key(), it.value());
    appendExpanded(std::move(entry));
}

} // namespace StartupDiagnostics
