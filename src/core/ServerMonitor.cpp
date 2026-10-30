#include "ServerMonitor.h"

#include <QDateTime>
#include <QJsonObject>
#include <QRegularExpression>
#include <QStringList>
#include <QtMath>

namespace {
int firstDecoded(const QJsonObject &slot)
{
    const QJsonArray next = slot.value(QStringLiteral("next_token")).toArray();
    return next.isEmpty() ? 0 : next.at(0).toObject().value(QStringLiteral("n_decoded")).toInt();
}

double numberOr(const QString &s, double fallback)
{
    bool ok = false;
    const double v = s.trimmed().toDouble(&ok);
    return ok ? v : fallback;
}

QString fmt1(double v)
{
    return QString::number(v, 'f', 1);
}
} // namespace

void ServerMonitor::reset()
{
    *this = ServerMonitor{};
}

void ServerMonitor::push(QVector<double> &series, double v)
{
    series.append(v);
    if (series.size() > kHistory)
        series.remove(0, series.size() - kHistory);
}

void ServerMonitor::finalize(int slotId, const SlotTrack &t, qint64 endMs)
{
    // La tarea terminó en algún momento entre el último poll que la vio
    // corriendo y éste: el punto medio es la mejor estimación del fin.
    const qint64 end = t.seenRunning ? (t.lastMs + endMs) / 2 : endMs;
    double decodeTps = -1;
    if (t.decodeStartMs >= 0 && end > t.decodeStartMs && t.decoded > t.decodeStartTokens)
        decodeTps = (t.decoded - t.decodeStartTokens) * 1000.0 / double(end - t.decodeStartMs);
    QVariantMap r;
    r[QStringLiteral("at")] = QDateTime::currentMSecsSinceEpoch();
    r[QStringLiteral("slot")] = slotId;
    r[QStringLiteral("task")] = t.taskId;
    r[QStringLiteral("prompt")] = t.prompt;
    r[QStringLiteral("reused")] = t.cached;
    r[QStringLiteral("prefill")] = t.processed;
    r[QStringLiteral("output")] = t.decoded;
    r[QStringLiteral("decodeTps")] = decodeTps;
    r[QStringLiteral("tookMs")] = t.seenRunning ? double(end - t.firstMs) : -1.0;
    r[QStringLiteral("contextPct")] = t.nCtx > 0 ? (t.prompt + t.decoded) * 100.0 / t.nCtx : 0.0;
    m_requests.append(r);
    if (m_requests.size() > kMaxRequests)
        m_requests.remove(0, m_requests.size() - kMaxRequests);
    ++m_served;
}

