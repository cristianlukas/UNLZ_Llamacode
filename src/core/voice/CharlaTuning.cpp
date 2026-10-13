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
    const QString ctx = argValue(args, QStringLiteral("--ctx-size"));
    if (!ctx.isEmpty() && ctx.toInt() > 65536)
        out.append({QStringLiteral("--ctx-size"), ctx, QStringLiteral("32768"),
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
    const bool ctxAlreadyRecommended = ctxNow > 65536;   // arriba ya se bajó a 32k
    if (!ctxAlreadyRecommended && ctxNow > 0 && ctxNow < minCtx)
        out.append({QStringLiteral("--ctx-size"), ctx, QString::number(minCtx),
                    QStringLiteral("el agente de voz no entra en %1 tokens (compacta y pierde la consigna)")
                        .arg(ctxNow)});

    // ── Slots paralelos explícitos ── Con --parallel N y KV NO unificado cada
    // slot recibe ctx/N. (Sin --parallel, llama.cpp usa auto + kv unificado: los
    // slots comparten el pool y no achican el contexto de una conversación.)
    QString parallel = argValue(args, QStringLiteral("--parallel"));
    if (parallel.isEmpty()) parallel = argValue(args, QStringLiteral("-np"));
    const bool unified = args.contains(QStringLiteral("--kv-unified")) || args.contains(QStringLiteral("-kvu"));
    const int slotCount = parallel.toInt();
    const int effectiveCtx = ctxAlreadyRecommended ? 32768 : qMax(ctxNow, minCtx);
    if (!parallel.isEmpty() && slotCount > 1 && !unified && effectiveCtx / slotCount < minCtx)
        out.append({QStringLiteral("--parallel"), parallel, QStringLiteral("1"),
                    QStringLiteral("cada slot recibe %1 tokens; Charla es de un solo usuario")
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

} // namespace CharlaTuning
