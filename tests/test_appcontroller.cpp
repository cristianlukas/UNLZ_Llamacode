// Tests de las variantes headless (sin diálogo) de AppController: export/import
// de datos de usuario y export de sesión de chat a ruta explícita. Garantizan
// que toda feature con diálogo tenga un camino api/headless equivalente.

#include <QtTest>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTemporaryFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QFileInfo>
#include <QDir>
#include <QCoreApplication>
#include <QTimer>
#include <QSignalSpy>
#include "AppController.h"
#include "core/agent/BrowserTeach.h"
#include "core/agent/IAgentBackend.h"
#include "core/agent/LlamaAgentBackend.h"
#include "core/profiles/ProfileTypes.h"
#include "core/tasks/TaskStore.h"
#include "core/CatalogModel.h"

// Backend de agente fake para ejercitar el ciclo del bucle de Tasks sin un
// llama-server real. Cada sendMessage responde un texto scripteado y, async,
// emite messagesChanged + turnFinished (async para no recursar dentro de
// sendToAgent). El goal-check se detecta por el prompt; devuelve veredictos en
// secuencia (GOAL_NOT_MET → otra iteración; GOAL_MET → corta).
class FakeAgentBackend : public IAgentBackend
{
    Q_OBJECT
public:
    explicit FakeAgentBackend(QObject *parent = nullptr) : IAgentBackend(parent) {}

    QString adapter() const override { return QStringLiteral("llamaagent"); }
    bool running() const override { return m_running; }
    void start(const AgentContext &) override { m_running = true; emit runningChanged(); }
    void stop() override { m_running = false; emit runningChanged(); }
    void newSession() override { m_msgs.clear(); }   // sesión limpia por iteración
    QVariantList messages() const override { return m_msgs; }

    void sendMessage(const QString &text) override
    {
        QString reply;
        if (text.contains(QStringLiteral("objetivo del bucle"))) {
            reply = m_verdicts.isEmpty() ? QStringLiteral("GOAL_MET") : m_verdicts.takeFirst();
        } else {
            ++m_bodyRuns;
            m_lastBodyPrompt = text;
            reply = QStringLiteral("trabajo realizado %1").arg(m_bodyRuns);
        }
        m_msgs.append(QVariantMap{{QStringLiteral("role"), QStringLiteral("assistant")},
                                  {QStringLiteral("content"), reply}});
        emit messagesChanged();
        QTimer::singleShot(0, this, [this]() { emit turnFinished(); });
    }

    void setVerdicts(const QStringList &v) { m_verdicts = v; }
    int bodyRuns() const { return m_bodyRuns; }
    QString lastBodyPrompt() const { return m_lastBodyPrompt; }

private:
    bool m_running = false;
    int m_bodyRuns = 0;
    QStringList m_verdicts;
    QString m_lastBodyPrompt;
    QVariantList m_msgs;
};

class AppControllerTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void exportUserDataToWritesBackup();
    void importUserDataFromRoundTrips();
    void exportUserDataToEmptyPathErrors();
    void exportChatSessionToMissingSessionErrors();
    void parseGpuPowerCsvParses();
    void parseGpuPowerCsvTolerant();
    void researchReportGuardrailsRejectKnownErrors();
    void researchReportGuardrailsAcceptCorrectedClaims();
    void ggufRecommendationCandidateFilter();
    void modelRecommendationsUseResolvableGgufNames();
    void createRecommendedLaunchProfileBuildsProfile();
    void browserMcpEffectiveResolves();
    void voiceWhisperServerAvailabilityUsesConfiguredPath();
    void legacyVoiceConfigDefaultsToManagedPiper();
    void browserTeachSkillsLifecycle();
    void taskFailureTextDetected();
    void taskRequiresToolEvidenceForWebObjective();
    void readResearchReportPrependsLegacyTopic();
    void researchReportsExposeFormattedDate();
    void autoStartAgentOnLaunchPersists();
    void windowsStartupCommandQuotesExecutable();
    void startupHiddenRequiresBothFlags();
    void loopTaskRunsBodyUntilGoalMet();
    void loopTaskStopsAtMaxIterations();
    void earlyFailureRecordedInHistory();
    void harnessAdapterNormalizesToLlamaAgent();
    void charlaTranscriptRoutesToAgentWhenRunning();
    void agentLevels_contextBudgetLadder();

private:
    QTemporaryDir m_tmp;
    QString makeLoopTask(AppController &app, const QString &name, int maxIter);
};