void ServerMonitor::ingestSlots(const QJsonArray &slotList, qint64 nowMs)
{
    // El primer poll ve las tareas que ya terminaron antes de abrir el monitor
    // (llama-server conserva la anterior de cada slot): son línea base, no
    // requests nuevos.
    const bool baseline = !m_primed;
    double decode = 0, prefill = 0;
    bool reading = false, writing = false;
    int processing = 0;
    int ctxSlot = -1;
    qint64 ctxLast = -1;
    bool ctxActive = false;
    bool spec = false;

    for (const QJsonValue &v : slotList) {
        const QJsonObject o = v.toObject();
        const int id = o.value(QStringLiteral("id")).toInt();
        const bool isProc = o.value(QStringLiteral("is_processing")).toBool();
        spec = spec || o.value(QStringLiteral("speculative")).toBool();
        SlotTrack &t = m_slots[id];
        t.nCtx = o.value(QStringLiteral("n_ctx")).toInt(t.nCtx);
        if (!o.contains(QStringLiteral("id_task")))
            continue; // slot sin usar todavía

        const int taskId = o.value(QStringLiteral("id_task")).toInt();
        const int prompt = o.value(QStringLiteral("n_prompt_tokens")).toInt();
        const int processed = o.value(QStringLiteral("n_prompt_tokens_processed")).toInt();
        const int cached = o.value(QStringLiteral("n_prompt_tokens_cache")).toInt();
        const int decoded = firstDecoded(o);

        if (t.taskId != taskId) {
            // La tarea anterior terminó y otra tomó el slot entre dos polls.
            if (t.taskId >= 0 && t.processing && !baseline)
                finalize(id, t, nowMs);
            SlotTrack n;
            n.nCtx = t.nCtx;
            n.taskId = taskId;
            n.firstMs = nowMs;
            n.lastMs = nowMs;
            n.prompt = prompt; n.cached = cached; n.processed = processed; n.decoded = decoded;
            n.seenRunning = isProc;
            n.processing = isProc;
            if (isProc && decoded > 0) { n.decodeStartMs = nowMs; n.decodeStartTokens = decoded; }
            // Empezó y terminó entre dos polls: se cuenta, sin tiempos.
            if (!isProc && !baseline)
                finalize(id, n, nowMs);
            t = n;
        } else {
            const qint64 dt = nowMs - t.lastMs;
            if (t.processing && dt > 0) {
                if (decoded > t.decoded) decode += (decoded - t.decoded) * 1000.0 / dt;
                if (processed > t.processed) prefill += (processed - t.processed) * 1000.0 / dt;
            }
            const bool ended = t.processing && !isProc;
            t.prompt = prompt; t.cached = cached; t.processed = processed;
            if (isProc && decoded > 0 && t.decodeStartMs < 0) {
                t.decodeStartMs = nowMs;
                t.decodeStartTokens = decoded;
            }
            t.decoded = decoded;
            if (ended && !baseline)
                finalize(id, t, nowMs);
            if (isProc) t.seenRunning = true;
            t.processing = isProc;
            t.lastMs = nowMs;
        }

        if (isProc) {
            ++processing;
            (decoded > 0 ? writing : reading) = true;
        }
        // Contexto a mostrar: el slot que trabaja ahora, si no el último usado.
        if ((isProc && !ctxActive) || (!ctxActive && t.lastMs >= ctxLast)) {
            ctxSlot = id;
            ctxLast = t.lastMs;
            ctxActive = isProc;
        }
    }

    m_primed = true;
    m_speculative = spec;
    m_state = writing ? QStringLiteral("writing")
            : reading ? QStringLiteral("reading") : QStringLiteral("idle");
    m_processing = processing;
    m_decodeTps = decode;
    m_prefillTps = prefill;
    if (decode > m_peakDecode) {
        m_peakDecode = decode;
        m_peakDecodeAt = QDateTime::currentMSecsSinceEpoch();
    }
    push(m_history[QStringLiteral("decode")], decode);
    push(m_history[QStringLiteral("prefill")], prefill);

    m_context.clear();
    if (ctxSlot >= 0) {
        const SlotTrack &t = m_slots.value(ctxSlot);
        const int used = t.prompt + t.decoded;
        m_context[QStringLiteral("slot")] = ctxSlot;
        m_context[QStringLiteral("active")] = ctxActive;
        m_context[QStringLiteral("nCtx")] = t.nCtx;
        m_context[QStringLiteral("prompt")] = t.prompt;
        m_context[QStringLiteral("written")] = t.decoded;
        m_context[QStringLiteral("cached")] = t.cached;
        m_context[QStringLiteral("used")] = used;
        m_context[QStringLiteral("pct")] = t.nCtx > 0 ? used * 100.0 / t.nCtx : 0.0;
    }
    m_lastIngestMs = nowMs;
}

QHash<QString, double> ServerMonitor::parsePrometheus(const QString &text)
{
    QHash<QString, double> out;
    const QStringList lines = text.split(QLatin1Char('\n'), Qt::SkipEmptyParts);
    for (const QString &raw : lines) {
        const QString line = raw.trimmed();
        if (line.startsWith(QLatin1Char('#'))) continue;
        const int sp = line.lastIndexOf(QLatin1Char(' '));
        if (sp <= 0) continue;
        QString name = line.left(sp).trimmed();
        if (name.contains(QLatin1Char('{'))) continue; // series con labels: no se usan
        if (name.startsWith(QLatin1String("llamacpp:"))) name = name.mid(9);
        bool ok = false;
        const double v = line.mid(sp + 1).toDouble(&ok);
        if (ok) out.insert(name, v);
    }
    return out;
}

void ServerMonitor::ingestMetrics(const QString &prometheus)
{
    const auto m = parsePrometheus(prometheus);
    m_deferred = m.value(QStringLiteral("requests_deferred"), -1);
}

