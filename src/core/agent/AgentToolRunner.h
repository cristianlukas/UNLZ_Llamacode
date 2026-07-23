#pragma once
#include <QObject>
#include <QByteArray>
#include <QElapsedTimer>
#include <QSet>
#include <QHash>
#include <QJsonObject>
#include <QList>
#include <QVariantList>
#include <QVariantMap>
#include <QStringList>

class McpClient;
class QProcess;
class QTimer;

// Ejecuta las tools del agente (nativas + MCP) en un hilo worker, para no
// bloquear el hilo de UI (run_shell, descarga de npx en el handshake MCP y
// tools/call pueden tardar). El loop ReAct vive en el hilo principal
// (LlamaAgentBackend) y se comunica con este worker por señales/slots en cola.
class AgentToolRunner : public QObject
{
    Q_OBJECT
public:
    explicit AgentToolRunner(QObject *parent = nullptr);
    ~AgentToolRunner() override;

public slots:
    // Lanza los servers MCP (config = lista de {name,command,type,enabled}) y
    // emite serversReady con las tool-defs descubiertas.
    void initServers(const QVariantList &cfg, const QString &cwd);
    // Ejecuta una tool. Emite toolExecuted(result) con: callId, name, result,
    // ok y (si es write) isWrite/relPath/absPath/diff/existed/oldContentB64.
    void executeTool(const QString &callId, const QString &name,
                     const QString &argsJson, const QString &cwd);
    // Confinamiento al cwd. false = "Super Agente" (acceso a todo el disco).
    void setConfined(bool confined);
    // Carpetas extra permitidas además del cwd (scope "folder" de una Task). Rutas
    // absolutas; vacío = solo el cwd. Sin efecto si !m_confined (acceso total).
    void setAllowedRoots(const QStringList &roots);
    // URL base del llama-server (para /v1/embeddings en semantic_search).
    void setServerBaseUrl(const QString &url);
    // Sesión activa del agente: la tool recent_actions filtra el event-log por ella.
    void setSessionId(const QString &sessionId);
    // Cuentas de correo (con password ya resuelto) para email_send/list/read.
    void setMailAccounts(const QVariantList &accounts);
    // Proveedores web externos habilitados desde Integrations:
    // {provider,baseUrl,apiKey,enabled}. No instala servicios.
    void setWebProviders(const QVariantList &providers);
    // Config del modelo maestro (tool ask_teacher). Vacío = usar env vars.
    void setTeacherConfig(const QString &url, const QString &model, const QString &key);
    // Config de maestro tipo CLI (claude-code / codex). cliPath vacío = deshabilitado.
    // Si kind=="cli" la tool ask_teacher invoca el CLI en vez del endpoint HTTP.
    void setMasterCli(const QString &kind, const QString &cliName, const QString &cliPath,
                      bool applyEdits, int timeoutSec);
    // Cadena de fallbacks del maestro (resuelta: keys y cliPath ya resueltos por
    // AppController). Cada entry es un QVariantMap con: type (http|cli), cliName,
    // cliPath, httpUrl, httpModel, httpKey, applyEdits, timeoutSec, label.
    // Si la cadena está vacía, ask_teacher usa la config legacy/env.
    void setMasterChain(const QVariantList &chain);
    // Frugalidad "honey" en handoffs inter-agente: cuando está ON, el system
    // prompt del maestro (ask_teacher) le pide responder en formato denso
    // clave:valor en vez de prosa. Se propaga desde la directiva 'honey' del
    // perfil de agente. No cambia QUÉ se pregunta, sólo el formato de respuesta.
    void setHoneyHandoff(bool on);
    // Mata el run_shell en curso (cancelación real desde PARAR/steer).
    void cancelShell();
    void shutdown();

signals:
    void logAppended(const QString &chunk);
    void serversReady(const QVariantList &toolDefs); // {server,name,description,schema}
    void toolExecuted(const QVariantMap &result);
    // run_shell async: arranque (crea tarjeta en vivo) y chunks de salida.
    void toolStarted(const QVariantMap &info);       // {callId,name,kind,command}
    void toolOutputChunk(const QString &callId, const QString &chunk);

private slots:
    void onShellReadyRead();
    void onShellFinished();
    void onShellTimeout();

private:
    QString runNative(const QString &name, const QJsonObject &args,
                      const QString &cwd, QVariantMap &out, bool *ok);
public:
    // System prompt del maestro para los handoffs de ask_teacher. Pura y estática
    // → unit-testeable. honey=true pide respuesta densa clave:valor (frugalidad).
    static QString masterSystemPrompt(bool honey);
    // Helpers puros de la superficie web. La validación bloquea destinos locales,
    // privados y metadata antes de cualquier request; la extracción prioriza el
    // contenido principal y conserva estructura legible con presupuesto acotado.
    static bool isSafePublicWebUrl(const QString &url, QString *error = nullptr);
    static QString extractReadableWebText(const QString &html);
    static QStringList webEscalationReasons(const QString &html, const QString &text,
                                            const QString &transportError = QString());
    // Adapters individuales, públicos para probes/E2E sin pasar por la política.
    QString fetchViaPlaywright(const QString &url, QString *error);
    QString fetchViaCamofox(const QString &url, QString *error);
    bool consumeWebRateLimit(const QString &host, qint64 nowMs, QString *error = nullptr);
private:
    void startShell(const QString &callId, const QString &command,
                    const QString &cwd, int timeoutS);
    void finishShell(bool timedOut, bool cancelled);

