#pragma once

#include <QString>

namespace Gpu3090Helper {

struct CheckResult {
    QString name;
    bool ok = false;
    QString detail;
};

struct Inputs {
    QString workerJson;
    bool workerActive = false;
    bool workerEnabled = false;
    QString gpuInventory;
    QString kernelCommandLine;
    QString unlockModuleTargets;
    QString unlockKernelLog;
    bool unlockModulePresent = false;
    QString p2pRead;
    QString p2pWrite;
    QString diagnostics;
};

struct Snapshot {
    CheckResult vramQuarantine;
    CheckResult p2p;
    CheckResult gpuUnlock;
    QString diagnostics;

    bool healthy() const;
    QString report() const;
};

Snapshot evaluate(const Inputs &inputs);

} // namespace Gpu3090Helper
