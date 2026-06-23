#include "VoiceController.h"
#include "AudioCodec.h"
#include <QRegularExpression>

#include <QAudioSource>
#include <QAudioFormat>
#include <QMediaDevices>
#include <QAudioDevice>
#include <QIODevice>
#include <QMediaPlayer>
#include <QAudioOutput>
#include <QBuffer>
#include <QUrl>

VoiceController::VoiceController(QObject *parent) : QObject(parent)
{
    connect(&m_stt, &SttEngine::transcribed, this, &VoiceController::onSttDone);
    connect(&m_stt, &SttEngine::failed,      this, &VoiceController::onSttFailed);
    connect(&m_tts, &TtsEngine::audioReady,  this, &VoiceController::onTtsAudio);
    connect(&m_tts, &TtsEngine::failed,       this, &VoiceController::onTtsFailed);
}

VoiceController::~VoiceController()
{
    endCapture();
    teardownPlayback();
}

void VoiceController::setConfig(const VoiceConfig &cfg, const QString &sttKey, const QString &ttsKey)
{
    m_cfg = cfg;
    m_stt.setConfig(cfg, sttKey);
    m_tts.setConfig(cfg, ttsKey);
}

void VoiceController::setTtsPiper(const QString &binPath, const QString &modelPath)
{
    m_tts.setPiper(binPath, modelPath);
}

void VoiceController::setInputDevice(const QString &id)
{
    m_deviceId = id;
}

QVariantList VoiceController::inputDevices()
{
    QVariantList out;
    const QAudioDevice def = QMediaDevices::defaultAudioInput();
    const auto devs = QMediaDevices::audioInputs();
    for (const QAudioDevice &d : devs) {
        QVariantMap m;
        m["id"]   = QString::fromUtf8(d.id());
        m["name"] = d.description();
        m["isDefault"] = (d.id() == def.id());
        out.append(m);
    }
    return out;
}

QString VoiceController::stateStr() const
{
    switch (m_state) {
    case Idle:         return QStringLiteral("idle");
    case Listening:    return QStringLiteral("listening");
    case Transcribing: return QStringLiteral("transcribing");
    case Thinking:     return QStringLiteral("thinking");
    case Speaking:     return QStringLiteral("speaking");
    case Error:        return QStringLiteral("error");
    }
    return QStringLiteral("idle");
}

void VoiceController::setState(State s)
{
    if (m_state == s) return;
    m_state = s;
    emit stateChanged();
}

void VoiceController::fail(const QString &err)
{
    m_lastError = err;
    emit errorChanged();
    endCapture();
    teardownPlayback();
    setState(Error);
}

bool VoiceController::turnEnded(double peakLevel, double activationLevel,
                                int silenceAccumMs, int silenceMs)
{
    return peakLevel >= activationLevel && silenceAccumMs >= silenceMs;
}

// ── Ciclo de vida ──────────────────────────────────────────────────────────

void VoiceController::start()
{
    m_lastError.clear();
    startListening();
}

void VoiceController::stop()
{
    endCapture();
    teardownPlayback();
    m_ttsQueue.clear();
    m_audioQueue.clear();
    m_playing = false;
    m_streamBubble = -1;
    m_streamConsumed = 0;
    m_stt.cancel();
    m_tts.cancel();
    m_testMode = false;
    setState(Idle);
}

void VoiceController::startListening()
{
    teardownPlayback();            // barge-in: cortar cualquier TTS sonando
    m_ttsQueue.clear();            // descartar oraciones/clips pendientes del turno
    m_audioQueue.clear();
    m_playing = false;
    m_streamBubble = -1;           // resetear streaming incremental del turno previo
    m_streamConsumed = 0;
    m_tts.cancel();
    m_testMode = false;
    beginCapture();
    if (m_state != Error) setState(Listening);
}

void VoiceController::micTest()
{
    m_lastError.clear();
    emit errorChanged();
    teardownPlayback();
    beginCapture();
    m_testMode = true;
    if (m_state != Error) setState(Listening);
}

void VoiceController::stopMicTest()
{
    if (m_testMode) stop();
}

// ── Captura de micrófono + VAD ───────────────────────────────────────────────

