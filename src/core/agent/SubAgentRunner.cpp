#include "SubAgentRunner.h"
#include "AgentToolRunner.h"
#include "LlamaAgentBackend.h"   // toolSchemas() (built-in)

#include <QJsonDocument>
#include <QNetworkRequest>
#include <QRegularExpression>
#include <QThread>
#include <QUrl>
#include <algorithm>

static QString subArgsToString(const QJsonValue &v)
{
    if (v.isString()) return v.toString();
    if (v.isObject()) return QString::fromUtf8(QJsonDocument(v.toObject()).toJson(QJsonDocument::Compact));
    return {};
}

SubAgentRunner::SubAgentRunner(const QString &id, const QString &serverBaseUrl,
                               const QString &modelId, const QString &cwd,
                               const QString &taskPrompt, double temperature,
                               bool honey, QObject *parent)
    : QObject(parent), m_id(id), m_serverBaseUrl(serverBaseUrl), m_modelId(modelId),
      m_cwd(cwd), m_taskPrompt(taskPrompt), m_temperature(temperature), m_honey(honey)
{
    m_nam = new QNetworkAccessManager(this);
}

QString SubAgentRunner::systemPrompt(const QString &cwd, bool honey)
{
    QString sys = QStringLiteral(
        "Sos un sub-agente de coding autónomo. Trabajás en una copia aislada del "
        "proyecto (git worktree) en: %1. Tenés tools para leer/escribir/editar "
        "archivos, listar, buscar (grep/glob) y ejecutar shell, todas confinadas a "
        "esa carpeta. Resolvé la subtarea encomendada de forma completa y autónoma "
        "(no pidas permisos, no preguntes). Cuando termines, respondé con un RESUMEN "
        "conciso de qué hiciste y qué archivos cambiaste. Sé directo.")
        .arg(cwd);
    if (honey)
        sys += QStringLiteral(
            "\n\nFRUGALIDAD (honey): emití lo mínimo. Código YAGNI: parar en el "
            "primer escalón que funciona, sin scaffolding especulativo. "
            "Respuesta-primero, sin narrar lo que ya se lee en el código. El RESUMEN "
            "final en clave:valor compacto (files: ..., changes: ...), no prosa.");
    return sys;
}

QString SubAgentRunner::webSystemPrompt(bool honey)
{
    QString sys = QStringLiteral(
        "Sos un sub-agente de INVESTIGACIÓN WEB. Tenés exactamente dos tools: "
        "web_search (buscar) y web_fetch (descargar una URL y leer su texto). No "
        "tenés acceso al proyecto ni podés escribir archivos ni ejecutar comandos: "
        "tu único trabajo es investigar y redactar.\n\n"
        "Método:\n"
        "1. Buscá con web_search por varios ángulos distintos del tema (no repitas "
        "la misma consulta reformulada).\n"
        "2. Abrí con web_fetch las páginas que valgan la pena. Priorizá fuentes "
        "primarias (docs oficiales, repos, papers) sobre agregadores.\n"
        "3. Si las fuentes se contradicen, decilo explícitamente en vez de elegir "
        "una en silencio.\n\n"
        "Cuando termines, respondé con un INFORME en markdown:\n"
        "· Una respuesta directa a la pregunta, arriba de todo.\n"
        "· El detalle que la sostiene, citando las fuentes por número [n].\n"
        "· Una sección '## Fuentes' con la lista numerada (título — URL).\n"
        "· Lo que NO pudiste averiguar, si quedó algo abierto.\n\n"
        "El informe es lo único que vuelve: quien te llamó no ve las páginas que "
        "abriste. Todo lo que importe tiene que estar en el informe. No afirmes "
        "nada que no venga de una fuente que abriste.");
    if (honey)
        sys += QStringLiteral(
            "\n\nFRUGALIDAD (honey): informe corto y denso. Sin preámbulo, sin "
            "narrar el proceso de búsqueda. Respuesta-primero.");
    return sys;
}

QStringList SubAgentRunner::toolsForRole(Role r)
{
    if (r == Role::Web)
        return {QStringLiteral("web_search"), QStringLiteral("web_fetch")};
    return {};   // Coding: toolset completo
}

