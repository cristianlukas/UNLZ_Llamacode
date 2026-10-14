#pragma once
#include "VoiceTypes.h"
#include <QObject>
#include <QByteArray>
#include <QStringList>
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
    // Máscara CUDA para los procesos TTS locales. Vacía = heredar el entorno.
    void setGpuDeviceMask(const QString &mask);

    void synthesize(const QString &text);
    // Levanta el motor residente (hoy: piper --json-input) sin sintetizar nada,
    // para que la carga del modelo (~2 s medidos) ocurra mientras el usuario
    // habla y no en la primera oración de la respuesta. No-op en otros modos.
    void prewarm();
    // Ocupado = hay un request en vuelo (HTTP, spawn per-call, o turno pendiente
    // en el piper residente). El proceso residente vivo NO cuenta como ocupado.
    bool busy() const { return m_reply != nullptr || m_piper != nullptr || m_qwen != nullptr || m_inflect != nullptr || m_piperPending; }
    void cancel();

    // ¿Hay una voz piper local instalada (modelo .onnx presente)? Fallback cuando
    // el endpoint TTS HTTP no responde. Público para test.
    bool piperAvailable() const;
    // Ejecutable de piper marcado sin modo residente ("" si ninguno). Tests/diag.
    QString piperResidentBrokenProg() const { return m_piperResidentBrokenProg; }
    // Simula que el piper residente reportó terminado el WAV `outPath` del turno
    // pendiente (mismo camino que la línea real por stdout). Sólo tests.
    void piperResidentLineForTest(const QString &outPath);

    // ── Funciones puras (testeables sin red ni proceso) ──
    // Body JSON del request /v1/audio/speech.
    static QByteArray buildSpeechBody(const QString &model, const QString &voice,
                                      const QString &input, const QString &format);
    // Una línea JSON para piper residente (--json-input): {"text":...,
    // "output_file":...}\n. Piper sintetiza la línea y escribe el wav sin recargar
    // el modelo.
    static QByteArray buildPiperJsonLine(const QString &text, const QString &outFile);
    static QStringList buildQwenArgs(const VoiceConfig &cfg, const QString &text,
                                     const QString &outFile);
    static QStringList buildInflectArgs(const VoiceConfig &cfg, const QString &text,
                                        const QString &outFile);

signals:
    // audio crudo + formato ("wav"|"mp3"|"pcm").
    void audioReady(const QByteArray &audio, const QString &format);
    // Bloques PCM16 de un response HTTP chunked. streamFinished cierra la
    // oracion; el consumidor puede reproducir antes de que termine la sintesis.
    void audioChunk(const QByteArray &pcm, int sampleRate, int channels);
    void audioStreamFinished();
    void failed(const QString &error);

private:
    void synthesizePiper(const QString &text);       // residente (con fallback)
    void synthesizePiperOnce(const QString &text);   // spawn por-llamada (fallback)
    bool ensurePiperResident();                      // lanza/reusa el proceso vivo
    void tearDownPiperResident();
    void onPiperResidentLine();
    void finalizePiperTurn(QString outPath);  // por valor: el caller pasa m_piperPendingOut  // lee wav y emite audioReady
    QString resolvePiperModel() const;
    QString resolvePiperProg() const;
    void synthesizeQwen(const QString &text);
    void synthesizeInflect(const QString &text);
    void synthesizePocket(const QString &text);
    void consumePocketWav();
    void clearPocketStream();
    void fallbackFrom(const QString &failedMode, const QString &text, const QString &error);
    void applyGpuEnvironment(class QProcess *process) const;

    VoiceConfig m_cfg;
    QString m_key;
    QNetworkAccessManager m_nam;
    QNetworkReply *m_reply = nullptr;
    qint64 m_streamBytes = 0;
    QString m_piperBin, m_piperModel;
    QString m_gpuDeviceMask;
    class QProcess *m_piper = nullptr;   // spawn per-call (fallback)
    QString m_piperOut;                  // wav temporal de salida (per-call)
    class QProcess *m_qwen = nullptr;
    QString m_qwenOut;
    class QProcess *m_inflect = nullptr;
    QString m_inflectOut;

    // Piper residente: proceso vivo en modo --json-input. Un turno a la vez
    // (VoiceController serializa vía busy()).
    class QProcess *m_piperProc = nullptr;
    QString m_piperResidentModel;        // modelo con que arrancó el residente
    // Ejecutable cuyo modo residente (--json-input) murió sin completar ni una
    // oración: p.ej. el `piper` de pip (piper-tts 1.3), que no tiene ese flag.
    // Reintentarlo en cada oración costaba ~1,7 s extra por oración encima del
    // fallback per-call; se va directo al per-call mientras no cambie el binario.
    QString m_piperResidentBrokenProg;
    bool m_piperResidentServedAny = false;
    bool m_piperPending = false;         // turno en vuelo en el residente
    QString m_piperPendingOut;           // wav esperado del turno actual
    QString m_piperPendingText;          // texto del turno (para fallback si muere)
    QByteArray m_piperStdoutBuf;         // acumulador de stdout (líneas)

    // Pocket devuelve un WAV chunked con tamaños RIFF desconocidos. Se guarda
    // el encabezado y se emiten sólo los bytes del chunk data como PCM16.
    QByteArray m_pocketBuffer;
    int m_pocketDataOffset = -1;
    qint64 m_pocketDataEmitted = 0;
    quint32 m_pocketDataSize = 0;
    int m_pocketSampleRate = 0;
    int m_pocketChannels = 0;
    bool m_pocketStreaming = false;
    bool m_pocketCancelRequested = false;
};
