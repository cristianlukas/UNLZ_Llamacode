#include "ManagedAgentRunStore.h"

#include "core/tasks/RunHistoryStore.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QProcessEnvironment>
#include <QRegularExpression>
#include <QSaveFile>
#include <QStandardPaths>
#include <QTimer>
#include <QUuid>

#include <algorithm>

namespace {
QString asString(const QVariantMap &map, const QString &key)
{
    return map.value(key).toString().trimmed();
}

QString joinCommand(const QString &program, const QStringList &args)
{
    QStringList safe;
    safe.reserve(args.size());
    for (const QString &arg : args) {
        // Nunca se persiste el prompt como parte del comando visible.
        if (arg.size() > 180 || arg.contains(QRegularExpression(QStringLiteral("\\s"))))
            safe << QStringLiteral("<prompt>");
        else
            safe << arg;
    }
    return QDir::toNativeSeparators(program + QStringLiteral(" ") + safe.join(QLatin1Char(' ')));
}
}

ManagedAgentRunStore::ManagedAgentRunStore(RunHistoryStore *history, QObject *parent)
    : QObject(parent), m_history(history)
{
    loadPersistedRuns();
}

QString ManagedAgentRunStore::nowUtc()
{
    return QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
}

QString ManagedAgentRunStore::newRunId()
{
    return QUuid::createUuid().toString(QUuid::WithoutBraces).left(12);
}

QString ManagedAgentRunStore::tail(const QString &text, int maxChars)
{
    if (text.size() <= maxChars) return text;
    return QStringLiteral("…") + text.right(maxChars - 1);
}

QString ManagedAgentRunStore::runtimeName(const QVariantMap &request)
{
    return asString(request, QStringLiteral("runtime")).toLower();
}

bool ManagedAgentRunStore::validRuntime(const QString &runtime)
{
    return runtime == QLatin1String("claude") || runtime == QLatin1String("codex");
}

QString ManagedAgentRunStore::resolveCliPath(const QVariantMap &request)
{
    const QString explicitPath = asString(request, QStringLiteral("cliPath"));
    if (!explicitPath.isEmpty()) return explicitPath;
    const QString runtime = runtimeName(request);
    return QStandardPaths::findExecutable(runtime);
}

QVariantMap ManagedAgentRunStore::commandForRequest(const QVariantMap &request)
{
    const QString runtime = runtimeName(request);
    const QString prompt = request.value(QStringLiteral("prompt")).toString();
    const QString program = resolveCliPath(request);
    // Wrapper CLIs (o un probe de integración) pueden aportar argumentos de
    // entrada antes del contrato del runtime. En uso normal queda vacío.
    QStringList args = request.value(QStringLiteral("prefixArgs")).toStringList();
    QString permissionPosture = QStringLiteral("default");

    if (runtime == QLatin1String("claude")) {
        args << QStringLiteral("-p") << prompt;
        const QString model = asString(request, QStringLiteral("model"));
        if (!model.isEmpty()) args << QStringLiteral("--model") << model;
        const QString approval = asString(request, QStringLiteral("approvalMode"));
        if (request.value(QStringLiteral("applyEdits"), false).toBool()) {
            // acceptEdits permite que el CLI edite el workspace, pero conserva
            // el límite explícito del modo de aprobación. Nunca se agrega el
            // bypass de permisos automáticamente.
            args << QStringLiteral("--permission-mode")
                 << (approval == QLatin1String("plan")
                         ? QStringLiteral("plan")
                         : QStringLiteral("acceptEdits"));
            permissionPosture = approval == QLatin1String("plan")
                ? QStringLiteral("plan") : QStringLiteral("acceptEdits");
        } else {
            args << QStringLiteral("--permission-mode") << QStringLiteral("plan");
            permissionPosture = QStringLiteral("plan");
        }
    } else if (runtime == QLatin1String("codex")) {
        args << QStringLiteral("exec");
        const QString model = asString(request, QStringLiteral("model"));
        if (!model.isEmpty()) args << QStringLiteral("--model") << model;
        const bool dangerous = request.value(QStringLiteral("allowDangerous"), false).toBool();
        const QString approval = asString(request, QStringLiteral("approvalMode"));
        if (request.value(QStringLiteral("applyEdits"), false).toBool()
            && approval == QLatin1String("super") && dangerous) {
            args << QStringLiteral("--full-auto");
            permissionPosture = QStringLiteral("full-auto-explicit");
        } else if (request.value(QStringLiteral("applyEdits"), false).toBool()) {
            permissionPosture = QStringLiteral("default-with-edits-requested");
        } else {
            permissionPosture = QStringLiteral("default-read-only-intent");
        }
        args << prompt;
    }

    return {
        {QStringLiteral("program"), program},
        {QStringLiteral("args"), args},
        {QStringLiteral("permissionPosture"), permissionPosture},
        {QStringLiteral("promptTransport"), QStringLiteral("argv+manifest")},
        {QStringLiteral("display"), joinCommand(program, args)}
    };
}

