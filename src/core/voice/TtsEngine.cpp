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

void TtsEngine::synthesizePiper(const QString &text)
{
    QString modelPath = m_piperModel;
    if (modelPath.isEmpty())
        modelPath = VoiceServerManager::ttsModelPath(QStringLiteral("es_ES-davefx-medium"));
    if (modelPath.isEmpty() || !QFile::exists(modelPath)) {
        emit failed(QStringLiteral("voz piper no instalada")); return;
    }
    const QString tmp = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
        + QStringLiteral("/lc_tts_") + QUuid::createUuid().toString(QUuid::Id128)
        + QStringLiteral(".wav");
    m_piperOut = tmp;
    QString prog = m_piperBin;
    if (prog.isEmpty()) prog = VoiceServerManager::installedBinaryPath(QStringLiteral("piper"));
    if (prog.isEmpty()) prog = QStringLiteral("piper");
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

    QString base = m_cfg.ttsBaseUrl;
    while (base.endsWith('/')) base.chop(1);
    QNetworkRequest req(QUrl(base + QStringLiteral("/v1/audio/speech")));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (m_cfg.ttsIsCloud() && !m_key.isEmpty())
        req.setRawHeader("Authorization", "Bearer " + m_key.toUtf8());

    const QByteArray body = buildSpeechBody(m_cfg.ttsModel, m_cfg.ttsVoice, text, m_cfg.ttsFormat);
    const QString fmt = m_cfg.ttsFormat;
    m_reply = m_nam.post(req, body);
    connect(m_reply, &QNetworkReply::finished, this, [this, fmt, text]() {
        QNetworkReply *r = m_reply;
        m_reply = nullptr;
        r->deleteLater();
        if (r->error() != QNetworkReply::NoError) {
            // Endpoint HTTP caído (típico: nada escuchando en ttsBaseUrl). Si hay
            // una voz piper local instalada, sintetizar con piper en vez de fallar
            // (Ingi Charla local-first: la voz sigue andando sin servidor TTS).
            if (piperAvailable()) { synthesizePiper(text); return; }
            emit failed(r->errorString());
            return;
        }
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
}