QVariantMap ServerMonitor::parseBufferLine(const QString &line)
{
    static const QRegularExpression re(
        QStringLiteral("(?:^|[\\s:])([A-Za-z][A-Za-z0-9_]*)\\s+(model|KV|RS|compute|output)\\s+buffer size\\s*=\\s*([0-9.]+)\\s*MiB"));
    const auto m = re.match(line);
    if (!m.hasMatch()) return {};
    QString kind = m.captured(2);
    if (kind == QLatin1String("KV") || kind == QLatin1String("RS")) kind = QStringLiteral("kv");
    return {{QStringLiteral("device"), m.captured(1)},
            {QStringLiteral("kind"), kind},
            {QStringLiteral("mib"), m.captured(3).toDouble()}};
}

int ServerMonitor::gpuIndexForDevice(const QString &device)
{
    static const QRegularExpression re(QStringLiteral("^(?:CUDA|ROCm|Vulkan|SYCL|MUSA|CANN)(\\d+)$"));
    const auto m = re.match(device);
    if (m.hasMatch()) return m.captured(1).toInt();
    return device == QLatin1String("Metal") ? 0 : -1;
}

void ServerMonitor::ingestServerLog(const QString &text)
{
    m_logTail += text;
    const int lastNl = m_logTail.lastIndexOf(QLatin1Char('\n'));
    if (lastNl < 0) {
        if (m_logTail.size() > 4096) m_logTail.clear();
        return;
    }
    const QString complete = m_logTail.left(lastNl);
    m_logTail = m_logTail.mid(lastNl + 1);
    for (const QString &line : complete.split(QLatin1Char('\n'))) {
        if (!line.contains(QLatin1String("buffer size"))) continue;
        const QVariantMap b = parseBufferLine(line);
        if (b.isEmpty()) continue;
        QVariantMap &dev = m_buffers[b.value(QStringLiteral("device")).toString()];
        const QString kind = b.value(QStringLiteral("kind")).toString();
        dev[kind] = dev.value(kind).toDouble() + b.value(QStringLiteral("mib")).toDouble();
    }
}

void ServerMonitor::ingestHardware(const QVariantMap &sample)
{
    for (auto it = sample.constBegin(); it != sample.constEnd(); ++it) {
        const double v = it.value().toDouble();
        if (v >= 0) push(m_history[it.key()], v);
    }
}

QVariantMap ServerMonitor::snapshot() const
{
    QVariantMap s;
    s[QStringLiteral("available")] = m_primed;
    s[QStringLiteral("state")] = m_state;
    s[QStringLiteral("decodeTps")] = m_decodeTps;
    s[QStringLiteral("prefillTps")] = m_prefillTps;
    s[QStringLiteral("peakDecodeTps")] = m_peakDecode;
    s[QStringLiteral("peakDecodeAt")] = m_peakDecodeAt;
    s[QStringLiteral("msPerToken")] = m_decodeTps > 0 ? 1000.0 / m_decodeTps : -1.0;
    s[QStringLiteral("requestsServed")] = m_served;
    s[QStringLiteral("processing")] = m_processing;
    s[QStringLiteral("deferred")] = m_deferred;
    s[QStringLiteral("speculative")] = m_speculative;
    s[QStringLiteral("slots")] = int(m_slots.size());
    s[QStringLiteral("context")] = m_context;

    // Reutilización de caché sobre los requests vistos: cuánto prompt no hubo
    // que volver a leer.
    double prompt = 0, reused = 0;
    for (const QVariantMap &r : m_requests) {
        prompt += r.value(QStringLiteral("prompt")).toDouble();
        reused += r.value(QStringLiteral("reused")).toDouble();
    }
    s[QStringLiteral("cacheReusePct")] = prompt > 0 ? reused * 100.0 / prompt : -1.0;

    QVariantMap buffers;
    for (auto it = m_buffers.constBegin(); it != m_buffers.constEnd(); ++it)
        buffers.insert(it.key(), it.value());
    s[QStringLiteral("buffers")] = buffers;

    QVariantMap history;
    for (auto it = m_history.constBegin(); it != m_history.constEnd(); ++it) {
        QVariantList l;
        l.reserve(it.value().size());
        for (double v : it.value()) l.append(v);
        history.insert(it.key(), l);
    }
    s[QStringLiteral("history")] = history;
    return s;
}

QVariantList ServerMonitor::recentRequests(int limit) const
{
    QVariantList out;
    for (int i = m_requests.size() - 1; i >= 0 && out.size() < limit; --i)
        out.append(m_requests.at(i));
    return out;
}