int SubAgentRunner::maxItersForRole(Role r)
{
    return r == Role::Web ? 12 : 40;
}

QJsonArray SubAgentRunner::filterToolSchemas(const QJsonArray &all, const QStringList &allowed)
{
    if (allowed.isEmpty()) return all;
    QJsonArray out;
    for (const QJsonValue &v : all) {
        const QString name = v.toObject().value(QStringLiteral("function")).toObject()
                                 .value(QStringLiteral("name")).toString();
        if (allowed.contains(name)) out.append(v);
    }
    return out;
}

SubAgentRunner::~SubAgentRunner()
{
    if (m_reply) { m_reply->abort(); m_reply->deleteLater(); m_reply = nullptr; }
    if (m_workerThread) {
        if (m_worker) {
            disconnect(m_worker, nullptr, this, nullptr);
            QMetaObject::invokeMethod(m_worker, "shutdown", Qt::BlockingQueuedConnection);
        }
        m_workerThread->quit();
        if (!m_workerThread->wait(5000)) { m_workerThread->terminate(); m_workerThread->wait(1000); }
        delete m_worker;
        delete m_workerThread;
    }
}

void SubAgentRunner::start()
{
    // Worker propio (tools confinadas a la worktree).
    m_workerThread = new QThread(this);
    m_worker = new AgentToolRunner;
    m_worker->moveToThread(m_workerThread);
    m_worker->setConfined(true);
    m_worker->setServerBaseUrl(m_serverBaseUrl);
    connect(m_worker, &AgentToolRunner::toolExecuted, this, &SubAgentRunner::onToolExecuted);
    m_workerThread->start();

    const QString sys = m_role == Role::Web ? webSystemPrompt(m_honey)
                                            : systemPrompt(m_cwd, m_honey);

    m_messages = QJsonArray{
        QJsonObject{{QStringLiteral("role"), QStringLiteral("system")}, {QStringLiteral("content"), sys}},
        QJsonObject{{QStringLiteral("role"), QStringLiteral("user")}, {QStringLiteral("content"), m_taskPrompt}}
    };
    runCompletion();
}

void SubAgentRunner::cancel()
{
    if (m_done) return;
    if (m_reply) { QNetworkReply *r = m_reply; m_reply = nullptr; r->disconnect(this); r->abort(); r->deleteLater(); }
    if (m_worker) QMetaObject::invokeMethod(m_worker, "cancelShell", Qt::QueuedConnection);
    finishUp(QStringLiteral("[sub-agente cancelado]"), false);
}

void SubAgentRunner::runCompletion()
{
    if (m_done) return;
    if (++m_iters > maxItersForRole(m_role)) { finishUp(m_lastAssistantText + QStringLiteral("\n[corte: límite de iteraciones]"), false); return; }

    QJsonObject payload{
        {QStringLiteral("model"), m_modelId.isEmpty() ? QStringLiteral("local") : m_modelId},
        {QStringLiteral("messages"), m_messages},
        {QStringLiteral("tools"), filterToolSchemas(LlamaAgentBackend::toolSchemas(),
                                                    toolsForRole(m_role))},
        {QStringLiteral("tool_choice"), QStringLiteral("auto")},
        {QStringLiteral("parallel_tool_calls"), false},
        {QStringLiteral("parse_tool_calls"), false},
        {QStringLiteral("max_tokens"), 8192},
        {QStringLiteral("stream"), true},
        {QStringLiteral("cache_prompt"), true}
    };
    if (m_temperature >= 0.0) payload.insert(QStringLiteral("temperature"), m_temperature);

    QNetworkRequest req((QUrl(m_serverBaseUrl + QStringLiteral("/v1/chat/completions"))));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QByteArrayLiteral("application/json"));

    m_sseBuf.clear();
    m_streamContent.clear();
    m_streamToolCalls.clear();
    m_reply = m_nam->post(req, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    connect(m_reply, &QNetworkReply::readyRead, this, [this]() { handleStreamData(); });
    connect(m_reply, &QNetworkReply::finished, this, [this]() {
        QNetworkReply *r = m_reply;
        if (!r) return;
        const bool ok = r->error() == QNetworkReply::NoError;
        const QString err = r->errorString();
        m_reply = nullptr;
        r->deleteLater();
        handleStreamFinished(ok, err);
    });
}

