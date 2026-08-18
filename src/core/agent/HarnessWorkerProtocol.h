#pragma once

#include <QByteArray>
#include <QJsonObject>
#include <QObject>
#include <QProcess>
#include <QProcessEnvironment>
#include <QSet>
#include <QString>
#include <QStringList>

class QTimer;

struct HarnessWorkerFrame {
    QString type;
    QJsonObject body;
};

class HarnessWorkerProtocol final {
public:
    static constexpr quint32 kHeaderBytes = 4;
    static constexpr quint32 kDefaultMaxFrameBytes = 1024 * 1024;

    static QByteArray encode(const QJsonObject &body, quint32 maxFrameBytes,
                             QString *error = nullptr);
    static bool take(QByteArray &buffer, quint32 maxFrameBytes, QJsonObject *body,
                     QString *error = nullptr);
    static bool validate(const QJsonObject &body, QString *error = nullptr);
};

class HarnessWorkerSession final {
public:
    bool acceptHelloAck(const QJsonObject &body, const QString &nonce, QString *error = nullptr);
    bool beginCall(const QString &callId, QString *error = nullptr);
    bool finishCall(const QString &callId, QString *error = nullptr);
    bool cancelCall(const QString &callId, QString *error = nullptr);
    bool authenticated() const { return m_authenticated; }
    bool hasCall(const QString &callId) const { return m_calls.contains(callId); }
    QSet<QString> calls() const { return m_calls; }

private:
    bool m_authenticated = false;
    QSet<QString> m_calls;
};

struct HarnessWorkerPolicy {
    quint32 maxFrameBytes = HarnessWorkerProtocol::kDefaultMaxFrameBytes;
    int startupTimeoutMs = 10000;
    int callTimeoutMs = 120000;
    bool allowNetwork = false;
};

// Driver host-side para Node/Python u otros workers. El worker nunca hereda la
// autoridad de la app: primero debe responder al nonce y luego sólo recibe
// llamadas explícitas con IDs no reutilizables.
class HarnessWorkerDriver final : public QObject {
    Q_OBJECT

public:
    explicit HarnessWorkerDriver(QObject *parent = nullptr);
    ~HarnessWorkerDriver() override;

    bool start(const QString &program, const QStringList &arguments,
               const QString &workingDirectory, const HarnessWorkerPolicy &policy = {});
    bool call(const QString &callId, const QJsonObject &payload);
    bool cancel(const QString &callId);
    void stop();
    bool running() const;
    bool authenticated() const { return m_session.authenticated(); }
    QString lastError() const { return m_lastError; }

signals:
    void authenticatedChanged(bool authenticated);
    void callResult(const QString &callId, const QJsonObject &payload);
    void workerError(const QString &message);
    void workerExited(int exitCode);

private:
    void fail(const QString &message);
    void readStdout();
    bool send(const QJsonObject &body);

    QProcess m_process;
    HarnessWorkerPolicy m_policy;
    HarnessWorkerSession m_session;
    QByteArray m_buffer;
    QString m_nonce;
    QString m_lastError;
    QTimer *m_callTimer = nullptr;
};