void VoiceController::beginCapture()
{
    endCapture();
    m_silenceMs = 0;
    m_peak = 0.0;
    m_monitorOnly = false;

    QAudioFormat fmt;
    fmt.setSampleRate(m_sampleRate);
    fmt.setChannelCount(1);
    fmt.setSampleFormat(QAudioFormat::Int16);

    QAudioDevice dev = QMediaDevices::defaultAudioInput();
    if (!m_deviceId.isEmpty()) {
        const auto devs = QMediaDevices::audioInputs();
        for (const QAudioDevice &d : devs)
            if (QString::fromUtf8(d.id()) == m_deviceId) { dev = d; break; }
    }
    if (dev.isNull()) { fail(QStringLiteral("no hay micrófono disponible")); return; }
    // Pedimos siempre 16k/mono/Int16 (lo que espera STT); el backend resamplea.
    m_source = new QAudioSource(dev, fmt, this);
    connect(m_source, &QAudioSource::stateChanged, this, [this](QAudio::State st) {
        if (st == QAudio::StoppedState && m_source && m_source->error() != QAudio::NoError)
            fail(QStringLiteral("micrófono: error de captura"));
    });
    m_input = m_source->start();
    if (!m_input) { fail(QStringLiteral("no se pudo abrir el micrófono")); return; }
    connect(m_input, &QIODevice::readyRead, this, &VoiceController::onAudioReady);
}

void VoiceController::stopSource()
{
    if (m_input) { disconnect(m_input, nullptr, this, nullptr); m_input = nullptr; }
    if (m_source) {
        m_source->stop();
        m_source->deleteLater();
        m_source = nullptr;
    }
    m_level = 0.0;
    emit levelChanged();
}

void VoiceController::endCapture()
{
    stopSource();
    // Reset completo del estado de stream (descarta turno en curso).
    m_segment.clear();
    m_segPeak = 0.0;
    m_segSilenceMs = 0;
    m_partial.clear();
    m_segQueue.clear();
    m_turnEnding = false;
}

void VoiceController::onAudioReady()
{
    if (!m_input) return;
    const QByteArray chunk = m_input->readAll();
    if (chunk.isEmpty()) return;

    const double lvl = AudioCodec::rmsBytes(chunk);
    m_level = lvl;
    emit levelChanged();

    const int chunkMs = int((chunk.size() / 2) * 1000.0 / m_sampleRate);

    // Modo prueba de micrófono: solo nivel, sin VAD ni STT.
    if (m_testMode) return;

    // Modo monitor (durante Speaking): solo detectar barge-in, no acumular.
    if (m_monitorOnly) {
        if (m_cfg.bargeIn && lvl >= m_cfg.vadActivationLevel * 1.6)
            startListening();
        return;
    }

    m_segment += chunk;
    if (lvl >= m_cfg.vadThreshold) {
        if (lvl > m_peak) m_peak = lvl;
        if (lvl > m_segPeak) m_segPeak = lvl;
        m_silenceMs = 0;
        m_segSilenceMs = 0;
    } else if (m_peak >= m_cfg.vadActivationLevel) {
        m_silenceMs += chunkMs;
        m_segSilenceMs += chunkMs;
        // Micro-pausa: cerrar segmento y transcribirlo en vivo (sin terminar turno).
        if (m_segSilenceMs >= m_cfg.vadSegmentMs && m_segPeak >= m_cfg.vadActivationLevel)
            flushSegment(false);
    }

    // Silencio largo tras voz → fin de turno: cerrar último segmento y finalizar.
    if (turnEnded(m_peak, m_cfg.vadActivationLevel, m_silenceMs, m_cfg.vadSilenceMs))
        flushSegment(true);
}

void VoiceController::flushSegment(bool finalSeg)
{
    // Encolar el segmento solo si tuvo voz y dura algo (>200ms) — evita fragmentos.
    const int segMs = int((m_segment.size() / 2) * 1000.0 / m_sampleRate);
    if (m_segPeak >= m_cfg.vadActivationLevel && segMs >= 200)
        m_segQueue.append(m_segment);
    m_segment.clear();
    m_segPeak = 0.0;
    m_segSilenceMs = 0;

    if (finalSeg) {
        m_turnEnding = true;
        stopSource();                 // dejar de capturar; drenamos la cola de STT
        if (m_state != Error) setState(Transcribing);
    }
    pumpSegments();
}

void VoiceController::pumpSegments()
{
    if (m_stt.busy()) return;         // un request a la vez (orden + servers seriales)
    if (m_segQueue.isEmpty()) {
        if (m_turnEnding) finalizeTurn();
        return;
    }
    const QByteArray seg = m_segQueue.takeFirst();
    m_stt.transcribe(seg, m_sampleRate);
}

void VoiceController::finalizeTurn()
{
    m_turnEnding = false;
    const QString full = m_partial.trimmed();
    m_partial.clear();
    if (full.isEmpty()) {             // nada inteligible → reintentar escucha
        if (m_cfg.autoListen) startListening();
        else setState(Idle);
        return;
    }
    setState(Thinking);
    emit transcriptReady(full);
}

// ── STT → texto ──────────────────────────────────────────────────────────────

