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
            reply = QStringLiteral("trabajo realizado %1").arg(m_bodyRuns);
        }
        m_msgs.append(QVariantMap{{QStringLiteral("role"), QStringLiteral("assistant")},
                                  {QStringLiteral("content"), reply}});
        emit messagesChanged();
        QTimer::singleShot(0, this, [this]() { emit turnFinished(); });
    }

    void setVerdicts(const QStringList &v) { m_verdicts = v; }
    int bodyRuns() const { return m_bodyRuns; }

private:
    bool m_running = false;
    int m_bodyRuns = 0;
    QStringList m_verdicts;
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
        {QStringLiteral("executionMode"), QStringLiteral("agent")},
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

QTEST_MAIN(AppControllerTests)
#include "test_appcontroller.moc"
