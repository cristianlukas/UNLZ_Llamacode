// Unit tests de MermaidRenderer (sin sidecar mmdc):
//   - segments(): split de texto / bloques mermaid; fences sin cerrar = texto.
//   - sourceHash: estable y distinto por contenido.
//   - cachedPath: "" cuando no se rindió.
//   - requestRender: emite renderFailed si mmdc no está (entorno de test).
// El render real (mmdc → PNG) necesita mermaid-cli instalado → no se cubre acá.

#include <QtTest>
#include <QSignalSpy>
#include <QStandardPaths>
#include "core/MermaidRenderer.h"

class MermaidTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase() { QStandardPaths::setTestModeEnabled(true); }

    void segments_plainTextOnly();
    void segments_singleBlock();
    void segments_textBeforeAndAfter();
    void segments_unclosedFenceStaysText();
    void segments_caseInsensitiveLang();
    void hash_stableAndDistinct();
    void cachedPath_emptyWhenNotRendered();
    void requestRender_failsWithoutSidecar();
};

static QString segType(const QVariantList &l, int i)
{ return l.at(i).toMap().value("type").toString(); }
static QString segText(const QVariantList &l, int i)
{ return l.at(i).toMap().value("text").toString(); }

void MermaidTests::segments_plainTextOnly()
{
    MermaidRenderer m;
    const QVariantList s = m.segments("hola mundo, sin diagramas");
    QCOMPARE(s.size(), 1);
    QCOMPARE(segType(s, 0), QString("text"));
}

void MermaidTests::segments_singleBlock()
{
    MermaidRenderer m;
    const QVariantList s = m.segments("```mermaid\ngraph TD;A-->B;\n```");
    QCOMPARE(s.size(), 1);
    QCOMPARE(segType(s, 0), QString("mermaid"));
    QCOMPARE(segText(s, 0), QString("graph TD;A-->B;"));
}

void MermaidTests::segments_textBeforeAndAfter()
{
    MermaidRenderer m;
    const QString in = "antes\n```mermaid\ngraph TD;A-->B;\n```\ndespues";
    const QVariantList s = m.segments(in);
    QCOMPARE(s.size(), 3);
    QCOMPARE(segType(s, 0), QString("text"));
    QCOMPARE(segType(s, 1), QString("mermaid"));
    QCOMPARE(segType(s, 2), QString("text"));
    QVERIFY(segText(s, 0).contains("antes"));
    QVERIFY(segText(s, 2).contains("despues"));
}

void MermaidTests::segments_unclosedFenceStaysText()
{
    MermaidRenderer m;
    // Streaming: bloque sin cerrar → no se rinde, queda como texto.
    const QVariantList s = m.segments("texto\n```mermaid\ngraph TD;A-->B;");
    QCOMPARE(s.size(), 1);
    QCOMPARE(segType(s, 0), QString("text"));
}

void MermaidTests::segments_caseInsensitiveLang()
{
    MermaidRenderer m;
    const QVariantList s = m.segments("```Mermaid\nsequenceDiagram\n```");
    QCOMPARE(s.size(), 1);
    QCOMPARE(segType(s, 0), QString("mermaid"));
}

void MermaidTests::hash_stableAndDistinct()
{
    MermaidRenderer m;
    const QString a1 = m.sourceHash("graph TD;A-->B;");
    const QString a2 = m.sourceHash("graph TD;A-->B;");
    const QString b  = m.sourceHash("graph TD;A-->C;");
    QCOMPARE(a1, a2);
    QVERIFY(a1 != b);
    QVERIFY(!a1.isEmpty());
}

void MermaidTests::cachedPath_emptyWhenNotRendered()
{
    MermaidRenderer m;
    QVERIFY(m.cachedPath("diagrama inexistente xyz").isEmpty());
}

void MermaidTests::requestRender_failsWithoutSidecar()
{
    // En CI/test no hay mmdc → debe emitir renderFailed (o renderReady si por
    // alguna razón ya estuviera cacheado). Sin sidecar: failed sincrónico.
    if (qEnvironmentVariableIsSet("LLAMACODE_MMDC")) QSKIP("mmdc configurado");
    MermaidRenderer m;
    QSignalSpy failed(&m, &MermaidRenderer::renderFailed);
    QSignalSpy ready(&m, &MermaidRenderer::renderReady);
    m.requestRender("graph TD;A-->B; %% test sin sidecar");
    QVERIFY(failed.count() + ready.count() >= 1);
}

QTEST_MAIN(MermaidTests)
#include "test_mermaid.moc"
