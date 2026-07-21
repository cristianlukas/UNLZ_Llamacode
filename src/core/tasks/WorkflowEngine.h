#pragma once

#include <QJsonObject>
#include <QVariantMap>

// Motor determinista de estado. La ejecucion de agent/tool permanece en el
// controlador existente para conservar permisos, concurrencia y cancelacion.
class WorkflowEngine
{
public:
    enum Status { Ready, Running, WaitingApproval, Completed, Failed, Cancelled };
    struct State {
        int schemaVersion = 1;
        QString workflowId;
        QString currentStep;
        QStringList completedSteps;
        QVariantMap results;
        QVariantMap variables;
        int iterations = 0;
        qint64 startedAtMs = 0;
        Status status = Ready;
        QString error;
    };

    static QString validate(const QJsonObject &definition);
    static State start(const QJsonObject &definition, const QString &workflowId,
                       const QVariantMap &variables = {});
    static QJsonObject currentStep(const QJsonObject &definition, const State &state);
    static bool completeStep(const QJsonObject &definition, State *state,
                             const QVariant &result, bool success,
                             const QString &route = QString());
    static bool approve(const QJsonObject &definition, State *state,
                        const QString &choice, const QString &userText = QString());
    static QJsonObject toJson(const State &state);
    static State fromJson(const QJsonObject &object, QString *error = nullptr);
    static QString statusName(Status status);

private:
    static QString nextStep(const QJsonObject &step, const QString &route);
    static bool budgetExceeded(const QJsonObject &definition, const State &state);
};
