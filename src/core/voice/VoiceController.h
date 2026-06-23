#pragma once
#include "VoiceTypes.h"
#include "SttEngine.h"
#include "TtsEngine.h"
#include <QObject>
#include <QByteArray>
#include <QPointer>
#include <QVariantList>
#include <QList>
#include <QPair>
#include <QStringList>
#include <QString>

class QAudioSource;
class QIODevice;
class QMediaPlayer;
class QAudioOutput;
class QBuffer;

// Orquestador del modo "Charla" (voz-a-voz):
//   Listening → (VAD detecta fin de habla) → Transcribing (STT) →
//   emite transcriptReady(text) [AppController lo manda al backend de chat] →
//   Thinking (mientras el LLM genera) → speak(reply) → Speaking (TTS+playback) →
//   (autoListen) vuelve a Listening.
// Captura en PCM16 mono 16 kHz. VAD por energía RMS (sin libs externas).
class VoiceController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString state READ stateStr NOTIFY stateChanged)
    Q_PROPERTY(bool active READ active NOTIFY stateChanged)
    Q_PROPERTY(double level READ level NOTIFY levelChanged)        // RMS live [0..1] para meter
    Q_PROPERTY(QString lastError READ lastError NOTIFY errorChanged)
public:
    enum State { Idle, Listening, Transcribing, Thinking, Speaking, Error };
    Q_ENUM(State)

    explicit VoiceController(QObject *parent = nullptr);
    ~VoiceController() override;

    void setConfig(const VoiceConfig &cfg, const QString &sttKey, const QString &ttsKey);
    // Rutas para TTS modo piper (process-mode).
    void setTtsPiper(const QString &binPath, const QString &modelPath);
    // Dispositivo de entrada por id (QAudioDevice::id() como string utf8). "" = default.
    void setInputDevice(const QString &id);
    // Lista de micrófonos: [{id,name,isDefault}].
    static QVariantList inputDevices();

    QString stateStr() const;
    bool active() const { return m_state != Idle && m_state != Error; }
    double level() const { return m_level; }
    QString lastError() const { return m_lastError; }

    State state() const { return m_state; }

    // ── Función pura de VAD (testeable) ──
    // Decide si el turno terminó: hubo voz (peak>=activation) y luego silencio
    // continuo >= silenceMs. silenceAccumMs es el silencio acumulado hasta ahora.
    static bool turnEnded(double peakLevel, double activationLevel,
                          int silenceAccumMs, int silenceMs);

    // ── Función pura (testeable) ──
    // Trocea la respuesta en oraciones para TTS por chunks: se sintetiza la
    // primera oración apenas se cierra (audio rápido) mientras se generan las
    // siguientes. Acumula hasta un cierre de oración (.!?…\n) que supere minLen
    // para no spawnear piper por fragmentos minúsculos. Devuelve >=1 chunk.
    static QStringList splitSentences(const QString &text, int minLen = 40);

public slots:
    void start();          // arranca la sesión de charla (entra en Listening)
    void stop();           // corta todo y vuelve a Idle
    void startListening(); // fuerza escucha (corta TTS si suena)
    void micTest();        // captura solo para ver nivel (sin STT/chat); probar micrófono
    void stopMicTest();
    void speak(const QString &text);   // habla un texto (lo invoca AppController al cerrar turno)
    void notifyThinking();             // el LLM empezó a generar

signals:
    void stateChanged();
    void levelChanged();
    void errorChanged();
    // Texto reconocido del usuario; AppController lo envía al backend de chat.
    void transcriptReady(const QString &text);
    // Transcripción parcial en vivo (segmentos ya reconocidos del turno en curso).
    void partialTranscript(const QString &text);

private slots:
    void onAudioReady();
    void onSttDone(const QString &text);
    void onSttFailed(const QString &err);
    void onTtsAudio(const QByteArray &audio, const QString &format);
    void onTtsFailed(const QString &err);

private:
    void setState(State s);
    void fail(const QString &err);
    void beginCapture();
    void endCapture();              // tear-down de captura + reset del estado de stream
    void stopSource();             // detiene el QAudioSource sin resetear el transcript
    void flushSegment(bool finalSeg); // encola el segmento actual (si tuvo voz) y pumpea
    void pumpSegments();           // transcribe el próximo segmento si STT está libre
    void finalizeTurn();           // arma el texto final del turno y lo emite
    void playAudio(const QByteArray &audio, const QString &format);
    void teardownPlayback();
    void pumpTts();        // sintetiza la próxima oración pendiente si TTS está libre
    void playNextClip();   // reproduce el próximo clip de audio ya sintetizado

    VoiceConfig m_cfg;
    State m_state = Idle;
    double m_level = 0.0;
    QString m_lastError;

    SttEngine m_stt;
    TtsEngine m_tts;

    QAudioSource *m_source = nullptr;
    QPointer<QIODevice> m_input;     // device de QAudioSource (no es dueño)
    int   m_sampleRate = 16000;
    int   m_silenceMs = 0;           // silencio continuo acumulado (ms)
    double m_peak = 0.0;             // máximo RMS visto en el turno (¿hubo voz?)

    // Transcripción incremental (chunked): el turno se trocea en segmentos por
    // micro-silencios; cada segmento se transcribe en orden y se acumula en
    // m_partial (mostrado en vivo). Al silencio largo se finaliza el turno.
    QByteArray m_segment;            // PCM16 del segmento en curso
    double m_segPeak = 0.0;          // ¿el segmento tuvo voz?
    int    m_segSilenceMs = 0;       // micro-silencio del segmento
    QString m_partial;               // transcripción acumulada del turno
    QList<QByteArray> m_segQueue;    // segmentos esperando transcripción (en orden)
    bool   m_turnEnding = false;     // silencio largo detectado: finalizar al drenar la cola
    bool  m_monitorOnly = false;     // true durante Speaking (barge-in): no acumula
    bool  m_testMode = false;        // micTest: captura para nivel, no VAD/STT
    QString m_deviceId;              // micrófono elegido ("" = default del sistema)

    QMediaPlayer *m_player = nullptr;
    QAudioOutput *m_audioOut = nullptr;
    QBuffer *m_playBuf = nullptr;

    // TTS por chunks (streaming de oraciones): cola de oraciones pendientes de
    // sintetizar + cola de clips ya sintetizados esperando reproducción. Permite
    // empezar a hablar tras la primera oración mientras se generan las demás.
    QStringList m_ttsQueue;                          // oraciones pendientes
    QList<QPair<QByteArray, QString>> m_audioQueue;  // {audio, formato} a reproducir
    bool m_playing = false;                          // hay un clip sonando
};
