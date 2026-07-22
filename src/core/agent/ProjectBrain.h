#pragma once
#include <QVariantMap>

// Índice persistente, local y regenerable del workspace. Guarda sólo metadata y
// huellas; nunca copia el contenido fuente fuera del proyecto.
class ProjectBrain
{
public:
    static QVariantMap refresh(const QString &root, int maxFiles = 4000);
    static QVariantMap update(const QString &root, const QStringList &changedPaths,
                              int maxFiles = 4000);
    static QVariantMap load(const QString &root);
    static QString cachePath(const QString &root);
};