void AppControllerTests::voiceWhisperServerAvailabilityUsesConfiguredPath()
{
    AppController app;
    const QString missing = QDir::temp().filePath(QStringLiteral("missing-whisper-server.exe"));
    QFile::remove(missing);
    app.setVoiceWhisperServerPath(missing);
    QVERIFY(!app.voiceWhisperServerAvailable());

    QTemporaryFile executable(QDir::temp().filePath(QStringLiteral("whisper-server-XXXXXX.exe")));
    QVERIFY(executable.open());
    app.setVoiceWhisperServerPath(executable.fileName());
    QVERIFY(app.voiceWhisperServerAvailable());
    app.setVoiceWhisperServerPath(QString());
}

void AppControllerTests::legacyVoiceConfigDefaultsToManagedPiper()
{
    AppController app;
    const QVariantMap cfg = app.voiceConfig(QStringLiteral("missing-profile"));
    QCOMPARE(cfg.value(QStringLiteral("ttsMode")).toString(), QStringLiteral("piper"));
    QCOMPARE(cfg.value(QStringLiteral("ttsManagedVoice")).toString(),
             QStringLiteral("es_ES-davefx-medium"));
}

QString AppControllerTests::makeLoopTask(AppController &app, const QString &name, int maxIter)
{
    // Task local (sin keywords web → no exige evidencia de tool), en bucle, sin
    // postprompt ni verifyProfile (sin swap de modelo).
    const QVariantMap def{
        {QStringLiteral("name"), name},
        {QStringLiteral("description"), QStringLiteral("Escribí un resumen del texto dado")},
        {QStringLiteral("executionMode"), QStringLiteral("auto")},
        {QStringLiteral("loopEnabled"), true},
        {QStringLiteral("loopGoal"), QStringLiteral("el resumen quedó completo")},
        {QStringLiteral("loopMaxIterations"), maxIter}
    };
    return app.taskStore()->save(QString(), def);
}

void AppControllerTests::initTestCase()
{
    // Aísla AppData/AppLocalData a una ubicación de test.
    QStandardPaths::setTestModeEnabled(true);
    // QTEST_MAIN no setea org/app name; sin ellos QSettings no persiste. Igualamos
    // a lo que usa la app (main.cpp) para que el round-trip de settings funcione.
    QCoreApplication::setOrganizationName(QStringLiteral("LlamaCode"));
    QCoreApplication::setApplicationName(QStringLiteral("LlamaCode"));
    QVERIFY(m_tmp.isValid());
}

void AppControllerTests::exportUserDataToWritesBackup()
{
    AppController app;
    const QString path = m_tmp.filePath(QStringLiteral("backup.json"));
    const QString written = app.exportUserDataTo(path);
    QCOMPARE(written, path);

    QFile f(path);
    QVERIFY(f.open(QIODevice::ReadOnly));
    const QJsonObject root = QJsonDocument::fromJson(f.readAll()).object();
    QCOMPARE(root.value(QStringLiteral("app")).toString(), QStringLiteral("LlamaCode"));
}

void AppControllerTests::importUserDataFromRoundTrips()
{
    AppController app;
    const QString path = m_tmp.filePath(QStringLiteral("backup_rt.json"));
    QVERIFY(!app.exportUserDataTo(path).isEmpty());
    // Re-importar el backup recién escrito devuelve la ruta (no vacío).
    QCOMPARE(app.importUserDataFrom(path), path);
}

void AppControllerTests::exportUserDataToEmptyPathErrors()
{
    AppController app;
    QVERIFY(app.exportUserDataTo(QString()).isEmpty());
}

void AppControllerTests::exportChatSessionToMissingSessionErrors()
{
    AppController app;
    // Sesión inexistente → "" (sin colgar en diálogo).
    const QString out = app.exportChatSessionTo(QStringLiteral("no-such-id"),
                                                QStringLiteral("md"),
                                                m_tmp.filePath(QStringLiteral("c.md")));
    QVERIFY(out.isEmpty());
}

void AppControllerTests::readResearchReportPrependsLegacyTopic()
{
    AppController app;
    const QString id = QStringLiteral("legacy-research-report");
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                        + QStringLiteral("/research");
    QVERIFY(QDir().mkpath(dir));

    QFile md(dir + QLatin1Char('/') + id + QStringLiteral(".md"));
    QVERIFY(md.open(QIODevice::WriteOnly | QIODevice::Truncate));
    md.write("# Reporte\n\nContenido");
    md.close();

    QFile json(dir + QLatin1Char('/') + id + QStringLiteral(".json"));
    QVERIFY(json.open(QIODevice::WriteOnly | QIODevice::Truncate));
    json.write(QJsonDocument(QJsonObject{
        {QStringLiteral("topic"), QStringLiteral("Consulta completa del usuario")}
    }).toJson());
    json.close();

    const QString report = app.readResearchReport(id);
    QVERIFY(report.startsWith(QStringLiteral(
        "# Consulta original\n\nConsulta completa del usuario\n\n---\n\n# Reporte")));
}

