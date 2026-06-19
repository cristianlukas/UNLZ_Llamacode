#include "LlmGateway.h"

#include <QTcpServer>
#include <QTcpSocket>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonValue>
#include <QTimer>
#include <QUuid>
#include <QElapsedTimer>
#include <QPointer>

// ── Funciones puras ──────────────────────────────────────────────────────────

// Aplana el `content` de Anthropic (string o array de blocks) a texto OpenAI.
static QString flattenAnthropicContent(const QJsonValue &content)
{
    if (content.isString()) return content.toString();
    if (!content.isArray()) return {};
    QString out;
    for (const QJsonValue &v : content.toArray()) {
        const QJsonObject b = v.toObject();
        const QString type = b.value(QStringLiteral("type")).toString();
        if (type == QLatin1String("text"))
            out += b.value(QStringLiteral("text")).toString();
        else if (type == QLatin1String("tool_result"))
            out += b.value(QStringLiteral("content")).toString();
    }
    return out;
}

QJsonObject LlmGateway::anthropicToOpenAI(const QJsonObject &a)
{
    QJsonObject o;
    o.insert(QStringLiteral("model"), a.value(QStringLiteral("model")));
    if (a.contains(QStringLiteral("max_tokens")))
        o.insert(QStringLiteral("max_tokens"), a.value(QStringLiteral("max_tokens")));
    if (a.contains(QStringLiteral("temperature")))
        o.insert(QStringLiteral("temperature"), a.value(QStringLiteral("temperature")));
    if (a.contains(QStringLiteral("top_p")))
        o.insert(QStringLiteral("top_p"), a.value(QStringLiteral("top_p")));
    o.insert(QStringLiteral("stream"), a.value(QStringLiteral("stream")).toBool(false));

    // stop_sequences → stop
    if (a.contains(QStringLiteral("stop_sequences")))
        o.insert(QStringLiteral("stop"), a.value(QStringLiteral("stop_sequences")));

    QJsonArray msgs;
    // system (string o array de blocks) → primer mensaje system
    const QJsonValue sys = a.value(QStringLiteral("system"));
    const QString sysText = flattenAnthropicContent(sys);
    if (!sysText.isEmpty())
        msgs.append(QJsonObject{{QStringLiteral("role"), QStringLiteral("system")},
                                {QStringLiteral("content"), sysText}});

    for (const QJsonValue &mv : a.value(QStringLiteral("messages")).toArray()) {
        const QJsonObject m = mv.toObject();
        const QString role = m.value(QStringLiteral("role")).toString();
        msgs.append(QJsonObject{{QStringLiteral("role"), role},
                                {QStringLiteral("content"), flattenAnthropicContent(m.value(QStringLiteral("content")))}});
    }
    o.insert(QStringLiteral("messages"), msgs);

    // tools: anthropic {name,description,input_schema} → openai {type:function,function:{...}}
    if (a.contains(QStringLiteral("tools"))) {
        QJsonArray tools;
        for (const QJsonValue &tv : a.value(QStringLiteral("tools")).toArray()) {
            const QJsonObject t = tv.toObject();
            tools.append(QJsonObject{
                {QStringLiteral("type"), QStringLiteral("function")},
                {QStringLiteral("function"), QJsonObject{
                    {QStringLiteral("name"), t.value(QStringLiteral("name"))},
                    {QStringLiteral("description"), t.value(QStringLiteral("description"))},
                    {QStringLiteral("parameters"), t.value(QStringLiteral("input_schema"))}
                }}
            });
        }
        if (!tools.isEmpty()) o.insert(QStringLiteral("tools"), tools);
    }
    return o;
}

