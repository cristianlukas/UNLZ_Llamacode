// Integration tests de AgentToolRunner (tools nativas del agente). Sin MCP ni
// red ni modelo: ejercitamos el dispatch de tools deterministas contra un cwd
// temporal y verificamos el resultado vía la señal toolExecuted.
//   - write_file → read_file → edit_file (con metadata de diff).
//   - confinamiento al cwd (bloquea rutas fuera del proyecto).
//   - grep / glob.
//   - run_shell async (echo trivial).

#include <QtTest>
#include <QTemporaryDir>
#include <QSignalSpy>
#include <QJsonObject>
#include <QJsonDocument>
#include <QDir>
#include <QFile>
#include "core/agent/AgentToolRunner.h"
#include "core/agent/AgentEventLog.h"

class AgentToolsTests : public QObject
{
    Q_OBJECT
private slots:
    void init();
    void cleanup();

    void writeReadEditCycle();
    void confinement_blocksOutsideCwd();
    void allowedRoots_permitExtraFolder();
    void unconfined_permitsAnyPath();
    void editFile_missingFails();
    void editFile_whitespaceNearMissExplains();
    void parseErrorExplainsChunking();
    void grep_findsMatch();
    void glob_listsFiles();
    void runShell_echo();
    void hybridSearch_depGraphAndBudget();
    void recentActions_tailsEventLogForSession();
    void desktopWindows_returnsStructuredInventory();
    void desktopControls_invalidWindowErrorsCleanly();

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
}

QTEST_MAIN(AgentToolsTests)
#include "test_agent_tools.moc"
