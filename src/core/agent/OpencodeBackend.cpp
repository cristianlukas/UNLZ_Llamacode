#include "OpencodeBackend.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDir>
#include <QFileInfo>
#include <QTimer>
#include <QSettings>
#include <QDateTime>
#include <algorithm>

OpencodeBackend::OpencodeBackend(QObject *parent) : IAgentBackend(parent)
{
    m_nam = new QNetworkAccessManager(this);
}

OpencodeBackend::~OpencodeBackend()
{
    if (m_proc) { m_proc->kill(); m_proc->deleteLater(); }
}

bool OpencodeBackend::running() const
{
    return m_proc && m_proc->state() != QProcess::NotRunning;
}

QString OpencodeBackend::currentProjectDir() const
{
    return m_proc ? m_proc->workingDirectory() : QString();
}

QString OpencodeBackend::projectNameFromDir(const QString &dir)
{
    const QStringList parts = QDir::toNativeSeparators(dir).split(QDir::separator(), Qt::SkipEmptyParts);
    if (parts.size() >= 2) return parts[parts.size()-2] + QStringLiteral("/") + parts.last();
    return parts.isEmpty() ? QStringLiteral("(sin proyecto)") : parts.last();
}

void OpencodeBackend::start(const AgentContext &ctx)
{
    if (running()) return;
    m_ctx = ctx;
    m_stopping = false;
    launchProcess();
}

void OpencodeBackend::launchProcess()
{
    // Liberar el puerto 4096 si quedó ocupado por un server previo.
#ifdef Q_OS_WIN
    QProcess::execute(QStringLiteral("cmd"),
        {QStringLiteral("/c"),
         QStringLiteral("for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :4096 ^| findstr LISTENING') do taskkill /PID %a /F")});
#else
    QProcess::execute(QStringLiteral("sh"),
        {QStringLiteral("-c"), QStringLiteral("fuser -k 4096/tcp 2>/dev/null || true")});
#endif

    m_proc = new QProcess(this);
    m_proc->setProcessEnvironment(m_ctx.env);
    if (!m_ctx.cwd.isEmpty() && QFileInfo(m_ctx.cwd).isDir())
        m_proc->setWorkingDirectory(m_ctx.cwd);

    connect(m_proc, &QProcess::readyReadStandardOutput, this, [this]() {
        if (!m_proc) return;
        const QString chunk = QString::fromUtf8(m_proc->readAllStandardOutput());
        emit logAppended(chunk);
        if (m_sessionId.isEmpty() && chunk.contains(QLatin1String("server listening")))
            initSession();
    });
    connect(m_proc, &QProcess::readyReadStandardError, this, [this]() {
        if (!m_proc) return;
        const QString chunk = QString::fromUtf8(m_proc->readAllStandardError());
        emit logAppended(chunk);
        if (m_sessionId.isEmpty() && chunk.contains(QLatin1String("server listening")))
            initSession();
    });
    connect(m_proc, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, [this](int code, QProcess::ExitStatus) {
        emit logAppended(QStringLiteral("\n[agent exited with code %1]\n").arg(code));
        if (m_proc) { m_proc->deleteLater(); m_proc = nullptr; }
        if (m_eventReply) { m_eventReply->abort(); m_eventReply->deleteLater(); m_eventReply = nullptr; }
        m_sessionId.clear();
        m_messages.clear();
        m_curAsstIdx = -1;
        emit messagesChanged();
        m_stopping = false;
        emit runningChanged();
    });

    const QStringList args{
        QStringLiteral("serve"),
        QStringLiteral("--hostname"), QStringLiteral("127.0.0.1"),
        QStringLiteral("--port"), QStringLiteral("4096")
    };
    emit logAppended(QStringLiteral("[opencode headless server mode]\n"));
    if (!m_ctx.cwd.isEmpty())
        emit logAppended(QStringLiteral("[cwd: %1]\n").arg(QDir::toNativeSeparators(m_ctx.cwd)));
    m_proc->start(m_ctx.exePath, args);
    if (!m_proc->waitForStarted(5000)) {
        emit logAppended(QStringLiteral("[Error: no se pudo iniciar opencode]\n"));
        m_proc->deleteLater();
        m_proc = nullptr;
        return;
    }
    emit runningChanged();
}

