#include "HarnessWorkerProtocol.h"

#include <QDataStream>
#include <QDateTime>
#include <QJsonDocument>
#include <QTimer>
#include <QUuid>

QByteArray HarnessWorkerProtocol::encode(const QJsonObject &body, quint32 maxFrameBytes,
                                         QString *error)
{
    if (!validate(body, error)) return {};
    const QByteArray json = QJsonDocument(body).toJson(QJsonDocument::Compact);
    if (json.isEmpty() || static_cast<quint32>(json.size()) > maxFrameBytes) {
        if (error) *error = QStringLiteral("worker frame exceeds the configured limit");
        return {};
    }
    QByteArray frame;
    frame.resize(kHeaderBytes);
    frame[0] = static_cast<char>((json.size() >> 24) & 0xff);
    frame[1] = static_cast<char>((json.size() >> 16) & 0xff);
    frame[2] = static_cast<char>((json.size() >> 8) & 0xff);
    frame[3] = static_cast<char>(json.size() & 0xff);
    frame += json;
    return frame;
}

bool HarnessWorkerProtocol::take(QByteArray &buffer, quint32 maxFrameBytes,
                                 QJsonObject *body, QString *error)
{
    if (!body) return false;
    if (buffer.size() < static_cast<int>(kHeaderBytes)) return false;
    const quint32 size = (static_cast<quint8>(buffer.at(0)) << 24)
                         | (static_cast<quint8>(buffer.at(1)) << 16)
                         | (static_cast<quint8>(buffer.at(2)) << 8)
                         | static_cast<quint8>(buffer.at(3));
    if (size == 0 || size > maxFrameBytes) {
        if (error) *error = QStringLiteral("invalid worker frame size");
        buffer.clear();
        return false;
    }
    if (buffer.size() < static_cast<int>(kHeaderBytes + size)) return false;
    const QByteArray json = buffer.mid(kHeaderBytes, static_cast<int>(size));
    buffer.remove(0, static_cast<int>(kHeaderBytes + size));
    QJsonParseError parseError;
    const QJsonDocument doc = QJsonDocument::fromJson(json, &parseError);
    if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
        if (error) *error = QStringLiteral("invalid worker JSON: %1").arg(parseError.errorString());
        return false;
    }
    if (!validate(doc.object(), error)) return false;
    *body = doc.object();
    return true;
}

bool HarnessWorkerProtocol::validate(const QJsonObject &body, QString *error)
{
    if (body.value(QStringLiteral("protocol")).toString()
        != QStringLiteral("llamacode-worker-v1")) {
        if (error) *error = QStringLiteral("unsupported worker protocol");
        return false;
    }
    const QString type = body.value(QStringLiteral("type")).toString().trimmed();
    if (type.isEmpty()) {
        if (error) *error = QStringLiteral("worker frame has no type");
        return false;
    }
    static const QSet<QString> allowed{
        QStringLiteral("hello"), QStringLiteral("hello_ack"), QStringLiteral("call"),
        QStringLiteral("result"), QStringLiteral("cancel"), QStringLiteral("error")};
    if (!allowed.contains(type)) {
        if (error) *error = QStringLiteral("unknown worker frame type: %1").arg(type);
        return false;
    }
    return true;
}

bool HarnessWorkerSession::acceptHelloAck(const QJsonObject &body, const QString &nonce,
                                          QString *error)
{
    if (m_authenticated) {
        if (error) *error = QStringLiteral("worker authenticated twice");
        return false;
    }
    if (body.value(QStringLiteral("type")).toString() != QStringLiteral("hello_ack")
        || body.value(QStringLiteral("nonce")).toString() != nonce) {
        if (error) *error = QStringLiteral("worker nonce authentication failed");
        return false;
    }
    m_authenticated = true;
    return true;
}

bool HarnessWorkerSession::beginCall(const QString &callId, QString *error)
{
    if (!m_authenticated) {
        if (error) *error = QStringLiteral("worker is not authenticated");
        return false;
    }
    if (callId.trimmed().isEmpty() || m_calls.contains(callId)) {
        if (error) *error = QStringLiteral("worker call id is empty or already in use");
        return false;
    }
    m_calls.insert(callId);
    return true;
}

bool HarnessWorkerSession::finishCall(const QString &callId, QString *error)
{
    if (!m_calls.remove(callId)) {
        if (error) *error = QStringLiteral("unknown worker call id");
        return false;
    }
    return true;
}

bool HarnessWorkerSession::cancelCall(const QString &callId, QString *error)
{
    return finishCall(callId, error);
}

HarnessWorkerDriver::HarnessWorkerDriver(QObject *parent)
    : QObject(parent)
{
    connect(&m_process, &QProcess::readyReadStandardOutput,
            this, &HarnessWorkerDriver::readStdout);
    connect(&m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        fail(m_process.errorString());
    });
    connect(&m_process, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, [this](int code, QProcess::ExitStatus) {
        if (m_callTimer) m_callTimer->stop();
        emit workerExited(code);
    });
    m_callTimer = new QTimer(this);
    m_callTimer->setSingleShot(true);
    connect(m_callTimer, &QTimer::timeout, this, [this]() {
        fail(QStringLiteral("worker call timeout"));
        stop();
    });
}

