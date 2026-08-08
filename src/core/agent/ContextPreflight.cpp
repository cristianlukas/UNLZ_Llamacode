#include "ContextPreflight.h"
#include "ProjectBrain.h"
#include "CodeGraphIndexer.h"
#include <QFileInfo>
#include <QRegularExpression>
#include <algorithm>

namespace {
QStringList words(const QString &text)
{
    QStringList out;
    for (const QString &w : text.toLower().split(QRegularExpression(QStringLiteral("[^a-z0-9_]+")), Qt::SkipEmptyParts))
        if (w.size() >= 3) out.append(w);
    return out;
}
}

QString ContextPreflight::build(const QString &root, const QString &request, int maxFiles)
{
    QVariantMap brain = ProjectBrain::load(root);
    if (brain.isEmpty()) brain = ProjectBrain::refresh(root);
    if (brain.contains(QStringLiteral("error"))) return {};
    QString graphReport;
    CodeGraphIndexer::buildIncremental(root, {}, &graphReport);
    const QStringList query = words(request);
    struct Candidate { int score; QString path; };
    QList<Candidate> candidates;
    for (const QVariant &v : brain.value(QStringLiteral("files")).toList()) {
        const QString path = v.toMap().value(QStringLiteral("path")).toString();
        int score = 0;
        for (const QString &term : query) if (path.toLower().contains(term)) score += 3;
        if (score > 0) candidates.append({score, path});
    }
    std::sort(candidates.begin(), candidates.end(), [](const Candidate &a, const Candidate &b) {
        return a.score != b.score ? a.score > b.score : a.path < b.path;
    });
    QStringList selected;
    for (const Candidate &c : candidates.mid(0, qBound(1, maxFiles, 32))) selected.append(c.path);
    return QStringLiteral("[preflight de contexto — metadata regenerable]\nÍndice: %1 archivos. "
                          "Candidatos iniciales: %2\nUsá repo_slice/hybrid_search con "
                          "expand_graph=true y leé los rangos exactos antes de editar.")
        .arg(brain.value(QStringLiteral("fileCount")).toInt())
        .arg(selected.isEmpty() ? QStringLiteral("(ninguno por nombre; buscá por significado)")
                                : selected.join(QStringLiteral(", ")));
}
