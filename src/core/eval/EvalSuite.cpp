#include "EvalSuite.h"

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

namespace {

QStringList toStrList(const QJsonValue &v)
{
    QStringList out;
    for (const QJsonValue &e : v.toArray())
        if (e.isString()) out << e.toString();
    return out;
}

}  // namespace

EvalSuite EvalSuite::loadFromJson(const QByteArray &json, QString *err)
{
    EvalSuite suite;
    QJsonParseError perr;
    const QJsonDocument doc = QJsonDocument::fromJson(json, &perr);
    if (perr.error != QJsonParseError::NoError) {
        if (err) *err = QStringLiteral("JSON inválido: %1").arg(perr.errorString());
        return suite;
    }
    const QJsonObject root = doc.object();
    suite.name = root.value(QStringLiteral("name")).toString();
    suite.description = root.value(QStringLiteral("description")).toString();

    const QJsonArray tasks = root.value(QStringLiteral("tasks")).toArray();
    int auto_id = 0;
    for (const QJsonValue &tv : tasks) {
        const QJsonObject t = tv.toObject();
        if (t.isEmpty()) continue;
        EvalTask task;
        task.id = t.value(QStringLiteral("id")).toString(
            QStringLiteral("task-%1").arg(++auto_id, 3, 10, QLatin1Char('0')));
        task.category = t.value(QStringLiteral("category")).toString(QStringLiteral("other"));
        task.prompt = t.value(QStringLiteral("prompt")).toString();
        task.acceptance = toStrList(t.value(QStringLiteral("acceptance")));
        task.attachments = toStrList(t.value(QStringLiteral("attachments")));
        task.weight = t.value(QStringLiteral("weight")).toInt(1);
        if (task.prompt.isEmpty()) continue;   // tarea sin prompt = ignorar
        suite.tasks.append(task);
    }
    if (suite.tasks.isEmpty() && err && err->isEmpty())
        *err = QStringLiteral("suite sin tareas válidas");
    return suite;
}

EvalSuite EvalSuite::loadFromFile(const QString &path, QString *err)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) {
        if (err) *err = QStringLiteral("no se pudo abrir: %1").arg(path);
        return {};
    }
    return loadFromJson(f.readAll(), err);
}

QStringList EvalSuite::categories() const
{
    QStringList out;
    for (const EvalTask &t : tasks)
        if (!out.contains(t.category)) out << t.category;
    return out;
}