QString ManagedAgentRunStore::storageRoot() const
{
    const QByteArray overridePath = qgetenv("LLAMACODE_MANAGED_RUNS_DIR");
    const QString root = overridePath.isEmpty()
        ? QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
              + QStringLiteral("/managed-agent-runs")
        : QString::fromLocal8Bit(overridePath);
    QDir().mkpath(root);
    return root;
}

QString ManagedAgentRunStore::runDirectory(const QString &runId) const
{
    return storageRoot() + QLatin1Char('/') + RunHistoryStore::sanitize(runId);
}

QVariantList ManagedAgentRunStore::runs() const
{
    QVariantList result;
    for (auto it = m_runs.cbegin(); it != m_runs.cend(); ++it)
        result.append(it.value());
    std::sort(result.begin(), result.end(), [](const QVariant &a, const QVariant &b) {
        return a.toMap().value(QStringLiteral("startedAt")).toString()
             > b.toMap().value(QStringLiteral("startedAt")).toString();
    });
    return result;
}

bool ManagedAgentRunStore::writeTextFile(const QString &path, const QByteArray &data,
                                         bool append) const
{
    QFile file(path);
    if (!file.open((append ? QIODevice::Append : QIODevice::WriteOnly))) return false;
    return file.write(data) == data.size();
}

bool ManagedAgentRunStore::persist(const QVariantMap &run) const
{
    const QString dir = run.value(QStringLiteral("runDir")).toString();
    if (dir.isEmpty() || !QDir().mkpath(dir)) return false;
    QJsonObject object = QJsonObject::fromVariantMap(run);
    // El prompt vive en prompt.md y no se replica en el manifiesto ni en la
    // fila del store: reduce exposición accidental de instrucciones y secretos.
    object.remove(QStringLiteral("prompt"));
    QSaveFile file(dir + QStringLiteral("/manifest.json"));
    if (!file.open(QIODevice::WriteOnly)) return false;
    file.write(QJsonDocument(object).toJson(QJsonDocument::Indented));
    return file.commit();
}

void ManagedAgentRunStore::setError(const QString &message)
{
    if (message == m_lastError) return;
    m_lastError = message;
    emit lastErrorChanged();
}

void ManagedAgentRunStore::loadPersistedRuns()
{
    QDir root(storageRoot());
    const QStringList dirs = root.entryList(QDir::Dirs | QDir::NoDotAndDotDot);
    for (const QString &name : dirs) {
        QFile file(root.filePath(name + QStringLiteral("/manifest.json")));
        if (!file.open(QIODevice::ReadOnly)) continue;
        const QVariantMap run = QJsonDocument::fromJson(file.readAll()).object().toVariantMap();
        const QString id = run.value(QStringLiteral("runId")).toString();
        if (id.isEmpty()) continue;
        QVariantMap recovered = run;
        const QString status = recovered.value(QStringLiteral("status")).toString();
        if (status == QLatin1String("prepared") || status == QLatin1String("starting")
            || status == QLatin1String("running") || status == QLatin1String("stopping")) {
            recovered[QStringLiteral("status")] = QStringLiteral("stale");
            recovered[QStringLiteral("closeoutStatus")] = QStringLiteral("interrupted");
            recovered[QStringLiteral("finishedAt")] = nowUtc();
            recovered[QStringLiteral("summary")] = QStringLiteral(
                "La aplicación se cerró mientras la corrida estaba activa.");
            persist(recovered);
        }
        m_runs.insert(id, recovered);
    }
}

void ManagedAgentRunStore::updateRun(const QString &runId, const QVariantMap &run,
                                     bool persistManifest)
{
    m_runs.insert(runId, run);
    if (persistManifest) persist(run);
    emit runChanged(runId, run);
    emit runsChanged();
}