void VoiceController::onSttDone(const QString &text)
{
    const QString t = text.trimmed();
    if (!t.isEmpty()) {
        if (!m_partial.isEmpty()) m_partial += QLatin1Char(' ');
        m_partial += t;
        emit partialTranscript(m_partial);
    }
    pumpSegments();                   // siguiente segmento, o finalizar si era el último
}

void VoiceController::onSttFailed(const QString &err)
{
    // Si ya hay texto parcial, ignorar el segmento fallido y seguir; si no, error duro
    // (típico: server STT caído → "Conexión rechazada").
    if (m_partial.isEmpty()) { fail(QStringLiteral("STT: ") + err); return; }
    pumpSegments();
}

void VoiceController::notifyThinking()
{
    if (m_state != Idle && m_state != Error)
        setState(Thinking);
}

// ── TTS → audio → playback ───────────────────────────────────────────────────

QStringList VoiceController::splitSentences(const QString &text, int minLen)
{
    QStringList out;
    QString cur;
    for (const QChar c : text) {
        cur.append(c);
        const bool end = (c == QLatin1Char('.') || c == QLatin1Char('!')
                          || c == QLatin1Char('?') || c == QChar(0x2026)
                          || c == QLatin1Char('\n'));
        if (end && cur.trimmed().size() >= minLen) {
            out << cur.trimmed();
            cur.clear();
        }
    }
    if (!cur.trimmed().isEmpty()) out << cur.trimmed();
    if (out.isEmpty() && !text.trimmed().isEmpty()) out << text.trimmed();
    return out;
}

QStringList VoiceController::splitCompleteSentences(const QString &text, int minLen, int *consumed)
{
    QStringList out;
    QString cur;
    int consumedLen = 0;
    for (int i = 0; i < text.size(); ++i) {
        const QChar c = text.at(i);
        cur.append(c);
        const bool end = (c == QLatin1Char('.') || c == QLatin1Char('!')
                          || c == QLatin1Char('?') || c == QChar(0x2026)
                          || c == QLatin1Char('\n'));
        if (end && cur.trimmed().size() >= minLen) {
            out << cur.trimmed();
            cur.clear();
            consumedLen = i + 1;       // todo hasta acá ya formó oraciones cerradas
        }
    }
    if (consumed) *consumed = consumedLen;   // el resto (fragmento incompleto) se acumula
    return out;
}

void VoiceController::speak(const QString &text)
{
    if (m_state == Idle || m_state == Error) return;  // charla no activa
    if (text.trimmed().isEmpty()) {
        if (m_cfg.autoListen) startListening();
        return;
    }
    // TTS por chunks: trocear en oraciones y sintetizar la primera ya; las demás
    // se generan mientras suena la anterior (arranca a hablar mucho antes).
    m_streamBubble = -1;
    m_streamConsumed = 0;
    m_ttsQueue = splitSentences(text);
    m_audioQueue.clear();
    m_playing = false;
    setState(Speaking);
    pumpTts();
}

QString VoiceController::sanitizeForSpeech(const QString &s)
{
    QString out = s;
    // Bloques <think>…</think> cerrados.
    out.remove(QRegularExpression(QStringLiteral("<think>[\\s\\S]*?</think>"),
                                  QRegularExpression::CaseInsensitiveOption));
    // <think> abierto sin cerrar (razonamiento aún streameando): cortar desde ahí.
    const QRegularExpression openRe(QStringLiteral("<think\\b[^>]*>"),
                                    QRegularExpression::CaseInsensitiveOption);
    const QRegularExpressionMatch open = openRe.match(out);
    if (open.hasMatch()) out.truncate(open.capturedStart());
    // Indicador transitorio de preparación de tool: descartar líneas con ⏳.
    if (out.contains(QChar(0x23F3))) {
        QStringList keep;
        const QStringList lines = out.split(QLatin1Char('\n'));
        for (const QString &ln : lines)
            if (!ln.contains(QChar(0x23F3))) keep << ln;
        out = keep.join(QLatin1Char('\n'));
    }
    return out.trimmed();
}

void VoiceController::speakStreaming(int bubbleId, const QString &rawText)
{
    if (m_state == Idle || m_state == Error) return;  // charla no activa
    // El usuario está hablando (barge-in / próximo turno): no hablar encima aunque
    // sigan llegando deltas del agente del turno anterior.
    if (m_state == Listening || m_state == Transcribing) return;
    const QString fullText = sanitizeForSpeech(rawText);
    // Nueva burbuja del agente (narración intermedia o respuesta final): resetear
    // el puntero de consumidos. No tocamos las colas: lo ya encolado sigue sonando.
    if (bubbleId != m_streamBubble) {
        m_streamBubble = bubbleId;
        m_streamConsumed = 0;
    }
    if (m_streamConsumed > fullText.size()) m_streamConsumed = 0;   // texto se acortó
    const QString pending = fullText.mid(m_streamConsumed);
    int consumed = 0;
    const QStringList sents = splitCompleteSentences(pending, 40, &consumed);
    if (sents.isEmpty()) return;          // todavía no cerró ninguna oración nueva
    m_streamConsumed += consumed;
    if (m_state != Speaking) setState(Speaking);
    m_ttsQueue += sents;
    pumpTts();                            // onTtsAudio arranca la reproducción
}

