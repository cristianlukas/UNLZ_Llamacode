#pragma once
#include "core/BinaryRegistry.h"
#include "core/ModelRootRegistry.h"
#include "core/ModelCatalog.h"
#include "core/profiles/ProfileManager.h"
#include "core/profiles/EffectiveProfileBuilder.h"
#include <QObject>
#include <QProcess>
#include <QTimer>
#include <QVariantMap>
#include <QHash>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>

class AppController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(BinaryRegistry*     binaryRegistry  READ binaryRegistry  CONSTANT)
    Q_PROPERTY(ModelRootRegistry*  rootRegistry    READ rootRegistry    CONSTANT)
    Q_PROPERTY(ModelCatalog*       modelCatalog    READ modelCatalog    CONSTANT)
    Q_PROPERTY(ProfileManager*     profileManager  READ profileManager  CONSTANT)
    Q_PROPERTY(bool   serverRunning   READ serverRunning   NOTIFY serverRunningChanged)
    Q_PROPERTY(QString serverLog      READ serverLog       NOTIFY serverLogChanged)
    Q_PROPERTY(QString activeLaunchId READ activeLaunchId  NOTIFY activeLaunchIdChanged)
    Q_PROPERTY(QVariantMap effectiveProfile READ effectiveProfile NOTIFY effectiveProfileChanged)
    Q_PROPERTY(bool needsSetup READ needsSetup NOTIFY setupStateChanged)
    Q_PROPERTY(QString serverBaseUrl READ serverBaseUrl NOTIFY serverRunningChanged)
    Q_PROPERTY(bool installingOfficialBinary READ installingOfficialBinary NOTIFY installingOfficialBinaryChanged)
    Q_PROPERTY(QString officialBinaryInstallStatus READ officialBinaryInstallStatus NOTIFY officialBinaryInstallStatusChanged)
    Q_PROPERTY(QString officialBinaryInstallLog READ officialBinaryInstallLog NOTIFY officialBinaryInstallLogChanged)
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY languageChanged)
    Q_PROPERTY(int langV READ langV NOTIFY languageChanged)
    Q_PROPERTY(bool agentRunning      READ agentRunning      NOTIFY agentRunningChanged)
    Q_PROPERTY(QString agentLog       READ agentLog          NOTIFY agentLogChanged)
    Q_PROPERTY(QString activeAgentAdapter READ activeAgentAdapter NOTIFY agentRunningChanged)
    Q_PROPERTY(bool agentInTerminal   READ agentInTerminal   NOTIFY agentRunningChanged)
    Q_PROPERTY(bool installingHarness READ installingHarness NOTIFY harnessStatusChanged)
    Q_PROPERTY(QString harnessInstallStatus READ harnessInstallStatus NOTIFY harnessStatusChanged)
    Q_PROPERTY(int harnessCheckV READ harnessCheckV NOTIFY harnessStatusChanged)

public:
    explicit AppController(QObject *parent = nullptr);

    BinaryRegistry    *binaryRegistry()  { return &m_binaries; }
    ModelRootRegistry *rootRegistry()    { return &m_roots; }
    ModelCatalog      *modelCatalog()    { return &m_catalog; }
    ProfileManager    *profileManager()  { return &m_profiles; }

    bool   serverRunning()   const { return m_proc && m_proc->state() != QProcess::NotRunning; }
    QString serverLog()      const { return m_log; }
    QString activeLaunchId() const { return m_activeLaunchId; }
    QVariantMap effectiveProfile() const { return m_effectiveProfile; }
    bool needsSetup() const { return m_binaries.count() == 0 && m_catalog.count() == 0; }
    QString serverBaseUrl() const {
        const QStringList args = m_effectiveProfile.value("effectiveArgs").toStringList();
        QString host = QStringLiteral("127.0.0.1");
        int port = 8080;
        for (int i = 0; i + 1 < args.size(); ++i) {
            if (args[i] == "--host") host = args[i + 1];
            else if (args[i] == "--port") port = args[i + 1].toInt();
        }
        return QStringLiteral("http://%1:%2").arg(host).arg(port);
    }
    bool installingOfficialBinary() const { return m_installingOfficialBinary; }
    QString officialBinaryInstallStatus() const { return m_officialBinaryInstallStatus; }
    QString officialBinaryInstallLog() const { return m_officialBinaryInstallLog; }
    QString language() const { return m_language; }
    void setLanguage(const QString &lang);
    int langV() const { return 0; }
    bool agentRunning() const {
        return m_agentInTerminal ? (m_agentPid != 0) : (m_agentProc && m_agentProc->state() != QProcess::NotRunning);
    }
    QString agentLog() const { return m_agentLog; }
    QString activeAgentAdapter() const { return m_activeAgentAdapter; }
    bool agentInTerminal() const { return m_agentInTerminal; }
    bool installingHarness() const { return m_installingHarness; }
    QString harnessInstallStatus() const { return m_harnessInstallStatus; }
    int harnessCheckV() const { return 0; }

    Q_INVOKABLE void startServer(const QString &launchProfileId);
    Q_INVOKABLE void stopServer();
    Q_INVOKABLE void computeEffectiveProfile(const QString &launchProfileId);
    Q_INVOKABLE void clearLog();
    Q_INVOKABLE void copyToClipboard(const QString &text);
    Q_INVOKABLE void installOfficialBinary();
    Q_INVOKABLE void cancelOfficialBinaryInstall();
    Q_INVOKABLE void smokeTestServer(const QString &launchProfileId);
    Q_INVOKABLE bool smokeTestRunning() const { return m_smokeTestProc != nullptr; }
    Q_INVOKABLE QString resolveFlag(const QString &binaryId, const QString &flag) const;
    Q_INVOKABLE QString version() const { return QStringLiteral("0.1.0"); }
    Q_INVOKABLE QString l(const QString &key) const;
    Q_INVOKABLE QString lf(const QString &key, const QString &arg1) const { return l(key).arg(arg1); }
    Q_INVOKABLE QVariant readSetting(const QString &key, const QVariant &defaultValue = QVariant()) const;
    Q_INVOKABLE void writeSetting(const QString &key, const QVariant &value);
    Q_INVOKABLE bool isHarnessInstalled(const QString &adapter) const;
    Q_INVOKABLE void installHarness(const QString &adapter);
    Q_INVOKABLE void startAgent(const QString &launchProfileId);
    Q_INVOKABLE void stopAgent();
    Q_INVOKABLE void sendToAgent(const QString &text);
    Q_INVOKABLE void clearAgentLog();
    Q_INVOKABLE QString agentNativeLogDir(const QString &adapter) const;
    Q_INVOKABLE void openAgentLogDir(const QString &adapter) const;