void OpencodeBackend::stop()
{
    m_stopping = true;
    if (m_eventReply) { m_eventReply->abort(); m_eventReply->deleteLater(); m_eventReply = nullptr; }
    m_sessionId.clear();
    if (!m_proc) { emit runningChanged(); return; }
#ifdef Q_OS_WIN
    const qint64 pid = m_proc->processId();
    if (pid > 0)
        QProcess::execute(QStringLiteral("taskkill"),
            {QStringLiteral("/PID"), QString::number(pid),
             QStringLiteral("/T"), QStringLiteral("/F")});
#endif
    m_proc->terminate();
    if (!m_proc->waitForFinished(2000))
        m_proc->kill();
}

void OpencodeBackend::initSession()
{
    loadSessionList([this]() { resumeOrCreateSession(); });
}

void OpencodeBackend::loadSessionList(std::function<void()> then)
{
    auto *reply = m_nam->get(QNetworkRequest(QUrl(m_attachUrl + QStringLiteral("/session"))));
    connect(reply, &QNetworkReply::finished, this, [this, reply, then]() {
        reply->deleteLater();
        if (reply->error() == QNetworkReply::NoError) {
            const QJsonArray arr = QJsonDocument::fromJson(reply->readAll()).array();
            QVector<QJsonObject> sorted;
            sorted.reserve(arr.size());
            for (const QJsonValue &v : arr) sorted.append(v.toObject());
            std::sort(sorted.begin(), sorted.end(), [](const QJsonObject &a, const QJsonObject &b) {
                return a.value(QStringLiteral("time")).toObject().value(QStringLiteral("created")).toDouble()
                     > b.value(QStringLiteral("time")).toObject().value(QStringLiteral("created")).toDouble();
            });
            m_sessions.clear();
            for (const QJsonObject &s : sorted) {
                const QString dir = s.value(QStringLiteral("directory")).toString();
                AgentSession e;
                e.id          = s.value(QStringLiteral("id")).toString();
                e.title       = s.value(QStringLiteral("title")).toString();
                e.created     = s.value(QStringLiteral("time")).toObject().value(QStringLiteral("created")).toDouble();
                e.projectId   = s.value(QStringLiteral("projectID")).toString();
                e.projectName = projectNameFromDir(dir);
                e.projectDir  = dir;
                m_sessions.append(e.toMap());
            }
            emit sessionsChanged();
        }
        if (then) then();
    });
}

void OpencodeBackend::resumeOrCreateSession()
{
    if (m_forceNew) { m_forceNew = false; doCreateSession(); return; }
    QSettings st;
    const QString savedId = st.value(QStringLiteral("opencode/lastSessionId")).toString();
    if (!savedId.isEmpty()) {
        for (const QVariant &v : std::as_const(m_sessions)) {
            if (v.toMap().value(QStringLiteral("id")).toString() == savedId) {
                m_sessionId = savedId;
                m_sessionTitle = v.toMap().value(QStringLiteral("title")).toString();
                emit sessionsChanged();
                emit logAppended(QStringLiteral("[opencode session resumed]\n"));
                loadSessionMessages(savedId);
                subscribeEvents();
                return;
            }
        }
    }
    doCreateSession();
}

void OpencodeBackend::doCreateSession()
{
    QNetworkRequest req(QUrl(m_attachUrl + QStringLiteral("/session")));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));
    auto *reply = m_nam->post(req, QByteArrayLiteral("{}"));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit logAppended(QStringLiteral("[error: failed to create opencode session: %1]\n")
                                 .arg(reply->errorString()));
            return;
        }
        const QJsonObject obj = QJsonDocument::fromJson(reply->readAll()).object();
        m_sessionId    = obj.value(QStringLiteral("id")).toString();
        m_sessionTitle = obj.value(QStringLiteral("title")).toString();
        QSettings().setValue(QStringLiteral("opencode/lastSessionId"), m_sessionId);
        const QString cwd = currentProjectDir();
        AgentSession e;
        e.id          = m_sessionId;
        e.title       = m_sessionTitle;
        e.created     = static_cast<double>(QDateTime::currentMSecsSinceEpoch());
        e.projectId   = obj.value(QStringLiteral("projectID")).toString();
        e.projectName = projectNameFromDir(cwd);
        e.projectDir  = cwd;
        m_sessions.prepend(e.toMap());
        emit sessionsChanged();
        emit logAppended(QStringLiteral("[opencode session ready]\n"));
        subscribeEvents();
    });
}

