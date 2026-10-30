#pragma once

#include <QHash>
#include <QJsonArray>
#include <QMap>
#include <QString>
#include <QVariantList>
#include <QVariantMap>
#include <QVector>

// Estado en vivo del servidor para la pantalla Monitor. Junta tres fuentes que
// llama-server ya expone sin flags extra:
//   • GET /slots (por slot: tarea, tokens de prompt, reusados de caché, prefill
//     procesado, tokens generados, n_ctx). Polleado cada ~1 s da las
//     velocidades de prefill/decode y, cuando una tarea termina, una fila de
//     "requests recientes".
//   • El log de carga ("CUDA0 model buffer size = X MiB", KV, compute...) →
//     qué ocupa cada GPU.
//   • nvidia-smi y /proc → la máquina (carga, potencia, temperatura, CPU, RAM).
// Todo es puro (sin red ni procesos): AppController alimenta los textos y el
// reloj, y los tests hacen lo mismo con muestras fijas.
class ServerMonitor
{
public:
    static constexpr int kHistory = 120;      // muestras por serie (~2 min a 1 Hz)
    static constexpr int kMaxRequests = 200;

    void reset();

    // Una respuesta de GET /slots. nowMs: reloj monotónico del llamador.
    void ingestSlots(const QJsonArray &slotList, qint64 nowMs);
    // Texto de /metrics (Prometheus). Opcional: sin --metrics da 404 y no se llama.
    void ingestMetrics(const QString &prometheus);
    // stderr del server: acumula buffers por dispositivo. Tolera líneas partidas.
    void ingestServerLog(const QString &text);
    // Una muestra de hardware ya agregada (ver hardwareSample()).
    void ingestHardware(const QVariantMap &sample);

    // {state, decodeTps, prefillTps, peakDecodeTps, peakDecodeAt, msPerToken,
    //  requestsServed, processing, deferred, speculative, slots, context{...},
    //  buffers{device:{model,kv,compute,output}}, history{...}}
    QVariantMap snapshot() const;
    QVariantList recentRequests(int limit = kMaxRequests) const;
    bool hasSlots() const { return m_primed; }

    // ── Parsers puros ────────────────────────────────────────────────────────
    static QHash<QString, double> parsePrometheus(const QString &text);
    // "load_tensors: CUDA0 model buffer size = 7890.12 MiB" → {device, kind, mib}
    static QVariantMap parseBufferLine(const QString &line);
    // Índice de GPU de un dispositivo de ggml ("CUDA1" → 1, "ROCm0" → 0); -1 si
    // es CPU/host.
    static int gpuIndexForDevice(const QString &device);
    // nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,
    //   power.draw,power.limit,uuid,utilization.gpu,temperature.gpu,
    //   pcie.link.gen.current,pcie.link.width.current --format=csv,noheader,nounits
    // Mismo formato que publicaba AppController::serverStats (gpus + totales).
    static QVariantMap parseNvidiaSmiGpus(const QString &csv);
    // nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory → {uuid: {pid: MiB}}
    static QHash<QString, QHash<qint64, double>> parseComputeApps(const QString &csv);
    // Reparto de cada GPU: pesos, KV, activaciones, resto del server, otros
    // programas, libre. serverPid <= 0 o apps sin datos (WDDM) → el resto del
    // usado va a "server".
    static QVariantList gpuBreakdown(const QVariantMap &gpuStats,
                                     const QVariantMap &buffers,
                                     const QHash<QString, QHash<qint64, double>> &apps,
                                     qint64 serverPid);

    // /proc/stat → {total, idle} (jiffies de la línea "cpu").
    static QPair<quint64, quint64> parseProcStatCpu(const QString &text);
    // /proc/meminfo → {totalMb, availableMb}
    static QVariantMap parseMeminfo(const QString &text);
    // /proc/diskstats → {readSectors, writeSectors} de discos enteros
    // (sin particiones, loop, ram, zram ni device-mapper).
    static QPair<quint64, quint64> parseDiskstats(const QString &text);

    // Reporte en texto plano para "Copiar reporte".
    static QString report(const QVariantMap &snapshot, const QVariantMap &serverStats,
                          const QVariantMap &system, const QVariantList &requests,
                          const QString &model);

private:
    struct SlotTrack {
        int taskId = -1;
        bool processing = false;
        int prompt = 0, cached = 0, processed = 0, decoded = 0, nCtx = 0;
        qint64 firstMs = 0, lastMs = 0;
        qint64 decodeStartMs = -1;
        int decodeStartTokens = 0;
        bool seenRunning = false;
    };
    void finalize(int slotId, const SlotTrack &t, qint64 endMs);
    static void push(QVector<double> &series, double v);

    bool m_primed = false;
    QMap<int, SlotTrack> m_slots;
    QVector<QVariantMap> m_requests;      // más nuevo al final
    int m_served = 0;
    int m_processing = 0;
    double m_decodeTps = 0, m_prefillTps = 0, m_peakDecode = 0;
    qint64 m_peakDecodeAt = 0;            // ms epoch
    qint64 m_lastIngestMs = -1;
    bool m_speculative = false;
    QVariantMap m_context;
    QString m_state = QStringLiteral("idle");
    double m_deferred = -1;
    QString m_logTail;
    QMap<QString, QVariantMap> m_buffers; // device → {model,kv,compute,output} MiB
    QMap<QString, QVector<double>> m_history;
};