QString ManagedAgentRunStore::startRun(const QVariantMap &request)
{
    setError(QString());
    const QString runtime = runtimeName(request);
    const QString prompt = request.value(QStringLiteral("prompt")).toString().trimmed();
    const QString workspace = QFileInfo(asString(request, QStringLiteral("workspace"))).absoluteFilePath();
    if (!validRuntime(runtime)) {
        setError(QStringLiteral("runtime debe ser claude o codex"));
        return {};
    }
    if (prompt.isEmpty()) {
        setError(QStringLiteral("La corrida necesita un prompt no vacío"));
        return {};
    }
    if (prompt.size() > 200000) {
        setError(QStringLiteral("El prompt supera el límite de 200000 caracteres"));
        return {};
    }
    if (!QDir(workspace).exists()) {
        setError(QStringLiteral("El workspace no existe: %1").arg(workspace));
        return {};
    }
    const QVariantMap command = commandForRequest(request);
    const QString program = command.value(QStringLiteral("program")).toString();
    if (program.isEmpty()) {
        setError(QStringLiteral("No se encontró el CLI de %1 en PATH").arg(runtime));
        return {};
    }

    const QString id = newRunId();
    const QString dir = runDirectory(id);
    if (!QDir().mkpath(dir)) {
        setError(QStringLiteral("No se pudo crear el directorio de la corrida"));
        return {};
    }
    if (!writeTextFile(dir + QStringLiteral("/prompt.md"), prompt.toUtf8())) {
        setError(QStringLiteral("No se pudo guardar el prompt durable"));
        return {};
    }
    // Los artefactos existen desde el estado starting, incluso si el CLI no
    // emite ninguna línea antes de terminar.
    writeTextFile(dir + QStringLiteral("/stdout.log"), {});
    writeTextFile(dir + QStringLiteral("/stderr.log"), {});

    const QString presentation = asString(request, QStringLiteral("presentation")).isEmpty()
        ? QStringLiteral("managed_panel") : asString(request, QStringLiteral("presentation"));
    const bool visibleRequested = request.value(QStringLiteral("visibleRequested"), true).toBool();
    QVariantMap run{
        {QStringLiteral("runId"), id},
        {QStringLiteral("runtime"), runtime},
        {QStringLiteral("cliPath"), program},
        {QStringLiteral("workspace"), workspace},
        {QStringLiteral("ownerId"), asString(request, QStringLiteral("ownerId"))},
        {QStringLiteral("taskId"), asString(request, QStringLiteral("taskId"))},
        {QStringLiteral("agentProfileId"), asString(request, QStringLiteral("agentProfileId"))},
        {QStringLiteral("runDir"), dir},
        {QStringLiteral("promptPath"), dir + QStringLiteral("/prompt.md")},
        {QStringLiteral("stdoutPath"), dir + QStringLiteral("/stdout.log")},
        {QStringLiteral("stderrPath"), dir + QStringLiteral("/stderr.log")},
        {QStringLiteral("manifestPath"), dir + QStringLiteral("/manifest.json")},
        {QStringLiteral("promptSha256"), QString::fromLatin1(
             QCryptographicHash::hash(prompt.toUtf8(), QCryptographicHash::Sha256).toHex())},
        {QStringLiteral("promptBytes"), prompt.toUtf8().size()},
        {QStringLiteral("startedAt"), nowUtc()},
        {QStringLiteral("status"), QStringLiteral("starting")},
        {QStringLiteral("summary"), QStringLiteral("Iniciando %1").arg(runtime)},
        {QStringLiteral("applyEdits"), request.value(QStringLiteral("applyEdits"), false).toBool()},
        {QStringLiteral("permissionPosture"), command.value(QStringLiteral("permissionPosture"))},
        {QStringLiteral("command"), command.value(QStringLiteral("display"))},
        {QStringLiteral("presentation"), presentation},
        {QStringLiteral("visibleRequested"), visibleRequested},
        {QStringLiteral("visibleProof"), visibleRequested && presentation == QLatin1String("managed_panel")
             ? QStringLiteral("managed_panel") : QStringLiteral("not_proven")},
        {QStringLiteral("closeoutStatus"), QStringLiteral("pending")},
        {QStringLiteral("stdoutTail"), QString()},
        {QStringLiteral("stderrTail"), QString()}
    };
    m_runs.insert(id, run);
    persist(run);
    emit runChanged(id, run);
    emit runsChanged();

    auto *process = new QProcess(this);
    process->setWorkingDirectory(workspace);
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert(QStringLiteral("LLAMACODE_MANAGED_RUN"), QStringLiteral("1"));
    env.insert(QStringLiteral("LLAMACODE_RUN_ID"), id);
    env.insert(QStringLiteral("LLAMACODE_RUN_DIR"), dir);
    env.insert(QStringLiteral("LLAMACODE_RUN_MANIFEST"), dir + QStringLiteral("/manifest.json"));
    env.insert(QStringLiteral("LLAMACODE_RUN_PROMPT_FILE"), dir + QStringLiteral("/prompt.md"));
    process->setProcessEnvironment(env);
    m_processes.insert(id, process);
    m_stopRequested.insert(id, false);

    connect(process, &QProcess::started, this, [this, id, process]() {
        if (!m_runs.contains(id)) return;
        QVariantMap run = m_runs.value(id);
        run[QStringLiteral("status")] = QStringLiteral("running");
        run[QStringLiteral("pid")] = static_cast<qlonglong>(process->processId());
        run[QStringLiteral("summary")] = QStringLiteral("%1 está ejecutándose").arg(
            run.value(QStringLiteral("runtime")).toString());
        updateRun(id, run);
    });
    connect(process, &QProcess::readyReadStandardOutput, this, [this, id, process]() {
        appendOutput(id, QStringLiteral("stdout"), process->readAllStandardOutput());
    });
    connect(process, &QProcess::readyReadStandardError, this, [this, id, process]() {
        appendOutput(id, QStringLiteral("stderr"), process->readAllStandardError());
    });
    connect(process, &QProcess::errorOccurred, this,
            [this, id, process](QProcess::ProcessError error) {
        if (error != QProcess::FailedToStart || !m_processes.contains(id)) return;
        finishRun(id, -1, QStringLiteral("failed"), process->errorString());
    });
    connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
            [this, id](int exitCode, QProcess::ExitStatus) {
        const bool stopped = m_stopRequested.value(id, false);
        finishRun(id, exitCode, stopped ? QStringLiteral("cancelled")
                                        : (exitCode == 0 ? QStringLiteral("finished")
                                                         : QStringLiteral("failed")));
    });

    process->start(program, command.value(QStringLiteral("args")).toStringList());
    return id;
}