void SubAgentRunner::handleStreamData()
{
    if (!m_reply) return;
    m_sseBuf.append(m_reply->readAll());
    while (true) {
        const int nl = m_sseBuf.indexOf('\n');
        if (nl < 0) break;
        const QByteArray line = m_sseBuf.left(nl).trimmed();
        m_sseBuf.remove(0, nl + 1);
        if (!line.startsWith("data: ")) continue;
        const QByteArray data = line.mid(6).trimmed();
        if (data == "[DONE]") continue;
        const QJsonDocument d = QJsonDocument::fromJson(data);
        if (!d.isObject()) continue;
        const QJsonArray choices = d.object().value(QStringLiteral("choices")).toArray();
        if (choices.isEmpty()) continue;
        const QJsonObject delta = choices.first().toObject().value(QStringLiteral("delta")).toObject();
        m_streamContent += delta.value(QStringLiteral("content")).toString();
        const QJsonArray tcs = delta.value(QStringLiteral("tool_calls")).toArray();
        for (const QJsonValue &tv : tcs) {
            const QJsonObject tc = tv.toObject();
            const int idx = tc.value(QStringLiteral("index")).toInt(0);
            QJsonObject acc = m_streamToolCalls.value(idx);
            if (tc.contains(QStringLiteral("id"))) acc[QStringLiteral("id")] = tc.value(QStringLiteral("id")).toString();
            const QJsonObject fn = tc.value(QStringLiteral("function")).toObject();
            if (fn.contains(QStringLiteral("name"))) acc[QStringLiteral("name")] = fn.value(QStringLiteral("name")).toString();
            if (fn.contains(QStringLiteral("arguments")))
                acc[QStringLiteral("arguments")] = acc.value(QStringLiteral("arguments")).toString()
                                                   + fn.value(QStringLiteral("arguments")).toString();
            m_streamToolCalls.insert(idx, acc);
        }
    }
}

void SubAgentRunner::handleStreamFinished(bool ok, const QString &err)
{
    if (m_done) return;
    if (!ok) { finishUp(QStringLiteral("[error de red en sub-agente: %1]").arg(err), false); return; }

    // Quitar <think> del texto (el sub-agente no necesita reenviarlo).
    QString content = m_streamContent;
    content.remove(QRegularExpression(QStringLiteral("<think>[\\s\\S]*?</think>"),
                                      QRegularExpression::CaseInsensitiveOption));
    content = content.trimmed();
    if (!content.isEmpty()) m_lastAssistantText = content;

    QJsonArray toolCalls;
    QList<int> idxs = m_streamToolCalls.keys();
    std::sort(idxs.begin(), idxs.end());
    for (int i : idxs) {
        const QJsonObject acc = m_streamToolCalls.value(i);
        QString argStr = acc.value(QStringLiteral("arguments")).toString();
        QJsonParseError perr;
        QJsonDocument::fromJson(argStr.toUtf8(), &perr);
        if (perr.error != QJsonParseError::NoError && !argStr.trimmed().isEmpty())
            argStr = QStringLiteral("{}");
        toolCalls.append(QJsonObject{
            {QStringLiteral("id"), acc.value(QStringLiteral("id")).toString()},
            {QStringLiteral("type"), QStringLiteral("function")},
            {QStringLiteral("function"), QJsonObject{
                {QStringLiteral("name"), acc.value(QStringLiteral("name")).toString()},
                {QStringLiteral("arguments"), argStr}}}});
    }

    if (toolCalls.isEmpty()) {
        finishUp(content.isEmpty() ? QStringLiteral("[sub-agente terminó sin resumen]") : content, true);
        return;
    }

    m_messages.append(QJsonObject{
        {QStringLiteral("role"), QStringLiteral("assistant")},
        {QStringLiteral("content"), content},
        {QStringLiteral("tool_calls"), toolCalls}});
    m_pendingCalls = toolCalls;

    // Ejecutar el primer tool_call (secuencial dentro del sub-agente). Si el
    // guardrail lo bloquea, dispatchCall avanza solo hasta despachar/terminar.
    while (!m_pendingCalls.isEmpty()) {
        if (dispatchCall(m_pendingCalls.first().toObject())) return;  // esperando worker
        m_pendingCalls.removeFirst();                                 // bloqueado → siguiente
    }
    runCompletion();
}

