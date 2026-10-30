#include "MarkdownRender.h"

#include <QRegularExpression>
#include <QTextBlock>
#include <QTextCursor>
#include <QTextDocument>
#include <QTextFragment>
#include <QTextImageFormat>
#include <QTextTable>
#include <QTextTableFormat>

QString MarkdownRender::toHtml(const QString &markdown, const QString &codeFont)
{
    QTextDocument doc;
    doc.setMarkdown(markdown, QTextDocument::MarkdownFeatures(
                                  QTextDocument::MarkdownDialectGitHub
                                  | QTextDocument::MarkdownNoHTML));

    // Imágenes ![alt](url) → "[alt]": nada se descarga al mostrar el mensaje.
    for (QTextBlock b = doc.begin(); b.isValid(); b = b.next()) {
        QList<QTextFragment> images;
        for (auto it = b.begin(); !it.atEnd(); ++it)
            if (it.fragment().charFormat().isImageFormat()) images << it.fragment();
        for (int i = images.size() - 1; i >= 0; --i) {
            const QTextFragment f = images.at(i);
            const QString alt = f.charFormat().toImageFormat().property(QTextFormat::ImageAltText).toString();
            QTextCursor c(&doc);
            c.setPosition(f.position());
            c.setPosition(f.position() + f.length(), QTextCursor::KeepAnchor);
            c.insertText(QStringLiteral("[%1]").arg(alt.isEmpty() ? QStringLiteral("imagen") : alt),
                         QTextCharFormat());
        }
    }

    // Tablas legibles: borde fino y algo de aire (las de Qt salen pegadas).
    for (QTextFrame *frame : doc.rootFrame()->childFrames()) {
        if (auto *table = qobject_cast<QTextTable *>(frame)) {
            QTextTableFormat fmt = table->format();
            fmt.setBorder(1);
            fmt.setBorderStyle(QTextFrameFormat::BorderStyle_Solid);
            fmt.setCellPadding(4);
            fmt.setCellSpacing(0);
            table->setFormat(fmt);
        }
    }

    QString html = doc.toHtml();
    // toHtml() fija la fuente/tamaño del documento en <body>: se quita para que
    // manden los del TextEdit (tema y tamaño de la app).
    html.replace(QRegularExpression(QStringLiteral("<body style=\"[^\"]*\">")),
                 QStringLiteral("<body>"));
    if (!codeFont.isEmpty()) {
        // Qt marca el código con font-family:'monospace' (o la fija del sistema).
        static const QRegularExpression mono(QStringLiteral("font-family:'[^']*monospace[^']*'"));
        html.replace(mono, QStringLiteral("font-family:'%1'").arg(codeFont));
    }
    return html;
}
