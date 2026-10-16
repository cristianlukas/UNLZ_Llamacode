// Integration tests de AgentToolRunner (tools nativas del agente). Sin MCP ni
// red ni modelo: ejercitamos el dispatch de tools deterministas contra un cwd
// temporal y verificamos el resultado vía la señal toolExecuted.
//   - write_file → read_file → edit_file (con metadata de diff).
//   - confinamiento al cwd (bloquea rutas fuera del proyecto).
//   - grep / glob.
//   - run_shell async (echo trivial).

#include <QtTest>
#include "core/automation/DesktopAutomationBackend.h"
#include <QTemporaryDir>
#include <QSignalSpy>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonDocument>
#include <QDir>
#include <QFile>
#include <QCryptographicHash>
#include <QProcess>
#include <QTcpServer>
#include <QTcpSocket>
#include <QUrl>
#include <QUrlQuery>
#include <utility>
#include "core/agent/AgentToolRunner.h"
#include "core/agent/AgentLifecycle.h"
#include "core/agent/AgentEventLog.h"
#include "core/agent/WorkRegistry.h"
#include "core/agent/SubAgentRunner.h"

class CamofoxStub : public QTcpServer
{
public:
    explicit CamofoxStub(QObject *parent = nullptr) : QTcpServer(parent)
    {
        connect(this, &QTcpServer::newConnection, this, [this]() {
            QTcpSocket *socket = nextPendingConnection();
            connect(socket, &QTcpSocket::readyRead, socket, [socket]() {
                const QByteArray request = socket->readAll();
                if (!request.contains("\r\n\r\n")) return;
                QByteArray body;
                if (request.startsWith("POST /tabs HTTP/"))
                    body = QByteArrayLiteral(
                        "{\"tabId\":\"tab-1\",\"url\":\"https://93.184.216.34/\"}");
                else if (request.startsWith("POST /tabs/tab-1/evaluate HTTP/"))
                    body = QByteArrayLiteral(
                        "{\"result\":\"{\\\"title\\\":\\\"Example\\\",\\\"text\\\":"
                        "\\\"Contenido DOM renderizado suficientemente largo para validar el "
                        "proveedor Camofox de extremo a extremo sin acceder a Internet.\\\","
                        "\\\"url\\\":\\\"https://93.184.216.34/\\\",\\\"score\\\":900}\"}");
                else
                    body = QByteArrayLiteral("{\"ok\":true}");
                QByteArray response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                    "Connection: close\r\nContent-Length: " + QByteArray::number(body.size())
                    + "\r\n\r\n" + body;
                socket->write(response);
                socket->disconnectFromHost();
            });
            connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
        });
    }
};

class SearxngStub : public QTcpServer
{
public:
    explicit SearxngStub(
        QByteArray responseBody = QByteArrayLiteral(
            "{\"results\":[{\"title\":\"Local result\","
            "\"url\":\"https://docs.example.test/search\","
            "\"content\":\"Fixture result content\"}]}"),
        int responseStatus = 200, QByteArray responseHeaders = {},
        QObject *parent = nullptr)
        : QTcpServer(parent), m_responseBody(std::move(responseBody)),
          m_responseStatus(responseStatus), m_responseHeaders(std::move(responseHeaders))
    {
        connect(this, &QTcpServer::newConnection, this, [this]() {
            QTcpSocket *socket = nextPendingConnection();
            socket->setProperty("requestBuffer", QByteArray());
            connect(socket, &QTcpSocket::readyRead, socket, [this, socket]() {
                QByteArray request = socket->property("requestBuffer").toByteArray();
                request += socket->readAll();
                const qsizetype headerEnd = request.indexOf("\r\n\r\n");
                if (headerEnd < 0) {
                    socket->setProperty("requestBuffer", request);
                    return;
                }
                requests.append(QString::fromLatin1(request.left(request.indexOf("\r\n"))));
                const QByteArray response = QByteArrayLiteral("HTTP/1.1 ")
                    + QByteArray::number(m_responseStatus) + QByteArrayLiteral(" Test\r\n")
                    + QByteArrayLiteral("Content-Type: application/json\r\n")
                    + QByteArrayLiteral("Connection: close\r\n") + m_responseHeaders
                    + QByteArrayLiteral("Content-Length: ")
                    + QByteArray::number(m_responseBody.size())
                    + QByteArrayLiteral("\r\n\r\n") + m_responseBody;
                socket->write(response);
                socket->disconnectFromHost();
            });
            connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
        });
    }

    QStringList requests;

private:
    QByteArray m_responseBody;
    int m_responseStatus;
    QByteArray m_responseHeaders;
};

class ScopedEnvironmentVariable
{
public:
    explicit ScopedEnvironmentVariable(const QByteArray &name)
        : m_name(name),
          m_wasSet(qEnvironmentVariableIsSet(name.constData())),
          m_previous(qgetenv(name.constData()))
    {
    }

    ~ScopedEnvironmentVariable()
    {
        if (m_wasSet) qputenv(m_name.constData(), m_previous);
        else qunsetenv(m_name.constData());
    }

    ScopedEnvironmentVariable(const ScopedEnvironmentVariable &) = delete;
    ScopedEnvironmentVariable &operator=(const ScopedEnvironmentVariable &) = delete;

private:
    QByteArray m_name;
    bool m_wasSet;
    QByteArray m_previous;
};

class AgentToolsTests : public QObject
{
    Q_OBJECT
private slots:
    void init();
    void cleanup();

    void writeReadEditCycle();
    void hashGuard_rejectsStaleEditAndAcceptsFreshHash();
    void hashGuard_coversFullFileBeyondReadView();
    void writeFile_trimsModelPathWhitespace();
    void readAndList_trimsModelPathWhitespace();
    void readFile_compactViewAndSafeFallback();
    void projectBrain_persistsWorkspaceIndex();
    void confinement_blocksOutsideCwd();
    void allowedRoots_permitExtraFolder();
    void unconfined_permitsAnyPath();
    void readOnly_blocksMutationButAllowsRead();
    void editFile_missingFails();
    void editFile_whitespaceNearMissExplains();
    void parseErrorExplainsChunking();
    void grep_findsMatch();
    void glob_listsFiles();
    void reviewOverengineering_isReadOnlyAndExplainsCandidates();
    void reviewOverengineering_handlesEmptyStagedAndUntracked();
    void reviewOverengineering_rejectsInvalidScopeAndTruncates();
    void reviewOverengineering_withoutRepoExplainsRequirement();
    void runShell_echo();
    void hybridSearch_depGraphAndBudget();
    void hybridSearch_compactReturnsSpans();
    void hybridSearch_includeDocsReportsCorpus();
    void repoSlice_defaultsToCompactEvidence();
    void contextScoutAndFetch_validateHandle();
    void contextStatus_reportsPersistentIndex();
    void workStatus_reportsOtherSessions();
    void mutationGuard_detectsOpaqueShellAndDeclaredPaths();
    void graphPacketAndDoctor_areExposedByTool();
    void recentActions_tailsEventLogForSession();
    void desktopWindows_returnsStructuredInventory();
    void desktopNewTools_validateBeforeTouchingTheDesktop();
    void desktopClipboard_roundTripRestoresUserClipboard();
    void desktopControls_emptyPointsToReadText();
    void desktopControls_invalidWindowErrorsCleanly();
    void desktopLaunch_emptyAppErrorsCleanly();
    void desktopLaunch_unknownAppFailsWithoutLaunching();
    void desktopBackground_refusesMouseAndKeyboardTools();
    void honeyHandoff_densifiesMasterAndSubPrompts();
    void webUrlGuard_blocksPrivateAndCredentials();
    void readableWebText_prefersArticleAndPreservesStructure();
    void webEscalation_requiresVerifiableEvidence();
    void browserNetworkEvidence_redactsAndGroups();
    void webFetch_forcedUnavailableProviderFailsDeterministically();
    void webFetch_camofoxProviderE2E();
    void webFetch_rateLimitsPerHost();
    void webSearch_usesConfiguredSearxngJsonApi();
    void webSearch_usesConfiguredPlumbSearchAndPrefersIt();
    void webSearch_localOnlyFailsClosedOnEmptyResults();
    void webSearch_localOnlyRequiresLoopbackEndpoint();
    void webSearch_localOnlyRejectsRedirects();
    void auxiliaryEndpoint_prefersValidSidecarAndFallsBack();

private:
    QVariantMap call(const QString &name, const QJsonObject &args);
    AgentToolRunner *m_runner = nullptr;
    QTemporaryDir m_dir;
};

void AgentToolsTests::init()
{
    m_runner = new AgentToolRunner;
    m_runner->setConfined(true);
}

void AgentToolsTests::cleanup()
{
    delete m_runner;
    m_runner = nullptr;
    QDir dir(m_dir.path());
    dir.removeRecursively();
    QDir().mkpath(m_dir.path());
}

