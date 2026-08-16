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
    static QString hardwareFingerprint(const QVariantMap &hardware);
    static QString recommendedSplitMode(const QVariantMap &hardware);
    static QVariantMap performanceRecommendation(const QVariantMap &hardware,
                                                 const QString &target = {});
    static double performanceScore(const QVariantMap &sample, const QString &target = {});
};
