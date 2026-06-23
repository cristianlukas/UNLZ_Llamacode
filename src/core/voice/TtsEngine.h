#pragma once
#include "VoiceTypes.h"
#include <QObject>
#include <QByteArray>
#include <QNetworkAccessManager>

class QNetworkReply;

// Cliente TTS contra un endpoint OpenAI-compatible (/v1/audio/speech).
// Local (openedai-speech / piper-http) o cloud (key vía Bearer). Devuelve el
// audio crudo (formato según cfg.ttsFormat) por audioReady().
class TtsEngine : public QObject
{
    Q_OBJECT
public:
    explicit TtsEngine(QObject *parent = nullptr);

    void setConfig(const VoiceConfig &cfg, const QString &resolvedKey);
    // Rutas para modo piper (process-mode). bin vacío = buscar "piper" en PATH.
    void setPiper(const QString &binPath, const QString &modelPath);

    void synthesize(const QString &text);
    // Ocupado = hay un request en vuelo (HTTP, spawn per-call, o turno pendiente
    // en el piper residente). El proceso residente vivo NO cuenta como ocupado.
    bool busy() const { return m_reply != nullptr || m_piper != nullptr || m_piperPending; }
    void cancel();

    // ¿Hay una voz piper local instalada (modelo .onnx presente)? Fallback cuando
    // el endpoint TTS HTTP no responde. Público para test.
    bool piperAvailable() const;

    // ── Funciones puras (testeables sin red ni proceso) ──
    // Body JSON del request /v1/audio/speech.
    static QByteArray buildSpeechBody(const QString &model, const QString &voice,
                                      const QString &input, const QString &format);
    // Una línea JSON para piper residente (--json-input): {"text":...,
    // "output_file":...}\n. Piper sintetiza la línea y escribe el wav sin recargar
    // el modelo.
    static QByteArray buildPiperJsonLine(const QString &text, const QString &outFile);

signals:
    // audio crudo + formato ("wav"|"mp3"|"pcm").
    void audioReady(const QByteArray &audio, const QString &format);
    void failed(const QString &error);

private:
    void synthesizePiper(const QString &text);       // residente (con fallback)
    void synthesizePiperOnce(const QString &text);   // spawn por-llamada (fallback)
    bool ensurePiperResident();                      // lanza/reusa el proceso vivo
    void tearDownPiperResident();
    void finalizePiperTurn(const QString &outPath);  // lee wav y emite audioReady
    QString resolvePiperModel() const;
    QString resolvePiperProg() const;

    VoiceConfig m_cfg;
    QString m_key;
    QNetworkAccessManager m_nam;
    QNetworkReply *m_reply = nullptr;
    QString m_piperBin, m_piperModel;
    class QProcess *m_piper = nullptr;   // spawn per-call (fallback)
    QString m_piperOut;                  // wav temporal de salida (per-call)

    // Piper residente: proceso vivo en modo --json-input. Un turno a la vez
    // (VoiceController serializa vía busy()).
    class QProcess *m_piperProc = nullptr;
    QString m_piperResidentModel;        // modelo con que arrancó el residente
    bool m_piperPending = false;         // turno en vuelo en el residente
    QString m_piperPendingOut;           // wav esperado del turno actual
    QString m_piperPendingText;          // texto del turno (para fallback si muere)
    QByteArray m_piperStdoutBuf;         // acumulador de stdout (líneas)
};
