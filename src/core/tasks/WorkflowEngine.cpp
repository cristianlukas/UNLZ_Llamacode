#include "WorkflowEngine.h"

#include <QDateTime>
#include <QJsonArray>
#include <QSet>

QString WorkflowEngine::validate(const QJsonObject &def)
{
    if (def.value(QStringLiteral("schemaVersion")).toInt(1) != 1)
        return QStringLiteral("schemaVersion no soportada");
    const QString entry = def.value(QStringLiteral("entry")).toString();
    const QJsonObject steps = def.value(QStringLiteral("steps")).toObject();
    if (entry.isEmpty() || !steps.contains(entry)) return QStringLiteral("entry inexistente");
    if (steps.size() > 128) return QStringLiteral("demasiados pasos");
    static const QSet<QString> types{QStringLiteral("agent"), QStringLiteral("tool"),
        QStringLiteral("approval"), QStringLiteral("condition"), QStringLiteral("parallel"),
        QStringLiteral("verify"), QStringLiteral("finish")};
    for (auto it = steps.begin(); it != steps.end(); ++it) {
        const QJsonObject step = it.value().toObject();
        if (!types.contains(step.value(QStringLiteral("type")).toString()))
            return QStringLiteral("tipo invalido en %1").arg(it.key());
        for (const QString &key : {QStringLiteral("next"), QStringLiteral("onSuccess"),
                                   QStringLiteral("onFailure")}) {
            const QString target = step.value(key).toString();
            if (!target.isEmpty() && target != QLatin1String("stop") && !steps.contains(target))
                return QStringLiteral("destino %1 inexistente en %2").arg(target, it.key());
        }
    }
    return {};
}

WorkflowEngine::State WorkflowEngine::start(const QJsonObject &def, const QString &id,
                                             const QVariantMap &variables)
{
    State s;
    s.workflowId = id;
    s.variables = variables;
    s.startedAtMs = QDateTime::currentMSecsSinceEpoch();
    s.error = validate(def);
    if (!s.error.isEmpty()) { s.status = Failed; return s; }
    s.currentStep = def.value(QStringLiteral("entry")).toString();
    s.status = Running;
    if (currentStep(def, s).value(QStringLiteral("type")).toString() == QLatin1String("approval"))
        s.status = WaitingApproval;
    return s;
}

QJsonObject WorkflowEngine::currentStep(const QJsonObject &def, const State &s)
{
    return def.value(QStringLiteral("steps")).toObject().value(s.currentStep).toObject();
}

QString WorkflowEngine::nextStep(const QJsonObject &step, const QString &route)
{
    if (!route.isEmpty()) {
        const QString routed = step.value(route).toString();
        if (!routed.isEmpty()) return routed;
    }
    return step.value(QStringLiteral("next")).toString();
}

bool WorkflowEngine::budgetExceeded(const QJsonObject &def, const State &s)
{
    const QJsonObject budget = def.value(QStringLiteral("budget")).toObject();
    const int maxIterations = budget.value(QStringLiteral("maxIterations")).toInt(64);
    const qint64 maxSeconds = budget.value(QStringLiteral("maxSeconds")).toInteger(3600);
    return s.iterations >= maxIterations ||
        (maxSeconds > 0 && QDateTime::currentMSecsSinceEpoch() - s.startedAtMs > maxSeconds * 1000);
}

