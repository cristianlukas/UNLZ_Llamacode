#pragma once
#include "VoiceTypes.h"
#include <QObject>
#include <QByteArray>
#include <QPointer>
#include <QVariantMap>
#include <QNetworkAccessManager>

class QNetworkReply;
class QProcess;

// Cliente STT contra un endpoint OpenAI-compatible (/v1/audio/transcriptions).
// Sirve igual para un server local (whisper.cpp) o cloud (key vía Bearer).
class SttEngine : public QObject
{
    Q_OBJECT
public:
    explicit SttEngine(QObject *parent = nullptr);

    // resolvedKey: API key ya resuelta (vacía para local). cfg trae baseUrl/model/lang.
    void setConfig(const VoiceConfig &cfg, const QString &resolvedKey);

    // Transcribe PCM16 mono crudo. Lo envuelve en WAV y lo postea como multipart.
    void transcribe(const QByteArray &pcm16, int sampleRate);

    // Sidecar streaming protocol NDJSON v1. The QProcess is owned by
    // AppController so it participates in the existing Job Object lifecycle;
    // this class only attaches to its stdout/stdin for the active session.
    void attachStreamingProcess(QProcess *process);
    bool startStreaming(int sampleRate);
    void pushStreamingAudio(const QByteArray &pcm16);
    void finishStreaming();
    bool streaming() const { return m_streamingActive; }
    bool busy() const { return m_reply != nullptr || m_streamingActive; }
    void cancel();

    // ── Funciones puras (testeables sin red) ──
    // Cuerpo multipart/form-data con los campos file/model[/language].
    static QByteArray buildMultipart(const QByteArray &boundary, const QByteArray &wav,
                                     const QString &model, const QString &language);
    // Extrae el campo "text" de la respuesta JSON de transcripción.
    static QString parseTranscript(const QByteArray &json);

    // ── Protocolo NDJSON v1 (funciones puras) ──
    static QByteArray buildStreamingConfig(int sampleRate, const QString &language,
                                           const QString &model);
    static QByteArray buildStreamingAudio(const QByteArray &pcm16, quint64 sequence);
    static QByteArray buildStreamingEnd();
    static QByteArray buildStreamingCancel();
    static QVariantMap parseStreamingMessage(const QByteArray &line);

signals:
    void transcribed(const QString &text);
    void failed(const QString &error);
    void partialTranscribed(const QString &text);
    void streamingFinished(const QString &text);

private:
    void consumeStreamingOutput();
    void handleStreamingMessage(const QVariantMap &message);

    VoiceConfig m_cfg;
    QString m_key;
    QNetworkAccessManager m_nam;
    QNetworkReply *m_reply = nullptr;
    QPointer<QProcess> m_streamProcess;
    QByteArray m_streamOutput;
    QString m_streamLatestText;
    quint64 m_streamSequence = 0;
    bool m_streamingActive = false;
    bool m_streamEndRequested = false;
    bool m_streamFinalSeen = false;
};
