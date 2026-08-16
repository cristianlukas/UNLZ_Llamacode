#include "HardwareDiagnostics.h"

#include <QCryptographicHash>
#include <QRegularExpression>
#include <QStringList>

namespace {

QString normalized(QString value)
{
    return value.trimmed().remove(QRegularExpression(QStringLiteral("\\s+"))).toLower();
}

double number(const QString &value)
{
    bool ok = false;
    const double result = value.trimmed().toDouble(&ok);
    return ok ? result : 0.0;
}

QStringList splitCsvLine(const QString &line)
{
    // nvidia-smi no escapa comas en los campos consultados actualmente. Se
    // conserva una función pequeña y explícita para no introducir un parser
    // CSV general en el camino crítico del diagnóstico.
    return line.split(QLatin1Char(','), Qt::KeepEmptyParts);
}

}  // namespace

QVariantList HardwareDiagnostics::parseNvidiaSmiCsv(const QString &csv)
{
    QVariantList out;
    const QStringList lines = csv.split(QRegularExpression(QStringLiteral("[\\r\\n]+")),
                                        Qt::SkipEmptyParts);
    // index,name,memory.total,memory.free,pci.bus_id,pci.link.gen.current,
    // pci.link.width.current,temperature.gpu,power.draw,power.limit
    for (const QString &raw : lines) {
        const QStringList fields = splitCsvLine(raw);
        if (fields.size() < 7)
            continue;
        bool indexOk = false;
        const int index = fields.at(0).trimmed().toInt(&indexOk);
        if (!indexOk)
            continue;
        QVariantMap gpu;
        gpu[QStringLiteral("index")] = index;
        gpu[QStringLiteral("name")] = fields.at(1).trimmed();
        gpu[QStringLiteral("totalMb")] = number(fields.at(2));
        gpu[QStringLiteral("freeMb")] = number(fields.at(3));
        gpu[QStringLiteral("busId")] = fields.at(4).trimmed();
        gpu[QStringLiteral("pcieGeneration")] = number(fields.at(5));
        gpu[QStringLiteral("pcieLanes")] = number(fields.at(6));
        if (fields.size() > 7) gpu[QStringLiteral("temperatureC")] = number(fields.at(7));
        if (fields.size() > 8) gpu[QStringLiteral("powerDrawW")] = number(fields.at(8));
        if (fields.size() > 9) gpu[QStringLiteral("powerLimitW")] = number(fields.at(9));
        out.append(gpu);
    }
    return out;
}

QVariantMap HardwareDiagnostics::parseTopologyMatrix(const QString &text)
{
    QVariantMap result;
    QVariantList links;
    bool p2p = false;
    const QStringList lines = text.split(QRegularExpression(QStringLiteral("[\\r\\n]+")),
                                         Qt::SkipEmptyParts);
    QStringList columns;
    for (const QString &raw : lines) {
        const QString line = raw.trimmed();
        if (line.startsWith(QStringLiteral("GPU")) && columns.isEmpty()) {
            columns = line.split(QRegularExpression(QStringLiteral("\\s+")), Qt::SkipEmptyParts);
            continue;
        }
        if (!line.startsWith(QStringLiteral("GPU")) || columns.size() < 2)
            continue;
        const QStringList fields = line.split(QRegularExpression(QStringLiteral("\\s+")),
                                              Qt::SkipEmptyParts);
        if (fields.size() < 2)
            continue;
        const QString source = fields.first();
        for (int i = 1; i < fields.size() && i < columns.size(); ++i) {
            const QString relation = fields.at(i).toUpper();
            if (relation == QLatin1String("X") || relation == QLatin1String("N/A"))
                continue;
            const bool direct = relation.startsWith(QStringLiteral("NV"))
                                || relation == QLatin1String("PIX")
                                || relation == QLatin1String("PXB");
            p2p = p2p || direct;
            links.append(QVariantMap{{QStringLiteral("from"), source},
                                     {QStringLiteral("to"), columns.at(i)},
                                     {QStringLiteral("relation"), relation},
                                     {QStringLiteral("direct"), direct}});
        }
    }
    result[QStringLiteral("links")] = links;
    result[QStringLiteral("p2pAvailable")] = p2p;
    return result;
}