void ManagedAgentRunStore::appendOutput(const QString &runId, const QString &channel,
                                         const QByteArray &data)
{
    if (data.isEmpty() || !m_runs.contains(runId)) return;
    const QVariantMap run = m_runs.value(runId);
    const QString path = run.value(channel == QLatin1String("stderr")
                                       ? QStringLiteral("stderrPath")
                                       : QStringLiteral("stdoutPath")).toString();
    writeTextFile(path, data, true);
    QVariantMap updated = run;
    const QString value = QString::fromUtf8(data);
    const QString key = channel == QLatin1String("stderr")
        ? QStringLiteral("stderrTail") : QStringLiteral("stdoutTail");
    updated[key] = tail(updated.value(key).toString() + value);
    // El manifiesto se actualiza sólo con el tail acotado; el log completo vive
    // en su artefacto y no fuerza una escritura por cada token emitido.
    m_runs.insert(runId, updated);
    emit runChanged(runId, updated);
    emit logAppended(runId, channel, value);
}

QString ManagedAgentRunStore::log(const QString &runId) const
{
    const QVariantMap run = m_runs.value(runId);
    if (run.isEmpty()) return {};
    QString out;
    for (const QString &key : {QStringLiteral("stdoutPath"), QStringLiteral("stderrPath")}) {
        QFile file(run.value(key).toString());
        if (!file.open(QIODevice::ReadOnly)) continue;
        const QString content = QString::fromUtf8(file.readAll());
        if (!out.isEmpty()) out += QStringLiteral("\n");
        out += content;
    }
    return tail(out, 262144);
}

void ManagedAgentRunStore::finishRun(const QString &runId, int exitCode,
                                     const QString &status, const QString &error)
{
    if (!m_runs.contains(runId)) return;
    QVariantMap run = m_runs.value(runId);
    const QString current = run.value(QStringLiteral("status")).toString();
    if (current == QLatin1String("finished") || current == QLatin1String("failed")
        || current == QLatin1String("cancelled") || current == QLatin1String("stale"))
        return;
    run[QStringLiteral("status")] = status;
    run[QStringLiteral("finishedAt")] = nowUtc();
    run[QStringLiteral("exitCode")] = exitCode;
    run[QStringLiteral("closeoutStatus")] = status == QLatin1String("finished")
        ? QStringLiteral("completed") : (status == QLatin1String("cancelled")
                                              ? QStringLiteral("cancelled")
                                              : QStringLiteral("needs_attention"));
    if (!error.isEmpty()) {
        run[QStringLiteral("error")] = error;
        run[QStringLiteral("summary")] = error;
    } else {
        run[QStringLiteral("summary")] = status == QLatin1String("finished")
            ? QStringLiteral("%1 terminó correctamente").arg(run.value(QStringLiteral("runtime")).toString())
            : QStringLiteral("%1 terminó con estado %2").arg(
                  run.value(QStringLiteral("runtime")).toString(), status);
    }
    updateRun(runId, run);
    recordHistory(run);
    if (auto *process = m_processes.take(runId)) process->deleteLater();
    m_stopRequested.remove(runId);
    emit runFinished(runId, run);
    emit runsChanged();
}