void AgentToolsTests::auxiliaryEndpoint_prefersValidSidecarAndFallsBack()
{
    QCOMPARE(AgentToolRunner::auxiliaryEndpointForTest(
                 QStringLiteral("http://127.0.0.1:8090/"),
                 QStringLiteral("http://127.0.0.1:8080/")),
             QStringLiteral("http://127.0.0.1:8090"));
    QCOMPARE(AgentToolRunner::auxiliaryEndpointForTest(
                 QString(), QStringLiteral("http://127.0.0.1:8080/")),
             QStringLiteral("http://127.0.0.1:8080"));
    QCOMPARE(AgentToolRunner::auxiliaryEndpointForTest(
                 QStringLiteral("not-a-url"), QStringLiteral("http://127.0.0.1:8080/")),
             QStringLiteral("http://127.0.0.1:8080"));
    QCOMPARE(AgentToolRunner::auxiliaryEndpointForTest(
                 QStringLiteral("file:///tmp/model"), QStringLiteral("http://127.0.0.1:8080")),
             QStringLiteral("http://127.0.0.1:8080"));
    QCOMPARE(AgentToolRunner::auxiliaryEndpointForTest(
                 QStringLiteral("https://rag.example.test/v1/"),
                 QStringLiteral("http://127.0.0.1:8080")),
             QStringLiteral("https://rag.example.test"));

    const QString stable = AgentToolRunner::embeddingCacheKeyForTest(
        QStringLiteral("http://127.0.0.1:8090"), QStringLiteral("embed-a"),
        QStringLiteral("same document"));
    QCOMPARE(stable, AgentToolRunner::embeddingCacheKeyForTest(
                         QStringLiteral("http://127.0.0.1:8090"), QStringLiteral("embed-a"),
                         QStringLiteral("same document")));
    QVERIFY(stable != AgentToolRunner::embeddingCacheKeyForTest(
                         QStringLiteral("http://127.0.0.1:8080"), QStringLiteral("embed-a"),
                         QStringLiteral("same document")));
    QVERIFY(stable != AgentToolRunner::embeddingCacheKeyForTest(
                         QStringLiteral("http://127.0.0.1:8090"), QStringLiteral("embed-b"),
                         QStringLiteral("same document")));
}

// Ejecuta una tool síncrona y devuelve el map de toolExecuted.
QVariantMap AgentToolsTests::call(const QString &name, const QJsonObject &args)
{
    QSignalSpy spy(m_runner, &AgentToolRunner::toolExecuted);
    const QString argsJson = QString::fromUtf8(QJsonDocument(args).toJson(QJsonDocument::Compact));
    m_runner->executeTool("c1", name, argsJson, m_dir.path());
    if (spy.isEmpty()) spy.wait(3000);
    if (spy.isEmpty()) return {};
    return spy.last().first().toMap();
}

void AgentToolsTests::writeReadEditCycle()
{
    QVariantMap w = call("write_file", {{"path", "sub/a.txt"}, {"content", "hello world"}});
    QVERIFY(w.value("ok").toBool());
    QVERIFY(w.value("isWrite").toBool());
    QVERIFY(QFile::exists(m_dir.filePath("sub/a.txt")));

    QVariantMap r = call("read_file", {{"path", "sub/a.txt"}});
    QVERIFY(r.value("ok").toBool());
    QVERIFY(r.value("result").toString().contains("hello world"));

    QVariantMap e = call("edit_file", {{"path", "sub/a.txt"},
                                       {"old_string", "world"}, {"new_string", "qt"}});
    QVERIFY(e.value("ok").toBool());
    QVERIFY(e.value("diff").toString().length() > 0);

    QVariantMap r2 = call("read_file", {{"path", "sub/a.txt"}});
    QVERIFY(r2.value("result").toString().contains("hello qt"));
}

void AgentToolsTests::hashGuard_rejectsStaleEditAndAcceptsFreshHash()
{
    QVERIFY(call("write_file", {{"path", "shared.txt"}, {"content", "before\n"}})
                .value("ok").toBool());
    const QVariantMap read = call("read_file", {{"path", "shared.txt"}});
    QVERIFY(read.value("ok").toBool());
    const QString originalHash = read.value("sha256").toString();
    QCOMPARE(originalHash.size(), 64);
    QVERIFY(read.value("result").toString().startsWith(QStringLiteral("[archivo sha256=")));

    QFile changed(m_dir.filePath("shared.txt"));
    QVERIFY(changed.open(QIODevice::WriteOnly | QIODevice::Truncate));
    changed.write("other-session\n");
    changed.close();

    const QVariantMap stale = call("edit_file", {{"path", "shared.txt"},
        {"old_string", "other-session"}, {"new_string", "edited"},
        {"expected_sha256", originalHash}});
    QVERIFY(!stale.value("ok").toBool());
    QVERIFY(stale.value("result").toString().contains(QStringLiteral("conflicto hash")));
    QFile staleFile(m_dir.filePath("shared.txt"));
    QVERIFY(staleFile.open(QIODevice::ReadOnly));
    QCOMPARE(QString::fromUtf8(staleFile.readAll()), QStringLiteral("other-session\n"));

    const QVariantMap fresh = call("read_file", {{"path", "shared.txt"}});
    QVERIFY(fresh.value("ok").toBool());
    const QVariantMap accepted = call("edit_file", {{"path", "shared.txt"},
        {"old_string", "other-session"}, {"new_string", "edited"},
        {"expected_sha256", fresh.value("sha256").toString()}});
    QVERIFY(accepted.value("ok").toBool());
    QFile finalFile(m_dir.filePath("shared.txt"));
    QVERIFY(finalFile.open(QIODevice::ReadOnly));
    QCOMPARE(QString::fromUtf8(finalFile.readAll()), QStringLiteral("edited\n"));
}

void AgentToolsTests::hashGuard_coversFullFileBeyondReadView()
{
    const QByteArray content(4 * 1024 * 1024 + 123, 'x');
    QVERIFY(call("write_file", {{"path", "large-shared.txt"},
                                 {"content", QString::fromLatin1(content)}})
                .value("ok").toBool());
    const QVariantMap read = call("read_file", {{"path", "large-shared.txt"}});
    QVERIFY(read.value("ok").toBool());
    const QString expected = QString::fromLatin1(
        QCryptographicHash::hash(content, QCryptographicHash::Sha256).toHex());
    QCOMPARE(read.value("sha256").toString(), expected);

    const QVariantMap edited = call("edit_file", {{"path", "large-shared.txt"},
        {"old_string", "xxx"}, {"new_string", "yyy"},
        {"replace_all", true},
        {"expected_sha256", expected}});
    QVERIFY(edited.value("ok").toBool());
}

void AgentToolsTests::writeFile_trimsModelPathWhitespace()
{
    const QVariantMap w = call("write_file", {{"path", "\nsolution.py\n"},
                                                {"content", "def answer():\n    return 42\n"}});
    QVERIFY2(w.value("ok").toBool(), qPrintable(w.value("result").toString()));
    QVERIFY(QFile::exists(m_dir.filePath("solution.py")));
    QVERIFY(!QFile::exists(m_dir.filePath("\nsolution.py\n")));
    QCOMPARE(w.value("relPath").toString(), QStringLiteral("solution.py"));
}

void AgentToolsTests::readAndList_trimsModelPathWhitespace()
{
    QVariantMap w = call("write_file", {{"path", "solution.py"},
                                          {"content", "answer = 42\n"}});
    QVERIFY2(w.value("ok").toBool(), qPrintable(w.value("result").toString()));

    const QVariantMap read = call("read_file", {{"path", "\nsolution.py\n"}});
    QVERIFY2(read.value("ok").toBool(), qPrintable(read.value("result").toString()));
    QVERIFY(read.value("result").toString().contains("answer = 42"));

    const QVariantMap list = call("list_dir", {{"path", "\n.\n"}});
    QVERIFY2(list.value("ok").toBool(), qPrintable(list.value("result").toString()));
    QVERIFY(list.value("result").toString().contains("solution.py"));
}

void AgentToolsTests::readFile_compactViewAndSafeFallback()
{
    QVariantMap w = call("write_file", {{"path", "compact.cpp"},
        {"content", "int  add ( int a, int b ) {\n    return a + b;\n}\n"}});
    QVERIFY(w.value("ok").toBool());
    const QVariantMap compact = call("read_file", {{"path", "compact.cpp"}, {"compact", true}});
    QVERIFY(compact.value("ok").toBool());
    QVERIFY(compact.value("structuredSource").toBool());
    QVERIFY(compact.value("reductionPct").toDouble() > 0.0);
    QVERIFY(compact.value("result").toString().contains("vista compacta segura"));

    w = call("write_file", {{"path", "exact.py"}, {"content", "def x():\n    return 1\n"}});
    QVERIFY(w.value("ok").toBool());
    const QVariantMap exact = call("read_file", {{"path", "exact.py"}, {"compact", true}});
    QVERIFY(exact.value("ok").toBool());
    QVERIFY(!exact.value("structuredSource").toBool());
    QVERIFY(exact.value("structuredSourceFallback").toString().contains("indentacion"));
    QVERIFY(exact.value("result").toString().contains("    return 1"));
}