void AppControllerTests::researchReportsExposeFormattedDate()
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                        + QStringLiteral("/research");
    QVERIFY(QDir().mkpath(dir));
    const qint64 timestamp =
        QDateTime(QDate(2026, 6, 18), QTime(11, 30)).toMSecsSinceEpoch();

    QFile index(dir + QStringLiteral("/index.json"));
    QVERIFY(index.open(QIODevice::WriteOnly | QIODevice::Truncate));
    index.write(QJsonDocument(QJsonArray{
        QJsonObject{
            {QStringLiteral("id"), QStringLiteral("dated-report")},
            {QStringLiteral("title"), QStringLiteral("Reporte con fecha")},
            {QStringLiteral("timestamp"), static_cast<double>(timestamp)}
        }
    }).toJson());
    index.close();

    AppController app;
    app.refreshResearchReports();
    const QVariantList reports = app.researchReports();
    QVERIFY(!reports.isEmpty());
    QCOMPARE(reports.first().toMap().value(QStringLiteral("dateLabel")).toString(),
             QStringLiteral("18/06/2026 11:30"));
}

void AppControllerTests::autoStartAgentOnLaunchPersists()
{
    {
        AppController app;
        QVERIFY(!app.autoStartAgentOnLaunch());   // default off
        QSignalSpy spy(&app, &AppController::autoStartAgentOnLaunchChanged);
        app.setAutoStartAgentOnLaunch(true);
        QCOMPARE(spy.count(), 1);
        QVERIFY(app.autoStartAgentOnLaunch());
        // set idéntico no re-emite.
        app.setAutoStartAgentOnLaunch(true);
        QCOMPARE(spy.count(), 1);
    }
    // Persiste entre instancias (QSettings).
    AppController app2;
    QVERIFY(app2.autoStartAgentOnLaunch());
    app2.setAutoStartAgentOnLaunch(false);   // restaurar para no contaminar otros tests
}

void AppControllerTests::taskFailureTextDetected()
{
    QVERIFY(AppController::taskFinalTextIndicatesFailure(
        QStringLiteral("No puedo acceder a sitios web desde este entorno.")));
    QVERIFY(AppController::taskFinalTextIndicatesFailure(
        QStringLiteral("I can't browse the website without tools.")));
    QVERIFY(AppController::taskFinalTextIndicatesFailure(
        QStringLiteral("[error: Error transferring http://127.0.0.1:8081/v1/chat/completions - server replied: Bad Request]")));
    QVERIFY(!AppController::taskFinalTextIndicatesFailure(
        QStringLiteral("Compra: 1230. Venta: 1250. Fuente consultada correctamente.")));
}

void AppControllerTests::taskRequiresToolEvidenceForWebObjective()
{
    const QVariantMap webTask{
        {QStringLiteral("name"), QStringLiteral("Extraer cotización")},
        {QStringLiteral("description"), QStringLiteral("Entrá a https://dolarhoy.com/ y traé compra y venta")}
    };
    QVERIFY(AppController::taskRequiresToolEvidence(webTask));

    const QVariantMap localTask{
        {QStringLiteral("name"), QStringLiteral("Resumir nota")},
        {QStringLiteral("description"), QStringLiteral("Escribí un resumen corto del texto dado")}
    };
    QVERIFY(!AppController::taskRequiresToolEvidence(localTask));
}

void AppControllerTests::parseGpuPowerCsvParses()
{
    // index, name, limit, default, min, max, draw
    const QString csv =
        QStringLiteral("0, NVIDIA GeForce RTX 3090, 280.00, 350.00, 100.00, 350.00, 142.50\n");
    const QVariantList gpus = AppController::parseGpuPowerCsv(csv);
    QCOMPARE(gpus.size(), 1);
    const QVariantMap g = gpus.first().toMap();
    QCOMPARE(g.value("index").toInt(), 0);
    QCOMPARE(g.value("name").toString(), QStringLiteral("NVIDIA GeForce RTX 3090"));
    QCOMPARE(g.value("currentW").toDouble(), 280.0);
    QCOMPARE(g.value("defaultW").toDouble(), 350.0);
    QCOMPARE(g.value("minW").toDouble(), 100.0);
    QCOMPARE(g.value("maxW").toDouble(), 350.0);
    QCOMPARE(g.value("drawW").toDouble(), 142.5);
}

