#pragma once
#include <QObject>
#include <QString>
#include <QSet>
#include <QVariantList>

// Renderiza bloques ```mermaid del chat a PNG vía sidecar mermaid-cli (mmdc).
//  - Detección/split de bloques en C++ (testeable) → segments().
//  - Render async con QProcess; cache por md5 del source en AppLocalData/mermaid.
//  - PNG (no SVG) para que QML Image lo cargue sin depender de Qt6::Svg.
// Bloques sin cerrar (streaming) quedan como texto: no se rinde a medias.
// Sidecar: env LLAMACODE_MMDC pisa; si no, se busca "mmdc" en PATH.
class MermaidRenderer : public QObject
{
    Q_OBJECT
    // ¿Está mmdc disponible? La UI lo usa para decidir si parsear mermaid.
    Q_PROPERTY(bool available READ available CONSTANT)

public:
    explicit MermaidRenderer(QObject *parent = nullptr);

    bool available() const;

    // Parte el contenido en segmentos {type:"text"|"mermaid", text:...}.
    // Sólo cierra bloques mermaid con fence de apertura Y cierre.
    Q_INVOKABLE QVariantList segments(const QString &content) const;

    // md5 hex del source (clave de cache/identidad de diagrama).
    Q_INVOKABLE QString sourceHash(const QString &source) const;

    // Ruta del PNG cacheado, o "" si todavía no se rindió.
    Q_INVOKABLE QString cachedPath(const QString &source) const;

    // Dispara el render async. Emite renderReady o renderFailed. Idempotente:
    // si ya hay cache emite ready directo; si está en vuelo, no relanza.
    Q_INVOKABLE void requestRender(const QString &source);

    // Helper estático para tests: split puro sin instanciar QML.
    static QVariantList splitSegments(const QString &content);

signals:
    void renderReady(const QString &hash, const QString &pngPath);
    void renderFailed(const QString &hash, const QString &reason);

private:
    static QString cacheDir();
    static QString mmdcExe();

    QSet<QString> m_pending;  // hashes en vuelo (dedupe)
};