QVariantMap ServerMonitor::parseNvidiaSmiGpus(const QString &csv)
{
    QVariantList gpus;
    double sumTotal = 0, sumUsed = 0, sumFree = 0, sumDraw = 0, sumLimit = 0, sumUtil = 0;
    double maxTemp = -1;
    int utilCount = 0;
    const QStringList lines = csv.split(QLatin1Char('\n'), Qt::SkipEmptyParts);
    for (const QString &line : lines) {
        const QStringList p = line.split(QLatin1Char(','));
        if (p.size() < 5) continue;
        bool iOk = false, tOk = false, uOk = false, fOk = false;
        const int idx = p.at(0).trimmed().toInt(&iOk);
        const double totalMb = p.at(2).trimmed().toDouble(&tOk);
        const double usedMb = p.at(3).trimmed().toDouble(&uOk);
        const double freeMb = p.at(4).trimmed().toDouble(&fOk);
        if (!iOk || !tOk || !uOk || !fOk) continue;
        // Los campos de telemetría pueden venir "[N/A]" (GPUs sin sensores, WDDM).
        const double drawW = p.size() > 5 ? numberOr(p.at(5), 0.0) : 0.0;
        const double limitW = p.size() > 6 ? numberOr(p.at(6), 0.0) : 0.0;
        const double util = p.size() > 8 ? numberOr(p.at(8), -1.0) : -1.0;
        const double temp = p.size() > 9 ? numberOr(p.at(9), -1.0) : -1.0;
        QVariantMap g;
        g[QStringLiteral("index")] = idx;
        g[QStringLiteral("name")] = p.at(1).trimmed();
        g[QStringLiteral("totalMb")] = totalMb;
        g[QStringLiteral("usedMb")] = usedMb;
        g[QStringLiteral("freeMb")] = qMax(0.0, freeMb);
        g[QStringLiteral("pct")] = totalMb > 0 ? (usedMb / totalMb * 100.0) : 0.0;
        g[QStringLiteral("drawW")] = drawW;
        g[QStringLiteral("limitW")] = limitW;
        g[QStringLiteral("powerPct")] = limitW > 0 ? (drawW / limitW * 100.0) : 0.0;
        g[QStringLiteral("uuid")] = p.size() > 7 ? p.at(7).trimmed() : QString();
        g[QStringLiteral("util")] = util;
        g[QStringLiteral("tempC")] = temp;
        g[QStringLiteral("pcieGen")] = p.size() > 10 ? numberOr(p.at(10), -1.0) : -1.0;
        g[QStringLiteral("pcieWidth")] = p.size() > 11 ? numberOr(p.at(11), -1.0) : -1.0;
        gpus.append(g);
        sumTotal += totalMb;
        sumUsed += usedMb;
        sumFree += qMax(0.0, freeMb);
        sumDraw += drawW;
        sumLimit += limitW;
        if (util >= 0) { sumUtil += util; ++utilCount; }
        maxTemp = qMax(maxTemp, temp);
    }
    QVariantMap stats;
    stats[QStringLiteral("gpus")] = gpus;
    stats[QStringLiteral("totalMb")] = sumTotal;
    stats[QStringLiteral("usedMb")] = sumUsed;
    stats[QStringLiteral("freeMb")] = sumFree;
    stats[QStringLiteral("pct")] = sumTotal > 0 ? (sumUsed / sumTotal * 100.0) : 0.0;
    stats[QStringLiteral("drawW")] = sumDraw;
    stats[QStringLiteral("limitW")] = sumLimit;
    stats[QStringLiteral("powerPct")] = sumLimit > 0 ? (sumDraw / sumLimit * 100.0) : 0.0;
    stats[QStringLiteral("utilPct")] = utilCount > 0 ? sumUtil / utilCount : -1.0;
    stats[QStringLiteral("maxTempC")] = maxTemp;
    return stats;
}

QHash<QString, QHash<qint64, double>> ServerMonitor::parseComputeApps(const QString &csv)
{
    QHash<QString, QHash<qint64, double>> out;
    for (const QString &line : csv.split(QLatin1Char('\n'), Qt::SkipEmptyParts)) {
        const QStringList p = line.split(QLatin1Char(','));
        if (p.size() < 3) continue;
        bool pidOk = false, memOk = false;
        const qint64 pid = p.at(0).trimmed().toLongLong(&pidOk);
        const double mib = p.at(2).trimmed().toDouble(&memOk);
        if (!pidOk || !memOk) continue; // "[N/A]" en Windows/WDDM
        out[p.at(1).trimmed()][pid] += mib;
    }
    return out;
}