void AppControllerTests::parseGpuPowerCsvTolerant()
{
    // Línea basura (sin index numérico) y campo faltante → se ignoran sin romper.
    const QString csv = QStringLiteral("garbage line\n1, GPU B, 200, 250, 90, 250\n");
    const QVariantList gpus = AppController::parseGpuPowerCsv(csv);
    QCOMPARE(gpus.size(), 1);
    const QVariantMap g = gpus.first().toMap();
    QCOMPARE(g.value("index").toInt(), 1);
    QCOMPARE(g.value("drawW").toDouble(), 0.0);   // power.draw ausente
}

void AppControllerTests::researchReportGuardrailsRejectKnownErrors()
{
    const QString report = QStringLiteral(
        "La RTX 3090 no soporta NVLink. La ProArt Z790 trabaja x16+x8 y el segundo "
        "slot viene del chipset. Su VRM alimenta las dos GPU. El anuncio activo "
        "confirma stock. Precio estimado: $1.500.000 ARS.");
    const QStringList issues = AppController::researchReportGuardrailIssues(report);
    QVERIFY(issues.size() >= 5);
}

void AppControllerTests::researchReportGuardrailsAcceptCorrectedClaims()
{
    const QString report = QStringLiteral(
        "La RTX 3090 soporta NVLink sujeto al modelo, puente y software. En la "
        "ASUS ProArt Z790-CREATOR los dos slots principales usan líneas del CPU "
        "en x8/x8. La PSU alimenta las GPU. La publicación no confirma stock ni "
        "precio, por lo que se marca como no verificado.");
    QVERIFY(AppController::researchReportGuardrailIssues(report).isEmpty());
}

void AppControllerTests::ggufRecommendationCandidateFilter()
{
    QVERIFY(!AppController::isGgufRecommendationCandidate(
        QStringLiteral("lmstudio-community/Qwen3-14B-MLX-4bit"), false, false));
    QVERIFY(!AppController::isGgufRecommendationCandidate(
        QStringLiteral("cyankiwi/Qwen3.5-9B-AWQ-BF16-INT4"), false, false));
    QVERIFY(AppController::isGgufRecommendationCandidate(
        QStringLiteral("Qwen/Qwen3.5-9B-MTP"), false, true));
    QVERIFY(AppController::isGgufRecommendationCandidate(
        QStringLiteral("unsloth/Qwen3.5-9B-GGUF"), false, false));
}

void AppControllerTests::modelRecommendationsUseResolvableGgufNames()
{
    QCOMPARE(AppController::recommendedGgufFileName(
                 QStringLiteral("unsloth/Qwen3.6-35B-A3B-MTP-GGUF"),
                 QStringLiteral("Qwen/Qwen3.6-35B-A3B-MTP"),
                 QStringLiteral("Q4_K_M")),
             QStringLiteral("Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"));
    QCOMPARE(AppController::recommendedGgufFileName(
                 QStringLiteral("unsloth/Qwen3.5-2B-MTP-GGUF"),
                 QStringLiteral("Qwen/Qwen3.5-2B-MTP"),
                 QStringLiteral("Q4_K_M")),
             QStringLiteral("Qwen3.5-2B-Q4_K_M.gguf"));
    QCOMPARE(AppController::recommendedGgufFileName(
                 QStringLiteral("bartowski/Qwen2.5-7B-Instruct-GGUF"),
                 QStringLiteral("Qwen/Qwen2.5-7B-Instruct"),
                 QStringLiteral("Q4_K_M")),
             QStringLiteral("Qwen2.5-7B-Instruct-Q4_K_M.gguf"));

    const QStringList siblings = {
        QStringLiteral("Qwen3.6-35B-A3B-UD-IQ3_S.gguf"),
        QStringLiteral("Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"),
        QStringLiteral("Qwen3.6-35B-A3B-Q8_0.gguf")
    };
    QCOMPARE(AppController::resolveRecommendedGgufFileName(
                 siblings,
                 QStringLiteral("Qwen3.6-35B-A3B-MTP-Q4_K_M.gguf")),
             QStringLiteral("Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"));
    const QStringList hermesSiblings = {
        QStringLiteral("Hermes-3-Llama-3.1-8B-Q3_K_M.gguf"),
        QStringLiteral("Hermes-3-Llama-3.1-8B-IQ4_XS.gguf"),
        QStringLiteral("Hermes-3-Llama-3.1-8B-Q8_0.gguf")
    };
    QCOMPARE(AppController::resolveRecommendedGgufFileName(
                 hermesSiblings,
                 QStringLiteral("Hermes-3-Llama-3.1-8B-IQ4_XS.gguf")),
             QStringLiteral("Hermes-3-Llama-3.1-8B-IQ4_XS.gguf"));

    const QStringList catalogCandidates = {
        QStringLiteral(":/assets/hwfit/hf_models.json"),
        QDir::current().absoluteFilePath(QStringLiteral("assets/hwfit/hf_models.json")),
        QDir::current().absoluteFilePath(QStringLiteral("../assets/hwfit/hf_models.json")),
        QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(QStringLiteral("../../assets/hwfit/hf_models.json"))
    };
    QFile catalog;
    for (const QString &path : catalogCandidates) {
        catalog.setFileName(path);
        if (catalog.exists())
            break;
    }
    QVERIFY(catalog.open(QIODevice::ReadOnly));
    const QJsonArray rows = QJsonDocument::fromJson(catalog.readAll()).array();
    bool sawTinyQwen = false;
    for (const QJsonValue &v : rows) {
        const QJsonObject row = v.toObject();
        if (row.value(QStringLiteral("name")).toString() == QLatin1String("Qwen/Qwen3.5-2B-MTP")) {
            const QJsonArray sources = row.value(QStringLiteral("gguf_sources")).toArray();
            QVERIFY(!sources.isEmpty());
            QCOMPARE(sources.first().toObject().value(QStringLiteral("repo")).toString(),
                     QStringLiteral("unsloth/Qwen3.5-2B-MTP-GGUF"));
            sawTinyQwen = true;
            break;
        }
    }
    QVERIFY(sawTinyQwen);
}