void OpencodeBackend::loadSessionMessages(const QString &sessionId)
{
    const QUrl url(m_attachUrl + QStringLiteral("/session/") + sessionId + QStringLiteral("/message"));
    auto *reply = m_nam->get(QNetworkRequest(url));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) return;
        const QJsonArray msgs = QJsonDocument::fromJson(reply->readAll()).array();
        m_messages.clear();
        m_curAsstIdx = -1;
        for (const QJsonValue &mv : msgs) {
            const QJsonObject msg = mv.toObject();
            const QString role = msg.value(QStringLiteral("info")).toObject().value(QStringLiteral("role")).toString();
            QString text;
            for (const QJsonValue &pv : msg.value(QStringLiteral("parts")).toArray()) {
                const QJsonObject part = pv.toObject();
                if (part.value(QStringLiteral("type")).toString() == QLatin1String("text"))
                    text += part.value(QStringLiteral("text")).toString();
            }
            if (role.isEmpty() || text.isEmpty()) continue;
            AgentMessage e; e.role = role; e.content = text; e.typing = false;
            m_messages.append(e.toMap());
        }
        emit messagesChanged();
    });
}

void OpencodeBackend::sendMessage(const QString &text)
{
    if (!running()) return;
    emit logAppended(QStringLiteral("> %1\n").arg(text));

    AgentMessage um; um.role = QStringLiteral("user"); um.content = text;
    m_messages.append(um.toMap());
    AgentMessage am; am.role = QStringLiteral("assistant"); am.typing = true;
    m_messages.append(am.toMap());
    m_curAsstIdx = m_messages.size() - 1;
    emit messagesChanged();

    if (m_sessionId.isEmpty()) {
        emit logAppended(QStringLiteral("[waiting: opencode session not ready yet]\n"));
        return;
    }
    QNetworkRequest req(QUrl(m_attachUrl + QStringLiteral("/session/") + m_sessionId
                             + QStringLiteral("/prompt_async")));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));
    const QJsonObject partObj{{QStringLiteral("type"), QStringLiteral("text")}, {QStringLiteral("text"), text}};
    const QJsonObject payload{{QStringLiteral("parts"), QJsonArray{partObj}}};
    auto *reply = m_nam->post(req, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit logAppended(QStringLiteral("[error sending message: %1]\n").arg(reply->errorString()));
        }
    });
}

void OpencodeBackend::newSession()
{
    if (!running()) return;
    m_messages.clear();
    m_curAsstIdx = -1;
    m_sessionId.clear();
    m_sessionTitle.clear();
    emit messagesChanged();
    emit sessionsChanged();
    doCreateSession();
}

void OpencodeBackend::newSessionInProject(const QString &projectDir)
{
    if (projectDir.isEmpty()) { newSession(); return; }
    if (QDir::cleanPath(currentProjectDir()) == QDir::cleanPath(projectDir)) {
        newSession();
        return;
    }
    // Reiniciar el server en el nuevo cwd y forzar sesión nueva.
    m_forceNew = true;
    m_ctx.cwd = projectDir;
    auto conn = std::make_shared<QMetaObject::Connection>();
    *conn = connect(this, &IAgentBackend::runningChanged, this, [this, conn]() {
        if (running()) return;
        QObject::disconnect(*conn);
        QTimer::singleShot(300, this, [this]() { launchProcess(); });
    });
    stop();
}

void OpencodeBackend::switchSession(const QString &sessionId)
{
    if (sessionId == m_sessionId) return;
    m_sessionId = sessionId;
    m_messages.clear();
    m_curAsstIdx = -1;
    for (const QVariant &v : std::as_const(m_sessions)) {
        const QVariantMap m = v.toMap();
        if (m.value(QStringLiteral("id")).toString() == sessionId) {
            m_sessionTitle = m.value(QStringLiteral("title")).toString();
            break;
        }
    }
    QSettings().setValue(QStringLiteral("opencode/lastSessionId"), sessionId);
    emit sessionsChanged();
    emit messagesChanged();
    loadSessionMessages(sessionId);
}

