#pragma once

#include <QString>

// Markdown de una respuesta del modelo → HTML para un TextEdit RichText.
// TextEdit.MarkdownText de QML también interpreta HTML crudo y carga <img>
// remotas: un texto del modelo (o inyectado en lo que el agente lee) podía
// disparar pedidos de red con sólo mostrarse. Acá el HTML crudo queda como
// texto y las imágenes se reemplazan por su texto alternativo.
class MarkdownRender
{
public:
    // codeFont: familia para bloques/código en línea (Theme.codeFont).
    static QString toHtml(const QString &markdown, const QString &codeFont = QString());
};