void AppControllerTests::createRecommendedLaunchProfileBuildsProfile()
{
    AppController app;

    const QString exePath = m_tmp.filePath(QStringLiteral("llama-server.exe"));
    QFile exe(exePath);
    QVERIFY(exe.open(QIODevice::WriteOnly));
    exe.write("fake-binary");
    exe.close();
    const QString binaryId = app.binaryRegistry()->add(
        exePath, QStringLiteral("fake llama-server"), QStringLiteral("custom"),
        QStringLiteral("cpu"), QString());
    QVERIFY(!binaryId.isEmpty());

    const QString modelPath = m_tmp.filePath(QStringLiteral("Qwen3.5-9B-Q4_K_M.gguf"));
    QFile modelFile(modelPath);
    QVERIFY(modelFile.open(QIODevice::WriteOnly));
    modelFile.write("GGUF");
    modelFile.close();

    CatalogModel model;
    model.id = QStringLiteral("setup-model");
    model.rootId = QStringLiteral("setup-root");
    model.absolutePath = modelPath;
    model.fileName = QFileInfo(modelPath).fileName();
    model.sizeBytes = QFileInfo(modelPath).size();
    model.mtime = QFileInfo(modelPath).lastModified();
    model.familyHint = QStringLiteral("qwen");
    model.quantHint = QStringLiteral("Q4_K_M");
    model.isAvailable = true;
    app.modelCatalog()->addOrUpdate(model);

    const QString launchId = app.createRecommendedLaunchProfile();
    QVERIFY(!launchId.isEmpty());
    QVERIFY(app.hasAnyLaunch());
    QVERIFY(!app.needsSetup());
    QCOMPARE(app.profileManager()->getLaunchProfile(launchId).value("id").toString(), launchId);
}

void AppControllerTests::browserMcpEffectiveResolves()
{
    // Override "on"/"off" pisa el toggle global; "inherit" (u otro) lo hereda.
    QVERIFY( AppController::browserMcpEffective(QStringLiteral("on"),  false));
    QVERIFY( AppController::browserMcpEffective(QStringLiteral("on"),  true));
    QVERIFY(!AppController::browserMcpEffective(QStringLiteral("off"), true));
    QVERIFY(!AppController::browserMcpEffective(QStringLiteral("off"), false));
    QVERIFY( AppController::browserMcpEffective(QStringLiteral("inherit"), true));
    QVERIFY(!AppController::browserMcpEffective(QStringLiteral("inherit"), false));
    QVERIFY( AppController::browserMcpEffective(QString(), true));   // vacío → hereda
}