signals:
    void serverRunningChanged();
    void serverLogChanged();
    void activeLaunchIdChanged();
    void effectiveProfileChanged();
    void setupStateChanged();
    void installingOfficialBinaryChanged();
    void officialBinaryInstallStatusChanged();
    void officialBinaryInstallLogChanged();
    void officialBinaryInstallFinished(bool success, const QString &message, const QString &binaryPath);
    void serverError(const QString &message);
    void smokeTestFinished(bool passed, const QString &output);
    void languageChanged();
    void harnessStatusChanged();
    void harnessInstallFinished(bool success, const QString &adapter, const QString &message);
    void agentRunningChanged();
    void agentLogChanged();

private:
    void appendLog(const QString &text);
    void finishSmokeTest(bool passed, const QString &output);
    EffectiveProfileBuilder::Context buildContext(const QString &launchProfileId);

    BinaryRegistry    m_binaries;
    ModelCatalog      m_catalog;
    ModelRootRegistry m_roots{&m_catalog};
    ProfileManager    m_profiles;

    QProcess *m_proc = nullptr;
    QProcess *m_installerProc = nullptr;
    QProcess *m_smokeTestProc = nullptr;
    QTimer   *m_smokeTestTimer = nullptr;
    QString   m_smokeTestLog;
    bool      m_smokeTestDone = false;
    QString   m_log;
    QString   m_activeLaunchId;
    QVariantMap m_effectiveProfile;
    bool m_installingOfficialBinary = false;
    QString m_officialBinaryInstallStatus;
    QString m_officialBinaryInstallLog;
    bool m_cancelingOfficialBinaryInstall = false;
    bool m_timeoutOfficialBinaryInstall = false;
    QDateTime m_lastInstallProgressAt;
    QTimer *m_installWatchdog = nullptr;
    QString m_language;
    bool m_installingHarness = false;
    QString m_harnessInstallStatus;
    QProcess *m_harnessProc = nullptr;
    QProcess *m_agentProc = nullptr;
    qint64    m_agentPid = 0;
    bool      m_agentInTerminal = false;
    QTimer   *m_agentPollTimer = nullptr;
    QString   m_agentLog;
    QString   m_activeAgentAdapter;
    QString   m_opencodeAttachUrl = QStringLiteral("http://127.0.0.1:4096");
    QNetworkAccessManager *m_nam = nullptr;
    QString   m_opencodeSessionId;
    QNetworkReply *m_opencodeEventReply = nullptr;
    void initOpencodeSession();
    void subscribeOpencodeEvents();

    // Managed-process lifecycle
#ifdef Q_OS_WIN
    void *m_jobObject = nullptr;   // HANDLE — typed as void* to avoid pulling windows.h into header
#endif
    void createJobObject();
    void assignToJobObject(qint64 pid);
    void killManagedOrphans();
    void writeServiceState(const QString &role, qint64 pid, const QVariantMap &extra = {});
    void clearServiceState(const QString &role);
    QString serviceStatePath() const;

    static const QHash<QString, QHash<QString, QString>> &translations();
};
