#include "SecretStore.h"
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>

#ifdef Q_OS_WIN
#  include <windows.h>
#  include <wincrypt.h>   // CryptProtectData / CryptUnprotectData (DPAPI)
#endif

#ifdef HAVE_QTKEYCHAIN
#  if __has_include(<qt6keychain/keychain.h>)
#    include <qt6keychain/keychain.h>   // instalado en el sistema
#  else
#    include <keychain.h>               // vía FetchContent (include dir del target)
#  endif
#  include <QEventLoop>
#endif

// Servicio bajo el cual se guardan las entradas en el keyring del SO.
static QString kcService() { return QStringLiteral("LlamaCode"); }

// Marcadores de formato del valor persistido en el ARCHIVO de fallback. Permiten
// migrar el plaintext anterior y distinguir blobs cifrados de texto plano.
static const QString kEncPrefix   = QStringLiteral("dpapi:");   // DPAPI base64
static const QString kPlainPrefix = QStringLiteral("plain:");   // sin cifrado (no-Win)

// ───────────────────────── QtKeychain (sync wrappers) ─────────────────────────
#ifdef HAVE_QTKEYCHAIN
static bool kcWrite(const QString &key, const QString &val)
{
    QKeychain::WritePasswordJob job(kcService());
    job.setAutoDelete(false);
    job.setKey(key);
    job.setTextData(val);
    QEventLoop loop;
    QObject::connect(&job, &QKeychain::Job::finished, &loop, &QEventLoop::quit);
    job.start();
    loop.exec();
    return job.error() == QKeychain::NoError;
}
static QString kcRead(const QString &key, bool *ok)
{
    QKeychain::ReadPasswordJob job(kcService());
    job.setAutoDelete(false);
    job.setKey(key);
    QEventLoop loop;
    QObject::connect(&job, &QKeychain::Job::finished, &loop, &QEventLoop::quit);
    job.start();
    loop.exec();
    const bool good = job.error() == QKeychain::NoError;
    if (ok) *ok = good;
    return good ? job.textData() : QString();
}
static void kcDelete(const QString &key)
{
    QKeychain::DeletePasswordJob job(kcService());
    job.setAutoDelete(false);
    job.setKey(key);
    QEventLoop loop;
    QObject::connect(&job, &QKeychain::Job::finished, &loop, &QEventLoop::quit);
    job.start();
    loop.exec();
}
#endif

// ───────────────────────── Fallback: archivo cifrado ──────────────────────────
#ifdef Q_OS_WIN
// Entropía secundaria fija: liga el blob a esta app además de al usuario del SO.
static QByteArray appEntropy() { return QByteArrayLiteral("llamacode.secretstore.v1"); }

static QByteArray dpapiProtect(const QByteArray &plain)
{
    DATA_BLOB in, out, ent;
    QByteArray entropy = appEntropy();
    in.pbData  = reinterpret_cast<BYTE *>(const_cast<char *>(plain.constData()));
    in.cbData  = static_cast<DWORD>(plain.size());
    ent.pbData = reinterpret_cast<BYTE *>(entropy.data());
    ent.cbData = static_cast<DWORD>(entropy.size());
    if (!CryptProtectData(&in, L"llamacode-secret", &ent, nullptr, nullptr,
                          CRYPTPROTECT_UI_FORBIDDEN, &out))
        return {};
    QByteArray r(reinterpret_cast<char *>(out.pbData), static_cast<int>(out.cbData));
    LocalFree(out.pbData);
    return r;
}
static QByteArray dpapiUnprotect(const QByteArray &blob)
{
    DATA_BLOB in, out, ent;
    QByteArray entropy = appEntropy();
    in.pbData  = reinterpret_cast<BYTE *>(const_cast<char *>(blob.constData()));
    in.cbData  = static_cast<DWORD>(blob.size());
    ent.pbData = reinterpret_cast<BYTE *>(entropy.data());
    ent.cbData = static_cast<DWORD>(entropy.size());
    if (!CryptUnprotectData(&in, nullptr, &ent, nullptr, nullptr,
                            CRYPTPROTECT_UI_FORBIDDEN, &out))
        return {};
    QByteArray r(reinterpret_cast<char *>(out.pbData), static_cast<int>(out.cbData));
    LocalFree(out.pbData);
    return r;
}
#endif

