#include "TtsEngine.h"
#include "VoiceServerManager.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>
#include <QProcess>
#include <QDir>
#include <QFile>
#include <QStandardPaths>
#include <QUuid>
#include <QFileInfo>
#include <QDebug>

TtsEngine::TtsEngine(QObject *parent) : QObject(parent) {}

void TtsEngine::setConfig(const VoiceConfig &cfg, const QString &resolvedKey)
{
    m_cfg = cfg;
    m_key = resolvedKey;
}

QByteArray TtsEngine::buildSpeechBody(const QString &model, const QString &voice,
                                      const QString &input, const QString &format)
{
    QJsonObject o;
    o["model"] = model;
    o["voice"] = voice;
    o["input"] = input;
    o["response_format"] = format;
    return QJsonDocument(o).toJson(QJsonDocument::Compact);
}

void TtsEngine::setPiper(const QString &binPath, const QString &modelPath)
{
    m_piperBin = binPath;
    m_piperModel = modelPath;
}

bool TtsEngine::piperAvailable() const
{
    QString modelPath = m_piperModel;
    if (modelPath.isEmpty())
        modelPath = VoiceServerManager::ttsModelPath(
            m_cfg.ttsManagedVoice.isEmpty() ? QStringLiteral("es_ES-davefx-medium")
                                            : m_cfg.ttsManagedVoice);
    return !modelPath.isEmpty() && QFile::exists(modelPath);
}

QByteArray TtsEngine::buildPiperJsonLine(const QString &text, const QString &outFile)
{
    QJsonObject o;
    o["text"] = text;
    o["output_file"] = outFile;
    return QJsonDocument(o).toJson(QJsonDocument::Compact) + '\n';
}

QStringList TtsEngine::buildQwenArgs(const VoiceConfig &c, const QString &text,
                                     const QString &outFile)
{
    QStringList a{QStringLiteral("-m"), c.qwenModelDir,
                  QStringLiteral("-t"), text,
                  QStringLiteral("-o"), outFile,
                  QStringLiteral("-l"), c.qwenLanguage.isEmpty() ? QStringLiteral("es") : c.qwenLanguage};
    if (!c.qwenModelName.isEmpty()) a << QStringLiteral("--model-name") << c.qwenModelName;
    if (!c.qwenSpeakerEmbedding.isEmpty()) a << QStringLiteral("--speaker-embedding") << c.qwenSpeakerEmbedding;
    else if (!c.qwenReferenceWav.isEmpty()) {
        a << QStringLiteral("--reference") << c.qwenReferenceWav;
        if (!c.qwenReferenceText.isEmpty()) a << QStringLiteral("--reference-text") << c.qwenReferenceText;
    } else if (!c.qwenSpeaker.isEmpty()) a << QStringLiteral("--speaker") << c.qwenSpeaker;
    if (!c.qwenInstruction.isEmpty()) a << QStringLiteral("--instruct") << c.qwenInstruction;
    if (c.qwenThreads > 0) a << QStringLiteral("--threads") << QString::number(c.qwenThreads);
    return a;
}

void TtsEngine::fallbackFrom(const QString &failedMode, const QString &text, const QString &error)
{
    const QString fallback = m_cfg.ttsFallbackMode;
    qWarning().noquote() << QStringLiteral("[charla] TTS %1 falló: %2; fallback=%3")
                                .arg(failedMode, error, fallback);
    if (fallback == QLatin1String("piper") && failedMode != QLatin1String("piper") && piperAvailable()) {
        synthesizePiper(text);
        return;
    }
    emit failed(error);
}

