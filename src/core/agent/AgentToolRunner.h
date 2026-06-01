#pragma once
#include <QObject>
#include <QJsonObject>
#include <QList>
#include <QVariantList>
#include <QVariantMap>

class McpClient;

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
    void shutdown();

signals:
    void logAppended(const QString &chunk);
    void serversReady(const QVariantList &toolDefs); // {server,name,description,schema}
    void toolExecuted(const QVariantMap &result);

private:
    QString runNative(const QString &name, const QJsonObject &args,
                      const QString &cwd, QVariantMap &out, bool *ok);

    QList<McpClient *> m_mcp;
    bool m_confined = true;
};