void AgentToolsTests::projectBrain_persistsWorkspaceIndex()
{
    QVERIFY(call("write_file", {{"path", "src/main.cpp"}, {"content", "int main(){}\n"}})
                .value("ok").toBool());
    QVERIFY(call("write_file", {{"path", "README.md"}, {"content", "# Test\n"}})
                .value("ok").toBool());

    const QVariantMap result = call("project_brain", {{"max_files", 100}});
    QVERIFY(result.value("ok").toBool());
    const QJsonObject brain = QJsonDocument::fromJson(
        result.value("result").toString().toUtf8()).object();
    QCOMPARE(brain.value("schemaVersion").toInt(), 2);
    QCOMPARE(brain.value("root").toString(), QDir(m_dir.path()).absolutePath());
    QVERIFY(brain.value("fileCount").toInt() >= 2);
    QVERIFY(brain.value("extensions").toObject().value("cpp").toInt() >= 1);

    const QVariantMap second = call("project_brain", {{"max_files", 100}});
    const QJsonObject refreshed = QJsonDocument::fromJson(
        second.value("result").toString().toUtf8()).object();
    QVERIFY(refreshed.value("changes").toObject().value("reused").toInt() >= 2);
    QCOMPARE(refreshed.value("changes").toObject().value("updated").toInt(), 0);

    QVERIFY(call("write_file", {{"path", "src/main.cpp"},
                                {"content", "int main(){return 0;}\n"}}).value("ok").toBool());
    const QVariantMap third = call("project_brain", {{"max_files", 100}});
    const QJsonObject changed = QJsonDocument::fromJson(
        third.value("result").toString().toUtf8()).object();
    QCOMPARE(changed.value("scanMode").toString(), QStringLiteral("events"));
    QVERIFY(changed.value("changes").toObject().value("updated").toInt() >= 1);
}

void AgentToolsTests::confinement_blocksOutsideCwd()
{
    QVariantMap w = call("write_file", {{"path", "../escape.txt"}, {"content", "x"}});
    QVERIFY(!w.value("ok").toBool());
    QVERIFY(w.value("result").toString().contains("fuera del proyecto"));
    QVERIFY(!QFile::exists(QDir(m_dir.path()).filePath("../escape.txt")));
}

void AgentToolsTests::allowedRoots_permitExtraFolder()
{
    // Una carpeta extra autorizada (scope "folder" de una Task) permite escribir
    // ahí con ruta absoluta; otra ruta fuera de cwd y de los roots sigue bloqueada.
    QTemporaryDir extra;
    QVERIFY(extra.isValid());
    m_runner->setConfined(true);
    m_runner->setAllowedRoots({extra.path()});

    const QString okPath = QDir(extra.path()).filePath("out.txt");
    QVariantMap w = call("write_file", {{"path", okPath}, {"content", "dolar"}});
    QVERIFY(w.value("ok").toBool());
    QVERIFY(QFile::exists(okPath));

    QVariantMap blocked = call("write_file", {{"path", "../escape.txt"}, {"content", "x"}});
    QVERIFY(!blocked.value("ok").toBool());
    QVERIFY(blocked.value("result").toString().contains("fuera del proyecto"));

    m_runner->setAllowedRoots({});   // limpiar para no afectar otros tests
}

void AgentToolsTests::unconfined_permitsAnyPath()
{
    // Scope "full" (toda la PC): sin confinamiento, cualquier ruta válida pasa.
    QTemporaryDir other;
    QVERIFY(other.isValid());
    m_runner->setConfined(false);
    const QString p = QDir(other.path()).filePath("anywhere.txt");
    QVariantMap w = call("write_file", {{"path", p}, {"content", "ok"}});
    QVERIFY(w.value("ok").toBool());
    QVERIFY(QFile::exists(p));
    m_runner->setConfined(true);
}

void AgentToolsTests::editFile_missingFails()
{
    QVariantMap e = call("edit_file", {{"path", "nope.txt"},
                                       {"old_string", "a"}, {"new_string", "b"}});
    QVERIFY(!e.value("ok").toBool());
    QVERIFY(e.value("result").toString().contains("no existe"));
}

void AgentToolsTests::editFile_whitespaceNearMissExplains()
{
    call("write_file", {{"path", "indent.txt"}, {"content", "if (ok) {\n    return 1;\n}\n"}});
    QVariantMap e = call("edit_file", {{"path", "indent.txt"},
                                       {"old_string", "if (ok) { return 1; }"},
                                       {"new_string", "return 2;"}});
    QVERIFY(!e.value("ok").toBool());
    const QString result = e.value("result").toString();
    QVERIFY(result.contains("ignoran espacios") || result.contains("indentación"));
}

void AgentToolsTests::parseErrorExplainsChunking()
{
    QVariantMap e = call("write_file", {{"_parse_error", "unterminated string"},
                                        {"_raw_chars", 120000}});
    QVERIFY(!e.value("ok").toBool());
    const QString result = e.value("result").toString();
    QVERIFY(result.contains("tool_call demasiado grande"));
    QVERIFY(result.contains("heredocs"));
}

void AgentToolsTests::grep_findsMatch()
{
    call("write_file", {{"path", "code.txt"}, {"content", "alpha\nNEEDLE here\nomega"}});
    QVariantMap g = call("grep", {{"pattern", "NEEDLE"}});
    QVERIFY(g.value("result").toString().contains("NEEDLE") ||
            g.value("result").toString().contains("code.txt"));
}

void AgentToolsTests::glob_listsFiles()
{
    call("write_file", {{"path", "one.cpp"}, {"content", "1"}});
    call("write_file", {{"path", "two.cpp"}, {"content", "2"}});
    QVariantMap g = call("glob", {{"pattern", "*.cpp"}});
    QVERIFY(g.value("result").toString().contains("one.cpp"));
    QVERIFY(g.value("result").toString().contains("two.cpp"));
}

void AgentToolsTests::readOnly_blocksMutationButAllowsRead()
{
    const QVariantMap seed = call("write_file", {{"path", "inspect.txt"},
                                                  {"content", "before"}});
    QVERIFY(seed.value("ok").toBool());
    m_runner->setReadOnly(true);
    const QVariantMap read = call("read_file", {{"path", "inspect.txt"}});
    QVERIFY(read.value("ok").toBool());
    QVERIFY(read.value("result").toString().contains(QStringLiteral("before")));
    const QVariantMap write = call("write_file", {{"path", "inspect.txt"},
                                                   {"content", "after"}});
    QVERIFY(!write.value("ok").toBool());
    QVERIFY(write.value("result").toString().contains(QStringLiteral("solo lectura")));
    QFile file(m_dir.filePath("inspect.txt"));
    QVERIFY(file.open(QIODevice::ReadOnly));
    QCOMPARE(QString::fromUtf8(file.readAll()), QStringLiteral("before"));
}

void AgentToolsTests::reviewOverengineering_isReadOnlyAndExplainsCandidates()
{
    auto git = [this](const QStringList &args) {
        QProcess p;
        p.setWorkingDirectory(m_dir.path());
        p.start(QStringLiteral("git"), args);
        const bool finished = p.waitForFinished(10000);
        return finished && p.exitStatus() == QProcess::NormalExit && p.exitCode() == 0;
    };
    QVERIFY(git({QStringLiteral("init"), QStringLiteral("-q")}));
    QVERIFY(git({QStringLiteral("config"), QStringLiteral("user.email"),
                 QStringLiteral("test@example.invalid")}));
    QVERIFY(git({QStringLiteral("config"), QStringLiteral("user.name"),
                 QStringLiteral("LlamaCode Test")}));
    QFile fixture(m_dir.filePath("review.cpp"));
    QVERIFY(fixture.open(QIODevice::WriteOnly | QIODevice::Truncate));
    fixture.write("int answer() { return 1; }\n");
    fixture.close();
    QVERIFY(git({QStringLiteral("add"), QStringLiteral("review.cpp")}));
    QVERIFY(git({QStringLiteral("commit"), QStringLiteral("-qm"), QStringLiteral("fixture")}));
    fixture.open(QIODevice::WriteOnly | QIODevice::Append);
    fixture.write("// TODO future generic adapter configurable registry\n");
    fixture.close();

    const QVariantMap result = call("review_overengineering", {});
    QVERIFY2(result.value("ok").toBool(), qPrintable(result.value("result").toString()));
    const QJsonObject report = QJsonDocument::fromJson(result.value("result").toString().toUtf8()).object();
    QVERIFY(report.value("readOnly").toBool());
    QVERIFY(report.value("metrics").toObject().value("filesChanged").toInt() >= 1);
    QVERIFY(report.value("metrics").toObject().value("addedLines").toInt() >= 1);
    QVERIFY(report.value("deleteList").toArray().size() >= 1);
    QFile unchanged(m_dir.filePath("review.cpp"));
    QVERIFY(unchanged.open(QIODevice::ReadOnly));
    QVERIFY(QString::fromUtf8(unchanged.readAll()).contains(QStringLiteral("future generic adapter")));
}