void AppControllerTests::browserTeachSkillsLifecycle()
{
    // sanitize: slug seguro para filename.
    QCOMPARE(BrowserTeach::sanitize(QStringLiteral("Login   Banco!!")),
             QStringLiteral("login-banco"));
    QCOMPARE(BrowserTeach::sanitize(QStringLiteral("a.b/c")), QStringLiteral("a-b-c"));

    // skillPath usa el slug + .mjs dentro de skillsDir.
    const QString path = BrowserTeach::skillPath(QStringLiteral("My Skill"));
    QVERIFY(path.endsWith(QStringLiteral("/my-skill.mjs")));
    QVERIFY(path.startsWith(BrowserTeach::skillsDir()));

    // recordCommand: codegen con -o al path; agrega url http válida.
    const QString rc = BrowserTeach::recordCommand(QStringLiteral("My Skill"),
                                                   QStringLiteral("https://x.com"));
    QVERIFY(rc.contains(QStringLiteral("playwright codegen")));
    QVERIFY(rc.contains(QStringLiteral("my-skill.mjs")));
    QVERIFY(rc.endsWith(QStringLiteral("https://x.com")));
    // Perfil persistente: codegen graba con --user-data-dir al dir del skill, así el
    // replay reusa el login. El dir vive bajo skillsDir()/profiles/<slug>.
    const QString prof = BrowserTeach::profileDir(QStringLiteral("My Skill"));
    QVERIFY(prof.endsWith(QStringLiteral("/profiles/my-skill")));
    QVERIFY(prof.startsWith(BrowserTeach::skillsDir()));
    QVERIFY(rc.contains(QStringLiteral("--user-data-dir=\"") + prof + QLatin1Char('"')));
    QVERIFY(BrowserTeach::profileDir(QStringLiteral("!!!")).isEmpty());   // sin slug → vacío
    // url no-http se ignora.
    QVERIFY(!BrowserTeach::recordCommand(QStringLiteral("s"), QStringLiteral("ftp://x"))
                 .contains(QStringLiteral("ftp://")));

    // replayProgramArgs: {node, path}.
    const QStringList pa = BrowserTeach::replayProgramArgs(QStringLiteral("My Skill"));
    QCOMPARE(pa.size(), 2);
    QCOMPARE(pa.first(), QStringLiteral("node"));
    QVERIFY(pa.at(1).endsWith(QStringLiteral("my-skill.mjs")));

    // list/has/remove sobre un .mjs real escrito a disco (skillsDir aislado por
    // setTestModeEnabled en initTestCase).
    QVERIFY(!BrowserTeach::hasSkill(QStringLiteral("My Skill")));
    QFile f(path);
    QVERIFY(f.open(QIODevice::WriteOnly));
    f.write("// dummy\n");
    f.close();
    QVERIFY(BrowserTeach::hasSkill(QStringLiteral("My Skill")));
    QVERIFY(BrowserTeach::listSkills().contains(QStringLiteral("my-skill")));
    QVERIFY(BrowserTeach::removeSkill(QStringLiteral("My Skill")));
    QVERIFY(!BrowserTeach::hasSkill(QStringLiteral("My Skill")));
}

void AppControllerTests::windowsStartupCommandQuotesExecutable()
{
    QCOMPARE(AppController::windowsStartupCommand(
                 QStringLiteral("C:/Program Files/LlamaCode/LlamaCode.exe")),
             QStringLiteral("\"C:\\Program Files\\LlamaCode\\LlamaCode.exe\" --startup"));
}

void AppControllerTests::startupHiddenRequiresBothFlags()
{
    QVERIFY(AppController::shouldStartHidden(true, true));
    QVERIFY(!AppController::shouldStartHidden(true, false));
    QVERIFY(!AppController::shouldStartHidden(false, true));
    QVERIFY(!AppController::shouldStartHidden(false, false));
}

void AppControllerTests::loopTaskRunsBodyUntilGoalMet()
{
    AppController app;
    auto *fake = new FakeAgentBackend(&app);
    fake->start(AgentContext{});
    fake->setVerdicts({QStringLiteral("GOAL_NOT_MET falta"), QStringLiteral("GOAL_MET listo")});
    app.setTestAgentBackend(fake);

    const QString id = makeLoopTask(app, QStringLiteral("Loop hasta goal"), 5);
    QSignalSpy fin(&app, &AppController::taskRunFinished);
    app.runTaskBodyForTest(id);

    for (int i = 0; i < 100 && fin.isEmpty(); ++i)
        QTest::qWait(10);

    QVERIFY(!fin.isEmpty());
    const QList<QVariant> args = fin.takeFirst();
    QCOMPARE(args.at(2).toString(), QStringLiteral("ok"));   // status final
    // Cuerpo corrió 2 veces (iter1 GOAL_NOT_MET → iter2 GOAL_MET).
    QCOMPARE(fake->bodyRuns(), 2);
    // Checkpoint/resume: el cuerpo de la iteración 2 recibió el progreso del
    // veredicto previo ("falta") para retomar desde ahí, no arrancar de cero.
    QVERIFY(fake->lastBodyPrompt().contains(QStringLiteral("Progreso acumulado")));
    QVERIFY(fake->lastBodyPrompt().contains(QStringLiteral("falta")));
}

