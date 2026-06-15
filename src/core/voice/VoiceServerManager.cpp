#include "VoiceServerManager.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QUrl>

namespace {
// Catálogo declarativo. Las URLs de modelos ggml de whisper.cpp viven en HF
// (estables). Si una cambia, se ajusta acá.
struct Engine {
    const char *id; const char *name; const char *engine;
    const char *modelFile; const char *modelUrl; int sizeMb;
    const char *endpointPath; int defaultPort;
};
const Engine kEngines[] = {
    {"whisper-tiny",  "Whisper tiny (multilingüe, ~78 MB, rápido)",   "whisper-cpp",
     "ggml-tiny.bin",
     "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
     78,  "/inference", 8081},
    {"whisper-base",  "Whisper base (multilingüe, ~148 MB, balance)", "whisper-cpp",
     "ggml-base.bin",
     "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
     148, "/inference", 8081},
    {"whisper-small", "Whisper small (multilingüe, ~488 MB, preciso)","whisper-cpp",
     "ggml-small.bin",
     "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
     488, "/inference", 8081},
};
}

VoiceServerManager::VoiceServerManager(QObject *parent) : QObject(parent) {}

QVariantList VoiceServerManager::sttCatalog()
{
    QVariantList out;
    for (const Engine &e : kEngines) {
        out.append(QVariantMap{
            {"id", QString::fromLatin1(e.id)},
            {"name", QString::fromUtf8(e.name)},
            {"engine", QString::fromLatin1(e.engine)},
            {"modelFile", QString::fromLatin1(e.modelFile)},
            {"modelUrl", QString::fromLatin1(e.modelUrl)},
            {"sizeMb", e.sizeMb},
            {"endpointPath", QString::fromLatin1(e.endpointPath)},
            {"defaultPort", e.defaultPort}});
    }
    return out;
}

QVariantMap VoiceServerManager::sttEngine(const QString &id)
{
    for (const Engine &e : kEngines)
        if (id == QLatin1String(e.id))
            return sttCatalog().at(&e - kEngines).toMap();
    return {};
}

QString VoiceServerManager::installRoot()
{
    const QString base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    return base + QStringLiteral("/voice");
}

QString VoiceServerManager::modelPath(const QString &engineId)
{
    const QVariantMap e = sttEngine(engineId);
    if (e.isEmpty()) return {};
    return installRoot() + QStringLiteral("/") + engineId + QStringLiteral("/")
           + e.value("modelFile").toString();
}

bool VoiceServerManager::modelInstalled(const QString &engineId) const
{
    const QString p = modelPath(engineId);
    return !p.isEmpty() && QFile::exists(p);
}

QString VoiceServerManager::endpointPath(const QString &engineId)
{
    const QVariantMap e = sttEngine(engineId);
    return e.value("endpointPath", QStringLiteral("/inference")).toString();
}

QStringList VoiceServerManager::buildWhisperArgs(const QString &modelPath, const QString &host,
                                                 int port, const QString &language)
{
    QStringList a{QStringLiteral("-m"), modelPath,
                  QStringLiteral("--host"), host,
                  QStringLiteral("--port"), QString::number(port)};
    if (!language.isEmpty() && language != QLatin1String("auto"))
        a << QStringLiteral("-l") << language;
    return a;
}

void VoiceServerManager::installModel(const QString &engineId)
{
    if (m_reply) { emit installFinished(engineId, false, QStringLiteral("descarga en curso")); return; }
    const QVariantMap e = sttEngine(engineId);
    if (e.isEmpty()) { emit installFinished(engineId, false, QStringLiteral("motor desconocido")); return; }

    const QString dst = modelPath(engineId);
    QDir().mkpath(QFileInfo(dst).absolutePath());
    m_file = new QFile(dst + QStringLiteral(".part"));
    if (!m_file->open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        delete m_file; m_file = nullptr;
        emit installFinished(engineId, false, QStringLiteral("no se pudo escribir el modelo"));
        return;
    }
    m_engineId = engineId;
    emit installProgress(engineId, 0, QStringLiteral("Descargando modelo…"));

    QNetworkRequest req(QUrl(e.value("modelUrl").toString()));
    req.setAttribute(QNetworkRequest::RedirectPolicyAttribute,
                     QNetworkRequest::NoLessSafeRedirectPolicy);
    m_reply = m_nam.get(req);
    connect(m_reply, &QNetworkReply::readyRead, this, [this]() {
        if (m_file) m_file->write(m_reply->readAll());
    });
    connect(m_reply, &QNetworkReply::downloadProgress, this, [this](qint64 r, qint64 t) {
        const int pct = (t > 0) ? int(r * 100 / t) : 0;
        emit installProgress(m_engineId, pct,
            QStringLiteral("Descargando modelo… %1%").arg(pct));
    });
    connect(m_reply, &QNetworkReply::finished, this, [this]() {
        QNetworkReply *r = m_reply; m_reply = nullptr;
        const QString id = m_engineId;
        const bool ok = (r->error() == QNetworkReply::NoError);
        const QString err = r->errorString();
        if (m_file) { m_file->write(r->readAll()); m_file->close(); }
        const QString part = m_file ? m_file->fileName() : QString();
        delete m_file; m_file = nullptr;
        r->deleteLater();
        if (ok && !part.isEmpty()) {
            const QString fin = part.left(part.size() - 5); // quita ".part"
            QFile::remove(fin);
            if (QFile::rename(part, fin)) { emit installFinished(id, true, QString()); return; }
            emit installFinished(id, false, QStringLiteral("no se pudo finalizar el archivo"));
        } else {
            if (!part.isEmpty()) QFile::remove(part);
            emit installFinished(id, false, ok ? QStringLiteral("descarga incompleta") : err);
        }
    });
}

void VoiceServerManager::cancelInstall()
{
    if (m_reply) m_reply->abort();
}