void AgentToolsTests::reviewOverengineering_handlesEmptyStagedAndUntracked()
{
    auto git = [this](const QStringList &args) {
        QProcess p;
        p.setWorkingDirectory(m_dir.path());
        p.start(QStringLiteral("git"), args);
        return p.waitForFinished(10000) && p.exitStatus() == QProcess::NormalExit
            && p.exitCode() == 0;
    };
    QVERIFY(git({QStringLiteral("init"), QStringLiteral("-q")}));
    QVERIFY(git({QStringLiteral("config"), QStringLiteral("user.email"), QStringLiteral("test@example.invalid")}));
    QVERIFY(git({QStringLiteral("config"), QStringLiteral("user.name"), QStringLiteral("LlamaCode Test")}));
    QFile fixture(m_dir.filePath("staged.txt"));
    QVERIFY(fixture.open(QIODevice::WriteOnly));
    fixture.write("base\n");
    fixture.close();
    QVERIFY(git({QStringLiteral("add"), QStringLiteral("staged.txt")}));
    QVERIFY(git({QStringLiteral("commit"), QStringLiteral("-qm"), QStringLiteral("fixture")}));

    QVariantMap empty = call("review_overengineering", {});
    QVERIFY2(empty.value("ok").toBool(), qPrintable(empty.value("result").toString()));
    const QJsonObject emptyReport = QJsonDocument::fromJson(empty.value("result").toString().toUtf8()).object();
    QCOMPARE(emptyReport.value("metrics").toObject().value("filesChanged").toInt(), 0);
    QCOMPARE(emptyReport.value("metrics").toObject().value("addedLines").toInt(), 0);

    fixture.open(QIODevice::WriteOnly | QIODevice::Append);
    fixture.write("TODO staged\n");
    fixture.close();
    QVERIFY(git({QStringLiteral("add"), QStringLiteral("staged.txt")}));
    QVariantMap staged = call("review_overengineering", {{"scope", "staged"}});
    QVERIFY(staged.value("ok").toBool());
    const QJsonObject stagedReport = QJsonDocument::fromJson(staged.value("result").toString().toUtf8()).object();
    QCOMPARE(stagedReport.value("scope").toString(), QStringLiteral("staged"));
    QVERIFY(stagedReport.value("deleteList").toArray().size() >= 1);

    QFile untracked(m_dir.filePath("untracked.txt"));
    QVERIFY(untracked.open(QIODevice::WriteOnly));
    untracked.write("not staged\n");
    untracked.close();
    QVariantMap working = call("review_overengineering", {});
    QVERIFY(working.value("ok").toBool());
    const QJsonObject workingReport = QJsonDocument::fromJson(working.value("result").toString().toUtf8()).object();
    QVERIFY(workingReport.value("metrics").toObject().value("workingTreeDirty").toBool());
    QVERIFY(workingReport.value("metrics").toObject().value("untrackedPresent").toBool());
}

void AgentToolsTests::reviewOverengineering_rejectsInvalidScopeAndTruncates()
{
    auto git = [this](const QStringList &args) {
        QProcess p;
        p.setWorkingDirectory(m_dir.path());
        p.start(QStringLiteral("git"), args);
        return p.waitForFinished(10000) && p.exitStatus() == QProcess::NormalExit
            && p.exitCode() == 0;
    };
    QVERIFY(git({QStringLiteral("init"), QStringLiteral("-q")}));
    QVERIFY(git({QStringLiteral("config"), QStringLiteral("user.email"), QStringLiteral("test@example.invalid")}));
    QVERIFY(git({QStringLiteral("config"), QStringLiteral("user.name"), QStringLiteral("LlamaCode Test")}));
    QFile fixture(m_dir.filePath("large.txt"));
    QVERIFY(fixture.open(QIODevice::WriteOnly));
    fixture.write("base\n");
    fixture.close();
    QVERIFY(git({QStringLiteral("add"), QStringLiteral("large.txt")}));
    QVERIFY(git({QStringLiteral("commit"), QStringLiteral("-qm"), QStringLiteral("fixture")}));
    fixture.open(QIODevice::WriteOnly | QIODevice::Append);
    fixture.write(QByteArray(5000, 'x'));
    fixture.write("\n");
    fixture.close();

    const QVariantMap invalid = call("review_overengineering", {{"scope", "nope"}});
    QVERIFY(!invalid.value("ok").toBool());
    QVERIFY(invalid.value("result").toString().contains(QStringLiteral("scope inválido")));

    const QVariantMap truncated = call("review_overengineering", {{"max_diff_chars", 1000}});
    QVERIFY(truncated.value("ok").toBool());
    const QJsonObject report = QJsonDocument::fromJson(truncated.value("result").toString().toUtf8()).object();
    QVERIFY(report.value("metrics").toObject().value("truncated").toBool());
    QVERIFY(report.value("metrics").toObject().value("diffChars").toInt() <= 1000);
}

void AgentToolsTests::reviewOverengineering_withoutRepoExplainsRequirement()
{
    const QVariantMap result = call("review_overengineering", {});
    QVERIFY(!result.value("ok").toBool());
    QVERIFY(result.value("result").toString().contains(QStringLiteral("no se pudo leer el diff git")));
}

void AgentToolsTests::runShell_echo()
{
    QSignalSpy spy(m_runner, &AgentToolRunner::toolExecuted);
    m_runner->executeTool("sh1", "run_shell",
                          R"({"command":"echo hola_test","timeout_s":30})", m_dir.path());
    QVERIFY(spy.wait(15000));
    const QVariantMap out = spy.last().first().toMap();
    QVERIFY(out.value("result").toString().contains("hola_test"));
}

// hybrid_search sin server: cae a BM25 puro, pero igual debe empaquetar por
// token_budget y expandir el dep-graph (vecino vía #include). util.h es el vecino
// que main.cpp incluye y que NO contiene el término buscado.
void AgentToolsTests::hybridSearch_depGraphAndBudget()
{
    call("write_file", {{"path", "util.h"},
                        {"content", "int helper_widget_count();\n"}});
    call("write_file", {{"path", "main.cpp"},
                        {"content", "#include \"util.h\"\n"
                                    "// WIDGETKEY marker for retrieval\n"
                                    "int main(){ return helper_widget_count(); }\n"}});

    // budget chico → solo el chunk top (main.cpp); util.h queda fuera del
    // resultado y debe emerger como vecino del dep-graph.
    QVariantMap h = call("hybrid_search", {{"query", "WIDGETKEY"},
                                           {"token_budget", 25},
                                           {"expand_graph", true}});
    QVERIFY(h.value("ok").toBool());
    const QString res = h.value("result").toString();
    QVERIFY(res.contains("main.cpp"));            // hit BM25
    QVERIFY(res.contains("~"));                   // header con ~N tok (budget activo)
    QVERIFY(res.contains("dep-graph"));           // footer de vecinos
    QVERIFY(res.contains("util.h"));              // vecino vía #include
}

// compact=true (estilo FastContext): devuelve la cita span 'rel:Lini-Lfin' + un
// preview de 1 línea, SIN volcar el cuerpo del chunk. Provenance precisa, barato.
void AgentToolsTests::hybridSearch_compactReturnsSpans()
{
    call("write_file", {{"path", "blob.cpp"},
                        {"content", "// line one\n"
                                    "// line two\n"
                                    "int FASTCTX_marker = 42;\n"
                                    "// SECRETBODY should not be dumped\n"}});

    QVariantMap h = call("hybrid_search", {{"query", "FASTCTX_marker"},
                                           {"compact", true},
                                           {"expand_graph", false}});
    QVERIFY(h.value("ok").toBool());
    const QString res = h.value("result").toString();
    QVERIFY(res.contains("blob.cpp:1-"));         // cita span 'rel:Lini-Lfin'
    QVERIFY(!res.contains("SECRETBODY"));         // cuerpo NO volcado (sólo preview 1ª línea)
    QVERIFY(!res.contains("──────"));             // sin separador de bloques de cuerpo
}

// include_docs suma documentos (pdf/office/epub/html) al MISMO índice híbrido, no
// sólo código. Sin el flag, un .html se sigue indexando como texto plano (no se
// pierde nada); con el flag pasa por el extractor y el header reporta el corpus de
// docs — incluidos los que NO se pudieron extraer, para que el agente sepa que hay
// fuentes afuera. Acá no hay markitdown ni Python garantizados: lo que se fija es
// el contrato de reporte y la no-regresión del path de texto.
void AgentToolsTests::hybridSearch_includeDocsReportsCorpus()
{
    call("write_file", {{"path", "manual.html"},
                        {"content", "<html><body>DOCSCORPUS_MARKER estructuracion</body></html>\n"}});
    call("write_file", {{"path", "code.cpp"},
                        {"content", "// DOCSCORPUS_MARKER en codigo\n"}});

    // Sin el flag: el .html cuenta como texto plano y no hay nota de docs.
    const QVariantMap plain = call("hybrid_search", {{"query", "DOCSCORPUS_MARKER"},
                                                     {"expand_graph", false}});
    QVERIFY(plain.value("ok").toBool());
    const QString plainRes = plain.value("result").toString();
    QVERIFY(plainRes.contains("manual.html"));
    QVERIFY(!plainRes.contains("docs"));

    // Con el flag: el header reporta el corpus de documentos (indexados y fallidos).
    const QVariantMap docs = call("hybrid_search", {{"query", "DOCSCORPUS_MARKER"},
                                                    {"include_docs", true},
                                                    {"expand_graph", false}});
    QVERIFY(docs.value("ok").toBool());
    const QString docsRes = docs.value("result").toString();
    QVERIFY(docsRes.contains(QRegularExpression(QStringLiteral("\\d+ docs"))));
    QVERIFY(docsRes.contains("code.cpp"));   // el path de código sigue vivo
}