void AppControllerTests::loopTaskStopsAtMaxIterations()
{
    AppController app;
    auto *fake = new FakeAgentBackend(&app);
    fake->start(AgentContext{});
    // Nunca cumple → debe cortar por techo de iteraciones.
    fake->setVerdicts({QStringLiteral("GOAL_NOT_MET"), QStringLiteral("GOAL_NOT_MET"),
                       QStringLiteral("GOAL_NOT_MET"), QStringLiteral("GOAL_NOT_MET")});
    app.setTestAgentBackend(fake);

    const QString id = makeLoopTask(app, QStringLiteral("Loop sin fin"), 3);
    QSignalSpy fin(&app, &AppController::taskRunFinished);
    app.runTaskBodyForTest(id);

    for (int i = 0; i < 100 && fin.isEmpty(); ++i)
        QTest::qWait(10);

    QVERIFY(!fin.isEmpty());
    QCOMPARE(fake->bodyRuns(), 3);   // exactamente maxIter corridas del cuerpo
}

void AppControllerTests::charlaTranscriptRoutesToAgentWhenRunning()
{
    AppController app;
    auto *fake = new FakeAgentBackend(&app);
    fake->start(AgentContext{});
    app.setTestAgentBackend(fake);

    // Ingi Charla con agente corriendo: el transcript de voz va al agente
    // (computer-use/visión), no al chat backend.
    QVERIFY(app.dispatchCharlaTranscript(QStringLiteral("abrí el navegador")));
    QVERIFY(app.charlaUseAgentForTest());
    QCOMPARE(fake->bodyRuns(), 1);   // el agente recibió el mensaje

    // Agente detenido: NO rutea al agente (no más mensajes al fake). La rama de
    // fallback a chat se ejercita en QA manual (requiere server real).
    fake->stop();
    QCOMPARE(fake->bodyRuns(), 1);
    QVERIFY(!(app.charlaUseAgentForTest() && fake->running()));
}

void AppControllerTests::earlyFailureRecordedInHistory()
{
    AppController app;
    // Sin agente: canRunTask() es false → runTask falla en el gating ANTES de
    // arrancar el cuerpo. Antes esto no dejaba rastro; ahora debe quedar una
    // corrida con estado error en el historial del Proceso.
    const QString id = makeLoopTask(app, QStringLiteral("Falla temprana"), 3);
    QSignalSpy fin(&app, &AppController::taskRunFinished);

    app.runTask(id);

    QVERIFY(!fin.isEmpty());
    QCOMPARE(fin.takeFirst().at(2).toString(), QStringLiteral("error"));

    const QVariantList hist = app.runHistory(id);
    QCOMPARE(hist.size(), 1);
    QCOMPARE(hist.first().toMap().value(QStringLiteral("status")).toString(),
             QStringLiteral("error"));
}

void AppControllerTests::harnessAdapterNormalizesToLlamaAgent()
{
    // Política: todo perfil usa LlamaAgent. "none"/vacío/"opencode" → "llamaagent".
    QCOMPARE(AppController::normalizeHarnessAdapter(QString()), QStringLiteral("llamaagent"));
    QCOMPARE(AppController::normalizeHarnessAdapter(QStringLiteral("  ")), QStringLiteral("llamaagent"));
    QCOMPARE(AppController::normalizeHarnessAdapter(QStringLiteral("none")), QStringLiteral("llamaagent"));
    QCOMPARE(AppController::normalizeHarnessAdapter(QStringLiteral("opencode")), QStringLiteral("llamaagent"));
    // Respeta llamaagent y raw (modo Chat).
    QCOMPARE(AppController::normalizeHarnessAdapter(QStringLiteral("llamaagent")), QStringLiteral("llamaagent"));
    QCOMPARE(AppController::normalizeHarnessAdapter(QStringLiteral("raw")), QStringLiteral("raw"));
}

