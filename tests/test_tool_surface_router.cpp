#include <QtTest>

#include "core/agent/ToolSurfaceRouter.h"

class ToolSurfaceRouterTests : public QObject
{
    Q_OBJECT
private slots:
    void ambiguousPromptFailsOpen();
    void webAndBrowserIntentAddsRelevantGroups();
    void desktopIntentIsAppAgnostic();
    void canonicalizesCatalogLabels();
    void wantsDesktopSeparatesAppsFromFiles();
};

static QVariantList catalog()
{
    return {QVariantMap{{QStringLiteral("name"), QStringLiteral("read_file")},
                        {QStringLiteral("group"), QStringLiteral("Archivos")}},
            QVariantMap{{QStringLiteral("name"), QStringLiteral("grep")},
                        {QStringLiteral("group"), QStringLiteral("Búsqueda")}},
            QVariantMap{{QStringLiteral("name"), QStringLiteral("edit_file")},
                        {QStringLiteral("group"), QStringLiteral("Código")}},
            QVariantMap{{QStringLiteral("name"), QStringLiteral("web_search")},
                        {QStringLiteral("group"), QStringLiteral("Web")}},
            QVariantMap{{QStringLiteral("name"), QStringLiteral("browser_skill_replay")},
                        {QStringLiteral("group"), QStringLiteral("Browser")}},
            QVariantMap{{QStringLiteral("name"), QStringLiteral("desktop_click_element")},
                        {QStringLiteral("group"), QStringLiteral("Escritorio")}},
            QVariantMap{{QStringLiteral("name"), QStringLiteral("email_list")},
                        {QStringLiteral("group"), QStringLiteral("Correo")}},
            QVariantMap{{QStringLiteral("name"), QStringLiteral("memory")},
                        {QStringLiteral("group"), QStringLiteral("Conocimiento")}}};
}

void ToolSurfaceRouterTests::ambiguousPromptFailsOpen()
{
    const auto d = ToolSurfaceRouter::decide(QStringLiteral("hola, ¿cómo estás?"), catalog());
    QVERIFY(d.fullSurface);
    QVERIFY(d.groups.isEmpty());
}

void ToolSurfaceRouterTests::webAndBrowserIntentAddsRelevantGroups()
{
    const auto d = ToolSurfaceRouter::decide(
        QStringLiteral("abrí el navegador y buscá información en internet"), catalog());
    QVERIFY(!d.fullSurface);
    QVERIFY(d.groups.contains(QStringLiteral("web")));
    QVERIFY(d.groups.contains(QStringLiteral("browser")));
    QVERIFY(!d.groups.contains(QStringLiteral("mail")));
    QVERIFY(ToolSurfaceRouter::groupAllowed(QStringLiteral("Browser"), d));
}

void ToolSurfaceRouterTests::desktopIntentIsAppAgnostic()
{
    const auto d = ToolSurfaceRouter::decide(
        QStringLiteral("usá la ventana visible, observá los controles y hacé click"), catalog());
    QVERIFY(!d.fullSurface);
    QVERIFY(d.groups.contains(QStringLiteral("desktop")));
}

void ToolSurfaceRouterTests::canonicalizesCatalogLabels()
{
    QCOMPARE(ToolSurfaceRouter::canonicalGroup(QStringLiteral("Búsqueda")),
             QStringLiteral("search"));
    QCOMPARE(ToolSurfaceRouter::canonicalGroup(QStringLiteral("Multi-Agente")),
             QStringLiteral("multiagent"));
    QVERIFY(ToolSurfaceRouter::canonicalGroup(QStringLiteral("future")).isEmpty());
}

// Pedido real del usuario con el perfil "Intermedio" (sin tools de escritorio):
// el agente contestaba "no puedo abrir aplicaciones". Hay que reconocerlo como
// computer use sin confundir "abrí el archivo X" (archivos) con abrir una app.
void ToolSurfaceRouterTests::wantsDesktopSeparatesAppsFromFiles()
{
    QVERIFY(ToolSurfaceRouter::wantsDesktop(QStringLiteral("quiero que abras la calculadora y hagas 12*12")));
    QVERIFY(ToolSurfaceRouter::wantsDesktop(QStringLiteral("Abrí el Bloc de notas y escribí hola")));
    QVERIFY(ToolSurfaceRouter::wantsDesktop(QStringLiteral("hacé clic en Guardar")));
    QVERIFY(ToolSurfaceRouter::wantsDesktop(QStringLiteral("¿qué hay en pantalla?")));
    QVERIFY(ToolSurfaceRouter::wantsDesktop(QStringLiteral("open the calculator")));
    QVERIFY(ToolSurfaceRouter::wantsDesktop(QStringLiteral("cerrá la ventana de Paint")));

    QVERIFY(!ToolSurfaceRouter::wantsDesktop(QStringLiteral("abrí el archivo main.cpp y arreglá el bug")));
    QVERIFY(!ToolSurfaceRouter::wantsDesktop(QStringLiteral("usá la función abrir() del módulo")));
    QVERIFY(!ToolSurfaceRouter::wantsDesktop(QStringLiteral("calculá 12*12 en Python")));
    QVERIFY(!ToolSurfaceRouter::wantsDesktop(QString()));
}

QTEST_MAIN(ToolSurfaceRouterTests)
#include "test_tool_surface_router.moc"