void AgentToolsTests::repoSlice_defaultsToCompactEvidence()
{
    call("write_file", {{"path", "auth.cpp"},
                        {"content", "// first preview REPOSLICE_MARKER\n"
                                    "void authenticate_user() {}\n"
                                    "// BODY_MUST_STAY_OUT\n"}});

    const QVariantMap hit = call("repo_slice", {{"query", "REPOSLICE_MARKER"},
                                                 {"expand_graph", false}});
    QVERIFY(hit.value("ok").toBool());
    const QString result = hit.value("result").toString();
    QVERIFY(result.contains("repo_slice"));
    QVERIFY(result.contains(QRegularExpression(QStringLiteral("auth\\.cpp:\\d+-\\d+"))));
    QVERIFY(result.contains("REPOSLICE_MARKER"));
    QVERIFY(!result.contains("BODY_MUST_STAY_OUT"));
    QVERIFY(!result.contains("──────"));
}

void AgentToolsTests::contextScoutAndFetch_validateHandle()
{
    call("write_file", { {"path", "context.cpp"},
                          {"content", "// CONTEXT_TOOL_MARKER\nint context_value = 42;\n"} });
    const QVariantMap scout = call("context_scout", {{"query", "CONTEXT_TOOL_MARKER"},
                                                       {"token_budget", 300}});
    QVERIFY(scout.value("ok").toBool());
    const QVariantMap receipt = scout.value("receipt").toMap();
    QVERIFY(!receipt.value("returned").toList().isEmpty());
    const QString handle = receipt.value("returned").toList().first().toMap()
                               .value("handle").toString();
    QVERIFY(handle.startsWith("ctx:"));
    const QVariantMap fetched = call("context_fetch", {{"handle", handle}});
    QVERIFY(fetched.value("ok").toBool());
    QVERIFY(fetched.value("result").toString().contains("CONTEXT_TOOL_MARKER"));
}

void AgentToolsTests::contextStatus_reportsPersistentIndex()
{
    call("write_file", {{"path", "status.cpp"}, {"content", "int status_value;\n"}});
    const QVariantMap status = call("context_status", {});
    QVERIFY(status.value("ok").toBool());
    QVERIFY(status.value("result").toString().contains("files"));
    QVERIFY(status.value("result").toString().contains("chunks"));
}

void AgentToolsTests::workStatus_reportsOtherSessions()
{
    const QString claim = WorkRegistry::acquire(
        m_dir.path(), QStringLiteral("S2"), QStringLiteral("agent-b"),
        QStringLiteral("revisar el módulo compartido"), {QStringLiteral("src/shared.cpp")});
    QVERIFY(!claim.isEmpty());
    m_runner->setSessionId(QStringLiteral("S1"));
    const QVariantMap status = call("work_status", {});
    QVERIFY(status.value("ok").toBool());
    QVERIFY(status.value("result").toString().contains(QStringLiteral("módulo compartido")));
    QVERIFY(status.value("result").toString().contains(QStringLiteral("src/shared.cpp")));
}

void AgentToolsTests::mutationGuard_detectsOpaqueShellAndDeclaredPaths()
{
    QVERIFY(!AgentLifecycle::shellCommandMayMutate(QStringLiteral("git status --short")));
    QVERIFY(!AgentLifecycle::shellCommandMayMutate(QStringLiteral("cmake --build build/Debug")));
    QVERIFY(AgentLifecycle::shellCommandMayMutate(QStringLiteral("echo hi > generated.txt")));
    QVERIFY(AgentLifecycle::shellCommandMayMutate(QStringLiteral("git apply change.patch")));
    QVERIFY(AgentLifecycle::shellCommandMayMutate(QStringLiteral("Set-Content out.txt hi")));

    const QJsonObject input{
        {QStringLiteral("arguments"), QJsonObject{
            {QStringLiteral("command"), QStringLiteral("echo hi > generated.txt")},
            {QStringLiteral("changed_paths"), QJsonArray{QStringLiteral("generated.txt")}}}}};
    QCOMPARE(AgentLifecycle::changedPathsFromToolInput(QStringLiteral("mcp_call_tool"), input),
             QStringList{QStringLiteral("generated.txt")});
}

void AgentToolsTests::graphPacketAndDoctor_areExposedByTool()
{
    const QVariantMap entity = call("graph", {{"action", "add_entity"},
                                                {"name", "Store"},
                                                {"etype", "module"}});
    QVERIFY2(entity.value("ok").toBool(), qPrintable(entity.value("result").toString()));
    const QVariantMap link = call("graph", {{"action", "link"},
                                              {"subj", "Store"},
                                              {"pred", "requires"},
                                              {"obj", "Config"}});
    QVERIFY2(link.value("ok").toBool(), qPrintable(link.value("result").toString()));

    const QVariantMap packet = call("graph", {{"action", "query"},
                                                {"name", "Store"},
                                                {"format", "packet"},
                                                {"depth", 1}});
    QVERIFY(packet.value("ok").toBool());
    const QJsonObject packetJson = QJsonDocument::fromJson(
        packet.value("result").toString().toUtf8()).object();
    QVERIFY(packetJson.value("ok").toBool());
    QVERIFY(packetJson.value("edges").toArray().size() >= 1);
    QVERIFY(packetJson.value("receipt").toObject().contains(QStringLiteral("schemaVersion")));

    const QVariantMap doctor = call("graph", {{"action", "doctor"}});
    QVERIFY(doctor.value("ok").toBool());
    const QJsonObject doctorJson = QJsonDocument::fromJson(
        doctor.value("result").toString().toUtf8()).object();
    QVERIFY(doctorJson.value("healthy").toBool());
}

void AgentToolsTests::recentActions_tailsEventLogForSession()
{
    // Sembrar el event-log del cwd con eventos de DOS sesiones. recent_actions con
    // la sesión "S1" debe traer sólo lo de S1 (filtrado por sessionId del runner).
    AgentEventLog::append(m_dir.path(), QStringLiteral("S1"), QStringLiteral("tool_call"),
                          {{QStringLiteral("tool"), QStringLiteral("read_file")}});
    AgentEventLog::append(m_dir.path(), QStringLiteral("S2"), QStringLiteral("tool_call"),
                          {{QStringLiteral("tool"), QStringLiteral("OTRA_SESION")}});
    AgentEventLog::append(m_dir.path(), QStringLiteral("S1"), QStringLiteral("failure"),
                          {{QStringLiteral("tool"), QStringLiteral("run_shell")},
                           {QStringLiteral("ok"), false},
                           {QStringLiteral("reason"), QStringLiteral("anti_loop")}});

    m_runner->setSessionId(QStringLiteral("S1"));
    QVariantMap r = call("recent_actions", {{"count", 10}});
    QVERIFY(r.value("ok").toBool());
    const QString out = r.value("result").toString();
    QVERIFY(out.contains(QStringLiteral("read_file")));
    QVERIFY(out.contains(QStringLiteral("run_shell")));
    QVERIFY(out.contains(QStringLiteral("FALLO")));        // el evento failure se marca
    QVERIFY(out.contains(QStringLiteral("anti_loop")));    // reason arrastrado
    QVERIFY(!out.contains(QStringLiteral("OTRA_SESION"))); // S2 filtrada

    // Sesión sin eventos → mensaje claro, ok igual (no es un error de tool).
    m_runner->setSessionId(QStringLiteral("VACIA"));
    QVariantMap empty = call("recent_actions", {});
    QVERIFY(empty.value("ok").toBool());
    QVERIFY(empty.value("result").toString().contains(QStringLiteral("sin eventos")));
}

// Las tools nuevas de computer use validan alcance, coordenadas y modificadores
// ANTES de mandar input: estos casos no deben mover el mouse ni hacer clics.
void AgentToolsTests::desktopNewTools_validateBeforeTouchingTheDesktop()
{
    QVariantMap r = call("desktop_read_text",
                         {{"scope_kind", "window"}, {"target_id", "zzznothex"}});
    QVERIFY(!r.value("ok").toBool());
    QVERIFY(r.value("result").toString().startsWith(QStringLiteral("[desktop_read_text:")));
    // Ventana cerrada (sin scope_kind cae a "screen"): el mensaje dice que ya no
    // existe, no "no existe screen con id" (eso confundia al modelo).
    QVariantMap gone = call("desktop_read_text", {{"target_id", "2e60394"}});
    QVERIFY(!gone.value("ok").toBool());
    QVERIFY2(gone.value("result").toString().contains(QStringLiteral("ya se cerr")),
             qPrintable(gone.value("result").toString()));

    QVariantMap h = call("desktop_hover",
                         {{"scope_kind", "screen"}, {"target_id", "0"}, {"x", 1.7}, {"y", 0.5}});
    QVERIFY(!h.value("ok").toBool());
    QVERIFY(h.value("result").toString().contains(QStringLiteral("normalizadas")));

    QVariantMap c = call("desktop_click",
                         {{"scope_kind", "window"}, {"target_id", "zzznothex"},
                          {"x", 0.5}, {"y", 0.5}, {"modifiers", QJsonArray{"HYPER"}}});
    QVERIFY(!c.value("ok").toBool());
    QVERIFY(c.value("result").toString().startsWith(QStringLiteral("[desktop_click:")));

    QVariantMap s = call("desktop_scroll",
                         {{"scope_kind", "window"}, {"target_id", "zzznothex"},
                          {"x", 0.5}, {"y", 0.5}, {"delta", -120}});
    QVERIFY(!s.value("ok").toBool());   // no hay alcance → ni hover ni rueda
    QVERIFY(s.value("result").toString().startsWith(QStringLiteral("[desktop_scroll:")));

    // Sin target_id y sin ninguna ventana elegida por el agente, NO se teclea
    // (antes escribía en la app que el usuario tuviera adelante).
    QVariantMap t = call("desktop_type", {{"text", "no debería escribirse"}});
    QVERIFY(!t.value("ok").toBool());
    QVERIFY(t.value("result").toString().contains(QStringLiteral("NO tecleé")));
    QVariantMap k = call("desktop_key", {{"key", "ENTER"}});
    QVERIFY(!k.value("ok").toBool());
    QVERIFY(k.value("result").toString().contains(QStringLiteral("NO tecleé")));

    QVariantMap bad = call("desktop_clipboard", {{"op", "borrar"}});
    QVERIFY(!bad.value("ok").toBool());
    QVERIFY(bad.value("result").toString().contains(QStringLiteral("op inválida")));
}