QJsonObject LlmGateway::openAIToAnthropic(const QJsonObject &o)
{
    const QJsonObject choice = o.value(QStringLiteral("choices")).toArray().isEmpty()
        ? QJsonObject() : o.value(QStringLiteral("choices")).toArray().first().toObject();
    const QJsonObject message = choice.value(QStringLiteral("message")).toObject();

    QJsonArray content;
    const QString text = message.value(QStringLiteral("content")).toString();
    if (!text.isEmpty())
        content.append(QJsonObject{{QStringLiteral("type"), QStringLiteral("text")},
                                   {QStringLiteral("text"), text}});
    // tool_calls → tool_use blocks
    for (const QJsonValue &tcv : message.value(QStringLiteral("tool_calls")).toArray()) {
        const QJsonObject tc = tcv.toObject();
        const QJsonObject fn = tc.value(QStringLiteral("function")).toObject();
        content.append(QJsonObject{
            {QStringLiteral("type"), QStringLiteral("tool_use")},
            {QStringLiteral("id"), tc.value(QStringLiteral("id"))},
            {QStringLiteral("name"), fn.value(QStringLiteral("name"))},
            {QStringLiteral("input"), QJsonDocument::fromJson(
                fn.value(QStringLiteral("arguments")).toString().toUtf8()).object()}
        });
    }

    const QString finish = choice.value(QStringLiteral("finish_reason")).toString();
    const QString stopReason = finish == QLatin1String("length") ? QStringLiteral("max_tokens")
                             : finish == QLatin1String("tool_calls") ? QStringLiteral("tool_use")
                             : QStringLiteral("end_turn");

    const QJsonObject usage = o.value(QStringLiteral("usage")).toObject();
    return QJsonObject{
        {QStringLiteral("id"), o.value(QStringLiteral("id")).toString(
            QStringLiteral("msg_") + QUuid::createUuid().toString(QUuid::WithoutBraces).left(24))},
        {QStringLiteral("type"), QStringLiteral("message")},
        {QStringLiteral("role"), QStringLiteral("assistant")},
        {QStringLiteral("model"), o.value(QStringLiteral("model"))},
        {QStringLiteral("content"), content},
        {QStringLiteral("stop_reason"), stopReason},
        {QStringLiteral("stop_sequence"), QJsonValue::Null},
        {QStringLiteral("usage"), QJsonObject{
            {QStringLiteral("input_tokens"), usage.value(QStringLiteral("prompt_tokens")).toInt()},
            {QStringLiteral("output_tokens"), usage.value(QStringLiteral("completion_tokens")).toInt()}
        }}
    };
}

QString LlmGateway::resolveModel(const QString &requested, const QStringList &available)
{
    const QString r = requested.trimmed();
    if (r.isEmpty() || available.isEmpty()) return {};
    // Exacto (case-insensitive)
    for (const QString &m : available)
        if (m.compare(r, Qt::CaseInsensitive) == 0) return m;
    // El pedido contiene al candidato, o viceversa (substring, el más largo gana).
    QString best; int bestLen = -1;
    for (const QString &m : available) {
        const bool hit = m.contains(r, Qt::CaseInsensitive) || r.contains(m, Qt::CaseInsensitive);
        if (hit && m.size() > bestLen) { best = m; bestLen = m.size(); }
    }
    return best;
}

QStringList LlmGateway::lruTouch(QStringList &order, const QString &name, int keepN)
{
    if (name.isEmpty()) return {};
    order.removeAll(name);
    order.prepend(name);
    QStringList evicted;
    const int keep = qMax(1, keepN);
    while (order.size() > keep) evicted.append(order.takeLast());
    return evicted;
}

QJsonObject LlmGateway::applyStructuredOutput(QJsonObject payload,
                                              const QString &grammar,
                                              const QJsonObject &jsonSchema)
{
    if (!grammar.trimmed().isEmpty()) {
        payload.insert(QStringLiteral("grammar"), grammar);
    } else if (!jsonSchema.isEmpty()) {
        // llama-server: response_format json_schema o json_schema directo.
        payload.insert(QStringLiteral("response_format"), QJsonObject{
            {QStringLiteral("type"), QStringLiteral("json_schema")},
            {QStringLiteral("json_schema"), QJsonObject{{QStringLiteral("schema"), jsonSchema}}}
        });
    }
    return payload;
}

// ── Runtime ──────────────────────────────────────────────────────────────────

LlmGateway::LlmGateway(QObject *parent) : QObject(parent)
{
    m_nam = new QNetworkAccessManager(this);
}

LlmGateway::~LlmGateway() { stop(); }

bool LlmGateway::start(quint16 port, const QHostAddress &addr)
{
    stop();
    if (port == 0) return false;
    m_server = new QTcpServer(this);
    connect(m_server, &QTcpServer::newConnection, this, &LlmGateway::onNewConnection);
    if (!m_server->listen(addr, port)) {
        qWarning("LlmGateway: no pude escuchar en %s:%u", qPrintable(addr.toString()), port);
        m_server->deleteLater(); m_server = nullptr;
        return false;
    }
    m_port = port;
    qInfo("LlmGateway: escuchando en http://%s:%u", qPrintable(addr.toString()), port);
    return true;
}