void OpencodeBackend::refreshSessions()
{
    loadSessionList(nullptr);
}

void OpencodeBackend::renameSession(const QString &sessionId, const QString &title)
{
    const QString t = title.trimmed();
    if (sessionId.isEmpty() || t.isEmpty()) return;
    QNetworkRequest req(QUrl(m_attachUrl + QStringLiteral("/session/") + sessionId));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));
    const QByteArray body = QJsonDocument(QJsonObject{{QStringLiteral("title"), t}}).toJson(QJsonDocument::Compact);
    auto *reply = m_nam->sendCustomRequest(req, QByteArrayLiteral("PATCH"), body);
    connect(reply, &QNetworkReply::finished, this, [this, reply, sessionId, t]() {
        reply->deleteLater();
        for (int i = 0; i < m_sessions.size(); ++i) {
            QVariantMap m = m_sessions[i].toMap();
            if (m.value(QStringLiteral("id")).toString() == sessionId) {
                m[QStringLiteral("title")] = t; m_sessions[i] = m; break;
            }
        }
        if (sessionId == m_sessionId) m_sessionTitle = t;
        emit sessionsChanged();
        loadSessionList(nullptr);
    });
}

void OpencodeBackend::deleteSession(const QString &sessionId)
{
    if (sessionId.isEmpty()) return;
    QNetworkRequest req(QUrl(m_attachUrl + QStringLiteral("/session/") + sessionId));
    auto *reply = m_nam->deleteResource(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, sessionId]() {
        reply->deleteLater();
        for (int i = 0; i < m_sessions.size(); ++i) {
            if (m_sessions[i].toMap().value(QStringLiteral("id")).toString() == sessionId) {
                m_sessions.removeAt(i); break;
            }
        }
        if (sessionId == m_sessionId) {
            m_sessionId.clear(); m_sessionTitle.clear();
            m_messages.clear(); m_curAsstIdx = -1;
            QSettings().remove(QStringLiteral("opencode/lastSessionId"));
            emit messagesChanged();
        }
        emit sessionsChanged();
        loadSessionList(nullptr);
    });
}

void OpencodeBackend::forkSession(const QString &sessionId)
{
    if (sessionId.isEmpty()) return;
    QNetworkRequest req(QUrl(m_attachUrl + QStringLiteral("/session")));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));
    const QByteArray body = QJsonDocument(QJsonObject{{QStringLiteral("parentID"), sessionId}}).toJson(QJsonDocument::Compact);
    auto *reply = m_nam->post(req, body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit logAppended(QStringLiteral("[error fork sesión: %1]\n").arg(reply->errorString()));
            return;
        }
        const QJsonObject obj = QJsonDocument::fromJson(reply->readAll()).object();
        const QString newId = obj.value(QStringLiteral("id")).toString();
        loadSessionList([this, newId]() { if (!newId.isEmpty()) switchSession(newId); });
    });
}

