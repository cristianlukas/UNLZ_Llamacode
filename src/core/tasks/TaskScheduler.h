#pragma once
#include <QObject>
#include <QDateTime>
#include <QSet>
#include <QString>
#include <QVariantList>

class TaskStore;
class QTimer;

// TaskScheduler — disparador in-app de Tasks programadas (cron). Tick por minuto;
// en cada tick consulta el TaskStore por Tasks con scheduleEnabled + cron válido
// que matcheen el minuto actual y emite taskDue(id). AppController conecta
// taskDue→runTask. Solo corre mientras la app vive (decisión: timer in-app).
//
// La selección es PURA y estática (dueTaskIds) → unit-testeable sin reloj real.
// La instancia evita doble-disparo en el mismo minuto con una clave id@minuto.
class TaskScheduler : public QObject
{
    Q_OBJECT
public:
    explicit TaskScheduler(TaskStore *store, QObject *parent = nullptr);

    void setEnabled(bool on);
    bool enabled() const { return m_enabled; }

    // Ids de Tasks que deben dispararse en `now` (scheduleEnabled + cron matchea).
    // Pura: no toca estado de instancia ni de-duplica. tasks = filas del TaskStore
    // como QVariantList de QVariantMap.
    static QStringList dueTaskIds(const QVariantList &tasks, const QDateTime &now);

    // Evalúa `now` y emite taskDue por cada Task vencida no disparada aún ese minuto.
    // Expuesta para test (inyecta el instante); el tick interno la llama con now().
    void evaluate(const QDateTime &now);

signals:
    void taskDue(const QString &id);

private:
    void tick();
    QVariantList snapshot() const;

    TaskStore *m_store = nullptr;
    QTimer    *m_timer = nullptr;
    bool       m_enabled = false;
    QSet<QString> m_fired;   // claves "id@yyyyMMddHHmm" ya disparadas
};