void TtsEngine::synthesizeQwen(const QString &text)
{
    QString prog = m_cfg.qwenBinaryPath.trimmed();
    if (prog.isEmpty()) prog = QStringLiteral("qwen3-tts-cli");
    if (m_cfg.qwenModelDir.trimmed().isEmpty()) {
        fallbackFrom(QStringLiteral("qwen3"), text, QStringLiteral("configurá la carpeta de modelos Qwen3-TTS"));
        return;
    }
    m_qwenOut = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
        + QStringLiteral("/lc_qwen_tts_") + QUuid::createUuid().toString(QUuid::Id128) + QStringLiteral(".wav");
    m_qwen = new QProcess(this);
    m_qwen->setProcessChannelMode(QProcess::SeparateChannels);
    connect(m_qwen, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this, text](int code, QProcess::ExitStatus status) {
        QProcess *p = m_qwen; m_qwen = nullptr;
        const QString detail = p ? QString::fromUtf8(p->readAllStandardError()).trimmed() : QString();
        if (p) p->deleteLater();
        QFile f(m_qwenOut);
        if (status != QProcess::NormalExit || code != 0 || !f.open(QIODevice::ReadOnly)) {
            QFile::remove(m_qwenOut);
            fallbackFrom(QStringLiteral("qwen3"), text,
                         detail.isEmpty() ? QStringLiteral("Qwen3-TTS no generó audio") : detail);
            return;
        }
        const QByteArray wav = f.readAll(); f.close(); QFile::remove(m_qwenOut);
        if (wav.isEmpty()) { fallbackFrom(QStringLiteral("qwen3"), text, QStringLiteral("audio Qwen3-TTS vacío")); return; }
        emit audioReady(wav, QStringLiteral("wav"));
    });
    connect(m_qwen, &QProcess::errorOccurred, this, [this, text](QProcess::ProcessError) {
        if (!m_qwen) return;
        const QString err = m_qwen->errorString();
        m_qwen->deleteLater(); m_qwen = nullptr;
        QFile::remove(m_qwenOut);
        fallbackFrom(QStringLiteral("qwen3"), text, QStringLiteral("no se pudo lanzar Qwen3-TTS: %1").arg(err));
    });
    m_qwen->start(prog, buildQwenArgs(m_cfg, text, m_qwenOut));
}

QString TtsEngine::resolvePiperModel() const
{
    QString modelPath = m_piperModel;
    if (modelPath.isEmpty())
        modelPath = VoiceServerManager::ttsModelPath(QStringLiteral("es_ES-davefx-medium"));
    return modelPath;
}

QString TtsEngine::resolvePiperProg() const
{
    QString prog = m_piperBin;
    if (prog.isEmpty()) prog = VoiceServerManager::installedBinaryPath(QStringLiteral("piper"));
    if (prog.isEmpty()) prog = QStringLiteral("piper");
    return prog;
}

// Lanza (o reusa) el proceso piper residente en modo --json-input. Mantiene el
// modelo .onnx + eSpeak cargados entre turnos: la latencia dominante de piper era
// recargar el modelo en cada spawn. Devuelve true si hay un proceso vivo listo.
bool TtsEngine::ensurePiperResident()
{
    if (m_piperProc && m_piperProc->state() == QProcess::Running
        && m_piperResidentModel == resolvePiperModel())
        return true;
    // Modelo cambió o proceso muerto: reiniciar limpio.
    tearDownPiperResident();

    const QString modelPath = resolvePiperModel();
    if (modelPath.isEmpty() || !QFile::exists(modelPath)) return false;

    const QString outDir = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
    const QStringList args = VoiceServerManager::buildPiperResidentArgs(modelPath, outDir);

    m_piperProc = new QProcess(this);
    m_piperProc->setProcessChannelMode(QProcess::SeparateChannels);
    m_piperResidentModel = modelPath;

    connect(m_piperProc, &QProcess::readyReadStandardOutput, this, [this]() {
        if (!m_piperProc) return;
        m_piperStdoutBuf += m_piperProc->readAllStandardOutput();
        // Piper imprime la ruta del wav escrito (una línea por turno). Al llegar
        // una línea completa, el archivo ya está cerrado y listo.
        int nl;
        while ((nl = m_piperStdoutBuf.indexOf('\n')) >= 0) {
            const QByteArray line = m_piperStdoutBuf.left(nl).trimmed();
            m_piperStdoutBuf.remove(0, nl + 1);
            if (line.isEmpty()) continue;
            if (m_piperPending) finalizePiperTurn(m_piperPendingOut);
        }
    });
    auto onDead = [this]() {
        // El residente murió. Si había un turno en vuelo, reintentar con spawn
        // per-call (fallback) para no perder la respuesta.
        const bool hadPending = m_piperPending;
        const QString pendingText = m_piperPendingText;
        qWarning().noquote() << QStringLiteral("[charla] piper: residente murió (pendiente=%1)")
                                    .arg(hadPending);
        tearDownPiperResident();
        if (hadPending) {
            m_piperPending = false;
            if (!pendingText.isEmpty()) synthesizePiperOnce(pendingText);
            else emit failed(QStringLiteral("piper residente murió"));
        }
    };
    connect(m_piperProc, &QProcess::errorOccurred, this,
            [onDead](QProcess::ProcessError) { onDead(); });
    connect(m_piperProc, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, [onDead](int, QProcess::ExitStatus) { onDead(); });

    qInfo().noquote() << QStringLiteral("[charla] piper: lanzando residente (%1, modelo=%2)")
                             .arg(resolvePiperProg(), QFileInfo(modelPath).fileName());
    m_piperProc->start(resolvePiperProg(), args);
    if (!m_piperProc->waitForStarted(4000)) {
        qWarning().noquote() << QStringLiteral("[charla] piper: residente NO arrancó (%1)")
                                    .arg(m_piperProc ? m_piperProc->errorString() : QString());
        tearDownPiperResident();
        return false;
    }
    return true;
}