void OpencodeBackend::subscribeEvents()
{
    QNetworkRequest req(QUrl(m_attachUrl + QStringLiteral("/event")));
    req.setRawHeader(QByteArrayLiteral("Accept"), QByteArrayLiteral("text/event-stream"));
    req.setAttribute(QNetworkRequest::CacheLoadControlAttribute, QNetworkRequest::AlwaysNetwork);
    m_eventReply = m_nam->get(req);

    connect(m_eventReply, &QNetworkReply::readyRead, this, [this]() {
        if (!m_eventReply) return;
        const QByteArray data = m_eventReply->readAll();
        for (const QByteArray &raw : data.split('\n')) {
            const QByteArray line = raw.trimmed();
            if (!line.startsWith("data: ")) continue;
            const QJsonDocument doc = QJsonDocument::fromJson(line.mid(6));
            if (doc.isNull()) continue;
            const QJsonObject obj = doc.object();
            const QString type = obj.value(QStringLiteral("type")).toString();
            const QJsonObject props = obj.value(QStringLiteral("properties")).toObject();
            if (type == QLatin1String("message.part.delta")) {
                if (props.value(QStringLiteral("field")).toString() == QLatin1String("text")) {
                    const QString delta = props.value(QStringLiteral("delta")).toString();
                    if (!delta.isEmpty()) {
                        emit logAppended(delta);
                        if (m_curAsstIdx >= 0 && m_curAsstIdx < m_messages.size()) {
                            auto msg = m_messages[m_curAsstIdx].toMap();
                            msg[QStringLiteral("content")] = msg[QStringLiteral("content")].toString() + delta;
                            m_messages[m_curAsstIdx] = msg;
                            emit messagesChanged();
                        }
                    }
                }
            } else if (type == QLatin1String("session.updated")) {
                const QJsonObject info = props.value(QStringLiteral("info")).toObject();
                const QString title = info.value(QStringLiteral("title")).toString();
                const QString sid   = info.value(QStringLiteral("id")).toString();
                if (!title.isEmpty() && sid == m_sessionId) {
                    m_sessionTitle = title;
                    for (int i = 0; i < m_sessions.size(); ++i) {
                        auto sm = m_sessions[i].toMap();
                        if (sm.value(QStringLiteral("id")).toString() == sid) {
                            sm[QStringLiteral("title")] = title; m_sessions[i] = sm; break;
                        }
                    }
                    emit sessionsChanged();
                }
            } else if (type == QLatin1String("session.status")) {
                const QString status = props.value(QStringLiteral("status"))
                                            .toObject().value(QStringLiteral("type")).toString();
                if (status == QLatin1String("idle")) {
                    emit logAppended(QStringLiteral("\n"));
                    if (m_curAsstIdx >= 0 && m_curAsstIdx < m_messages.size()) {
                        auto msg = m_messages[m_curAsstIdx].toMap();
                        msg[QStringLiteral("typing")] = false;
                        m_messages[m_curAsstIdx] = msg;
                        emit messagesChanged();
                    }
                    m_curAsstIdx = -1;
                }
            } else if (type == QLatin1String("permission.asked")) {
                // Etapa 4 reemplazará esto por aprobación visible. Por ahora auto-aprueba.
                respondPermission(props.value(QStringLiteral("sessionID")).toString(),
                                  props.value(QStringLiteral("id")).toString());
            } else if (type.contains(QLatin1String("error"))) {
                const QString errMsg = props.value(QStringLiteral("message")).toString();
                if (!errMsg.isEmpty()) {
                    emit logAppended(QStringLiteral("[error: %1]\n").arg(errMsg));
                    if (m_curAsstIdx >= 0 && m_curAsstIdx < m_messages.size()) {
                        auto msg = m_messages[m_curAsstIdx].toMap();
                        msg[QStringLiteral("content")] = QStringLiteral("[error: %1]").arg(errMsg);
                        msg[QStringLiteral("typing")] = false;
                        m_messages[m_curAsstIdx] = msg;
                        emit messagesChanged();
                    }
                    m_curAsstIdx = -1;
                }
            }
        }
    });

    // Mantener vivo: el server opencode se apaga sin suscriptores de eventos.
    connect(m_eventReply, &QNetworkReply::finished, this, [this]() {
        QNetworkReply *r = m_eventReply;
        if (!r) return;
        m_eventReply = nullptr;
        r->deleteLater();
        if (m_stopping) return;
        if (running())
            QTimer::singleShot(200, this, [this]() {
                if (!m_stopping && running()) subscribeEvents();
            });
    });
    connect(m_eventReply, &QNetworkReply::errorOccurred, this, [this](QNetworkReply::NetworkError) {
        if (!m_eventReply) return;
        if (!m_stopping) emit logAppended(QStringLiteral("[opencode event stream reconectando...]\n"));
    });
}

void OpencodeBackend::respondPermission(const QString &sessionId, const QString &permissionId)
{
    if (sessionId.isEmpty() || permissionId.isEmpty()) return;
    QNetworkRequest req(QUrl(m_attachUrl + QStringLiteral("/session/") + sessionId
                             + QStringLiteral("/permissions/") + permissionId));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    QJsonObject body{{QStringLiteral("response"), QStringLiteral("always")}};
    auto *reply = m_nam->post(req, QJsonDocument(body).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() != QNetworkReply::NoError)
            emit logAppended(QStringLiteral("[error: permission response failed: %1]\n").arg(reply->errorString()));
        reply->deleteLater();
    });
}