bool HardwareDiagnostics::parseNvlinkActive(const QString &text)
{
    const QString lower = text.toLower();
    return lower.contains(QStringLiteral("active"))
           && !lower.contains(QStringLiteral("inactive"))
           && !lower.contains(QStringLiteral("disabled"));
}

QVariantMap HardwareDiagnostics::enrichTopology(const QVariantMap &hardware,
                                                const QString &topologyText,
                                                const QString &nvlinkText)
{
    QVariantMap result = hardware;
    const QVariantMap topology = parseTopologyMatrix(topologyText);
    const bool topologyP2p = topology.value(QStringLiteral("p2pAvailable")).toBool();
    const bool nvlink = parseNvlinkActive(nvlinkText);
    result[QStringLiteral("topology")] = topology.value(QStringLiteral("links"));
    result[QStringLiteral("p2pAvailable")] = topologyP2p || nvlink;
    result[QStringLiteral("nvlinkAvailable")] = nvlink;
    result[QStringLiteral("topologySource")] = !topologyText.trimmed().isEmpty()
        ? QStringLiteral("nvidia-smi topo -m") : QStringLiteral("unavailable");
    return result;
}

QString HardwareDiagnostics::hardwareFingerprint(const QVariantMap &hardware)
{
    QStringList parts;
    parts << hardware.value(QStringLiteral("cpuModel")).toString();
    QVariantList gpus = hardware.value(QStringLiteral("gpus")).toList();
    if (gpus.isEmpty() && hardware.value(QStringLiteral("gpuName")).toString().size())
        parts << hardware.value(QStringLiteral("gpuName")).toString();
    for (const QVariant &value : gpus) {
        const QVariantMap gpu = value.toMap();
        parts << QStringLiteral("%1/%2/%3/%4/%5")
                     .arg(gpu.value(QStringLiteral("name")).toString())
                     .arg(gpu.value(QStringLiteral("totalMb")).toInt())
                     .arg(gpu.value(QStringLiteral("pcieGeneration")).toDouble())
                     .arg(gpu.value(QStringLiteral("pcieLanes")).toDouble())
                     .arg(gpu.value(QStringLiteral("busId")).toString());
    }
    const QByteArray digest = QCryptographicHash::hash(
        normalized(parts.join(QLatin1Char('|'))).toUtf8(), QCryptographicHash::Sha256);
    return QStringLiteral("hw-%1").arg(QString::fromLatin1(digest.toHex().left(16)));
}

QString HardwareDiagnostics::recommendedSplitMode(const QVariantMap &hardware)
{
    const QVariantList gpus = hardware.value(QStringLiteral("gpus")).toList();
    if (gpus.size() < 2)
        return QStringLiteral("layer");
    double minBandwidth = 1e9;
    for (const QVariant &value : gpus) {
        const QVariantMap gpu = value.toMap();
        const double gen = gpu.value(QStringLiteral("pcieGeneration")).toDouble();
        const double lanes = gpu.value(QStringLiteral("pcieLanes")).toDouble();
        if (gen > 0.0 && lanes > 0.0)
            minBandwidth = qMin(minBandwidth, gen * lanes);
    }
    // Tensor/row/graph requieren transferencias frecuentes. Layer es el
    // fallback conservador cuando el enlace mínimo es desconocido o débil.
    if (!hardware.value(QStringLiteral("p2pAvailable")).toBool() || minBandwidth < 16.0)
        return QStringLiteral("layer");
    return QStringLiteral("tensor");
}

