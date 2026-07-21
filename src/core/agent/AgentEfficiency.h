#pragma once

#include <QJsonObject>
#include <QVariantList>
#include <QVariantMap>

// Telemetria estable del harness. Acepta respuestas llama.cpp y OpenAI-compatible
// incompletas: los campos desconocidos permanecen en cero en vez de inventarse.
class AgentEfficiency
{
public:
    struct Request {
        QString phase;
        int promptTokens = 0;
        int generatedTokens = 0;
        double promptMs = 0.0;
        double generatedMs = 0.0;
        double wallMs = 0.0;
        int toolCalls = 0;
        qint64 toolBytes = 0;

        QVariantMap toVariant() const;
        static Request fromResponse(const QJsonObject &root, const QString &phase,
                                    double wallMs = 0.0);
    };

    static QVariantMap summarize(const QVariantList &requests);
    static QVariantMap compare(const QVariantMap &baseline, const QVariantMap &candidate);
    static QString normalizedPhase(const QString &phase);
};
