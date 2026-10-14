#pragma once

#include <QJsonObject>
#include <QString>

// Progreso de carga de un modelo en llama-server, leido de su stderr.
//
// Las ETAPAS son reales (marcadores del log: "loading model", "llama_context:",
// "warming up"). El PORCENTAJE dentro de la carga de pesos sale de:
//  1. los '.' del progress_callback de llama.cpp (uno por cada % de tensores),
//     cuando la verbosidad del server los deja pasar; si no
//  2. el tiempo transcurrido contra lo que tardo la ultima carga del mismo
//     perfil (o una estimacion por tamano del GGUF). Es estimado: queda topado
//     en 89% hasta que el log confirme la etapa siguiente.
//
// Estados: "idle" | "starting" | "loading" | "warmup" | "ready" | "failed".
// progress = 0..100 (-1 = sin dato).
class ModelLoadProgress
{
public:
    // Server lanzado. expectedMs = duracion esperada de la carga (0 = desconocida).
    void reset(qint64 nowMs, qint64 expectedMs);
    void feed(const QString &chunk);    // stderr crudo, en cualquier particion
    // Health OK. Devuelve cuanto tardo la carga (para la proxima estimacion).
    qint64 markReady(qint64 nowMs);
    void markFailed(const QString &detail = QString());
    void markIdle();

    QString state() const { return m_state; }
    int progress(qint64 nowMs) const;
    bool estimated() const { return m_dots == 0; }
    QString detail() const { return m_detail; }
    bool active() const;                // starting/loading/warmup
    QJsonObject toJson(qint64 nowMs) const;

    // Duracion esperada sin historial: arranque fijo + lectura del archivo.
    static qint64 expectedMsForFileSize(qint64 bytes);
    // Etiqueta corta para la UI ("Cargando modelo remoto 42%").
    static QString label(const QString &state, int progress, bool remote);

private:
    void advance(const QString &state);

    QString m_state = QStringLiteral("idle");
    QString m_detail;
    qint64 m_startMs = 0;
    qint64 m_expectedMs = 0;
    int m_dots = 0;      // 0..100: '.' contados del progress_callback
};
