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
#include <QJsonArray>
#include <QJsonDocument>
#include <QDir>
#include <QFile>
#include "core/agent/AgentToolRunner.h"
#include "core/agent/AgentEventLog.h"
#include "core/agent/SubAgentRunner.h"

class AgentToolsTests : public QObject
{
    Q_OBJECT
private slots:
    void init();
    void cleanup();

    void writeReadEditCycle();
    void readFile_compactViewAndSafeFallback();
    void projectBrain_persistsWorkspaceIndex();
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
    void hybridSearch_compactReturnsSpans();
    void repoSlice_defaultsToCompactEvidence();
    void recentActions_tailsEventLogForSession();
    void desktopWindows_returnsStructuredInventory();
    void desktopControls_invalidWindowErrorsCleanly();
    void desktopLaunch_emptyAppErrorsCleanly();
    void honeyHandoff_densifiesMasterAndSubPrompts();
    void webUrlGuard_blocksPrivateAndCredentials();
    void readableWebText_prefersArticleAndPreservesStructure();
    void webEscalation_requiresVerifiableEvidence();
    void webFetch_forcedUnavailableProviderFailsDeterministically();

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

QTEST_MAIN(AgentToolsTests)
#include "test_agent_tools.moc"
