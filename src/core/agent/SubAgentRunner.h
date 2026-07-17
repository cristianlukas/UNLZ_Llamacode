#pragma once
#include <QObject>
#include <QByteArray>
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>

class QThread;
class AgentToolRunner;

// Sub-agente headless: corre un loop ReAct propio (sin UI/sesiones/MCP) contra
// el mismo llama-server, con su propio worker de tools confinado a `cwd` (una
// git worktree aislada). Lo usa la tool `task` del agente principal para delegar
// subtareas en paralelo. Emite finished(result) al terminar.
//
// Rol: define qué tools ve el sub-agente y con qué system prompt arranca.
//  · Coding — toolset completo, worktree git, hasta 40 iteraciones (tool `task`).
//  · Web    — SOLO web_search/web_fetch, sin worktree (no escribe nada), pocas
//             iteraciones. Lo usa `deep_research`: las páginas descargadas mueren
//             acá y al agente principal sólo le vuelve el informe sintetizado.
class SubAgentRunner : public QObject
{
    Q_OBJECT
public:
    enum class Role { Coding, Web };

    SubAgentRunner(const QString &id, const QString &serverBaseUrl, const QString &modelId,
                   const QString &cwd, const QString &taskPrompt,
                   double temperature, bool honey = false, QObject *parent = nullptr);
    ~SubAgentRunner() override;

    QString id() const { return m_id; }
    QString cwd() const { return m_cwd; }
    // Setear ANTES de start(); define toolset + system prompt + tope de iteraciones.
    void setRole(Role r) { m_role = r; }
    Role role() const { return m_role; }
    void start();
    void cancel();

    // Guardrail Zero-Autonomy en el sub-agente: como corre headless (sin HITL), no
    // puede pedir aprobación. Con el guardrail ON, una tool destructiva/irreversible
    // se RECHAZA de plano (no se ejecuta) y se le devuelve al sub-agente un mensaje
    // para que difiera la acción al agente principal. ON por defecto; lo propaga el
    // agente principal desde su propio m_hitlDestructive. Sin efecto en modo super.
    void setHitlDestructive(bool on) { m_hitlDestructive = on; }

    // System prompt del sub-agente. Pura y estática → unit-testeable. honey=true
    // suma la directiva de frugalidad (código YAGNI, respuesta-primero, salida
    // mínima) para que el sub-árbol entero emita menos. Se propaga desde la
    // directiva 'honey' del perfil del agente principal.
    static QString systemPrompt(const QString &cwd, bool honey);

    // System prompt del rol Web (investigación). Pura y estática → unit-testeable.
    static QString webSystemPrompt(bool honey);

    // Filtra un array de schemas OpenAI-style dejando sólo las tools en `allowed`.
    // Pura y estática → unit-testeable. `allowed` vacío = pasa todo.
    static QJsonArray filterToolSchemas(const QJsonArray &all, const QStringList &allowed);

    // Tools que ve cada rol. Vacío = todas (Coding).
    static QStringList toolsForRole(Role r);

    // Tope de iteraciones del loop ReAct según rol. Web es corto a propósito:
    // buscar+fetchear+sintetizar no necesita 40 vueltas, y un tope bajo acota el
    // costo de un sub-agente que se va por las ramas.
    static int maxItersForRole(Role r);

signals:
    void progressed(const QString &id, const QString &note);   // tool/avance (para tarjeta en vivo)
    void finished(const QString &id, const QString &result, bool ok);

private slots:
    void onToolExecuted(const QVariantMap &result);

private:
    void runCompletion();
    // Despacha el tool_call `call` al worker, salvo que el guardrail lo clasifique
    // destructivo: en ese caso NO ejecuta, inyecta un tool result de rechazo y sigue
    // con el resto del turno. Devuelve true si despachó (hay que esperar el worker),
    // false si lo bloqueó (ya avanzó al siguiente).
    bool dispatchCall(const QJsonObject &call);
    void handleStreamData();
    void handleStreamFinished(bool ok, const QString &err);
    void finishUp(const QString &result, bool ok);

    QString m_id;
    QString m_serverBaseUrl;
    QString m_modelId;
    QString m_cwd;
    QString m_taskPrompt;
    double  m_temperature = -1.0;
    bool    m_honey = false;
    Role    m_role = Role::Coding;
    bool    m_hitlDestructive = true;   // guardrail: rechazar destructivas (headless)

    QNetworkAccessManager *m_nam = nullptr;
    QNetworkReply *m_reply = nullptr;
    QThread *m_workerThread = nullptr;
    AgentToolRunner *m_worker = nullptr;

    QJsonArray m_messages;        // conversación API del sub-agente
    QJsonArray m_pendingCalls;    // tool_calls del turno actual
    QString    m_execCallId;
    QString    m_lastAssistantText;

    QByteArray m_sseBuf;
    QString    m_streamContent;
    QHash<int, QJsonObject> m_streamToolCalls;

    int  m_iters = 0;
    bool m_done = false;
};