bool SubAgentRunner::dispatchCall(const QJsonObject &call)
{
    const QJsonObject fn = call.value(QStringLiteral("function")).toObject();
    const QString name = fn.value(QStringLiteral("name")).toString();
    const QString id = call.value(QStringLiteral("id")).toString();
    const QString argStr = subArgsToString(fn.value(QStringLiteral("arguments")));

    // Gating por rol: filtrar el schema no alcanza — un modelo chico igual puede
    // inventar un nombre de tool que no le pasamos. El rol es el límite real.
    const QStringList allowed = toolsForRole(m_role);
    if (!allowed.isEmpty() && !allowed.contains(name)) {
        emit progressed(m_id, QStringLiteral("⛔ %1 (fuera del rol)").arg(name));
        m_messages.append(QJsonObject{
            {QStringLiteral("role"), QStringLiteral("tool")},
            {QStringLiteral("tool_call_id"), id},
            {QStringLiteral("content"), QStringLiteral(
                "[rol: '%1' no existe para vos. Tus únicas tools son: %2. "
                "Seguí con esas y terminá con el informe.]")
                 .arg(name, allowed.join(QStringLiteral(", ")))}});
        return false;   // bloqueada; el caller avanza al siguiente
    }

    // Guardrail: el sub-agente no tiene HITL → rechazar destructivas de plano.
    if (m_hitlDestructive) {
        QJsonParseError perr;
        const QJsonObject args =
            QJsonDocument::fromJson(argStr.toUtf8(), &perr).object();
        if (LlamaAgentBackend::isDestructiveAction(name, args)) {
            emit progressed(m_id, QStringLiteral("⛔ %1 (bloqueada: destructiva)").arg(name));
            m_messages.append(QJsonObject{
                {QStringLiteral("role"), QStringLiteral("tool")},
                {QStringLiteral("tool_call_id"), id},
                {QStringLiteral("content"), QStringLiteral(
                    "[guardrail: '%1' es una acción destructiva/irreversible y está "
                    "prohibida dentro de un sub-agente (no hay aprobación humana). "
                    "NO la ejecutes. Reportá al agente principal que esta acción "
                    "requiere confirmación y dejá que él la maneje.]").arg(name)}});
            return false;   // bloqueada; el caller avanza al siguiente
        }
    }

    emit progressed(m_id, QStringLiteral("🔧 %1").arg(name));
    m_execCallId = id;
    QMetaObject::invokeMethod(m_worker, "executeTool", Qt::QueuedConnection,
                              Q_ARG(QString, id), Q_ARG(QString, name),
                              Q_ARG(QString, argStr), Q_ARG(QString, m_cwd));
    return true;
}

void SubAgentRunner::onToolExecuted(const QVariantMap &result)
{
    if (m_done) return;
    const QString callId = result.value(QStringLiteral("callId")).toString();
    if (callId.isEmpty() || callId != m_execCallId) return;
    m_execCallId.clear();
    const QString res = result.value(QStringLiteral("result")).toString().left(16 * 1024);

    m_messages.append(QJsonObject{
        {QStringLiteral("role"), QStringLiteral("tool")},
        {QStringLiteral("tool_call_id"), callId},
        {QStringLiteral("content"), res}});

    if (!m_pendingCalls.isEmpty()) m_pendingCalls.removeFirst();
    // Siguiente tool del mismo turno (saltando las que el guardrail bloquee).
    while (!m_pendingCalls.isEmpty()) {
        if (dispatchCall(m_pendingCalls.first().toObject())) return;  // esperando worker
        m_pendingCalls.removeFirst();
    }
    runCompletion();   // re-consultar con los resultados
}

void SubAgentRunner::finishUp(const QString &result, bool ok)
{
    if (m_done) return;
    m_done = true;
    emit finished(m_id, result, ok);
}
