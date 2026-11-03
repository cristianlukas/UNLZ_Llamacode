#pragma once
#include <QString>
#include <QStringList>
#include <QList>
#include <QVariantList>
#include <QVariantMap>

// Recomendador de ajustes de llama-server para Ingi Charla (voz real-time).
// Analiza los args EFECTIVOS del perfil activo y propone solo lo que mejora la
// latencia de voz en ESE perfil (dinámico, no una lista fija):
//   - ubatch/batch chicos → prefill lento (el asesino: 53k tokens a 230 tok/s).
//   - ctx gigante → KV/checkpoints pesados y VRAM desperdiciada para charla.
//   - sin --cache-reuse → cada turno re-procesa el prefijo entero.
//   - --predict alto/infinito → respuestas de voz no necesitan 4k tokens.
// VRAM-aware: en equipos chicos no sube batches (costo de compute buffers).
// Todo puro y testeable; AppController lo aplica al relanzar el server.
namespace CharlaTuning {

struct Change {
    QString flag;         // ej "--ubatch-size"
    QString current;      // valor actual ("" = ausente)
    QString recommended;  // valor propuesto
    QString reason;       // explicación corta para el popup
};

// Valor de un flag en los args ("" si no está).
QString argValue(const QStringList &args, const QString &flag);

// Cambios recomendados para voz. vramGb <= 0 = desconocida (conservador:
// no sube batches, solo ctx/predict/cache-reuse).
QList<Change> recommend(const QStringList &args, double vramGb);

// Aplica los cambios sobre args: reemplaza el valor si el flag existe, o
// agrega el par al final si falta. No toca nada más.
QStringList apply(QStringList args, const QList<Change> &changes);

// ¿Hay un cambio que el modo AGENTE de Charla no puede tolerar? Hoy: subir un
// --ctx-size por debajo del mínimo (con 4096 el agente de voz compacta en cada
// turno y pierde la consigna). Esto se aplica aunque el usuario no haya tildado
// "siempre aplicar mejoras": sin ello el modo agente no funciona.
bool requiredForAgent(const QList<Change> &changes);

// Para QML: [{flag, current, recommended, reason}].
QVariantList toVariantList(const QList<Change> &changes);

// Perfil de lanzamiento candidato para conversar con Charla. AppController lo
// arma a partir de los perfiles del menú; la elección es pura para testearla.
struct ModelCandidate {
    QString id;
    QString name;
    bool    charlaTuned = false;    // perfil pensado para Charla (sys-charla-*)
    bool    ready = false;          // binario + modelo presentes: arranca ya
    bool    active = false;         // es el perfil activo
    double  minVramGb = 0.0;        // piso declarado del bundle (0 = desconocido)
    bool    placementKnown = false; // el plan de GPU de voz pudo estimar el modelo
    bool    placementSafe = false;  // y entra junto a la voz
};

struct ModelPick {
    QString id;            // "" = no hay candidato que entre en este equipo
    QString name;
    QString reason;
    bool    ready = false;
    bool    active = false;
    // Perfil pensado para Charla que también entra pero todavía no está
    // instalado (sólo cuando la elección principal no es uno de esos).
    QString upgradeId;
    QString upgradeName;
};

// Elige el perfil para Charla: descarta lo que no entra (plan de GPU de voz si
// se conoce; si no, minVramGb contra la VRAM total) y prefiere, en orden, lo
// que ya arranca, lo pensado para Charla, el modelo más grande y el activo.
// vramGb <= 0 = desconocida: no descarta por piso de VRAM.
ModelPick pickModel(const QList<ModelCandidate> &candidates, double vramGb);
QVariantMap toVariantMap(const ModelPick &pick);

} // namespace CharlaTuning