// Cifra un secreto para persistir en el archivo de fallback.
static QString encodeSecret(const QString &plain)
{
#ifdef Q_OS_WIN
    const QByteArray blob = dpapiProtect(plain.toUtf8());
    if (!blob.isEmpty())
        return kEncPrefix + QString::fromLatin1(blob.toBase64());
    return QString();   // si DPAPI falla, no degradar a texto plano
#else
    return kPlainPrefix + plain;   // fallback no-Windows: marcado como NO cifrado
#endif
}
static QString decodeSecret(const QString &stored)
{
    if (stored.startsWith(kEncPrefix)) {
#ifdef Q_OS_WIN
        const QByteArray blob = QByteArray::fromBase64(
            stored.mid(kEncPrefix.size()).toLatin1());
        return QString::fromUtf8(dpapiUnprotect(blob));
#else
        return QString();
#endif
    }
    if (stored.startsWith(kPlainPrefix))
        return stored.mid(kPlainPrefix.size());
    return stored;   // legacy plaintext sin marcador
}

// ─────────────────────────────── SecretStore ──────────────────────────────────
QString SecretStore::filePath()
{
    QString dir = QStandardPaths::writableLocation(QStandardPaths::AppConfigLocation);
    if (dir.isEmpty())
        dir = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    return dir + QStringLiteral("/secrets.json");
}

SecretStore::SecretStore(QObject *parent) : QObject(parent)
{
    // Elegir backend una vez: probar el keyring del SO; si responde, usarlo. Si no
    // (Linux headless sin Secret Service, etc.), caer al archivo cifrado.
#ifdef HAVE_QTKEYCHAIN
    const QString probe = QStringLiteral("__lc_probe__");
    if (kcWrite(probe, QStringLiteral("1"))) {
        m_useKeychain = true;
        kcDelete(probe);
    }
#endif
    if (!m_useKeychain)
        load();
}

QString SecretStore::backendName() const
{
    return m_useKeychain ? QStringLiteral("keychain") : QStringLiteral("file");
}

void SecretStore::load()
{
    m_secrets.clear();
    QFile f(filePath());
    if (!f.open(QIODevice::ReadOnly)) return;
    const QJsonObject o = QJsonDocument::fromJson(f.readAll()).object();
    bool needsMigration = false;
    for (auto it = o.begin(); it != o.end(); ++it) {
        const QString stored = it.value().toString();
        if (!stored.startsWith(kEncPrefix) && !stored.startsWith(kPlainPrefix))
            needsMigration = true;
        const QString plain = decodeSecret(stored);
        if (!plain.isEmpty())
            m_secrets.insert(it.key(), plain);
    }
    if (needsMigration && !m_secrets.isEmpty())
        save();
}

void SecretStore::save() const
{
    const QString path = filePath();
    QDir().mkpath(QFileInfo(path).absolutePath());
    QJsonObject o;
    for (auto it = m_secrets.begin(); it != m_secrets.end(); ++it) {
        const QString enc = encodeSecret(it.value());
        if (!enc.isEmpty())
            o.insert(it.key(), enc);
    }
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return;
    f.write(QJsonDocument(o).toJson(QJsonDocument::Compact));
    f.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner);
}

QString SecretStore::resolve(const QString &ref) const
{
    if (ref.isEmpty()) return {};
    // 1) variable de entorno con ese nombre exacto (lo más seguro/portable, headless).
    const QByteArray env = qgetenv(ref.toUtf8().constData());
    if (!env.isEmpty()) return QString::fromUtf8(env);
    // 2) cache en memoria.
    if (m_secrets.contains(ref)) return m_secrets.value(ref);
#ifdef HAVE_QTKEYCHAIN
    // 3) keyring del SO (cifrado por el SO). Se cachea el resultado.
    if (m_useKeychain) {
        bool ok = false;
        const QString v = kcRead(ref, &ok);
        if (ok && !v.isEmpty()) m_secrets.insert(ref, v);
        return v;
    }
#endif
    return {};   // file mode: ya estaba en m_secrets (load) si existía
}

bool SecretStore::has(const QString &ref) const
{
    return !resolve(ref).isEmpty();
}

void SecretStore::set(const QString &ref, const QString &value)
{
    if (ref.isEmpty()) return;
    if (value.isEmpty()) { remove(ref); return; }
    m_secrets.insert(ref, value);
#ifdef HAVE_QTKEYCHAIN
    if (m_useKeychain) { kcWrite(ref, value); return; }
#endif
    save();
}

void SecretStore::remove(const QString &ref)
{
    const bool had = m_secrets.remove(ref) > 0;
#ifdef HAVE_QTKEYCHAIN
    if (m_useKeychain) { kcDelete(ref); return; }
#endif
    if (had) save();
}