// Niveles de agente = escalera de presupuesto de contexto. Ejercita los 5 presets
// con la traducción REAL (applyAgentProfileCaps) sobre un LlamaAgentBackend con 37
// tools MCP inyectadas, y mide el contexto efectivo (system prompt + tool schemas)
// por nivel. Garantías:
//   - escalera monótona: Chat < Básico < Intermedio < Avanzado < Máximo.
//   - Chat es el único con MCP off → sin tools mcp__ en el schema.
//   - Máximo ("*") NO arrastra las opt-in puras (honey/antiBias): regresión que se
//     coló al sumar antiBias al catálogo; acá queda pinchada.
void AppControllerTests::agentLevels_contextBudgetLadder()
{
    AppController app;

    // 37 tools MCP sintéticas (14 filesystem + 23 playwright), como en producción.
    QVariantList mcp;
    auto mkTool = [](const QString &server, const QString &name) {
        return QVariant(QVariantMap{
            {"server", server}, {"name", name},
            {"description", QStringLiteral("Tool %1 del MCP %2.").arg(name, server)},
            {"schema", QStringLiteral("{\"type\":\"object\",\"properties\":"
                "{\"path\":{\"type\":\"string\"},\"opts\":{\"type\":\"object\"}}}")}});
    };
    for (int i = 0; i < 14; ++i) mcp << mkTool("filesystem", QStringLiteral("fs_%1").arg(i));
    for (int i = 0; i < 23; ++i) mcp << mkTool("playwright", QStringLiteral("pw_%1").arg(i));

    auto budgetFor = [&](const AgentProfile &ap, bool *hasMcp, QString *sysOut) {
        LlamaAgentBackend be;
        be.setMcpToolsForTest(mcp);
        app.applyAgentProfileCapsForTest(&be, ap);   // traducción REAL de la app
        const QString sys = be.systemPromptForTest();
        const QJsonArray tools = be.toolSchemasForTest();
        if (sysOut) *sysOut = sys;
        if (hasMcp) {
            *hasMcp = false;
            for (const QJsonValue &v : tools) {
                const QString n = v.toObject().value("function").toObject().value("name").toString();
                if (n.startsWith(QStringLiteral("mcp__"))) { *hasMcp = true; break; }
            }
        }
        const int toolBytes = QJsonDocument(tools).toJson(QJsonDocument::Compact).size();
        return sys.toUtf8().size() + toolBytes;
    };

    const QList<AgentProfile> ps = AgentProfile::systemPresets();
    auto byId = [&](const QString &id) {
        for (const AgentProfile &p : ps) if (p.id == id) return p;
        return AgentProfile{};
    };

    bool chatMcp = true, maxMcp = false;
    QString chatSys, maxSys;
    const int chat   = budgetFor(byId(QStringLiteral("agent-chat")),       &chatMcp, &chatSys);
    const int basico = budgetFor(byId(QStringLiteral("agent-basico")),     nullptr, nullptr);
    const int inter  = budgetFor(byId(QStringLiteral("agent-intermedio")), nullptr, nullptr);
    const int avanz  = budgetFor(byId(QStringLiteral("agent-avanzado")),   nullptr, nullptr);
    const int maximo = budgetFor(byId(QStringLiteral("agent-maximo")),     &maxMcp, &maxSys);

    qInfo() << "presupuesto por nivel (system+tools, bytes):";
    qInfo() << "  Chat liviano:" << chat;
    qInfo() << "  Básico:" << basico;
    qInfo() << "  Intermedio:" << inter;
    qInfo() << "  Avanzado:" << avanz;
    qInfo() << "  Máximo (+37 MCP):" << maximo;

    // Escalera monótona estricta.
    QVERIFY2(chat < basico,   qPrintable(QStringLiteral("Chat %1 !< Básico %2").arg(chat).arg(basico)));
    QVERIFY2(basico < inter,  qPrintable(QStringLiteral("Básico %1 !< Intermedio %2").arg(basico).arg(inter)));
    QVERIFY2(inter < avanz,   qPrintable(QStringLiteral("Intermedio %1 !< Avanzado %2").arg(inter).arg(avanz)));
    QVERIFY2(avanz < maximo,  qPrintable(QStringLiteral("Avanzado %1 !< Máximo %2").arg(avanz).arg(maximo)));

    // Chat: único sin MCP. Máximo: con MCP.
    QVERIFY2(!chatMcp, "Chat liviano no debería inyectar tools MCP");
    QVERIFY2(maxMcp, "Máximo debería inyectar tools MCP");

    // Opt-in puras NO entran por el sentinel "*" de Máximo.
    QVERIFY2(!maxSys.contains(QStringLiteral("ANTI-SESGO")),
             "Máximo arrastró antiBias por '*' (debe ser opt-in puro)");
    QVERIFY2(!maxSys.contains(QStringLiteral("FRUGALIDAD (Honey)")),
             "Máximo arrastró honey por '*' (debe ser opt-in puro)");
}

QTEST_MAIN(AppControllerTests)
#include "test_appcontroller.moc"