HarnessWorkerDriver::~HarnessWorkerDriver()
{
    stop();
}

bool HarnessWorkerDriver::start(const QString &program, const QStringList &arguments,
                                const QString &workingDirectory,
                                const HarnessWorkerPolicy &policy)
{
    stop();
    m_policy = policy;
    m_lastError.clear();
    m_buffer.clear();
    m_session = {};
    m_nonce = QUuid::createUuid().toString(QUuid::WithoutBraces);
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert(QStringLiteral("LLAMACODE_WORKER_PROTOCOL"), QStringLiteral("llamacode-worker-v1"));
    env.insert(QStringLiteral("LLAMACODE_WORKER_NONCE"), m_nonce);
    env.insert(QStringLiteral("LLAMACODE_WORKER_NETWORK"),
               policy.allowNetwork ? QStringLiteral("1") : QStringLiteral("0"));
    m_process.setProcessEnvironment(env);
    if (!workingDirectory.trimmed().isEmpty())
        m_process.setWorkingDirectory(workingDirectory);
    m_process.start(program, arguments);
    if (!m_process.waitForStarted(policy.startupTimeoutMs)) {
        fail(QStringLiteral("could not start worker: %1").arg(m_process.errorString()));
        return false;
    }
    return send(QJsonObject{{QStringLiteral("protocol"), QStringLiteral("llamacode-worker-v1")},
                            {QStringLiteral("type"), QStringLiteral("hello")},
                            {QStringLiteral("nonce"), m_nonce},
                            {QStringLiteral("network"), policy.allowNetwork}});
}

bool HarnessWorkerDriver::call(const QString &callId, const QJsonObject &payload)
{
    QString error;
    if (!m_session.beginCall(callId, &error)) {
        fail(error);
        return false;
    }
    if (!send(QJsonObject{{QStringLiteral("protocol"), QStringLiteral("llamacode-worker-v1")},
                         {QStringLiteral("type"), QStringLiteral("call")},
                         {QStringLiteral("callId"), callId},
                         {QStringLiteral("payload"), payload}})) {
        m_session.finishCall(callId);
        return false;
    }
    m_callTimer->start(m_policy.callTimeoutMs);
    return true;
}

bool HarnessWorkerDriver::cancel(const QString &callId)
{
    QString error;
    if (!m_session.cancelCall(callId, &error)) {
        fail(error);
        return false;
    }
    return send(QJsonObject{{QStringLiteral("protocol"), QStringLiteral("llamacode-worker-v1")},
                            {QStringLiteral("type"), QStringLiteral("cancel")},
                            {QStringLiteral("callId"), callId}});
}

void HarnessWorkerDriver::stop()
{
    if (m_callTimer) m_callTimer->stop();
    m_session = {};
    if (m_process.state() != QProcess::NotRunning) {
        m_process.terminate();
        if (!m_process.waitForFinished(1000)) {
            m_process.kill();
            m_process.waitForFinished(1000);
        }
    }
    m_buffer.clear();
}

bool HarnessWorkerDriver::running() const
{
    return m_process.state() != QProcess::NotRunning;
}

void HarnessWorkerDriver::fail(const QString &message)
{
    m_lastError = message;
    emit workerError(message);
}

void HarnessWorkerDriver::readStdout()
{
    m_buffer += m_process.readAllStandardOutput();
    while (!m_buffer.isEmpty()) {
        QJsonObject body;
        QString error;
        const int before = m_buffer.size();
        if (!HarnessWorkerProtocol::take(m_buffer, m_policy.maxFrameBytes, &body, &error)) {
            if (!error.isEmpty()) fail(error);
            if (m_buffer.size() == before && error.isEmpty()) return;
            if (!error.isEmpty()) return;
        }
        if (body.value(QStringLiteral("type")).toString() == QStringLiteral("hello_ack")) {
            if (!m_session.acceptHelloAck(body, m_nonce, &error)) {
                fail(error);
                stop();
                return;
            }
            emit authenticatedChanged(true);
            continue;
        }
        if (!m_session.authenticated()) {
            fail(QStringLiteral("worker sent data before authentication"));
            stop();
            return;
        }
        if (body.value(QStringLiteral("type")).toString() == QStringLiteral("result")) {
            const QString callId = body.value(QStringLiteral("callId")).toString();
            if (!m_session.finishCall(callId, &error)) {
                fail(error);
                continue;
            }
            if (m_session.calls().isEmpty()) m_callTimer->stop();
            emit callResult(callId, body.value(QStringLiteral("payload")).toObject());
        } else if (body.value(QStringLiteral("type")).toString() == QStringLiteral("error")) {
            fail(body.value(QStringLiteral("message")).toString());
        }
    }
}

bool HarnessWorkerDriver::send(const QJsonObject &body)
{
    QString error;
    const QByteArray frame = HarnessWorkerProtocol::encode(body, m_policy.maxFrameBytes, &error);
    if (frame.isEmpty()) {
        fail(error);
        return false;
    }
    if (m_process.write(frame) != frame.size()) {
        fail(m_process.errorString());
        return false;
    }
    return m_process.waitForBytesWritten(1000);
}
