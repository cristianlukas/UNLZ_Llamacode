#pragma once
#include <QObject>
#include <QHostAddress>
#include <QJsonObject>
#include <QString>
#include <QStringList>
#include <functional>

class QTcpServer;
class QTcpSocket;
class QNetworkAccessManager;
class QNetworkReply;

// LlmGateway — proxy HTTP delante del llama-server activo. Aporta lo que el
// llama-server crudo no da:
//   • Endpoint Anthropic-compatible /v1/messages (Claude Code → tu GPU local).
//   • Auto-load por nombre de modelo: el request nombra un modelo y el gateway
//     lo carga al vuelo (vía callbacks al AppController) antes de reenviar.
//   • Pool LRU keepN (bookkeeping; con un solo server efectivo = swap del activo).
//   • Bump de actividad para el idle auto-stop.
//
// La lógica de traducción / resolución / LRU son funciones PURAS estáticas
// (unit-testeables sin red). El runtime es un QTcpServer que reenvía con QNAM.
class LlmGateway : public QObject
{
    Q_OBJECT
public:
    explicit LlmGateway(QObject *parent = nullptr);
    ~LlmGateway() override;

    // Callbacks que inyecta AppController (desacople: el gateway no conoce al app).
    struct Hooks {
        std::function<QString()>      baseUrl;        // url del llama-server activo
        std::function<bool()>         ready;          // server listo (health ok)
        std::function<QString()>      currentModel;   // modelo cargado ahora
        std::function<QStringList()>  modelNames;     // modelos disponibles (catálogo+perfiles)
        std::function<void(QString)>  ensureModel;    // pedir carga de un modelo
        std::function<void()>         activity;       // bump idle watchdog
    };
    void setHooks(const Hooks &h) { m_hooks = h; }
    void setKeepN(int n) { m_keepN = qMax(1, n); }
    void setAutoSwap(bool on) { m_autoSwap = on; }
    void setApiKey(const QString &k) { m_apiKey = k; }   // vacío = sin auth

    bool start(quint16 port, const QHostAddress &addr = QHostAddress::LocalHost);
    void stop();
    bool listening() const;
    quint16 port() const { return m_port; }

    // ── Funciones puras (testeables) ─────────────────────────────────────────
    // Anthropic /v1/messages → OpenAI /v1/chat/completions (request).
    static QJsonObject anthropicToOpenAI(const QJsonObject &anthropic);
    // OpenAI respuesta no-stream → Anthropic /v1/messages respuesta.
    static QJsonObject openAIToAnthropic(const QJsonObject &openai);
    // Resolver el modelo pedido contra la librería (match exacto > substring > "").
    static QString resolveModel(const QString &requested, const QStringList &available);
    // LRU: registrar uso de `name`; devuelve los ids a desalojar (size > keepN).
    static QStringList lruTouch(QStringList &order, const QString &name, int keepN);
    // Inyecta salida estructurada (grammar GBNF o json_schema) en un payload OpenAI.
    static QJsonObject applyStructuredOutput(QJsonObject payload,
                                             const QString &grammar,
                                             const QJsonObject &jsonSchema);

signals:
    void requestServed(const QString &path, const QString &model);

private:
    void onNewConnection();
    void handle(QTcpSocket *sock, const QByteArray &method, const QString &path,
                const QByteArray &body, const QString &authHeader);
    void forward(QTcpSocket *sock, const QString &path, const QByteArray &body,
                 bool anthropic, bool stream);
    void writeError(QTcpSocket *sock, int code, const QString &msg);

    QTcpServer            *m_server = nullptr;
    QNetworkAccessManager *m_nam = nullptr;
    Hooks   m_hooks;
    int     m_keepN = 4;
    bool    m_autoSwap = true;
    QString m_apiKey;
    quint16 m_port = 0;
    QStringList m_lru;   // orden de uso (frente = más reciente)
};