void LlmGateway::stop()
{
    if (m_server) { m_server->close(); m_server->deleteLater(); m_server = nullptr; }
    m_port = 0;
}

bool LlmGateway::listening() const { return m_server && m_server->isListening(); }

void LlmGateway::onNewConnection()
{
    while (m_server->hasPendingConnections()) {
        QTcpSocket *sock = m_server->nextPendingConnection();
        connect(sock, &QTcpSocket::readyRead, this, [this, sock]() {
            sock->setProperty("buf", sock->property("buf").toByteArray() + sock->readAll());
            QByteArray data = sock->property("buf").toByteArray();
            const int hdrEnd = data.indexOf("\r\n\r\n");
            if (hdrEnd < 0) return;
            const QByteArray headers = data.left(hdrEnd);
            int contentLen = 0;
            QString auth;
            const QList<QByteArray> lines = headers.split('\n');
            for (const QByteArray &l : lines) {
                const QByteArray ll = l.toLower();
                if (ll.startsWith("content-length:"))
                    contentLen = l.mid(l.indexOf(':') + 1).trimmed().toInt();
                else if (ll.startsWith("authorization:") || ll.startsWith("x-api-key:"))
                    auth = QString::fromUtf8(l.mid(l.indexOf(':') + 1).trimmed());
            }
            const QByteArray body = data.mid(hdrEnd + 4);
            if (body.size() < contentLen) return;   // esperar resto del body
            const QByteArray reqLine = lines.isEmpty() ? QByteArray() : lines.first().trimmed();
            const QList<QByteArray> parts = reqLine.split(' ');
            if (parts.size() < 2) { sock->disconnectFromHost(); return; }
            handle(sock, parts.at(0), QString::fromUtf8(parts.at(1)),
                   body.left(contentLen), auth);
        });
        connect(sock, &QTcpSocket::disconnected, sock, &QObject::deleteLater);
    }
}

void LlmGateway::writeError(QTcpSocket *sock, int code, const QString &msg)
{
    const QByteArray json = QJsonDocument(QJsonObject{
        {QStringLiteral("error"), QJsonObject{{QStringLiteral("message"), msg}}}
    }).toJson(QJsonDocument::Compact);
    QByteArray r = "HTTP/1.1 " + QByteArray::number(code) + " ERR\r\n";
    r += "Content-Type: application/json\r\n";
    r += "Access-Control-Allow-Origin: *\r\n";
    r += "Content-Length: " + QByteArray::number(json.size()) + "\r\n\r\n" + json;
    sock->write(r); sock->flush(); sock->disconnectFromHost();
}

