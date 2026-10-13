#pragma once

#include <QVariantList>
#include <QVariantMap>
#include <QStringList>

// Decide la superficie inicial de tools por intención, sin conocer apps,
// controles ni layouts concretos. Ante ambigüedad falla abierto.
class ToolSurfaceRouter
{
public:
    struct Decision {
        QStringList groups;
        double confidence = 0.0;
        bool fullSurface = true;
        QString reason;
        QVariantMap toVariantMap() const;
    };

    static Decision decide(const QString &prompt, const QVariantList &catalog);
    // ¿El pedido es de computer use (abrir/usar una app del escritorio, clickear,
    // escribir en una ventana)? Distingue "abrí la calculadora" de "abrí el
    // archivo main.cpp" (eso es de archivos, no de escritorio).
    static bool wantsDesktop(const QString &prompt);
    static QString canonicalGroup(const QString &label);
    static bool groupAllowed(const QString &group, const Decision &decision);
};