void TtsEngine::tearDownPiperResident()
{
    if (m_piperProc) {
        QProcess *p = m_piperProc;
        m_piperProc = nullptr;
        p->disconnect(this);
        p->kill();
        p->deleteLater();
    }
    m_piperResidentModel.clear();
    m_piperStdoutBuf.clear();
    // No tocamos m_piperPending acá: el caller decide reintentar o fallar.
}

void TtsEngine::finalizePiperTurn(const QString &outPath)
{
    m_piperPending = false;
    m_piperPendingText.clear();
    m_piperPendingOut.clear();
    QFile f(outPath);
    if (!f.open(QIODevice::ReadOnly)) { emit failed(QStringLiteral("piper no generó audio")); return; }
    const QByteArray wav = f.readAll();
    f.close();
    QFile::remove(outPath);
    if (wav.isEmpty()) { emit failed(QStringLiteral("piper no generó audio")); return; }
    emit audioReady(wav, QStringLiteral("wav"));
}

// Modo piper local: intenta el proceso residente (modelo cargado una sola vez).
// Si no se puede levantar, cae al spawn per-call.
void TtsEngine::synthesizePiper(const QString &text)
{
    if (resolvePiperModel().isEmpty() || !QFile::exists(resolvePiperModel())) {
        emit failed(QStringLiteral("voz piper no instalada")); return;
    }
    if (ensurePiperResident()) {
        const QString outPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
            + QStringLiteral("/lc_tts_") + QUuid::createUuid().toString(QUuid::Id128)
            + QStringLiteral(".wav");
        m_piperPending = true;
        m_piperPendingOut = outPath;
        m_piperPendingText = text;
        const qint64 n = m_piperProc->write(buildPiperJsonLine(text, outPath));
        if (n < 0) {
            // Escritura falló: residente roto, fallback per-call.
            m_piperPending = false; m_piperPendingText.clear(); m_piperPendingOut.clear();
            tearDownPiperResident();
            synthesizePiperOnce(text);
        }
        return;
    }
    synthesizePiperOnce(text);
}

// Fallback: un proceso piper por llamada (recarga el modelo cada vez). Se usa si
// el residente no arranca o muere.
void TtsEngine::synthesizePiperOnce(const QString &text)
{
    qInfo().noquote() << QStringLiteral("[charla] piper: fallback per-call (recarga modelo — lento)");
    const QString modelPath = resolvePiperModel();
    if (modelPath.isEmpty() || !QFile::exists(modelPath)) {
        emit failed(QStringLiteral("voz piper no instalada")); return;
    }
    const QString tmp = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
        + QStringLiteral("/lc_tts_") + QUuid::createUuid().toString(QUuid::Id128)
        + QStringLiteral(".wav");
    m_piperOut = tmp;
    const QString prog = resolvePiperProg();
    const QStringList args = VoiceServerManager::buildPiperArgs(modelPath, tmp);

    m_piper = new QProcess(this);
    connect(m_piper, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        if (!m_piper) return;
        m_piper->deleteLater(); m_piper = nullptr;
        emit failed(QStringLiteral("no se pudo lanzar piper (configurá su ruta)"));
    });
    connect(m_piper, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this](int code, QProcess::ExitStatus) {
        QProcess *p = m_piper; m_piper = nullptr;
        if (p) p->deleteLater();
        QFile f(m_piperOut);
        if (code != 0 || !f.open(QIODevice::ReadOnly)) {
            QFile::remove(m_piperOut);
            emit failed(QStringLiteral("piper falló")); return;
        }
        const QByteArray wav = f.readAll();
        f.close();
        QFile::remove(m_piperOut);
        if (wav.isEmpty()) { emit failed(QStringLiteral("piper no generó audio")); return; }
        emit audioReady(wav, QStringLiteral("wav"));
    });
    m_piper->start(prog, args);
    if (m_piper->waitForStarted(4000)) {
        m_piper->write(text.toUtf8());
        m_piper->closeWriteChannel();
    }
}