QVariantList ServerMonitor::gpuBreakdown(const QVariantMap &gpuStats, const QVariantMap &buffers,
                                         const QHash<QString, QHash<qint64, double>> &apps,
                                         qint64 serverPid)
{
    QVariantList out;
    for (const QVariant &gv : gpuStats.value(QStringLiteral("gpus")).toList()) {
        QVariantMap g = gv.toMap();
        const int idx = g.value(QStringLiteral("index")).toInt();
        double weights = 0, kv = 0, compute = 0;
        for (auto it = buffers.constBegin(); it != buffers.constEnd(); ++it) {
            if (gpuIndexForDevice(it.key()) != idx) continue;
            const QVariantMap b = it.value().toMap();
            weights += b.value(QStringLiteral("model")).toDouble();
            kv += b.value(QStringLiteral("kv")).toDouble();
            compute += b.value(QStringLiteral("compute")).toDouble()
                     + b.value(QStringLiteral("output")).toDouble();
        }
        const double used = g.value(QStringLiteral("usedMb")).toDouble();
        const double known = weights + kv + compute;
        const auto procs = apps.value(g.value(QStringLiteral("uuid")).toString());
        double others = 0;
        bool othersKnown = false;
        if (!procs.isEmpty()) {
            othersKnown = true;
            for (auto it = procs.constBegin(); it != procs.constEnd(); ++it)
                if (it.key() != serverPid) others += it.value();
        }
        // "Resto": contexto CUDA, pools, memoria reservada por el driver y lo
        // que el log no reporta. Se calcula como lo que sobra del usado.
        const double rest = qMax(0.0, used - known - others);
        g[QStringLiteral("weightsMb")] = weights;
        g[QStringLiteral("kvMb")] = kv;
        g[QStringLiteral("computeMb")] = compute;
        g[QStringLiteral("restMb")] = rest;
        g[QStringLiteral("othersMb")] = others;
        g[QStringLiteral("othersKnown")] = othersKnown;
        out.append(g);
    }
    return out;
}

QPair<quint64, quint64> ServerMonitor::parseProcStatCpu(const QString &text)
{
    for (const QString &line : text.split(QLatin1Char('\n'))) {
        if (!line.startsWith(QLatin1String("cpu "))) continue;
        const QStringList p = line.split(QLatin1Char(' '), Qt::SkipEmptyParts);
        quint64 total = 0;
        for (int i = 1; i < p.size(); ++i) total += p.at(i).toULongLong();
        // idle + iowait
        const quint64 idle = (p.size() > 4 ? p.at(4).toULongLong() : 0)
                           + (p.size() > 5 ? p.at(5).toULongLong() : 0);
        return {total, idle};
    }
    return {0, 0};
}

QVariantMap ServerMonitor::parseMeminfo(const QString &text)
{
    double total = -1, avail = -1;
    for (const QString &line : text.split(QLatin1Char('\n'))) {
        const QStringList p = line.split(QLatin1Char(' '), Qt::SkipEmptyParts);
        if (p.size() < 2) continue;
        if (p.at(0) == QLatin1String("MemTotal:")) total = p.at(1).toDouble() / 1024.0;
        else if (p.at(0) == QLatin1String("MemAvailable:")) avail = p.at(1).toDouble() / 1024.0;
    }
    return {{QStringLiteral("totalMb"), total}, {QStringLiteral("availableMb"), avail}};
}

QPair<quint64, quint64> ServerMonitor::parseDiskstats(const QString &text)
{
    static const QRegularExpression partition(
        QStringLiteral("^(?:(?:sd|hd|vd|xvd)[a-z]+\\d+|nvme\\d+n\\d+p\\d+|mmcblk\\d+p\\d+)$"));
    static const QRegularExpression virtualDev(QStringLiteral("^(?:loop|ram|zram|dm-|sr|fd)"));
    quint64 read = 0, write = 0;
    for (const QString &line : text.split(QLatin1Char('\n'))) {
        const QStringList p = line.split(QLatin1Char(' '), Qt::SkipEmptyParts);
        if (p.size() < 10) continue;
        const QString name = p.at(2);
        if (partition.match(name).hasMatch() || virtualDev.match(name).hasMatch()) continue;
        read += p.at(5).toULongLong();
        write += p.at(9).toULongLong();
    }
    return {read, write};
}