// Si una app no expone controles UIA (Calculadora de Win11 desde un agente, por
// ejemplo), el resultado sugiere leerla por OCR: los modelos chicos concluían
// "no puedo leerlo" en vez de usar desktop_read_text. Sólo lectura de UIA.
void AgentToolsTests::desktopControls_emptyPointsToReadText()
{
    const QVariantList wins = DesktopAutomationBackend::windows();
    if (wins.isEmpty()) QSKIP("sin ventanas visibles en esta sesión");
    const QString id = wins.first().toMap().value(QStringLiteral("id")).toString();
    QVariantMap c = call("desktop_controls",
                         {{"target_id", id}, {"query", "zzqqxx-ningun-control-se-llama-asi"}});
    QVERIFY(c.value("ok").toBool());
    const QString out = c.value("result").toString();
    QVERIFY(out.contains(QStringLiteral("0 controles")));
    QVERIFY(out.contains(QStringLiteral("desktop_read_text")));
    QVERIFY(out.contains(id));
}

// get/set del portapapeles real; se restaura lo que el usuario tenía copiado.
void AgentToolsTests::desktopClipboard_roundTripRestoresUserClipboard()
{
    QString before;
    QString err;
    if (!DesktopAutomationBackend::clipboardText(&before, &err))
        QSKIP(qPrintable(QStringLiteral("portapapeles no disponible: ") + err));
    const QString probe = QStringLiteral("LlamaCode ✓ portapapeles 123");
    QVariantMap set = call("desktop_clipboard", {{"op", "set"}, {"text", probe}});
    QVariantMap get = call("desktop_clipboard", {{"op", "get"}});
    DesktopAutomationBackend::setClipboardText(before, &err);   // restaurar siempre
    QVERIFY(set.value("ok").toBool());
    QVERIFY(get.value("ok").toBool());
    QVERIFY(get.value("result").toString().contains(probe));
}

void AgentToolsTests::desktopWindows_returnsStructuredInventory()
{
    // No depende de qué ventanas haya: el tool siempre resuelve ok y devuelve un
    // encabezado coherente (lista estructurada o aviso de "sin ventanas").
    QVariantMap r = call("desktop_windows", {});
    QVERIFY(r.value("ok").toBool());
    const QString out = r.value("result").toString();
    QVERIFY(out.contains(QStringLiteral("desktop_windows")));
    QVERIFY(out.contains(QStringLiteral("ventana")));
}

void AgentToolsTests::desktopControls_invalidWindowErrorsCleanly()
{
    // Sin una ventana real no podemos enumerar UIA de forma determinista, pero el
    // dispatch + validación de target SÍ: un id de ventana inválido falla limpio
    // (no crashea, no cuelga) por ambas tools del árbol de controles.
    QVariantMap c = call("desktop_controls", {{"target_id", "zzznothex"}});
    QVERIFY(!c.value("ok").toBool());
    QVERIFY(c.value("result").toString().contains(QStringLiteral("desktop_controls")));
    QVERIFY(c.value("result").toString().contains(QStringLiteral("no encontrada")));

    QVariantMap k = call("desktop_click_element",
                         {{"target_id", "zzznothex"}, {"control_id", "1.2.3"}});
    QVERIFY(!k.value("ok").toBool());
    QVERIFY(k.value("result").toString().startsWith(QStringLiteral("[desktop_click_element:")));

    // desktop_stroke: validar dispatch + parseo sin tocar el escritorio real. Un
    // punto fuera de 0..1 se rechaza antes de consultar la sesión o emitir input.
    // El arrastre real pertenece exclusivamente al probe manual qa_visual_automation.
    QJsonArray pts{QJsonObject{{"x", -0.1}, {"y", 0.1}},
                   QJsonObject{{"x", 0.5}, {"y", 0.5}}};
    QVariantMap s = call("desktop_stroke",
                         {{"target_id", "0"}, {"scope_kind", "screen"}, {"points", pts}});
    QVERIFY(!s.value("ok").toBool());
    QVERIFY(s.value("result").toString().startsWith(QStringLiteral("[desktop_stroke:")));
    QVERIFY(s.value("result").toString().contains(QStringLiteral("no se movió el mouse")));

    // desktop_wait_for: dispatch + timeout. Un título de ventana inexistente con
    // timeout corto → found:false, sin colgar, con prefijo [desktop_wait_for:.
    QVariantMap w = call("desktop_wait_for",
                         {{"window_title", "ventana-que-no-existe-zzz"}, {"timeout_ms", 200}});
    QVERIFY(!w.value("ok").toBool());
    QVERIFY(w.value("result").toString().startsWith(QStringLiteral("[desktop_wait_for:")));

    // desktop_assert: un texto inexistente con timeout corto → FAIL limpio, ok=false.
    QVariantMap a = call("desktop_assert",
                         {{"expect_text", "texto-que-no-existe-zzz"}, {"timeout_ms", 200}});
    QVERIFY(!a.value("ok").toBool());
    QVERIFY(a.value("result").toString().startsWith(QStringLiteral("[desktop_assert: FAIL")));

    // Tools visuales: una plantilla inexistente falla de manera determinista y
    // conserva el nombre de la tool para que el agente pueda autocorregirse.
    for (const QString &tool : {QStringLiteral("desktop_find_image"),
                                QStringLiteral("desktop_click_image"),
                                QStringLiteral("desktop_wait_image"),
                                QStringLiteral("desktop_assert_image")}) {
        const QVariantMap visual = call(tool, {{"target_id", "0"},
                                                {"scope_kind", "screen"},
                                                {"template_path", "Z:/missing-template.png"},
                                                {"timeout_ms", 0}});
        QVERIFY2(!visual.value("ok").toBool(), qPrintable(tool));
        QVERIFY(visual.value("result").toString().contains(tool));
    }
}

void AgentToolsTests::desktopBackground_refusesMouseAndKeyboardTools()
{
    // Modo "segundo plano": las tools que usan el mouse/teclado reales se
    // rechazan ANTES de tocar nada (no se teclea en la app que tengas adelante).
    for (const char *tool : {"desktop_type", "desktop_key", "desktop_click",
                             "desktop_focus", "desktop_scroll", "desktop_clipboard"}) {
        const QVariantMap r = call(tool, {{"_lc_background", true}, {"text", "x"},
                                          {"key", "ESC"}, {"target_id", "0"},
                                          {"x", 0.5}, {"y", 0.5}});
        QVERIFY2(!r.value("ok").toBool(), tool);
        QVERIFY2(r.value("result").toString().contains(QStringLiteral("segundo plano")),
                 qPrintable(r.value("result").toString()));
    }
    // Las de UI Automation siguen disponibles (acá fallan sólo por el id falso).
    const QVariantMap uia = call("desktop_controls", {{"_lc_background", true},
                                                      {"target_id", "zzznothex"}});
    QVERIFY(!uia.value("result").toString().contains(QStringLiteral("segundo plano")));
}

void AgentToolsTests::desktopLaunch_unknownAppFailsWithoutLaunching()
{
#ifdef Q_OS_WIN
    // Un nombre que Windows no resuelve se rechaza ANTES de `start`: si no, cmd
    // arranca igual, Windows abre su dialogo "no se encuentra" y el agente lo
    // tomaba por la app. Este nombre no existe: no se abre nada.
    QVariantMap r = call("desktop_launch", {{"app", "app-que-no-existe-lc-7f3a"}});
    QVERIFY(!r.value("ok").toBool());
    const QString text = r.value("result").toString();
    QVERIFY2(text.contains(QStringLiteral("No encontr")), qPrintable(text));
    QVERIFY(text.contains(QStringLiteral("'calc'")));
    QVariantMap path = call("desktop_launch", {{"app", "C:/no/existe/lc-7f3a.exe"}});
    QVERIFY(!path.value("ok").toBool());
    QVERIFY(path.value("result").toString().contains(QStringLiteral("No existe la ruta")));
#else
    QSKIP("validacion de nombres de start: solo Windows");
#endif
}

