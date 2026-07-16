#include "VoiceController.h"
#include "AudioCodec.h"
#include <QRegularExpression>
#include <QDebug>
#include <algorithm>

#include <QAudioSource>
#include <QAudioFormat>
#include <QMediaDevices>
#include <QAudioDevice>
#include <QIODevice>
#include <QMediaPlayer>
#include <QAudioOutput>
#include <QAudioSink>
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

QString VoiceController::stateName(State s)
{
    switch (s) {
    case Idle:         return QStringLiteral("idle");
    case Listening:    return QStringLiteral("listening");
    case Transcribing: return QStringLiteral("transcribing");
    case Thinking:     return QStringLiteral("thinking");
    case Speaking:     return QStringLiteral("speaking");
    case Error:        return QStringLiteral("error");
    }
    return QStringLiteral("idle");
}

QString VoiceController::stateStr() const
{
    return stateName(m_state);
}

void VoiceController::setState(State s)
{
    if (m_state == s) return;
    // Timeline del pipeline en el log central: cada transición con el tiempo que
    // duró el estado anterior (diagnóstico de dónde se va la latencia).
    qInfo().noquote() << QStringLiteral("[charla] estado %1 → %2 (%3 ms en %1)")
                             .arg(stateName(m_state), stateName(s),
                                  QString::number(m_tState.isValid() ? m_tState.elapsed() : 0));
    m_tState.restart();
    m_state = s;
    emit stateChanged();
}