void TtsEngine::synthesize(const QString &text)
{
    if (busy()) { emit failed(QStringLiteral("TTS ocupado")); return; }
    if (text.trimmed().isEmpty()) { emit failed(QStringLiteral("texto vacío")); return; }
    if (m_cfg.ttsMode == QLatin1String("piper")) { synthesizePiper(text); return; }
    if (m_cfg.ttsMode == QLatin1String("qwen3")) { synthesizeQwen(text); return; }

    QString base = m_cfg.ttsBaseUrl;
    while (base.endsWith('/')) base.chop(1);
    QNetworkRequest req(QUrl(base + QStringLiteral("/v1/audio/speech")));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (m_cfg.ttsIsCloud() && !m_key.isEmpty())
        req.setRawHeader("Authorization", "Bearer " + m_key.toUtf8());

    const QByteArray body = buildSpeechBody(m_cfg.ttsModel, m_cfg.ttsVoice, text, m_cfg.ttsFormat);
    const QString fmt = m_cfg.ttsFormat;
    m_streamBytes = 0;
    m_reply = m_nam.post(req, body);
    const bool streamPcm = m_cfg.ttsStreamAudio && fmt == QLatin1String("pcm");
    if (streamPcm) {
        connect(m_reply, &QNetworkReply::readyRead, this, [this]() {
            if (!m_reply) return;
            const int http = m_reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            const QByteArray contentType = m_reply->header(QNetworkRequest::ContentTypeHeader).toByteArray();
            if (http < 200 || http >= 300 || contentType.contains("json")) return;
            const QByteArray chunk = m_reply->readAll();
            if (!chunk.isEmpty()) {
                m_streamBytes += chunk.size();
                emit audioChunk(chunk, m_cfg.ttsPcmSampleRate, m_cfg.ttsPcmChannels);
            }
        });
    }
    connect(m_reply, &QNetworkReply::finished, this, [this, fmt, text]() {
        QNetworkReply *r = m_reply;
        m_reply = nullptr;
        r->deleteLater();
        if (r->error() != QNetworkReply::NoError) {
            // Endpoint HTTP caído (típico: nada escuchando en ttsBaseUrl). Si hay
            // una voz piper local instalada, sintetizar con piper en vez de fallar
            // (Ingi Charla local-first: la voz sigue andando sin servidor TTS).
            qWarning().noquote() << QStringLiteral("[charla] TTS http falló (%1); piper local=%2")
                                        .arg(r->errorString()).arg(piperAvailable());
            if (piperAvailable()) { synthesizePiper(text); return; }
            emit failed(r->errorString());
            return;
        }
        const bool streamed = m_cfg.ttsStreamAudio && fmt == QLatin1String("pcm");
        const QByteArray audio = r->readAll();
        // Algunos servers devuelven JSON de error con 200; detectar.
        if (audio.startsWith('{')) {
            const QJsonObject o = QJsonDocument::fromJson(audio).object();
            if (o.contains("error")) {
                emit failed(o.value("error").toObject().value("message").toString(
                                QStringLiteral("error TTS")));
                return;
            }
        }
        if (streamed) {
            if (!audio.isEmpty()) {
                m_streamBytes += audio.size();
                emit audioChunk(audio, m_cfg.ttsPcmSampleRate, m_cfg.ttsPcmChannels);
            }
            if (m_streamBytes <= 0) { emit failed(QStringLiteral("stream PCM vacío")); return; }
            emit audioStreamFinished();
            return;
        }
        if (audio.isEmpty()) { emit failed(QStringLiteral("audio vacío")); return; }
        emit audioReady(audio, fmt);
    });
}

void TtsEngine::cancel()
{
    if (m_reply) m_reply->abort();
    if (m_piper) {
        QProcess *p = m_piper; m_piper = nullptr;
        p->kill(); p->deleteLater();
        if (!m_piperOut.isEmpty()) QFile::remove(m_piperOut);
    }
    if (m_qwen) {
        QProcess *p = m_qwen; m_qwen = nullptr;
        p->kill(); p->deleteLater();
        if (!m_qwenOut.isEmpty()) QFile::remove(m_qwenOut);
    }
    // Turno residente en vuelo: descartarlo y matar el proceso (se relanza en el
    // próximo synthesize). Evita mezclar audio de un turno cancelado.
    if (m_piperPending) {
        if (!m_piperPendingOut.isEmpty()) QFile::remove(m_piperPendingOut);
        m_piperPending = false;
        m_piperPendingText.clear();
        m_piperPendingOut.clear();
    }
    tearDownPiperResident();
}