void VoiceController::speakFlush(int bubbleId, const QString &rawText)
{
    if (m_state == Idle || m_state == Error) return;
    if (m_state == Listening || m_state == Transcribing) return;  // user hablando
    const QString fullText = sanitizeForSpeech(rawText);
    // Encolar el fragmento final que quedó sin terminador (la última oración de la
    // respuesta del agente suele no cerrar con punto antes de finalizar el turno).
    int start = (bubbleId == m_streamBubble) ? m_streamConsumed : 0;
    if (start > fullText.size()) start = 0;
    const QString tail = fullText.mid(start).trimmed();
    m_streamBubble = -1;
    m_streamConsumed = 0;
    if (!tail.isEmpty()) {
        if (m_state != Speaking) setState(Speaking);
        m_ttsQueue += splitSentences(tail);
        pumpTts();
        return;
    }
    // Nada que hablar y nada en vuelo → retomar escucha (o quedar Idle).
    if (m_ttsQueue.isEmpty() && m_audioQueue.isEmpty() && !m_playing && !m_tts.busy()) {
        if (m_cfg.autoListen) startListening();
        else if (m_state == Speaking) setState(Idle);
    }
}

void VoiceController::pumpTts()
{
    if (m_tts.busy() || m_ttsQueue.isEmpty()) return;
    m_tts.synthesize(m_ttsQueue.takeFirst());
}

void VoiceController::onTtsAudio(const QByteArray &audio, const QString &format)
{
    m_audioQueue.append(qMakePair(audio, format));
    pumpTts();                 // adelantar la síntesis de la próxima oración
    if (!m_playing) playNextClip();
}

void VoiceController::playNextClip()
{
    if (m_audioQueue.isEmpty()) return;
    const auto clip = m_audioQueue.takeFirst();
    m_playing = true;
    playAudio(clip.first, clip.second);
}

void VoiceController::onTtsFailed(const QString &err)
{
    fail(QStringLiteral("TTS: ") + err);
}

void VoiceController::playAudio(const QByteArray &audio, const QString &format)
{
    teardownPlayback();

    m_playBuf = new QBuffer(this);
    m_playBuf->setData(audio);
    m_playBuf->open(QIODevice::ReadOnly);

    m_audioOut = new QAudioOutput(this);
    m_player = new QMediaPlayer(this);
    m_player->setAudioOutput(m_audioOut);
    m_player->setSourceDevice(m_playBuf, QUrl(QStringLiteral("voice.") + format));

    connect(m_player, &QMediaPlayer::mediaStatusChanged, this,
            [this](QMediaPlayer::MediaStatus st) {
        if (st == QMediaPlayer::EndOfMedia) {
            teardownPlayback();
            m_playing = false;
            // ¿Más clips ya sintetizados? Reproducir el siguiente.
            if (!m_audioQueue.isEmpty()) { playNextClip(); return; }
            // ¿Quedan oraciones por sintetizar (o una síntesis en vuelo)? Esperar
            // a que llegue su audio (onTtsAudio reanuda la reproducción).
            if (!m_ttsQueue.isEmpty() || m_tts.busy()) return;
            if (m_state == Speaking) {
                if (m_cfg.autoListen) startListening();
                else setState(Idle);
            }
        }
    });
    connect(m_player, &QMediaPlayer::errorOccurred, this,
            [this](QMediaPlayer::Error, const QString &es) { fail(QStringLiteral("playback: ") + es); });

    // Barge-in: monitorear el micrófono mientras hablamos. Solo iniciar la captura
    // una vez (no por cada clip del streaming de oraciones).
    if (m_cfg.bargeIn && !m_source) {
        beginCapture();
        m_monitorOnly = true;
        if (m_state != Error) setState(Speaking);
    }
    m_player->play();
}

void VoiceController::teardownPlayback()
{
    if (m_player) { m_player->stop(); m_player->deleteLater(); m_player = nullptr; }
    if (m_audioOut) { m_audioOut->deleteLater(); m_audioOut = nullptr; }
    if (m_playBuf) { m_playBuf->close(); m_playBuf->deleteLater(); m_playBuf = nullptr; }
}
