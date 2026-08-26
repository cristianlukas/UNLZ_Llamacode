#pragma once

#include <QVariantList>
#include <QVariantMap>

// Reglas portables para convertir la salida de nvidia-smi en señales útiles
// para perfiles y benchmarks. No ejecuta procesos: el probe de hardware queda
// en AppController y esta clase se mantiene pura para poder testearla sin GPU.
class HardwareDiagnostics
{
public:
    static QVariantList parseNvidiaSmiCsv(const QString &csv);
    static QVariantMap parseTopologyMatrix(const QString &text);
    static bool parseNvlinkActive(const QString &text);
    static QVariantMap enrichTopology(const QVariantMap &hardware,
                                      const QString &topologyText,
                                      const QString &nvlinkText);
    // Plan opt-in para Ingi Charla: reserva la GPU con menos VRAM para STT/TTS
    // y auxiliares, y calcula el reparto de la VRAM restante para el LLM. Si
    // modelRequiredMb > 0, también evita prometer un perfil que no entre en
    // esa capacidad. Es puro para poder probarlo sin tener dos GPU físicas.
    static QVariantMap voiceGpuPlan(const QVariantMap &hardware,
                                    double voiceReserveMb = 2048.0,
                                    double modelRequiredMb = 0.0);
    static QString hardwareFingerprint(const QVariantMap &hardware);
    static QString recommendedSplitMode(const QVariantMap &hardware);
    static QVariantMap performanceRecommendation(const QVariantMap &hardware,
                                                 const QString &target = {});
    static double performanceScore(const QVariantMap &sample, const QString &target = {});
};