void LlmGateway::handle(QTcpSocket *sock, const QByteArray &method, const QString &path,
                        const QByteArray &body, const QString &authHeader)
{
    const QString p = path.section('?', 0, 0);

    if (method == "OPTIONS") {   // CORS preflight
        QByteArray r = "HTTP/1.1 204 No Content\r\n";
        r += "Access-Control-Allow-Origin: *\r\n";
        r += "Access-Control-Allow-Headers: *\r\n";
        r += "Access-Control-Allow-Methods: GET,POST,OPTIONS\r\n\r\n";
        sock->write(r); sock->flush(); sock->disconnectFromHost();
        return;
    }
    if (p == QLatin1String("/health") || p == QLatin1String("/")) {
        const QByteArray j = "{\"ok\":true,\"gateway\":true}";
        QByteArray r = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n";
        r += "Content-Length: " + QByteArray::number(j.size()) + "\r\n\r\n" + j;
        sock->write(r); sock->flush(); sock->disconnectFromHost();
        return;
    }

    // Auth opcional (Bearer o x-api-key).
    if (!m_apiKey.isEmpty()) {
        const QString tok = authHeader.startsWith(QLatin1String("Bearer "))
            ? authHeader.mid(7).trimmed() : authHeader.trimmed();
        if (tok != m_apiKey) { writeError(sock, 401, QStringLiteral("API key inválida")); return; }
    }

    const bool anthropic = p.endsWith(QLatin1String("/v1/messages"));
    const bool openai = p.contains(QLatin1String("/v1/"));
    if (!anthropic && !openai) { writeError(sock, 404, QStringLiteral("endpoint desconocido")); return; }

    const QJsonObject reqObj = QJsonDocument::fromJson(body).object();
    const bool stream = reqObj.value(QStringLiteral("stream")).toBool(false);
    const QString requested = reqObj.value(QStringLiteral("model")).toString();

    if (m_hooks.activity) m_hooks.activity();

    // Auto-load del modelo pedido (si difiere del activo y autoSwap está on).
    if (m_autoSwap && m_hooks.modelNames && m_hooks.ensureModel) {
        const QString resolved = resolveModel(requested, m_hooks.modelNames());
        const QString current = m_hooks.currentModel ? m_hooks.currentModel() : QString();
        if (!resolved.isEmpty() && resolved.compare(current, Qt::CaseInsensitive) != 0) {
            lruTouch(m_lru, resolved, m_keepN);
            m_hooks.ensureModel(resolved);
        } else if (!resolved.isEmpty()) {
            lruTouch(m_lru, resolved, m_keepN);
        }
    }

    // Esperar a que el server esté listo (carga puede tardar), con timeout.
    auto *waitTimer = new QTimer(this);
    auto *clock = new QElapsedTimer; clock->start();
    QPointer<QTcpSocket> psock(sock);
    waitTimer->setInterval(150);
    connect(waitTimer, &QTimer::timeout, this, [this, waitTimer, clock, psock, p, body, anthropic, stream]() {
        const bool ready = m_hooks.ready ? m_hooks.ready() : true;
        if (!psock) { waitTimer->stop(); waitTimer->deleteLater(); delete clock; return; }
        if (ready) {
            waitTimer->stop(); waitTimer->deleteLater();
            delete clock;
            forward(psock, p, body, anthropic, stream);
            return;
        }
        if (clock->elapsed() > 90000) {   // 90s
            waitTimer->stop(); waitTimer->deleteLater(); delete clock;
            writeError(psock, 503, QStringLiteral("modelo no quedó listo a tiempo"));
        }
    });
    waitTimer->start();
}

