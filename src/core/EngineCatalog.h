#pragma once

#include <QVariantList>
#include <QString>
#include <QStringList>

struct EngineVariant {
    QString id;
    QString label;
    QString backend;
    QStringList platforms;
    QStringList gpuVendors;
    bool hasPrebuilt = false;
    bool buildFromSource = false;
    QString stability;
    QString speed;
};

struct EngineCatalogEntry {
    QString id;
    QString name;
    QString kind;
    QString description;
    QString repo;
    QString homepage;
    QString flavor;
    QString support;
    QString note;
    QList<EngineVariant> variants;
};

struct HardwareSignals {
    QString platform;
    QString arch;
    QString gpuVendor;
    bool hasGpu = false;
};

struct EngineUpdateStatus {
    QString installed;
    QString latest;
    bool hasUpdate = false;
    bool comparable = false;
    bool rebuild = false;
    QString error;
};

class EngineCatalog
{
public:
    static QList<EngineCatalogEntry> entries();
    static EngineCatalogEntry entry(const QString &id);
    static QVariantList toVariantList(const HardwareSignals &hw);
    static QVariantMap toVariantMap(const EngineCatalogEntry &entry, const HardwareSignals &hw);
    static HardwareSignals detectHardware();
    static QString recommendedEngineId(const HardwareSignals &hw);

    static int parseBuildTag(const QString &tag);
    static QList<int> parseDottedVersion(const QString &version);
    static int compareVersions(const QString &installed, const QString &latest);
    static EngineUpdateStatus computeUpdateStatus(const QString &installed,
                                                  const QString &latest,
                                                  bool sourceBuild = false);

    static QString normalizeRepo(const QString &repoOrUrl);
    static QString buildDirName(const QString &repoOrUrl, const QString &branch = {});
    static bool isVariantCompatible(const EngineVariant &variant,
                                    const HardwareSignals &hw,
                                    QString *reason = nullptr);
};