    QList<McpClient *> m_mcp;
    bool m_confined = true;
    QStringList m_allowedRoots;   // carpetas extra permitidas (scope "folder")
    QString m_serverBaseUrl;
    QString m_sessionId;           // sesión activa (filtro de recent_actions)
    QVariantList m_mailAccounts;   // cuentas de correo con password resuelto
    QVariantList m_webProviders;   // proveedores REST opt-in (p.ej. Camofox)
    QHash<QString, QList<qint64>> m_webRequestTimes; // rate limit por host, ventana 60 s
    QString m_teacherUrl, m_teacherModel, m_teacherKey;   // ask_teacher (override de env)
    // Maestro CLI (claude-code / codex). m_masterKind: "none"|"http"|"cli".
    QString m_masterKind = QStringLiteral("none");
    QString m_masterCliName, m_masterCliPath;
    bool    m_masterApplyEdits = true;
    int     m_masterTimeoutS = 300;
    QVariantList m_masterChain;   // cadena de fallbacks resuelta (ver setMasterChain)
    bool    m_honeyHandoff = false;  // directiva honey: respuesta densa del maestro
    // Ejecuta el CLI maestro de forma bloqueante (worker thread). Devuelve stdout
    // o un mensaje [ask_teacher: ...] de error.
    QString runMasterCli(const QString &cliName, const QString &cliPath, bool applyEdits,
                         int timeoutSec, const QString &question, const QString &context,
                         const QString &cwd, bool *ok);
    // Consulta HTTP OpenAI-compat a un maestro. ok=true si hubo respuesta útil.
    QString runHttpTeacher(const QString &url, const QString &model, const QString &key,
                           const QString &question, const QString &context, bool *ok);
    // Recorre la cadena de fallbacks en orden; devuelve la primera respuesta OK.
    QString runMasterChain(const QString &question, const QString &context,
                           const QString &cwd, bool *ok);

    // Estado del run_shell async en curso (uno a la vez; el loop es secuencial).
    QProcess   *m_shellProc = nullptr;
    QTimer     *m_shellTimer = nullptr;
    QString     m_shellCallId;
    QByteArray  m_shellOut;          // salida acumulada
    QElapsedTimer m_shellClock;
    int         m_shellTimeoutS = 120;
    QSet<QString> m_projectBrainDirtyPaths;
};
