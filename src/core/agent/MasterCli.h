#pragma once
#include <QObject>
#include <QString>
#include <QVariantMap>
#include <QHash>
#include <QSet>

// Detección y metadata de CLIs "maestro" (claude code / codex) usados como
// supervisor del agente local. La detección también expone capacidades; la
// ejecución pasa por ManagedAgentRunStore desde AgentToolRunner (tool ask_teacher).
class MasterCli : public QObject
{
    Q_OBJECT
public:
    explicit MasterCli(QObject *parent = nullptr) : QObject(parent) {}

    // CLIs soportados: "claude" | "codex". Lista para poblar la UI.
    Q_INVOKABLE static QStringList supported() { return {QStringLiteral("claude"),
                                                         QStringLiteral("codex")}; }

    // Estado de un CLI: {name, installed(bool), version, path, label, installCommand}.
    // Cachea el resultado por nombre; pasar force=true reejecuta la detección.
    Q_INVOKABLE QVariantMap status(const QString &name, bool force = false);

    // Versión no bloqueante para la UI: el probe corre `--version` y `--help`
    // (CLIs Node: segundos), así que nunca se hace en el hilo de QML. Devuelve
    // la cache si la hay; si no (o con force), lanza el probe en un worker y
    // devuelve un placeholder con probing=true (o la cache vieja marcada así).
    // Al terminar emite statusChanged(name) y status(name) ya sale de cache.
    Q_INVOKABLE QVariantMap requestStatus(const QString &name, bool force = false);

    // Detección pura, sin cache (thread-safe: sólo QProcess local).
    static QVariantMap probe(const QString &name);

    // Comando de instalación sugerido (npm global). No instala: la UI lo muestra.
    Q_INVOKABLE static QString installCommand(const QString &name);

    // Nombre legible para la UI.
    Q_INVOKABLE static QString label(const QString &name);

    // Binario invocable resuelto en PATH ("" si no está). Reusa cache de status.
    QString resolvePath(const QString &name);

    // Limpia la cache (tras instalar, por ej.).
    Q_INVOKABLE void invalidate() { m_cache.clear(); }

    bool isProbing(const QString &name) const { return m_probing.contains(name); }

signals:
    void statusChanged(const QString &name);

private:
    QHash<QString, QVariantMap> m_cache;
    QSet<QString> m_probing;
};
