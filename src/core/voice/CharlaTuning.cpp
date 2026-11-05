#include "CharlaTuning.h"
#include <QVariantMap>

namespace CharlaTuning {

QString argValue(const QStringList &args, const QString &flag)
{
    const int i = args.indexOf(flag);
    return (i >= 0 && i + 1 < args.size()) ? args.at(i + 1) : QString();
}

QList<Change> recommend(const QStringList &args, double vramGb)
{
    QList<Change> out;

    // ── Prefill: batches ── El default de llama.cpp ya es 2048/512; solo actuar
    // si el perfil los BAJÓ explícitamente. Subirlos cuesta VRAM de compute
    // buffers, así que se escala por VRAM disponible.
    int ubatchRec = 0, batchRec = 0;
    if (vramGb >= 8.0)      { ubatchRec = 512; batchRec = 2048; }
    else if (vramGb >= 4.0) { ubatchRec = 256; batchRec = 1024; }
    const QString ubatch = argValue(args, QStringLiteral("--ubatch-size"));
    if (ubatchRec > 0 && !ubatch.isEmpty() && ubatch.toInt() < ubatchRec)
        out.append({QStringLiteral("--ubatch-size"), ubatch, QString::number(ubatchRec),
                    QStringLiteral("prefill %1x más rápido (procesa el prompt en bloques más grandes)")
                        .arg(qMax(2, ubatchRec / qMax(1, ubatch.toInt())))});
    const QString batch = argValue(args, QStringLiteral("--batch-size"));
    if (batchRec > 0 && !batch.isEmpty() && batch.toInt() < batchRec)
        out.append({QStringLiteral("--batch-size"), batch, QString::number(batchRec),
                    QStringLiteral("acompaña al ubatch en prompts largos")});

    // ── Contexto ── Charla no necesita 262k: el KV gigante come VRAM y hace
    // checkpoints/gestión de cache pesados. 32k sobra para una conversación
    // hablada (el historial del agente además se poda de imágenes viejas).
    // Con --parallel N (sin KV unificado) el tope es por slot: Charla multitarea
    // usa los slots extra para agentes en segundo plano, cada uno con 32k.
    QString parallel = argValue(args, QStringLiteral("--parallel"));
    if (parallel.isEmpty()) parallel = argValue(args, QStringLiteral("-np"));
    const bool unified = args.contains(QStringLiteral("--kv-unified")) || args.contains(QStringLiteral("-kvu"));
    const int slotCount = parallel.toInt();
    const int ctxSlots = (slotCount > 1 && !unified) ? slotCount : 1;
    const QString ctx = argValue(args, QStringLiteral("--ctx-size"));
    if (!ctx.isEmpty() && ctx.toInt() / ctxSlots > 65536)
        out.append({QStringLiteral("--ctx-size"), ctx, QString::number(32768 * ctxSlots),
                    QStringLiteral("KV cache liviano; la charla no usa contexto gigante")});

    // ── Reuso de prefijo ── Sin esto, un cambio a mitad del historial re-procesa
    // todo lo que sigue; con reuse el server salva los bloques comunes.
    const QString reuse = argValue(args, QStringLiteral("--cache-reuse"));
    if (reuse.isEmpty())
        out.append({QStringLiteral("--cache-reuse"), QString(), QStringLiteral("512"),
                    QStringLiteral("reusa bloques del prompt ya procesados entre turnos")});

    // ── Tope de generación ── Respuestas habladas son cortas; un --predict alto
    // (o infinito) deja al modelo divagar minutos si se va por las ramas.
    const QString predict = argValue(args, QStringLiteral("--predict"));
    if (predict.isEmpty() || predict.toInt() > 2048 || predict.toInt() < 0)
        out.append({QStringLiteral("--predict"), predict, QStringLiteral("1024"),
                    QStringLiteral("acota la respuesta (voz = respuestas cortas)")});

    // ── Contexto mínimo para el agente de voz ── El modo JARVIS manda system +
    // tools de PC (~2-3k tokens en protocolo textual, ~13k nativo) más historial
    // y lecturas de pantalla. Con 4096 (default de muchos perfiles) el agente
    // compacta en cada turno y un 9B pierde la consigna (medido: respondía a un
    // saludo viejo en vez de la tarea). llama.cpp ajusta a la VRAM con -fit.
    const int minCtx = vramGb >= 8.0 ? 16384 : 8192;
    const int ctxNow = ctx.toInt();
    const bool ctxAlreadyRecommended = ctxNow / ctxSlots > 65536;   // arriba ya se bajó a 32k por slot
    if (!ctxAlreadyRecommended && ctxNow > 0 && ctxNow < minCtx)
        out.append({QStringLiteral("--ctx-size"), ctx, QString::number(minCtx),
                    QStringLiteral("el agente de voz no entra en %1 tokens (compacta y pierde la consigna)")
                        .arg(ctxNow)});

    // ── Slots paralelos explícitos ── Con --parallel N y KV NO unificado cada
    // slot recibe ctx/N. (Sin --parallel, llama.cpp usa auto + kv unificado: los
    // slots comparten el pool y no achican el contexto de una conversación.)
    const int effectiveCtx = ctxAlreadyRecommended ? 32768 * ctxSlots : qMax(ctxNow, minCtx);
    if (!parallel.isEmpty() && slotCount > 1 && !unified && effectiveCtx / slotCount < minCtx)
        out.append({QStringLiteral("--parallel"), parallel, QStringLiteral("1"),
                    QStringLiteral("cada slot recibe %1 tokens: no entra el agente de voz")
                        .arg(effectiveCtx / slotCount)});

    return out;
}

QStringList apply(QStringList args, const QList<Change> &changes)
{
    for (const Change &c : changes) {
        // `-np` es el alias corto de --parallel: dejar ambos sería ambiguo.
        if (c.flag == QLatin1String("--parallel")) {
            int j;
            while ((j = args.indexOf(QStringLiteral("-np"))) >= 0)
                args.remove(j, qMin(2, int(args.size() - j)));
        }
        const int i = args.indexOf(c.flag);
        if (i >= 0 && i + 1 < args.size()) args[i + 1] = c.recommended;
        else args << c.flag << c.recommended;
    }
    return args;
}

bool requiredForAgent(const QList<Change> &changes)
{
    for (const Change &c : changes)
        if (c.flag == QLatin1String("--ctx-size") && c.current.toInt() > 0
            && c.current.toInt() < c.recommended.toInt())
            return true;
    return false;
}

QVariantList toVariantList(const QList<Change> &changes)
{
    QVariantList out;
    for (const Change &c : changes)
        out.append(QVariantMap{{QStringLiteral("flag"), c.flag},
                               {QStringLiteral("current"), c.current},
                               {QStringLiteral("recommended"), c.recommended},
                               {QStringLiteral("reason"), c.reason}});
    return out;
}

namespace {
bool fits(const ModelCandidate &c, double vramGb)
{
    if (c.placementKnown) return c.placementSafe;
    return vramGb <= 0.0 || c.minVramGb <= vramGb + 0.01;
}

// a antes que b en la recomendación.
bool better(const ModelCandidate &a, const ModelCandidate &b)
{
    if (a.ready != b.ready) return a.ready;
    if (a.charlaTuned != b.charlaTuned) return a.charlaTuned;
    if (!qFuzzyCompare(a.minVramGb + 1.0, b.minVramGb + 1.0)) return a.minVramGb > b.minVramGb;
    return a.active && !b.active;
}
} // namespace

ModelPick pickModel(const QList<ModelCandidate> &candidates, double vramGb)
{
    const ModelCandidate *best = nullptr;
    const ModelCandidate *upgrade = nullptr;
    for (const ModelCandidate &c : candidates) {
        if (c.id.isEmpty() || !fits(c, vramGb)) continue;
        if (!best || better(c, *best)) best = &c;
        if (c.charlaTuned && !c.ready && (!upgrade || better(c, *upgrade))) upgrade = &c;
    }
    ModelPick pick;
    if (!best) {
        pick.reason = QStringLiteral(
            "Ningún perfil entra en la VRAM de este equipo junto a la voz. "
            "Descargá un modelo más chico desde Modelos.");
        return pick;
    }
    pick.id = best->id;
    pick.name = best->name;
    pick.ready = best->ready;
    pick.active = best->active;
    if (best->charlaTuned && best->ready)
        pick.reason = QStringLiteral("Perfil pensado para Charla (voz + PC + web) que entra en tu GPU.");
    else if (best->charlaTuned)
        pick.reason = QStringLiteral("Perfil pensado para Charla que entra en tu GPU; falta descargar el modelo.");
    else if (best->ready)
        pick.reason = QStringLiteral("El modelo instalado más grande que entra en tu GPU dejando lugar para la voz.");
    else
        pick.reason = QStringLiteral("No hay un modelo instalado que entre; este perfil entra pero hay que descargarlo.");
    if (upgrade && !best->charlaTuned) {
        pick.upgradeId = upgrade->id;
        pick.upgradeName = upgrade->name;
    }
    return pick;
}

QVariantMap toVariantMap(const ModelPick &pick)
{
    return {{QStringLiteral("id"), pick.id},
            {QStringLiteral("name"), pick.name},
            {QStringLiteral("reason"), pick.reason},
            {QStringLiteral("ready"), pick.ready},
            {QStringLiteral("active"), pick.active},
            {QStringLiteral("upgradeId"), pick.upgradeId},
            {QStringLiteral("upgradeName"), pick.upgradeName}};
}

} // namespace CharlaTuning
