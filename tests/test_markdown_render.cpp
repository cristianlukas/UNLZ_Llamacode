#include <QtTest>

#include "core/MarkdownRender.h"

// Respuestas del modelo en Chat / Agente: markdown renderizado, pero sin HTML
// crudo ni imágenes remotas (mostrar un mensaje no puede disparar red).
class TestMarkdownRender : public QObject
{
    Q_OBJECT
private slots:
    void rendersTablesAndCode()
    {
        const QString html = MarkdownRender::toHtml(
            "| GPU | VRAM |\n|---|---|\n| RTX 3090 | 24 GB |\n\n```python\nprint(\"hola\")\n```\n\n**negrita**",
            "monospace");
        QVERIFY(html.contains("<table"));
        QVERIFY(html.contains("RTX 3090"));
        QVERIFY(!html.contains("|---|"));
        QVERIFY(!html.contains("```"));
        QVERIFY(html.contains("print(&quot;hola&quot;)") || html.contains("print(\"hola\")"));
        QVERIFY(html.contains("font-weight"));
        QVERIFY2(html.contains("border=\"1\"") || html.contains("border-width:1"), qPrintable(html));
        // El bloque de código no queda pegado a la tabla.
        QVERIFY2(html.contains("margin-top:8px"), qPrintable(html));
        // La fuente/tamaño del documento no pisa los del TextEdit.
        QVERIFY(!html.contains("<body style="));
    }

    void rawHtmlStaysText()
    {
        const QString html = MarkdownRender::toHtml("hola <img src=\"http://evil.example/x.png\"> <b>x</b>");
        QVERIFY(!html.contains("<img"));
        QVERIFY(!html.contains("<b>"));
        QVERIFY(html.contains("&lt;b&gt;"));
    }

    void markdownImagesBecomeAltText()
    {
        const QString html = MarkdownRender::toHtml("mirá ![diagrama](http://evil.example/track.png) acá");
        QVERIFY2(!html.contains("<img"), qPrintable(html));
        QVERIFY(!html.contains("evil.example"));
        QVERIFY(html.contains("[diagrama]"));
    }
};

QTEST_MAIN(TestMarkdownRender)
#include "test_markdown_render.moc"