void AgentToolsTests::desktopLaunch_emptyAppErrorsCleanly()
{
    // No lanzamos una app real (abriría una ventana en la máquina de test): sólo el
    // path de error. app vacío → falla limpio, sin colgar ni abrir nada. El lanzado
    // real (detached) es QA manual, como el resto de la automatización de escritorio.
    QVariantMap r = call("desktop_launch", {{"app", "   "}});
    QVERIFY(!r.value("ok").toBool());
    QVERIFY(r.value("result").toString().startsWith(QStringLiteral("[desktop_launch:")));
}

// Handoffs densos (directiva honey): los helpers puros que arman el system prompt
// del maestro (ask_teacher) y del sub-agente cambian a formato denso clave:valor
// cuando honey está ON, y conservan el formato normal cuando está OFF. No cambian
// QUÉ se pide, sólo el formato → quality-neutral, ahorro de tokens en el handoff.
void AgentToolsTests::honeyHandoff_densifiesMasterAndSubPrompts()
{
    // Maestro OFF: prosa normal, sin pedir clave:valor.
    const QString mOff = AgentToolRunner::masterSystemPrompt(false);
    QVERIFY(mOff.contains(QStringLiteral("conciso")));
    QVERIFY(!mOff.contains(QStringLiteral("clave:valor")));
    // Maestro ON: pide formato denso clave:valor.
    const QString mOn = AgentToolRunner::masterSystemPrompt(true);
    QVERIFY(mOn.contains(QStringLiteral("clave:valor")));
    QVERIFY(mOn.contains(QStringLiteral("Sin prosa")));

    // Sub-agente: el cwd siempre aparece; honey suma la sección de frugalidad.
    const QString sOff = SubAgentRunner::systemPrompt(QStringLiteral("C:/ws"), false);
    QVERIFY(sOff.contains(QStringLiteral("C:/ws")));
    QVERIFY(!sOff.contains(QStringLiteral("FRUGALIDAD")));
    const QString sOn = SubAgentRunner::systemPrompt(QStringLiteral("C:/ws"), true);
    QVERIFY(sOn.contains(QStringLiteral("C:/ws")));
    QVERIFY(sOn.contains(QStringLiteral("FRUGALIDAD (honey)")));
    QVERIFY(sOn.contains(QStringLiteral("YAGNI")));
}

void AgentToolsTests::webUrlGuard_blocksPrivateAndCredentials()
{
    QString error;
    QVERIFY(!AgentToolRunner::isSafePublicWebUrl(QStringLiteral("http://127.0.0.1/admin"),
                                                  &error));
    QVERIFY(error.contains(QStringLiteral("no pública")));
    QVERIFY(!AgentToolRunner::isSafePublicWebUrl(
        QStringLiteral("http://169.254.169.254/latest/meta-data"), &error));
    QVERIFY(!AgentToolRunner::isSafePublicWebUrl(QStringLiteral("http://[::1]/"), &error));
    QVERIFY(!AgentToolRunner::isSafePublicWebUrl(
        QStringLiteral("http://[::ffff:127.0.0.1]/"), &error));
    QVERIFY(!AgentToolRunner::isSafePublicWebUrl(
        QStringLiteral("https://user:secret@example.com/"), &error));
    QVERIFY(error.contains(QStringLiteral("credenciales")));
    QVERIFY(!AgentToolRunner::isSafePublicWebUrl(QStringLiteral("file:///etc/passwd"), &error));
}

void AgentToolsTests::readableWebText_prefersArticleAndPreservesStructure()
{
    const QString html = QStringLiteral(
        "<html><body><nav>Menú secreto</nav><article><h1>Título &amp; prueba</h1>"
        "<p>Primer párrafo.</p><script>robar()</script><p>Segundo &#x1F999;</p>"
        "</article><footer>Publicidad</footer></body></html>");
    const QString text = AgentToolRunner::extractReadableWebText(html);
    QVERIFY(text.contains(QStringLiteral("Título & prueba")));
    QVERIFY(text.contains(QStringLiteral("Primer párrafo.")));
    QVERIFY(text.contains(QStringLiteral("Segundo")));
    QVERIFY(text.indexOf(QStringLiteral("Primer párrafo."))
            < text.indexOf(QStringLiteral("Segundo")));
    QVERIFY(text.contains(QString::fromUtf8("🦙")));
    QVERIFY(!text.contains(QStringLiteral("Menú secreto")));
    QVERIFY(!text.contains(QStringLiteral("robar")));
    QVERIFY(!text.contains(QStringLiteral("Publicidad")));
}

void AgentToolsTests::webEscalation_requiresVerifiableEvidence()
{
    QVERIFY(AgentToolRunner::webEscalationReasons(
                QStringLiteral("<article>Contenido documental suficientemente largo para "
                               "resolver una consulta normal sin navegador.</article>"),
                QString(400, QLatin1Char('x'))).isEmpty());

    const QStringList challenge = AgentToolRunner::webEscalationReasons(
        QStringLiteral("<title>Checking your browser</title><div>Cloudflare Ray ID</div>"),
        QStringLiteral("Checking your browser"));
    QVERIFY(challenge.contains(QStringLiteral("challenge")));
    QVERIFY(challenge.contains(QStringLiteral("thin_content")));

    const QStringList js = AgentToolRunner::webEscalationReasons(
        QStringLiteral("<div id=\"root\"></div><noscript>Please enable JavaScript</noscript>"),
        QString());
    QVERIFY(js.contains(QStringLiteral("javascript_required")));
    QVERIFY(js.contains(QStringLiteral("empty")));

    const QStringList transport = AgentToolRunner::webEscalationReasons(
        QString(), QString(), QStringLiteral("timeout"));
    QVERIFY(transport.contains(QStringLiteral("transport_error")));
}

void AgentToolsTests::browserNetworkEvidence_redactsAndGroups()
{
    const QString raw = QStringLiteral(
        "GET https://example.com/assets/app.js?token=SECRETO => [200] OK\n"
        "POST https://api.example.com/v1/jobs/123456?api_key=SECRETO => [201] Created\n"
        "POST https://api.example.com/v1/jobs/987654?api_key=OTRO => [202] Accepted\n"
        "GET https://api.example.com/v1/jobs/550e8400-e29b-41d4-a716-446655440000 "
        "=> [200] OK\n");
    const QString summary = AgentToolRunner::summarizeBrowserNetworkEvidence(raw);
    const QJsonObject root = QJsonDocument::fromJson(summary.toUtf8()).object();
    QCOMPARE(root.value("endpointCount").toInt(), 2);
    QCOMPARE(root.value("ignoredStatic").toInt(), 1);
    QVERIFY(!summary.contains("SECRETO"));
    QVERIFY(!summary.contains("OTRO"));
    QVERIFY(summary.contains("api_key"));
    QVERIFY(summary.contains("/v1/jobs/{id}"));
    QVERIFY(summary.contains("observed_order"));
    const QJsonObject privacy = root.value("privacy").toObject();
    QVERIFY(!privacy.value("queryValuesRetained").toBool());
    QVERIFY(privacy.value("queryParameterNamesRetained").toBool());
    QVERIFY(!privacy.value("headersRetained").toBool());
    QVERIFY(!privacy.value("bodiesRetained").toBool());
    QVERIFY(root.value("truncatedInput").isBool());
}

void AgentToolsTests::webFetch_forcedUnavailableProviderFailsDeterministically()
{
    // IP pública literal: supera la guarda sin DNS. Como Camofox no está
    // configurado, falla antes de hacer red y deja un diagnóstico accionable.
    const QVariantMap result = call(
        QStringLiteral("web_fetch"),
        QJsonObject{{QStringLiteral("url"), QStringLiteral("https://93.184.216.34/")},
                    {QStringLiteral("provider"), QStringLiteral("camofox")}});
    QVERIFY(!result.value(QStringLiteral("ok")).toBool());
    QVERIFY(result.value(QStringLiteral("result")).toString()
                .contains(QStringLiteral("Camofox no está configurado")));
}

void AgentToolsTests::webFetch_camofoxProviderE2E()
{
    CamofoxStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost));
    m_runner->setWebProviders({QVariantMap{
        {QStringLiteral("provider"), QStringLiteral("camofox")},
        {QStringLiteral("baseUrl"),
         QStringLiteral("http://127.0.0.1:%1").arg(server.serverPort())},
        {QStringLiteral("enabled"), true}}});
    QString error;
    const QString text = m_runner->fetchViaCamofox(
        QStringLiteral("https://93.184.216.34/"), &error);
    QVERIFY2(!text.isEmpty(), qPrintable(error));
    QVERIFY(text.contains(QStringLiteral("Contenido DOM renderizado")));
}

void AgentToolsTests::webFetch_rateLimitsPerHost()
{
    QString error;
    for (int i = 0; i < 30; ++i)
        QVERIFY(m_runner->consumeWebRateLimit(QStringLiteral("example.com"), 1000 + i,
                                             &error));
    QVERIFY(!m_runner->consumeWebRateLimit(QStringLiteral("example.com"), 2000, &error));
    QVERIFY(error.contains(QStringLiteral("rate limit")));
    QVERIFY(m_runner->consumeWebRateLimit(QStringLiteral("example.com"), 61031, &error));
}

