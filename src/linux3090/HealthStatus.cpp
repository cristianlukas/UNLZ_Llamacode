#include "HealthStatus.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QSet>

namespace Gpu3090Helper {
namespace {

const QString kAsusUuid = QStringLiteral("GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6");
const QString kPnyUuid = QStringLiteral("GPU-5b9f385f-6a8e-b802-f69c-e62a71c91049");
const QString kAsusPci = QStringLiteral("0000:01:00.0");
const QString kPnyPci = QStringLiteral("0000:03:00.0");

QSet<QString> normalizedTargets(QString value)
{
    value = value.trimmed().toLower();
    value.remove(QLatin1Char('"'));
    QSet<QString> result;
    for (QString target : value.split(QLatin1Char(','), Qt::SkipEmptyParts)) {
        target = target.trimmed();
        if (!target.startsWith(QStringLiteral("0000:")))
            target.prepend(QStringLiteral("0000:"));
        result.insert(target);
    }
    return result;
}

bool hasPairwiseOk(const QString &matrix)
{
    QString clean = matrix;
    clean.remove(QRegularExpression(QStringLiteral("\\x1B\\[[0-9;]*[A-Za-z]")));
    const QStringList lines = clean.split(QLatin1Char('\n'));
    int gpu0Column = -1;
    int gpu1Column = -1;
    for (const QString &line : lines) {
        const QStringList cells = line.simplified().split(QLatin1Char(' '), Qt::SkipEmptyParts);
        if (cells.isEmpty())
            continue;
        if (cells.size() >= 2 && cells.first() == QLatin1String("GPU0")) {
            // Matrix data rows add their row label before these header columns.
            gpu0Column = cells.indexOf(QStringLiteral("GPU0")) + 1;
            gpu1Column = cells.indexOf(QStringLiteral("GPU1")) + 1;
            if (gpu0Column > 0 && gpu1Column > 0)
                break;
        }
    }
    if (gpu0Column < 0 || gpu1Column < 0)
        return false;

    bool gpu0To1 = false;
    bool gpu1To0 = false;
    for (const QString &line : lines) {
        const QStringList cells = line.simplified().split(QLatin1Char(' '), Qt::SkipEmptyParts);
        if (cells.isEmpty())
            continue;
        if (cells.first() == QLatin1String("GPU0"))
            gpu0To1 = cells.size() > gpu1Column && cells.at(gpu1Column) == QLatin1String("OK");
        else if (cells.first() == QLatin1String("GPU1"))
            gpu1To0 = cells.size() > gpu0Column && cells.at(gpu0Column) == QLatin1String("OK");
    }
    return gpu0To1 && gpu1To0;
}

bool hasUnlockLine(const QString &log, const QString &pci)
{
    const QString escaped = QRegularExpression::escape(pci);
    const QRegularExpression success(
        QStringLiteral("%1[^\\n]*gpu_unlock: unlocked(?:\\s|$)").arg(escaped),
        QRegularExpression::CaseInsensitiveOption);
    return success.match(log).hasMatch();
}

bool hasExpectedGpuPair(const QString &inventory)
{
    bool asus = false;
    bool pny = false;
    for (const QString &line : inventory.split(QLatin1Char('\n'))) {
        const QStringList fields = line.split(QLatin1Char(','));
        if (fields.size() < 3)
            continue;
        const QString uuid = fields.at(0).trimmed();
        const QString name = fields.at(1).trimmed();
        const QString pci = fields.at(2).trimmed().toLower();
        if (uuid == kAsusUuid && name.contains(QStringLiteral("3090"), Qt::CaseInsensitive)
            && pci.endsWith(QStringLiteral("01:00.0")))
            asus = true;
        if (uuid == kPnyUuid && name.contains(QStringLiteral("3090"), Qt::CaseInsensitive)
            && pci.endsWith(QStringLiteral("03:00.0")))
            pny = true;
    }
    return asus && pny;
}

} // namespace

bool Snapshot::healthy() const
{
    return vramQuarantine.ok && p2p.ok && gpuUnlock.ok;
}

QString Snapshot::report() const
{
    const auto line = [](const CheckResult &check) {
        return QStringLiteral("[%1] %2 — %3")
            .arg(check.ok ? QStringLiteral("OK") : QStringLiteral("FALLO"),
                 check.name, check.detail);
    };
    return QStringList{
        QStringLiteral("3090 HELPER — estado: %1")
            .arg(healthy() ? QStringLiteral("VERDE") : QStringLiteral("ROJO")),
        line(vramQuarantine),
        line(p2p),
        line(gpuUnlock)
    }.join(QLatin1Char('\n')) + (diagnostics.isEmpty()
        ? QString() : QStringLiteral("\n\n--- Diagnóstico reciente ---\n") + diagnostics);
}

Snapshot evaluate(const Inputs &inputs)
{
    Snapshot result;
    result.vramQuarantine.name = QStringLiteral("Reserva VRAM ASUS");
    const QJsonDocument stateDoc = QJsonDocument::fromJson(inputs.workerJson.toUtf8());
    const QJsonObject state = stateDoc.object();
    const qint64 held = state.value(QStringLiteral("held")).toInteger(-1);
    const qint64 total = state.value(QStringLiteral("total")).toInteger(-1);
    const qint64 pending = state.value(QStringLiteral("pending")).toInteger(-1);
    const bool correctGpu = state.value(QStringLiteral("uuid")).toString() == kAsusUuid
        && state.value(QStringLiteral("pci")).toString().compare(kAsusPci, Qt::CaseInsensitive) == 0;
    const bool protectedFrames = state.value(QStringLiteral("state")).toString()
                                     == QLatin1String("protected")
        && held > 0 && held == total && pending == 0;
    const bool matchingDriver = !state.value(QStringLiteral("driver")).toString().isEmpty()
        && state.value(QStringLiteral("driver")).toString()
               == state.value(QStringLiteral("built_for")).toString();
    result.vramQuarantine.ok = inputs.workerActive && inputs.workerEnabled
        && stateDoc.isObject() && correctGpu && protectedFrames && matchingDriver;
    if (!stateDoc.isObject()) {
        result.vramQuarantine.detail = QStringLiteral("No hay un estado JSON válido del worker.");
    } else {
        result.vramQuarantine.detail = QStringLiteral(
            "%1; servicio %2/%3; marcos %4/%5, pendientes %6; driver %7/%8")
            .arg(correctGpu ? QStringLiteral("ASUS identificada")
                            : QStringLiteral("UUID/PCI no corresponde a la ASUS"),
                 inputs.workerActive ? QStringLiteral("activo") : QStringLiteral("inactivo"),
                 inputs.workerEnabled ? QStringLiteral("habilitado") : QStringLiteral("deshabilitado"),
                 QString::number(held), QString::number(total), QString::number(pending),
                 state.value(QStringLiteral("driver")).toString(),
                 state.value(QStringLiteral("built_for")).toString());
    }

    result.p2p.name = QStringLiteral("NVIDIA P2P entre las dos 3090");
    const bool readOk = hasPairwiseOk(inputs.p2pRead);
    const bool writeOk = hasPairwiseOk(inputs.p2pWrite);
    const bool pairOk = hasExpectedGpuPair(inputs.gpuInventory);
    result.p2p.ok = readOk && writeOk && pairOk;
    result.p2p.detail = result.p2p.ok
        ? QStringLiteral("Par ASUS/PNY RTX 3090 confirmado; lectura y escritura P2P habilitadas en ambas direcciones.")
        : QStringLiteral("Par de GPU %1; matriz: lectura %2, escritura %3. Requiere driver P2P activo y reinicio si se acaba de instalar.")
              .arg(pairOk ? QStringLiteral("ASUS/PNY confirmado") : QStringLiteral("no coincide con ASUS/PNY RTX 3090"),
                   readOk ? QStringLiteral("OK") : QStringLiteral("no disponible"),
                   writeOk ? QStringLiteral("OK") : QStringLiteral("no disponible"));

    result.gpuUnlock.name = QStringLiteral("gpu-unlock en ambas 3090");
    const QSet<QString> expected{ kAsusPci, kPnyPci };
    const QSet<QString> cmdTargets = normalizedTargets(
        QRegularExpression(QStringLiteral("(?:^|\\s)gpu_unlock\\.targets=([^\\s]+)"))
            .match(inputs.kernelCommandLine).captured(1));
    const QSet<QString> moduleTargets = normalizedTargets(inputs.unlockModuleTargets);
    const bool targetsMatch = cmdTargets == expected && moduleTargets == expected;
    const bool bothLogged = hasUnlockLine(inputs.unlockKernelLog, kAsusPci)
        && hasUnlockLine(inputs.unlockKernelLog, kPnyPci);
    result.gpuUnlock.ok = inputs.unlockModulePresent && targetsMatch && bothLogged;
    result.gpuUnlock.detail = QStringLiteral(
        "Módulo %1; targets boot/módulo %2; éxito ASUS/PNY %3/%4.")
        .arg(inputs.unlockModulePresent ? QStringLiteral("cargado") : QStringLiteral("ausente"),
             targetsMatch ? QStringLiteral("correctos") : QStringLiteral("no coinciden con ambas PCI"),
             hasUnlockLine(inputs.unlockKernelLog, kAsusPci) ? QStringLiteral("OK") : QStringLiteral("falló"),
             hasUnlockLine(inputs.unlockKernelLog, kPnyPci) ? QStringLiteral("OK") : QStringLiteral("falló"));
    result.diagnostics = inputs.diagnostics;
    return result;
}

} // namespace Gpu3090Helper
