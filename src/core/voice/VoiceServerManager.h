#pragma once
#include <QObject>
#include <functional>
#include <QJsonArray>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QNetworkAccessManager>

class QNetworkReply;
class QFile;

// Gestión de motores STT locales "gestionados": catálogo de modelos instalables,
// descarga del modelo a AppLocalData y construcción del comando del server. El
// proceso del server lo lanza AppController (Job Object + lifecycle), igual que
// llama-server; acá solo vive lo descargable + las funciones puras (testeables).
//
// whisper.cpp se administra de forma nativa. Parakeet se administra mediante
// su CLI nativo incluido en el paquete de whisper.cpp; otros motores pueden
// conectarse como sidecars explícitos con el protocolo streaming NDJSON v1.
// Así el binario Qt no incorpora runtimes Python/NeMo/ONNX pesados.
class VoiceServerManager : public QObject
{
    Q_OBJECT
public:
    explicit VoiceServerManager(QObject *parent = nullptr);

    // Catálogo de motores STT: incluye transport/installable/requiresCommand
    // para distinguir servidores batch de sidecars streaming.
    static QVariantList sttCatalog();
    // Entrada del catálogo por id ({} si no existe).
    static QVariantMap sttEngine(const QString &id);

    // Catálogo de voces TTS (piper): [{id,name,lang,modelFile,modelUrl,jsonUrl,sizeMb}].
    static QVariantList ttsCatalog();
    static QVariantMap ttsVoice(const QString &id);
    // Voz piper por defecto para un código de idioma (es/en/...). Si no hay voz
    // para ese idioma, cae a la voz española base. Pura (testeable).
    static QString defaultTtsVoiceForLang(const QString &lang);

    // Rutas en disco (bajo AppLocalData/LlamaCode/voice/).
    static QString installRoot();
    static QString modelPath(const QString &engineId);   // STT: "" si el id no está en el catálogo
    bool modelInstalled(const QString &engineId) const;
    static QString ttsModelPath(const QString &voiceId); // ruta del .onnx de la voz piper
    bool ttsVoiceInstalled(const QString &voiceId) const;

    // Pocket TTS: runtime aislado y script HTTP residente bajo la instalación
    // administrada. El script se extrae desde los recursos de la aplicación.
    static QString pocketRoot();
    static QString pocketVenvDir();
    static QString pocketManagedPythonPath();
    static QString pocketCacheDir();
    static QString pocketServerScriptPath();
    static int pocketDefaultPort();
    static bool pocketRuntimeInstalled();
    static bool pocketServerScriptAvailable();
    static bool ensurePocketServerScript(QString *error = nullptr);

    // Descarga del modelo STT / de la voz TTS (async). Emite installProgress/installFinished.
    void installModel(const QString &engineId);
    void installTtsVoice(const QString &voiceId);
    void cancelInstall();
    bool installing() const { return m_reply != nullptr; }

    // ── Binarios (whisper-server / piper): descarga del release + extracción ──
    // kind: "whisper-server" | "piper". URL por defecto por SO (overridable).
    static QString defaultBinaryUrl(const QString &kind);
    // whisper.cpp dejó de adjuntar binarios a los releases vX.Y.Z (quedan con 0
    // assets) y los publica en releases por build (bNNNN): el viejo
    // releases/latest/download/whisper-bin-x64.zip daba 404 y Charla no se podía
    // instalar en Windows. Se resuelve contra la API de releases buscando el
    // primer release que traiga alguno de estos assets (orden de preferencia).
    static QStringList whisperServerAssetNames();
    // Puerto para un server de voz gestionado: el preferido si está libre y no
    // es uno a evitar (p.ej. el del LLM activo, que en varios perfiles también
    // es 8081 = el default de whisper), si no el siguiente libre. -1 si no hay.
    // isFree se inyecta para testear sin abrir sockets.
    static int pickManagedPort(int preferred, const QList<int> &avoid,
                               const std::function<bool(int)> &isFree, int span = 64);
    static bool localPortFree(int port);
    // Pura: URL del primer asset (por preferencia) del release más reciente que
    // lo tenga. "" si ninguno lo trae.
    static QString pickReleaseAssetUrl(const QJsonArray &releases, const QStringList &assetNames);
    static QString binDir();
    // Localiza un binario ya extraído dentro del directorio administrado.
    static QString installedBinaryPath(const QString &kind);
    // Descarga el archivo (zip/tar.gz), lo extrae y localiza el ejecutable.
    // urlOverride vacío = usar defaultBinaryUrl. Emite binaryInstalled(kind,ok,path,msg).
    void installBinary(const QString &kind, const QString &urlOverride = QString());
private:
    void startBinaryDownload(const QString &kind, const QString &url);
public:

    // ── Funciones puras (testeables) ──
    // Args de whisper-server: -m <model> --host <h> --port <p> [-l <lang>].
    static QStringList buildWhisperArgs(const QString &modelPath, const QString &host,
                                        int port, const QString &language);
    // endpointPath del motor (ej "/inference" para whisper.cpp).
    static QString endpointPath(const QString &engineId);
    // Args de piper (process-mode): -m <model> -f <outWav> (texto por stdin).
    static QStringList buildPiperArgs(const QString &modelPath, const QString &outWav);
    // Args de piper residente (streaming): -m <model> --json-input --output_dir
    // <dir>. Lee una línea JSON por turno y escribe un wav por línea sin recargar
    // el modelo. Cada línea JSON lleva su propio output_file (ver
    // TtsEngine::buildPiperJsonLine).
    static QStringList buildPiperResidentArgs(const QString &modelPath, const QString &outDir);
    // Args del sidecar residente Pocket TTS. Se pasan sin shell al intérprete
    // Python administrado por la app.
    static QStringList buildPocketServerArgs(const QString &scriptPath,
                                             const QString &language,
                                             const QString &voice,
                                             const QString &modelConfig,
                                             int port, bool quantize);

signals:
    void installProgress(const QString &engineId, int pct, const QString &status);
    void installFinished(const QString &engineId, bool ok, const QString &message);
    // Fin de la instalación de un binario: path = ejecutable localizado (si ok).
    void binaryInstalled(const QString &kind, bool ok, const QString &path, const QString &message);

private:
    // Descarga secuencial de una lista de (url, destino). Emite progreso global.
    void startDownloadQueue(const QString &id, const QList<QPair<QString, QString>> &files);
    void downloadNext();

    QNetworkAccessManager m_nam;
    QNetworkReply *m_reply = nullptr;
    QFile *m_file = nullptr;
    QString m_engineId;
    QList<QPair<QString, QString>> m_dlQueue;  // pendientes (url, dest)
    int m_dlTotal = 0;                          // total de archivos del job

    // Instalación de binarios (descarga + extracción).
    void extractAndLocate(const QString &kind, const QString &archive, const QString &destDir);
    QString m_binKind;
    class QProcess *m_extractProc = nullptr;
};