void AgentToolsTests::webSearch_usesConfiguredSearxngJsonApi()
{
    SearxngStub server;
    QVERIFY(server.listen(QHostAddress::LocalHost));
    ScopedEnvironmentVariable restoreSearxngUrl(QByteArrayLiteral("LLAMACODE_SEARXNG_URL"));
    QVERIFY(qputenv("LLAMACODE_SEARXNG_URL",
                    QStringLiteral("http://127.0.0.1:%1").arg(server.serverPort()).toUtf8()));

    const QVariantMap result = call(
        QStringLiteral("web_search"),
        QJsonObject{{QStringLiteral("query"), QStringLiteral("C++ local search")},
                    {QStringLiteral("count"), 1}});

    QVERIFY(result.value(QStringLiteral("ok")).toBool());
    const QString text = result.value(QStringLiteral("result")).toString();
    QVERIFY(text.contains(QStringLiteral("Local result")));
    QVERIFY(text.contains(QStringLiteral("https://docs.example.test/search")));
    QVERIFY(text.contains(QStringLiteral("Fixture result content")));
    QCOMPARE(server.requests.size(), 1);

    const QString requestLine = server.requests.constFirst();
    const QStringList parts = requestLine.split(QLatin1Char(' '));
    QCOMPARE(parts.size(), 3);
    const QUrl requestUrl(QStringLiteral("http://127.0.0.1")
                          + parts.at(1));
    QCOMPARE(requestUrl.path(), QStringLiteral("/search"));
    const QUrlQuery query(requestUrl);
    QCOMPARE(query.queryItemValue(QStringLiteral("q")), QStringLiteral("C++ local search"));
    QCOMPARE(query.queryItemValue(QStringLiteral("format")), QStringLiteral("json"));
}

void AgentToolsTests::webSearch_usesConfiguredPlumbSearchAndPrefersIt()
{
    SearxngStub plumbServer(QByteArrayLiteral(
        "{\"results\":[{\"title\":\"Plumb result\","
        "\"url\":\"https://plumb.example.test/result\","
        "\"content\":\"Plumb fixture content\"}]}"));
    SearxngStub searxngServer(QByteArrayLiteral(
        "{\"results\":[{\"title\":\"SearXNG result\","
        "\"url\":\"https://searxng.example.test/result\","
        "\"content\":\"SearXNG fixture content\"}]}"));
    QVERIFY(plumbServer.listen(QHostAddress::LocalHost));
    QVERIFY(searxngServer.listen(QHostAddress::LocalHost));
    ScopedEnvironmentVariable restorePlumbUrl(QByteArrayLiteral("LLAMACODE_PLUMBSEARCH_URL"));
    ScopedEnvironmentVariable restoreSearxngUrl(QByteArrayLiteral("LLAMACODE_SEARXNG_URL"));
    ScopedEnvironmentVariable restoreMode(QByteArrayLiteral("LLAMACODE_WEB_SEARCH_MODE"));
    QVERIFY(qputenv("LLAMACODE_PLUMBSEARCH_URL",
                    QStringLiteral("http://127.0.0.1:%1").arg(plumbServer.serverPort()).toUtf8()));
    QVERIFY(qputenv("LLAMACODE_SEARXNG_URL",
                    QStringLiteral("http://127.0.0.1:%1").arg(searxngServer.serverPort()).toUtf8()));
    qunsetenv("LLAMACODE_WEB_SEARCH_MODE");

    const QVariantMap result = call(
        QStringLiteral("web_search"),
        QJsonObject{{QStringLiteral("query"), QStringLiteral("PlumbSearch provider test")},
                    {QStringLiteral("count"), 1}});

    QVERIFY(result.value(QStringLiteral("ok")).toBool());
    const QString text = result.value(QStringLiteral("result")).toString();
    QVERIFY(text.contains(QStringLiteral("Plumb result")));
    QVERIFY(!text.contains(QStringLiteral("SearXNG result")));
    QCOMPARE(plumbServer.requests.size(), 1);
    QVERIFY(searxngServer.requests.isEmpty());
    const QStringList parts = plumbServer.requests.constFirst().split(QLatin1Char(' '));
    QCOMPARE(parts.size(), 3);
    const QUrl requestUrl(QStringLiteral("http://127.0.0.1") + parts.at(1));
    QCOMPARE(requestUrl.path(), QStringLiteral("/search"));
    const QUrlQuery query(requestUrl);
    QCOMPARE(query.queryItemValue(QStringLiteral("q")),
             QStringLiteral("PlumbSearch provider test"));
    QCOMPARE(query.queryItemValue(QStringLiteral("format")), QStringLiteral("json"));
}

void AgentToolsTests::webSearch_localOnlyFailsClosedOnEmptyResults()
{
    SearxngStub server(QByteArrayLiteral("{\"results\":[]}"));
    QVERIFY(server.listen(QHostAddress::LocalHost));
    ScopedEnvironmentVariable restorePlumbUrl(QByteArrayLiteral("LLAMACODE_PLUMBSEARCH_URL"));
    ScopedEnvironmentVariable restoreSearxngUrl(QByteArrayLiteral("LLAMACODE_SEARXNG_URL"));
    ScopedEnvironmentVariable restoreMode(QByteArrayLiteral("LLAMACODE_WEB_SEARCH_MODE"));
    QVERIFY(qputenv("LLAMACODE_SEARXNG_URL",
                    QStringLiteral("http://127.0.0.1:%1").arg(server.serverPort()).toUtf8()));
    qunsetenv("LLAMACODE_PLUMBSEARCH_URL");
    QVERIFY(qputenv("LLAMACODE_WEB_SEARCH_MODE", "local-only"));

    const QVariantMap result = call(
        QStringLiteral("web_search"),
        QJsonObject{{QStringLiteral("query"), QStringLiteral("empty local-only fixture")},
                    {QStringLiteral("count"), 1}});

    QVERIFY(!result.value(QStringLiteral("ok")).toBool());
    QVERIFY(result.value(QStringLiteral("result")).toString().contains(
        QStringLiteral("no se consultaron buscadores públicos")));
    QCOMPARE(server.requests.size(), 1);
}

void AgentToolsTests::webSearch_localOnlyRequiresLoopbackEndpoint()
{
    ScopedEnvironmentVariable restorePlumbUrl(QByteArrayLiteral("LLAMACODE_PLUMBSEARCH_URL"));
    ScopedEnvironmentVariable restoreSearxngUrl(QByteArrayLiteral("LLAMACODE_SEARXNG_URL"));
    ScopedEnvironmentVariable restoreMode(QByteArrayLiteral("LLAMACODE_WEB_SEARCH_MODE"));
    qunsetenv("LLAMACODE_PLUMBSEARCH_URL");
    QVERIFY(qputenv("LLAMACODE_SEARXNG_URL", "https://search.example.invalid"));
    QVERIFY(qputenv("LLAMACODE_WEB_SEARCH_MODE", "local-only"));

    const QVariantMap result = call(
        QStringLiteral("web_search"),
        QJsonObject{{QStringLiteral("query"), QStringLiteral("blocked remote endpoint")},
                    {QStringLiteral("count"), 1}});

    QVERIFY(!result.value(QStringLiteral("ok")).toBool());
    QVERIFY(result.value(QStringLiteral("result")).toString().contains(
        QStringLiteral("sólo admite un endpoint HTTP(S) loopback")));
}

void AgentToolsTests::webSearch_localOnlyRejectsRedirects()
{
    SearxngStub redirectTarget(QByteArrayLiteral(
        "{\"results\":[{\"title\":\"Redirect target\","
        "\"url\":\"https://redirect.example.test/result\","
        "\"content\":\"Should never be read\"}]}"));
    QVERIFY(redirectTarget.listen(QHostAddress::LocalHost));
    const QByteArray location = QByteArrayLiteral("Location: http://127.0.0.1:")
        + QByteArray::number(redirectTarget.serverPort())
        + QByteArrayLiteral("/search?format=json\r\n");
    SearxngStub redirectServer(QByteArray(), 302, location);
    QVERIFY(redirectServer.listen(QHostAddress::LocalHost));
    ScopedEnvironmentVariable restorePlumbUrl(QByteArrayLiteral("LLAMACODE_PLUMBSEARCH_URL"));
    ScopedEnvironmentVariable restoreSearxngUrl(QByteArrayLiteral("LLAMACODE_SEARXNG_URL"));
    ScopedEnvironmentVariable restoreMode(QByteArrayLiteral("LLAMACODE_WEB_SEARCH_MODE"));
    qunsetenv("LLAMACODE_PLUMBSEARCH_URL");
    QVERIFY(qputenv("LLAMACODE_SEARXNG_URL",
                    QStringLiteral("http://127.0.0.1:%1").arg(redirectServer.serverPort()).toUtf8()));
    QVERIFY(qputenv("LLAMACODE_WEB_SEARCH_MODE", "local-only"));

    const QVariantMap result = call(
        QStringLiteral("web_search"),
        QJsonObject{{QStringLiteral("query"), QStringLiteral("local redirect fixture")},
                    {QStringLiteral("count"), 1}});

    QVERIFY(!result.value(QStringLiteral("ok")).toBool());
    QVERIFY(result.value(QStringLiteral("result")).toString().contains(
        QStringLiteral("redirect bloqueado en modo local-only")));
    QCOMPARE(redirectServer.requests.size(), 1);
    QVERIFY(redirectTarget.requests.isEmpty());
}

QTEST_MAIN(AgentToolsTests)
#include "test_agent_tools.moc"