QString ServerMonitor::report(const QVariantMap &snapshot, const QVariantMap &serverStats,
                              const QVariantMap &system, const QVariantList &requests,
                              const QString &model)
{
    QStringList out;
    out << QStringLiteral("LlamaCode · Monitor · %1")
               .arg(QDateTime::currentDateTime().toString(Qt::ISODate));
    if (!model.isEmpty()) out << QStringLiteral("Modelo: %1").arg(model);
    out << QStringLiteral("Estado: %1").arg(snapshot.value(QStringLiteral("state")).toString());
    out << QStringLiteral("Decode: %1 tok/s · Prefill: %2 tok/s · Pico decode: %3 tok/s")
               .arg(fmt1(snapshot.value(QStringLiteral("decodeTps")).toDouble()),
                    fmt1(snapshot.value(QStringLiteral("prefillTps")).toDouble()),
                    fmt1(snapshot.value(QStringLiteral("peakDecodeTps")).toDouble()));
    out << QStringLiteral("Requests vistos: %1 · Especulación: %2")
               .arg(snapshot.value(QStringLiteral("requestsServed")).toInt())
               .arg(snapshot.value(QStringLiteral("speculative")).toBool()
                        ? QStringLiteral("sí") : QStringLiteral("no"));
    const QVariantMap ctx = snapshot.value(QStringLiteral("context")).toMap();
    if (!ctx.isEmpty())
        out << QStringLiteral("Contexto: %1 / %2 tokens (%3%)")
                   .arg(ctx.value(QStringLiteral("used")).toInt())
                   .arg(ctx.value(QStringLiteral("nCtx")).toInt())
                   .arg(fmt1(ctx.value(QStringLiteral("pct")).toDouble()));
    for (const QVariant &gv : serverStats.value(QStringLiteral("gpus")).toList()) {
        const QVariantMap g = gv.toMap();
        out << QStringLiteral("GPU %1 %2: %3/%4 GB · %5% carga · %6 W · %7 °C")
                   .arg(g.value(QStringLiteral("index")).toInt())
                   .arg(g.value(QStringLiteral("name")).toString(),
                        fmt1(g.value(QStringLiteral("usedMb")).toDouble() / 1024.0),
                        fmt1(g.value(QStringLiteral("totalMb")).toDouble() / 1024.0))
                   .arg(qRound(g.value(QStringLiteral("util")).toDouble()))
                   .arg(qRound(g.value(QStringLiteral("drawW")).toDouble()))
                   .arg(qRound(g.value(QStringLiteral("tempC")).toDouble()));
    }
    if (system.value(QStringLiteral("cpuPct")).toDouble() >= 0)
        out << QStringLiteral("CPU: %1% · RAM: %2/%3 GB")
                   .arg(qRound(system.value(QStringLiteral("cpuPct")).toDouble()))
                   .arg(fmt1(system.value(QStringLiteral("ramUsedGb")).toDouble()),
                        fmt1(system.value(QStringLiteral("ramTotalGb")).toDouble()));
    if (!requests.isEmpty()) {
        out << QString() << QStringLiteral("Requests recientes (prompt / reusado / prefill / salida / decode tok/s / duración):");
        for (const QVariant &rv : requests) {
            const QVariantMap r = rv.toMap();
            const double tps = r.value(QStringLiteral("decodeTps")).toDouble();
            const double took = r.value(QStringLiteral("tookMs")).toDouble();
            out << QStringLiteral("  %1  %2 / %3 / %4 / %5 / %6 / %7")
                       .arg(QDateTime::fromMSecsSinceEpoch(r.value(QStringLiteral("at")).toLongLong())
                                .toString(QStringLiteral("HH:mm:ss")))
                       .arg(r.value(QStringLiteral("prompt")).toInt())
                       .arg(r.value(QStringLiteral("reused")).toInt())
                       .arg(r.value(QStringLiteral("prefill")).toInt())
                       .arg(r.value(QStringLiteral("output")).toInt())
                       .arg(tps >= 0 ? fmt1(tps) : QStringLiteral("—"),
                            took >= 0 ? fmt1(took / 1000.0) + QStringLiteral(" s") : QStringLiteral("—"));
        }
    }
    return out.join(QLatin1Char('\n'));
}
