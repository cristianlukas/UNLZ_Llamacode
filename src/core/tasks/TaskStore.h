#pragma once
#include <QAbstractListModel>
#include <QList>
#include <QVariantMap>
#include <QJsonObject>
#include <QJsonArray>

// TaskStore — catálogo de "Tasks": macros configurables que NO son tontas. Cada
// Task guarda un objetivo en lenguaje natural (la intención) + una secuencia de
// pasos de referencia. En la ejecución el agente IA re-deriva las acciones con
// sus tools (browser MCP, shell, mail, etc.) y se adapta si cambió un botón o un
// archivo de lugar. La grabación literal queda como referencia, no como guion
// rígido.
//
// Persistencia: <AppLocalData>/tasks/tasks.json (respeta
// QStandardPaths::setTestModeEnabled para aislamiento en tests).
//
// Las funciones de (de)serialización y composición de prompt son PURAS (estáticas,
// sin disco) → unit test directo. El modelo expone CRUD a QML como BinaryRegistry.
//
// Fase 1: CRUD + ejecución manual. El campo `schedule` (cron) se persiste pero su
// disparo automático es Fase 2.
class TaskStore : public QAbstractListModel
{
    Q_OBJECT
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    enum Roles {
        IdRole = Qt::UserRole + 1,
        NameRole,
        DescriptionRole,
        ProfileIdRole,
        StepsRole,          // QVariantList de pasos {kind,intent,ref}
        StepCountRole,
        ScheduleEnabledRole,
        ScheduleCronRole,
        CreatedAtRole,
        UpdatedAtRole,
        LastRunAtRole,
        LastRunStatusRole   // "" | "ok" | "error" | "running"
    };

    explicit TaskStore(QObject *parent = nullptr);

    // QAbstractListModel
    int rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    int count() const { return m_items.size(); }

    // CRUD. `def` usa las claves de roleNames (name, description, profileId,
    // steps[], scheduleEnabled, scheduleCron). Devuelve el id (nuevo o existente).
    Q_INVOKABLE QString save(const QString &id, const QVariantMap &def);
    Q_INVOKABLE bool remove(const QString &id);
    Q_INVOKABLE QVariantMap get(const QString &id) const;
    // Todas las Tasks como filas (para el scheduler).
    QVariantList all() const;
    Q_INVOKABLE QString duplicate(const QString &id);
    Q_INVOKABLE void refresh();
    // Marca el resultado de una corrida (actualiza lastRunAt/lastRunStatus).
    Q_INVOKABLE void markRun(const QString &id, const QString &status);

    // Nombre → slug seguro / id. minúsculas [a-z0-9_-].
    static QString sanitize(const QString &name);

    // Compone el prompt-objetivo que recibe el agente. PURA y testeable: arma el
    // objetivo + los pasos de referencia + la consigna de adaptación.
    static QString composePrompt(const QVariantMap &task);

    // (de)serialización pura (sin disco).
    static QJsonObject toJson(const QVariantMap &task);
    static QVariantMap fromJson(const QJsonObject &obj);

signals:
    void countChanged();
    void changed();

private:
    void load();
    void save() const;
    QString storagePath() const;
    int indexOfId(const QString &id) const;

    QList<QVariantMap> m_items;
};