void ManagedAgentRunStore::recordHistory(const QVariantMap &run)
{
    if (!m_history) return;
    QVariantMap metadata{
        {QStringLiteral("managedRunId"), run.value(QStringLiteral("runId"))},
        {QStringLiteral("runtime"), run.value(QStringLiteral("runtime"))},
        {QStringLiteral("workspace"), run.value(QStringLiteral("workspace"))},
        {QStringLiteral("promptPath"), run.value(QStringLiteral("promptPath"))},
        {QStringLiteral("manifestPath"), run.value(QStringLiteral("manifestPath"))},
        {QStringLiteral("stdoutPath"), run.value(QStringLiteral("stdoutPath"))},
        {QStringLiteral("stderrPath"), run.value(QStringLiteral("stderrPath"))},
        {QStringLiteral("permissionPosture"), run.value(QStringLiteral("permissionPosture"))},
        {QStringLiteral("visibleProof"), run.value(QStringLiteral("visibleProof"))},
        {QStringLiteral("exitCode"), run.value(QStringLiteral("exitCode"))}
    };
    QVariantMap record{
        {QStringLiteral("runId"), run.value(QStringLiteral("runId"))},
        {QStringLiteral("startedAt"), run.value(QStringLiteral("startedAt"))},
        {QStringLiteral("finishedAt"), run.value(QStringLiteral("finishedAt"))},
        {QStringLiteral("status"), run.value(QStringLiteral("status"))},
        {QStringLiteral("summary"), run.value(QStringLiteral("summary"))},
        {QStringLiteral("source"), QStringLiteral("managed_agent")},
        {QStringLiteral("log"), log(run.value(QStringLiteral("runId")).toString())},
        {QStringLiteral("metadata"), metadata},
        {QStringLiteral("report"), QVariantList{
             QVariantMap{{QStringLiteral("n"), 1}, {QStringLiteral("tool"),
                          QStringLiteral("managed_cli")}, {QStringLiteral("ok"),
                          run.value(QStringLiteral("status")).toString()
                              == QLatin1String("finished")},
                         {QStringLiteral("summary"), run.value(QStringLiteral("summary"))}}}}
    };
    const QString owner = run.value(QStringLiteral("ownerId")).toString();
    if (!owner.isEmpty()) m_history->append(owner, record);
    const QString taskId = run.value(QStringLiteral("taskId")).toString();
    if (!taskId.isEmpty() && taskId != owner) m_history->append(taskId, record);
}

QVariantMap ManagedAgentRunStore::run(const QString &runId) const
{
    return m_runs.value(runId);
}

bool ManagedAgentRunStore::stopRun(const QString &runId)
{
    auto *process = m_processes.value(runId, nullptr);
    if (!process) return false;
    m_stopRequested[runId] = true;
    QVariantMap run = m_runs.value(runId);
    run[QStringLiteral("status")] = QStringLiteral("stopping");
    run[QStringLiteral("summary")] = QStringLiteral("Cancelación solicitada");
    updateRun(runId, run);
#ifdef Q_OS_WIN
    if (process->processId() != 0) {
        QProcess::startDetached(QStringLiteral("taskkill"),
                                {QStringLiteral("/PID"), QString::number(process->processId()),
                                 QStringLiteral("/T"), QStringLiteral("/F")});
    } else {
        process->terminate();
    }
#else
    process->terminate();
    QTimer::singleShot(2500, process, [process]() {
        if (process->state() != QProcess::NotRunning) process->kill();
    });
#endif
    return true;
}

bool ManagedAgentRunStore::removeRun(const QString &runId)
{
    if (m_processes.contains(runId)) return false;
    const QVariantMap row = m_runs.take(runId);
    if (row.isEmpty()) return false;
    // El destino se deriva del id y no de un path arbitrario que pudiera
    // aparecer en un manifiesto local manipulado.
    QDir(runDirectory(runId)).removeRecursively();
    emit runsChanged();
    return true;
}
