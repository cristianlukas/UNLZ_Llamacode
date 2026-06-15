#pragma once
#include <QObject>
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
// Motor soportado: whisper.cpp `whisper-server` (endpoint `/inference`). El
// binario se resuelve desde un setting/PATH; los MODELOS ggml se descargan de
// HuggingFace (URLs estables) por la app.
class VoiceServerManager : public QObject
{
    Q_OBJECT
public:
    explicit VoiceServerManager(QObject *parent = nullptr);

    // Catálogo de motores STT: [{id,name,engine,modelFile,modelUrl,sizeMb,endpointPath,defaultPort}].
    static QVariantList sttCatalog();
    // Entrada del catálogo por id ({} si no existe).
    static QVariantMap sttEngine(const QString &id);

    // Rutas en disco (bajo AppLocalData/LlamaCode/voice/).
    static QString installRoot();
    static QString modelPath(const QString &engineId);   // "" si el id no está en el catálogo
    bool modelInstalled(const QString &engineId) const;

    // Descarga el modelo del motor (async). Emite installProgress/installFinished.
    void installModel(const QString &engineId);
    void cancelInstall();
    bool installing() const { return m_reply != nullptr; }

    // ── Funciones puras (testeables) ──
    // Args de whisper-server: -m <model> --host <h> --port <p> [-l <lang>].
    static QStringList buildWhisperArgs(const QString &modelPath, const QString &host,
                                        int port, const QString &language);
    // endpointPath del motor (ej "/inference" para whisper.cpp).
    static QString endpointPath(const QString &engineId);

signals:
    void installProgress(const QString &engineId, int pct, const QString &status);
    void installFinished(const QString &engineId, bool ok, const QString &message);

private:
    QNetworkAccessManager m_nam;
    QNetworkReply *m_reply = nullptr;
    QFile *m_file = nullptr;
    QString m_engineId;
};