bool WorkflowEngine::completeStep(const QJsonObject &def, State *s, const QVariant &result,
                                  bool success, const QString &route)
{
    if (!s || (s->status != Running && s->status != WaitingApproval)) return false;
    const QJsonObject step = currentStep(def, *s);
    if (step.isEmpty()) { s->status = Failed; s->error = QStringLiteral("paso inexistente"); return false; }
    s->results[s->currentStep] = result;
    s->completedSteps.append(s->currentStep);
    ++s->iterations;
    if (budgetExceeded(def, *s)) {
        s->status = Failed; s->error = QStringLiteral("presupuesto agotado"); return false;
    }
    QString next = nextStep(step, route);
    if (next.isEmpty()) next = nextStep(step, success ? QStringLiteral("onSuccess")
                                                     : QStringLiteral("onFailure"));
    if (!success && next.isEmpty()) {
        s->status = Failed; s->error = QStringLiteral("paso fallido sin recuperacion"); return false;
    }
    if (next.isEmpty() || next == QLatin1String("stop") ||
        step.value(QStringLiteral("type")).toString() == QLatin1String("finish")) {
        s->currentStep.clear(); s->status = success ? Completed : Failed; return true;
    }
    s->currentStep = next;
    s->status = currentStep(def, *s).value(QStringLiteral("type")).toString() == QLatin1String("approval")
        ? WaitingApproval : Running;
    return true;
}

bool WorkflowEngine::approve(const QJsonObject &def, State *s, const QString &choice,
                             const QString &userText)
{
    if (!s || s->status != WaitingApproval) return false;
    if (!userText.isEmpty()) s->variables[QStringLiteral("userText")] = userText;
    return completeStep(def, s, choice, true, choice);
}

QJsonObject WorkflowEngine::toJson(const State &s)
{
    return {{QStringLiteral("schemaVersion"), s.schemaVersion},
            {QStringLiteral("workflowId"), s.workflowId},
            {QStringLiteral("currentStep"), s.currentStep},
            {QStringLiteral("completedSteps"), QJsonArray::fromStringList(s.completedSteps)},
            {QStringLiteral("results"), QJsonObject::fromVariantMap(s.results)},
            {QStringLiteral("variables"), QJsonObject::fromVariantMap(s.variables)},
            {QStringLiteral("iterations"), s.iterations},
            {QStringLiteral("startedAtMs"), s.startedAtMs},
            {QStringLiteral("status"), statusName(s.status)},
            {QStringLiteral("error"), s.error}};
}

WorkflowEngine::State WorkflowEngine::fromJson(const QJsonObject &o, QString *error)
{
    State s;
    s.schemaVersion = o.value(QStringLiteral("schemaVersion")).toInt(1);
    if (s.schemaVersion != 1) { if (error) *error = QStringLiteral("snapshot no soportado"); s.status = Failed; return s; }
    s.workflowId = o.value(QStringLiteral("workflowId")).toString();
    s.currentStep = o.value(QStringLiteral("currentStep")).toString();
    for (const QJsonValue &v : o.value(QStringLiteral("completedSteps")).toArray()) s.completedSteps << v.toString();
    s.results = o.value(QStringLiteral("results")).toObject().toVariantMap();
    s.variables = o.value(QStringLiteral("variables")).toObject().toVariantMap();
    s.iterations = o.value(QStringLiteral("iterations")).toInt();
    s.startedAtMs = o.value(QStringLiteral("startedAtMs")).toInteger();
    const QString status = o.value(QStringLiteral("status")).toString();
    if (status == QLatin1String("running")) s.status = Running;
    else if (status == QLatin1String("waiting_approval")) s.status = WaitingApproval;
    else if (status == QLatin1String("completed")) s.status = Completed;
    else if (status == QLatin1String("failed")) s.status = Failed;
    else if (status == QLatin1String("cancelled")) s.status = Cancelled;
    else s.status = Ready;
    s.error = o.value(QStringLiteral("error")).toString();
    if (error) error->clear();
    return s;
}

QString WorkflowEngine::statusName(Status status)
{
    switch (status) {
    case Ready: return QStringLiteral("ready");
    case Running: return QStringLiteral("running");
    case WaitingApproval: return QStringLiteral("waiting_approval");
    case Completed: return QStringLiteral("completed");
    case Failed: return QStringLiteral("failed");
    case Cancelled: return QStringLiteral("cancelled");
    }
    return QStringLiteral("failed");
}