void VoiceController::fail(const QString &err)
{
    qWarning().noquote() << QStringLiteral("[charla] FALLO: %1 (estado=%2)").arg(err, stateStr());
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

VadTuning VoiceController::vadTuningFor(const VoiceConfig &cfg)
{
    VadTuning t;
    // El viejo vadThreshold pasa a piso absoluto: en un cuarto muy silencioso el
    // piso medido tiende a 0 y el umbral relativo dejaría pasar cualquier cosa.
    if (cfg.vadThreshold > 0.0) t.absFloor = cfg.vadThreshold * 0.5;
    // El hangover no puede tragarse el corte de segmento (transcripción en vivo).
    if (cfg.vadSegmentMs > 0) t.hangoverMs = std::min(t.hangoverMs, cfg.vadSegmentMs / 2);
    return t;
}

// ── Ciclo de vida ──────────────────────────────────────────────────────────

void VoiceController::start()
{
    m_lastError.clear();
    startListening();
}

void VoiceController::finishTurn()
{
    if (m_state == Listening && !m_testMode && !m_monitorOnly)
        flushSegment(true);
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
    m_vad.setTuning(vadTuningFor(m_cfg));
    m_vad.reset();   // el piso de ruido se re-mide por captura (mic/entorno pueden cambiar)

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
    qInfo().noquote() << QStringLiteral("[charla] captura: mic='%1' 16kHz mono (monitorOnly=%2)")
                             .arg(dev.description()).arg(m_monitorOnly);
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
    m_segVoice = false;
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

    // Alimentar siempre el VAD adaptativo: aun en testMode/monitorOnly el piso
    // de ruido sigue aprendiendo, así que al volver a escuchar ya está calibrado.
    const VadEngine::Frame vf = m_vad.push(lvl, chunkMs);
    // El VAD adaptativo mide contra el ruido de fondo; el legacy contra umbrales
    // fijos de config. Misma decisión (¿este frame es voz?), dos formas de sacarla.
    const bool speech   = m_cfg.vadAdaptive ? vf.speech : (lvl >= m_cfg.vadThreshold);
    const bool sawVoice = m_cfg.vadAdaptive ? m_vad.sawSpeech()
                                            : (m_peak >= m_cfg.vadActivationLevel);

    // Modo prueba de micrófono: solo nivel, sin VAD ni STT.
    if (m_testMode) return;

    // Modo monitor (durante Speaking): solo detectar barge-in, no acumular.
    if (m_monitorOnly) {
        const bool interrupt = m_cfg.vadAdaptive ? vf.onset
                                                 : (lvl >= m_cfg.vadActivationLevel * 1.6);
        if (m_cfg.bargeIn && interrupt) {
            qInfo().noquote() << QStringLiteral("[charla] barge-in: usuario interrumpió (nivel=%1, piso=%2)")
                                     .arg(lvl, 0, 'f', 3).arg(vf.floor, 0, 'f', 4);
            startListening();
        }
        return;
    }

    m_segment += chunk;
    if (speech) {
        if (lvl > m_peak) m_peak = lvl;
        if (lvl > m_segPeak) m_segPeak = lvl;
        m_segVoice = true;
        m_silenceMs = 0;
        m_segSilenceMs = 0;
    } else if (sawVoice) {
        m_silenceMs += chunkMs;
        m_segSilenceMs += chunkMs;
        // Micro-pausa: cerrar segmento y transcribirlo en vivo (sin terminar turno).
        if (m_segSilenceMs >= m_cfg.vadSegmentMs && segmentHadVoice())
            flushSegment(false);
    }

    // Cuánto silencio exige cerrar el turno. Con smartTurn el umbral depende de
    // cómo quedó el parcial ya transcripto (frase cerrada → cortar antes; colgada
    // en "y…"/"porque…" → darle tiempo a seguir).
    const int needSilence = m_cfg.smartTurn
        ? TurnDetector::requiredSilenceMs(m_partial, m_cfg.vadSilenceMs)
        : m_cfg.vadSilenceMs;

    // Silencio largo tras voz → fin de turno: cerrar último segmento y finalizar.
    const bool ended = m_cfg.vadAdaptive
        ? (sawVoice && m_silenceMs >= needSilence)
        : turnEnded(m_peak, m_cfg.vadActivationLevel, m_silenceMs, needSilence);
    if (ended) {
        if (needSilence != m_cfg.vadSilenceMs)
            qInfo().noquote() << QStringLiteral("[charla] endpoint: corte a %1 ms (base %2, parcial=\"%3\")")
                                     .arg(needSilence).arg(m_cfg.vadSilenceMs).arg(m_partial.right(40));
        flushSegment(true);
    }
}

bool VoiceController::segmentHadVoice() const
{
    return m_cfg.vadAdaptive ? m_segVoice : (m_segPeak >= m_cfg.vadActivationLevel);
}

void VoiceController::flushSegment(bool finalSeg)
{
    // Encolar el segmento solo si tuvo voz y dura algo (>200ms) — evita fragmentos.
    const int segMs = int((m_segment.size() / 2) * 1000.0 / m_sampleRate);
    if (segmentHadVoice() && segMs >= 200) {
        m_segQueue.append(m_segment);
        qInfo().noquote() << QStringLiteral("[charla] VAD: segmento %1 ms (peak=%2, final=%3, cola=%4)")
                                 .arg(segMs).arg(m_segPeak, 0, 'f', 3)
                                 .arg(finalSeg).arg(m_segQueue.size());
    } else if (finalSeg && m_segQueue.isEmpty() && m_partial.isEmpty()) {
        qInfo().noquote() << QStringLiteral("[charla] VAD: turno sin voz útil (seg=%1 ms, peak=%2 < act=%3)")
                                 .arg(segMs).arg(m_segPeak, 0, 'f', 3)
                                 .arg(m_cfg.vadActivationLevel, 0, 'f', 3);
    }
    m_segment.clear();
    m_segPeak = 0.0;
    m_segVoice = false;
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
    m_tStt.restart();
    qInfo().noquote() << QStringLiteral("[charla] STT: enviando segmento (%1 ms de audio, quedan %2)")
                             .arg(int((seg.size() / 2) * 1000.0 / m_sampleRate))
                             .arg(m_segQueue.size());
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
    m_tTurn.restart();
    m_turnFirstAudio = false;
    qInfo().noquote() << QStringLiteral("[charla] turno del usuario: \"%1\" (%2 chars)")
                             .arg(full.left(120)).arg(full.size());
    setState(Thinking);
    emit transcriptReady(full);
}

// ── STT → texto ──────────────────────────────────────────────────────────────

void VoiceController::onSttDone(const QString &text)
{
    const QString t = text.trimmed();
    qInfo().noquote() << QStringLiteral("[charla] STT: ok en %1 ms → \"%2\"")
                             .arg(m_tStt.isValid() ? m_tStt.elapsed() : 0)
                             .arg(t.left(80));
    if (!t.isEmpty()) {
        if (!m_partial.isEmpty()) m_partial += QLatin1Char(' ');
        m_partial += t;
        emit partialTranscript(m_partial);
    }
    pumpSegments();                   // siguiente segmento, o finalizar si era el último
}

void VoiceController::onSttFailed(const QString &err)
{
    qWarning().noquote() << QStringLiteral("[charla] STT: fallo en %1 ms: %2 (parcial=%3 chars)")
                                .arg(m_tStt.isValid() ? m_tStt.elapsed() : 0)
                                .arg(err).arg(m_partial.size());
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

void VoiceController::notifyTurnFailed(const QString &err)
{
    if (m_state == Idle || m_state == Error) return;
    qWarning().noquote() << QStringLiteral("[charla] turno FALLÓ (estado=%1): %2")
                                .arg(stateStr(), err);
    m_lastError = err;
    emit errorChanged();
    teardownPlayback();
    m_ttsQueue.clear();
    m_audioQueue.clear();
    m_playing = false;
    m_streamBubble = -1;
    m_streamConsumed = 0;
    // Reintentable: volver a escuchar (el error queda visible en lastError).
    if (m_cfg.autoListen) startListening();
    else { endCapture(); setState(Idle); }
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
    // Primera oración del turno: umbral corto (arrancar a hablar YA con un "Ok."
    // o "Dale."); las siguientes usan 40 para no spawnear TTS por fragmentos.
    const int minLen = (m_streamConsumed == 0) ? 12 : 40;
    int consumed = 0;
    const QStringList sents = splitCompleteSentences(pending, minLen, &consumed);
    if (sents.isEmpty()) return;          // todavía no cerró ninguna oración nueva
    m_streamConsumed += consumed;
    qInfo().noquote() << QStringLiteral("[charla] stream: +%1 oración(es) (bubble=%2, consumido=%3)")
                             .arg(sents.size()).arg(bubbleId).arg(m_streamConsumed);
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
    const QString sent = m_ttsQueue.takeFirst();
    m_tTts.restart();
    qInfo().noquote() << QStringLiteral("[charla] TTS: sintetizando %1 chars (cola=%2)")
                             .arg(sent.size()).arg(m_ttsQueue.size());
    m_tts.synthesize(sent);
}

void VoiceController::onTtsAudio(const QByteArray &audio, const QString &format)
{
    qInfo().noquote() << QStringLiteral("[charla] TTS: audio listo en %1 ms (%2 KB, %3)")
                             .arg(m_tTts.isValid() ? m_tTts.elapsed() : 0)
                             .arg(audio.size() / 1024).arg(format);
    if (!m_turnFirstAudio && m_tTurn.isValid()) {
        m_turnFirstAudio = true;
        // Métrica clave: fin del habla del usuario → primer audio de respuesta.
        qInfo().noquote() << QStringLiteral("[charla] LATENCIA turno→primer audio: %1 ms")
                                 .arg(m_tTurn.elapsed());
    }
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

void VoiceController::onClipFinished()
{
    m_playing = false;
    // ¿Más clips ya sintetizados? Reproducir el siguiente.
    if (!m_audioQueue.isEmpty()) { playNextClip(); return; }
    // ¿Quedan oraciones por sintetizar (o una síntesis en vuelo)? Esperar a que
    // llegue su audio (onTtsAudio reanuda la reproducción).
    if (!m_ttsQueue.isEmpty() || m_tts.busy()) return;
    teardownPlayback();
    if (m_state == Speaking) {
        if (m_cfg.autoListen) startListening();
        else setState(Idle);
    }
}

void VoiceController::playPcm(const QByteArray &pcm, int sampleRate, int channels)
{
    // Limpiar solo el path QMediaPlayer; el sink se reusa entre oraciones.
    if (m_player) { m_player->stop(); m_player->deleteLater(); m_player = nullptr; }
    if (m_audioOut) { m_audioOut->deleteLater(); m_audioOut = nullptr; }
    if (m_sink && (m_sinkRate != sampleRate || m_sinkChannels != channels))
        teardownSink();
    if (m_playBuf) { m_playBuf->close(); m_playBuf->deleteLater(); m_playBuf = nullptr; }

    m_playBuf = new QBuffer(this);
    m_playBuf->setData(pcm);
    m_playBuf->open(QIODevice::ReadOnly);

    if (!m_sink) {
        qInfo().noquote() << QStringLiteral("[charla] playback: QAudioSink nuevo (%1 Hz, %2 ch)")
                                 .arg(sampleRate).arg(channels);
        QAudioFormat fmt;
        fmt.setSampleRate(sampleRate);
        fmt.setChannelCount(channels);
        fmt.setSampleFormat(QAudioFormat::Int16);
        m_sink = new QAudioSink(fmt, this);
        m_sinkRate = sampleRate;
        m_sinkChannels = channels;
        connect(m_sink, &QAudioSink::stateChanged, this, [this](QAudio::State st) {
            // IdleState = buffer drenado → clip terminado.
            if (st == QAudio::IdleState && m_playing) onClipFinished();
            else if (st == QAudio::StoppedState && m_sink
                     && m_sink->error() != QAudio::NoError)
                fail(QStringLiteral("playback: error de salida de audio"));
        });
    } else {
        m_sink->stop();
    }

    if (m_cfg.bargeIn && !m_source) {
        beginCapture();
        m_monitorOnly = true;
        if (m_state != Error) setState(Speaking);
    }
    m_sink->start(m_playBuf);
}

void VoiceController::playAudio(const QByteArray &audio, const QString &format)
{
    // WAV PCM16 (piper y la mayoría de servers TTS locales): directo a QAudioSink.
    int rate = 0, ch = 0;
    if (format == QLatin1String("wav") && AudioCodec::wavPcm16Format(audio, &rate, &ch)) {
        playPcm(AudioCodec::wavExtractPcm(audio), rate, ch);
        return;
    }

    qInfo().noquote() << QStringLiteral("[charla] playback: QMediaPlayer (%1, %2 KB)")
                             .arg(format).arg(audio.size() / 1024);
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
        if (st == QMediaPlayer::EndOfMedia) onClipFinished();
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

void VoiceController::teardownSink()
{
    if (m_sink) {
        QAudioSink *s = m_sink;
        m_sink = nullptr;          // antes de stop(): evita re-entrar por stateChanged
        s->disconnect(this);
        s->stop();
        s->deleteLater();
    }
    m_sinkRate = 0;
    m_sinkChannels = 0;
}

void VoiceController::teardownPlayback()
{
    if (m_player) { m_player->stop(); m_player->deleteLater(); m_player = nullptr; }
    if (m_audioOut) { m_audioOut->deleteLater(); m_audioOut = nullptr; }
    teardownSink();
    if (m_playBuf) { m_playBuf->close(); m_playBuf->deleteLater(); m_playBuf = nullptr; }
}