void LlmGateway::forward(QTcpSocket *sock, const QString &path, const QByteArray &body,
                         bool anthropic, bool stream)
{
    const QString base = m_hooks.baseUrl ? m_hooks.baseUrl() : QString();
    if (base.isEmpty()) { writeError(sock, 502, QStringLiteral("no hay server activo")); return; }

    // Cuerpo a reenviar: Anthropic se traduce a OpenAI; OpenAI pasa tal cual.
    QByteArray upstreamBody = body;
    QString upstreamPath = path;
    QJsonObject reqObj = QJsonDocument::fromJson(body).object();
    if (anthropic) {
        QJsonObject oai = anthropicToOpenAI(reqObj);
        oai.insert(QStringLiteral("stream"), stream);
        upstreamBody = QJsonDocument(oai).toJson(QJsonDocument::Compact);
        upstreamPath = QStringLiteral("/v1/chat/completions");
    }

    QNetworkRequest req(QUrl(base + upstreamPath));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));
    QNetworkReply *reply = m_nam->post(req, upstreamBody);
    QPointer<QTcpSocket> psock(sock);
    emit requestServed(path, reqObj.value(QStringLiteral("model")).toString());

    if (!stream) {
        connect(reply, &QNetworkReply::finished, this, [this, reply, psock, anthropic]() {
            if (!psock) { reply->deleteLater(); return; }
            const QByteArray raw = reply->readAll();
            QByteArray out = raw;
            if (anthropic) {
                const QJsonObject oai = QJsonDocument::fromJson(raw).object();
                out = QJsonDocument(openAIToAnthropic(oai)).toJson(QJsonDocument::Compact);
            }
            QByteArray r = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n";
            r += "Access-Control-Allow-Origin: *\r\n";
            r += "Content-Length: " + QByteArray::number(out.size()) + "\r\n\r\n" + out;
            psock->write(r); psock->flush(); psock->disconnectFromHost();
            reply->deleteLater();
        });
        return;
    }

    // ── Streaming ────────────────────────────────────────────────────────────
    // Headers SSE una sola vez.
    QByteArray hdr = "HTTP/1.1 200 OK\r\n";
    hdr += "Content-Type: text/event-stream\r\n";
    hdr += "Cache-Control: no-cache\r\n";
    hdr += "Access-Control-Allow-Origin: *\r\n";
    hdr += "Connection: close\r\n\r\n";
    sock->write(hdr); sock->flush();

    if (anthropic) {
        // Estado de traducción OpenAI-SSE → Anthropic-SSE (solo texto).
        auto *buf = new QByteArray;
        auto *started = new bool(false);
        const QString msgId = QStringLiteral("msg_") +
            QUuid::createUuid().toString(QUuid::WithoutBraces).left(24);

        auto sendEvent = [psock](const char *ev, const QJsonObject &data) {
            if (!psock) return;
            QByteArray e = "event: "; e += ev; e += "\r\n";
            e += "data: " + QJsonDocument(data).toJson(QJsonDocument::Compact) + "\r\n\r\n";
            psock->write(e); psock->flush();
        };

        connect(reply, &QNetworkReply::readyRead, this,
                [this, reply, psock, buf, started, msgId, sendEvent]() {
            if (!psock) return;
            buf->append(reply->readAll());
            while (true) {
                const int nl = buf->indexOf('\n');
                if (nl < 0) break;
                QByteArray line = buf->left(nl).trimmed();
                buf->remove(0, nl + 1);
                if (!line.startsWith("data:")) continue;
                const QByteArray d = line.mid(5).trimmed();
                if (d == "[DONE]") continue;
                const QJsonObject obj = QJsonDocument::fromJson(d).object();
                const QJsonArray choices = obj.value(QStringLiteral("choices")).toArray();
                if (choices.isEmpty()) continue;
                const QJsonObject delta = choices.first().toObject().value(QStringLiteral("delta")).toObject();
                const QString chunk = delta.value(QStringLiteral("content")).toString();
                if (chunk.isEmpty()) continue;
                if (!*started) {
                    *started = true;
                    sendEvent("message_start", QJsonObject{
                        {QStringLiteral("type"), QStringLiteral("message_start")},
                        {QStringLiteral("message"), QJsonObject{
                            {QStringLiteral("id"), msgId},
                            {QStringLiteral("type"), QStringLiteral("message")},
                            {QStringLiteral("role"), QStringLiteral("assistant")},
                            {QStringLiteral("content"), QJsonArray()},
                            {QStringLiteral("stop_reason"), QJsonValue::Null}
                        }}});
                    sendEvent("content_block_start", QJsonObject{
                        {QStringLiteral("type"), QStringLiteral("content_block_start")},
                        {QStringLiteral("index"), 0},
                        {QStringLiteral("content_block"), QJsonObject{
                            {QStringLiteral("type"), QStringLiteral("text")},
                            {QStringLiteral("text"), QStringLiteral("")}}}});
                }
                sendEvent("content_block_delta", QJsonObject{
                    {QStringLiteral("type"), QStringLiteral("content_block_delta")},
                    {QStringLiteral("index"), 0},
                    {QStringLiteral("delta"), QJsonObject{
                        {QStringLiteral("type"), QStringLiteral("text_delta")},
                        {QStringLiteral("text"), chunk}}}});
            }
        });
        connect(reply, &QNetworkReply::finished, this,
                [reply, psock, buf, started, sendEvent]() {
            if (psock) {
                if (*started) {
                    sendEvent("content_block_stop", QJsonObject{
                        {QStringLiteral("type"), QStringLiteral("content_block_stop")},
                        {QStringLiteral("index"), 0}});
                }
                sendEvent("message_delta", QJsonObject{
                    {QStringLiteral("type"), QStringLiteral("message_delta")},
                    {QStringLiteral("delta"), QJsonObject{
                        {QStringLiteral("stop_reason"), QStringLiteral("end_turn")}}}});
                sendEvent("message_stop", QJsonObject{
                    {QStringLiteral("type"), QStringLiteral("message_stop")}});
                psock->disconnectFromHost();
            }
            delete buf; delete started;
            reply->deleteLater();
        });
        return;
    }

    // OpenAI passthrough stream: relay crudo de bytes.
    connect(reply, &QNetworkReply::readyRead, this, [reply, psock]() {
        if (!psock) return;
        psock->write(reply->readAll()); psock->flush();
    });
    connect(reply, &QNetworkReply::finished, this, [reply, psock]() {
        if (psock) { psock->write(reply->readAll()); psock->flush(); psock->disconnectFromHost(); }
        reply->deleteLater();
    });
}
