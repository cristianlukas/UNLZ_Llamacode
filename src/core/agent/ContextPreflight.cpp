#include "ContextPreflight.h"
#include "ProjectBrain.h"
#include "CodeGraphIndexer.h"
#include "ContextIndex.h"

QString ContextPreflight::build(const QString &root, const QString &request, int maxFiles,
                                int tokenBudget, bool expandGraph)
{
    QVariantMap brain = ProjectBrain::load(root);
    if (brain.isEmpty()) brain = ProjectBrain::refresh(root);
    if (brain.contains(QStringLiteral("error"))) return {};
    QString graphReport;
    CodeGraphIndexer::buildIncremental(root, {}, &graphReport);
    const QVariantMap scout = ContextIndex::scout(root, request,
                                                   qBound(64, tokenBudget, 16000),
                                                   qBound(1, maxFiles, 15), expandGraph);
    if (!scout.value(QStringLiteral("ok")).toBool()) return {};
    return QStringLiteral("[preflight de contexto — índice local regenerable]\n"
                          "Archivos de ProjectBrain: %1\n%2\n"
                          "Leé los handles/rangos exactos antes de editar.\n"
                          "Graph: %3")
        .arg(brain.value(QStringLiteral("fileCount")).toInt())
        .arg(ContextIndex::formatScout(scout))
        .arg(graphReport);
}
