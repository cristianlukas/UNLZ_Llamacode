#pragma once
#include <QObject>
#include <QString>
#include <QHash>

// Almacén de secretos (API keys cloud) fuera del repo y NO commiteable: vive en
// AppConfigLocation (Roaming en Windows), nunca en los perfiles del project root.
// Los perfiles guardan sólo un *nombre de referencia* (ref); el secreto real se
// resuelve por: 1) variable de entorno con ese nombre, 2) este store en disco.
// Si no se encuentra, la UI debe pedirlo de nuevo al seleccionar el perfil.
//
// Cifrado at-rest, backend elegido en runtime:
//  1) QtKeychain (si se compiló con HAVE_QTKEYCHAIN y el keyring del SO responde):
//     Secret Service (Linux GNOME/KDE), Credential Store (Windows), Keychain (macOS).
//  2) Fallback si no hay keyring (ej Linux headless): archivo cifrado con DPAPI en
//     Windows; en otros OS, texto plano marcado (preferir env var ahí).
// En memoria los valores están descifrados (cache); el backend persiste cifrado.
class SecretStore : public QObject
{
    Q_OBJECT
public:
    explicit SecretStore(QObject *parent = nullptr);

    // Resuelve el secreto para `ref`: env var (qgetenv) → store en disco. "" si no hay.
    QString resolve(const QString &ref) const;
    // ¿Hay un valor resoluble (env o disco) para `ref`?
    bool has(const QString &ref) const;
    // Guarda/actualiza el secreto en disco (no toca env). ref vacío = no-op.
    void set(const QString &ref, const QString &value);
    // Borra el secreto en disco (no toca env).
    void remove(const QString &ref);

    // Ruta del archivo de secretos de fallback (para diagnóstico).
    static QString filePath();
    // Backend activo: "keychain" o "file".
    QString backendName() const;
    bool usingKeychain() const { return m_useKeychain; }

private:
    void load();
    void save() const;
    bool m_useKeychain = false;                  // backend elegido en el ctor
    mutable QHash<QString, QString> m_secrets;   // cache ref → valor descifrado
};