QVariantMap HardwareDiagnostics::performanceRecommendation(const QVariantMap &hardware,
                                                            const QString &target)
{
    const QString mode = recommendedSplitMode(hardware);
    const QVariantList gpus = hardware.value(QStringLiteral("gpus")).toList();
    const QString requested = target.trimmed().toLower();
    QVariantMap result;
    result[QStringLiteral("splitMode")] = mode;
    result[QStringLiteral("target")] = requested.isEmpty() ? QStringLiteral("balanced") : requested;
    result[QStringLiteral("confidence")] = gpus.size() >= 2 ? QStringLiteral("measured-topology")
                                                               : QStringLiteral("conservative-default");
    if (mode == QLatin1String("layer")) {
        result[QStringLiteral("reason")] = QStringLiteral(
            "Se recomienda layer porque el enlace PCIe mínimo entre las GPU es desconocido o débil; "
            "reduce las transferencias durante la generación.");
        result[QStringLiteral("alternatives")] = QVariantList{QStringLiteral("tensor")};
    } else {
        result[QStringLiteral("reason")] = QStringLiteral(
            "Las GPU tienen un enlace PCIe suficiente para probar tensor; validar pp/s y tg/s con benchmark.");
        result[QStringLiteral("alternatives")] = QVariantList{QStringLiteral("layer"), QStringLiteral("row")};
    }
    if (requested == QLatin1String("long-context")) {
        result[QStringLiteral("kvCache")] = QStringLiteral("q8_0");
        result[QStringLiteral("note")] = QStringLiteral("KV q8_0 prioriza capacidad de contexto con pérdida acotada.");
    } else if (requested == QLatin1String("quality")) {
        result[QStringLiteral("kvCache")] = QStringLiteral("f16");
        result[QStringLiteral("note")] = QStringLiteral("KV f16 prioriza fidelidad; confirmar que el contexto entra en VRAM.");
    } else {
        result[QStringLiteral("kvCache")] = QStringLiteral("q8_0");
        result[QStringLiteral("note")] = QStringLiteral("Perfil equilibrado; comparar contra KV f16 si sobra VRAM.");
    }
    result[QStringLiteral("hardwareFingerprint")] = hardwareFingerprint(hardware);
    return result;
}

double HardwareDiagnostics::performanceScore(const QVariantMap &sample, const QString &target)
{
    // La matriz acepta tanto muestras del benchmark técnico como artefactos de
    // benchmark de agente. Estos últimos usan avgTps y qualityScore/Total.
    const double pp = sample.contains(QStringLiteral("promptTps"))
        ? sample.value(QStringLiteral("promptTps")).toDouble()
        : sample.value(QStringLiteral("prefillTps")).toDouble();
    const double tg = sample.contains(QStringLiteral("generationTps"))
        ? sample.value(QStringLiteral("generationTps")).toDouble()
        : sample.value(QStringLiteral("avgTps")).toDouble();
    double quality = 1.0;
    if (sample.contains(QStringLiteral("quality"))) {
        quality = sample.value(QStringLiteral("quality")).toDouble();
    } else {
        const double total = sample.value(QStringLiteral("qualityTotal")).toDouble();
        if (total > 0.0)
            quality = sample.value(QStringLiteral("qualityScore")).toDouble() / total;
    }
    const bool stable = sample.contains(QStringLiteral("stable"))
        ? sample.value(QStringLiteral("stable")).toBool()
        : !sample.value(QStringLiteral("failed")).toBool()
          && !sample.value(QStringLiteral("timedOut")).toBool();
    const double stability = stable ? 1.0 : 0.0;
    const QString objective = target.trimmed().toLower();
    double speed = objective == QLatin1String("prefill") ? pp
                   : objective == QLatin1String("decode") ? tg
                   : 0.65 * tg + 0.35 * pp;
    return speed * qBound(0.0, quality, 1.0) * (0.5 + 0.5 * stability);
}
