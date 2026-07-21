#include "StructuredSourceView.h"

#include <QFileInfo>

double StructuredSourceView::Result::reductionPct() const
{
    return originalBytes > 0 ? (1.0 - double(compact.toUtf8().size()) / originalBytes) * 100.0 : 0.0;
}

StructuredSourceView::Result StructuredSourceView::build(const QString &source,
                                                          const QString &fileName,
                                                          bool keepComments)
{
    Result out;
    const QByteArray utf8 = source.toUtf8();
    out.originalBytes = utf8.size();
    const QString ext = QFileInfo(fileName).suffix().toLower();
    const bool indentationSensitive = ext == QLatin1String("py") || ext == QLatin1String("yaml")
                                   || ext == QLatin1String("yml");
    if (indentationSensitive) {
        out.error = QStringLiteral("lenguaje sensible a indentacion: usar fuente exacta");
        return out;
    }

    QByteArray compact;
    bool string = false, character = false, lineComment = false, blockComment = false;
    bool escape = false, pendingSpace = false;
    int braces = 0, brackets = 0, parens = 0;
    for (int i = 0; i < utf8.size(); ++i) {
        const char c = utf8.at(i);
        const char n = i + 1 < utf8.size() ? utf8.at(i + 1) : '\0';
        if (lineComment) {
            if (keepComments) { compact.append(c); out.segments.append({int(compact.size())-1, i, 1}); }
            if (c == '\n') { lineComment = false; pendingSpace = true; }
            continue;
        }
        if (blockComment) {
            if (keepComments) { compact.append(c); out.segments.append({int(compact.size())-1, i, 1}); }
            if (c == '*' && n == '/') {
                if (keepComments) { compact.append(n); out.segments.append({int(compact.size())-1, i+1, 1}); }
                ++i; blockComment = false; pendingSpace = true;
            }
            continue;
        }
        if (!string && !character && c == '/' && n == '/') { lineComment = true; if (!keepComments) ++i; continue; }
        if (!string && !character && c == '/' && n == '*') { blockComment = true; if (!keepComments) ++i; continue; }
        if (!string && !character && (c == ' ' || c == '\t' || c == '\r' || c == '\n')) {
            pendingSpace = true; continue;
        }
        if (pendingSpace && !compact.isEmpty()) {
            const char prev = compact.back();
            const bool wordA = (prev == '_' || (prev >= '0' && prev <= '9') ||
                                (prev >= 'A' && prev <= 'Z') || (prev >= 'a' && prev <= 'z'));
            const bool wordB = (c == '_' || (c >= '0' && c <= '9') ||
                                (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z'));
            if (wordA && wordB) compact.append(' ');
        }
        pendingSpace = false;
        compact.append(c);
        out.segments.append({int(compact.size())-1, i, 1});
        if (!character && c == '"' && !escape) string = !string;
        if (!string && c == '\'' && !escape) character = !character;
        escape = (string || character) && c == '\\' && !escape;
        if (c != '\\') escape = false;
        if (!string && !character) {
            if (c == '{') ++braces; else if (c == '}') --braces;
            if (c == '[') ++brackets; else if (c == ']') --brackets;
            if (c == '(') ++parens; else if (c == ')') --parens;
        }
        if (braces < 0 || brackets < 0 || parens < 0) break;
    }
    if (string || character || blockComment || braces != 0 || brackets != 0 || parens != 0) {
        out.error = QStringLiteral("fuente no validable: usar fuente exacta");
        return out;
    }
    out.compact = QString::fromUtf8(compact);
    out.safe = true;
    return out;
}

bool StructuredSourceView::projectRange(const Result &view, int start, int length,
                                        int *originalStart, int *originalLength)
{
    if (!view.safe || length <= 0 || start < 0) return false;
    int first = -1, last = -1;
    for (const Segment &s : view.segments) {
        if (s.compactStart >= start && s.compactStart < start + length) {
            if (first < 0) first = s.originalStart;
            last = s.originalStart + s.length;
        }
    }
    if (first < 0 || last <= first) return false;
    if (originalStart) *originalStart = first;
    if (originalLength) *originalLength = last - first;
    return true;
}
