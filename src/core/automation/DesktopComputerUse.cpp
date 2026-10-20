#include "DesktopComputerUse.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFileInfo>
#include <QSet>
#include <QHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QLockFile>
#include <QProcess>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QStringList>
#include <QUuid>
#include <cmath>

namespace DesktopComputerUse {

QVariantMap TargetRef::toVariantMap() const
{
    return {{QStringLiteral("snapshotId"), snapshotId},
            {QStringLiteral("windowId"), windowId},
            {QStringLiteral("controlId"), controlId},
            {QStringLiteral("automationId"), automationId},
            {QStringLiteral("name"), name},
            {QStringLiteral("role"), role},
            {QStringLiteral("windowTitle"), windowTitle},
            {QStringLiteral("pid"), pid},
            {QStringLiteral("x"), bounds.x()},
            {QStringLiteral("y"), bounds.y()},
            {QStringLiteral("width"), bounds.width()},
            {QStringLiteral("height"), bounds.height()},
            {QStringLiteral("enabled"), enabled},
            {QStringLiteral("password"), password}};
}

TargetRef TargetRef::fromVariantMap(const QVariantMap &map)
{
    TargetRef ref;
    ref.snapshotId = map.value(QStringLiteral("snapshotId")).toString();
    ref.windowId = map.value(QStringLiteral("windowId")).toString();
    ref.controlId = map.value(QStringLiteral("controlId")).toString();
    ref.automationId = map.value(QStringLiteral("automationId")).toString();
    ref.name = map.value(QStringLiteral("name")).toString();
    ref.role = map.value(QStringLiteral("role")).toString();
    ref.windowTitle = map.value(QStringLiteral("windowTitle")).toString();
    ref.pid = map.value(QStringLiteral("pid")).toLongLong();
    ref.bounds = QRect(map.value(QStringLiteral("x")).toInt(),
                       map.value(QStringLiteral("y")).toInt(),
                       map.value(QStringLiteral("width")).toInt(),
                       map.value(QStringLiteral("height")).toInt());
    ref.enabled = map.value(QStringLiteral("enabled"), true).toBool();
    ref.password = map.value(QStringLiteral("password")).toBool();
    return ref;
}

QVariantMap Snapshot::toVariantMap() const
{
    return {{QStringLiteral("snapshotId"), snapshotId},
            {QStringLiteral("scopeKind"), scopeKind},
            {QStringLiteral("targetId"), targetId},
            {QStringLiteral("provider"), provider},
            {QStringLiteral("fingerprint"), fingerprint},
            {QStringLiteral("createdAt"), createdAt},
            {QStringLiteral("target"), target},
            {QStringLiteral("windows"), windows},
            {QStringLiteral("controls"), controls},
            {QStringLiteral("focus"), focus},
            {QStringLiteral("capture"), capture}};
}

QJsonObject Snapshot::toJson() const
{
    return QJsonObject::fromVariantMap(toVariantMap());
}

QVariantMap ActionReceipt::toVariantMap() const
{
    return {{QStringLiteral("receiptId"), receiptId},
            {QStringLiteral("tool"), tool},
            {QStringLiteral("status"), status},
            {QStringLiteral("strategy"), strategy},
            {QStringLiteral("snapshotId"), snapshotId},
            {QStringLiteral("sessionId"), sessionId},
            {QStringLiteral("correlationId"), correlationId},
            {QStringLiteral("payloadHash"), payloadHash},
            {QStringLiteral("resultHash"), resultHash},
            {QStringLiteral("detail"), redactForEvidence(detail)},
            {QStringLiteral("createdAt"), createdAt},
            {QStringLiteral("target"), target}};
}

bool SessionLease::consume()
{
    if (!active || actions >= maxActions) {
        active = false;
        return false;
    }
    ++actions;
    return true;
}

QVariantMap SessionLease::toVariantMap() const
{
    return {{QStringLiteral("leaseId"), leaseId},
            {QStringLiteral("sessionId"), sessionId},
            {QStringLiteral("scopeKind"), scopeKind},
            {QStringLiteral("targetId"), targetId},
            {QStringLiteral("expiresAt"), expiresAt},
            {QStringLiteral("maxActions"), maxActions},
            {QStringLiteral("actions"), actions},
            {QStringLiteral("active"), active}};
}

ProcessSessionGuard::~ProcessSessionGuard()
{
    release();
}

QString ProcessSessionGuard::lockPath()
{
    QString root = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    if (root.isEmpty()) root = QDir::tempPath() + QStringLiteral("/LlamaCode");
    QDir().mkpath(root);
    return QDir(root).filePath(QStringLiteral("desktop-computer-use.lock"));
}

bool ProcessSessionGuard::acquire(QString *error)
{
    if (isHeld()) return true;
    release();
    m_lock = std::make_unique<QLockFile>(lockPath());
    m_lock->setStaleLockTime(30000);
    if (m_lock->tryLock(0)) return true;
    if (error) *error = QStringLiteral(
        "otra instancia ya controla el escritorio; detené esa corrida o esperá a que libere la sesión");
    m_lock.reset();
    return false;
}

void ProcessSessionGuard::release()
{
    if (!m_lock) return;
    if (m_lock->isLocked()) m_lock->unlock();
    m_lock.reset();
}

bool ProcessSessionGuard::isHeld() const
{
    return m_lock && m_lock->isLocked();
}

QString stableHash(const QVariantMap &value)
{
    const QByteArray bytes = QJsonDocument(QJsonObject::fromVariantMap(value))
                                  .toJson(QJsonDocument::Compact);
    return QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256)
                                   .toHex().left(24));
}

QString targetIdText(const QJsonValue &value)
{
    if (value.isString()) return value.toString();
    if (!value.isDouble()) return {};

    const double number = value.toDouble();
    constexpr double maxSafeJsonInteger = 9007199254740991.0;
    if (!std::isfinite(number) || number < 0.0 || number > maxSafeJsonInteger
        || std::floor(number) != number)
        return {};
    return QString::number(static_cast<qulonglong>(number));
}

QString controlIdText(const QJsonValue &value)
{
    if (value.isString()) return value.toString();
    if (!value.isDouble()) return {};

    const double number = value.toDouble();
    constexpr double maxSafeJsonInteger = 9007199254740991.0;
    if (!std::isfinite(number) || number < 0.0 || number > maxSafeJsonInteger)
        return {};

    // Let Qt use the same compact JSON number spelling that it parsed. This
    // retains fractional runtime IDs instead of calling QJsonValue::toString(),
    // which returns an empty string for every number.
    QJsonArray wrapped{value};
    const QByteArray serialized = QJsonDocument(wrapped).toJson(QJsonDocument::Compact);
    if (serialized.size() < 3 || serialized.front() != '[' || serialized.back() != ']')
        return {};
    return QString::fromLatin1(serialized.mid(1, serialized.size() - 2));
}

QString snapshotId(const QString &scopeKind, const QString &targetId,
                   const QVariantMap &target, const QVariantList &windows,
                   const QVariantList &controls)
{
    return stableHash({{QStringLiteral("scopeKind"), scopeKind},
                       {QStringLiteral("targetId"), targetId},
                       {QStringLiteral("target"), target},
                       {QStringLiteral("windows"), windows},
                       {QStringLiteral("controls"), controls}});
}

QVariantList snapshotIdentityWindows(const QString &scopeKind,
                                     const QVariantMap &target,
                                     const QVariantList &visibleWindows)
{
    if (scopeKind != QLatin1String("window")) return visibleWindows;
    return target.isEmpty() ? QVariantList{} : QVariantList{target};
}

QVariantList snapshotIdentityControls(const QVariantList &presentedControls,
                                      const QVariantList &canonicalControls)
{
    return canonicalControls.isEmpty() ? presentedControls : canonicalControls;
}

bool snapshotMatches(const QString &expected, const QString &actual, QString *error)
{
    if (expected.trimmed().isEmpty()) return true;
    if (expected == actual) return true;
    if (error) *error = QStringLiteral(
        "El snapshot quedó obsoleto; la ventana o sus controles cambiaron. Observá de nuevo antes de actuar.");
    return false;
}

ActionReceipt makeReceipt(const QString &tool, const QJsonObject &args, bool ok,
                          const QString &result, const QString &sessionId,
                          const QString &correlationId, const QString &strategy,
                          const QString &snapshot, const QVariantMap &target)
{
    ActionReceipt receipt;
    receipt.receiptId = QUuid::createUuid().toString(QUuid::WithoutBraces);
    receipt.tool = tool;
    receipt.status = ok ? QStringLiteral("settled") : QStringLiteral("failed");
    receipt.strategy = strategy.isEmpty() ? QStringLiteral("native") : strategy;
    receipt.snapshotId = snapshot;
    receipt.sessionId = sessionId;
    receipt.correlationId = correlationId;
    receipt.payloadHash = QString::fromLatin1(QCryptographicHash::hash(
        QJsonDocument(args).toJson(QJsonDocument::Compact), QCryptographicHash::Sha256).toHex());
    receipt.resultHash = QString::fromLatin1(QCryptographicHash::hash(
        result.toUtf8(), QCryptographicHash::Sha256).toHex());
    receipt.detail = redactForEvidence(result.left(600));
    receipt.createdAt = QDateTime::currentMSecsSinceEpoch();
    receipt.target = target;
    return receipt;
}

bool isDesktopTool(const QString &name)
{
    return name.startsWith(QStringLiteral("desktop_"));
}

QString inferScopeKind(const QString &explicitKind, bool targetIsWindow,
                       const QString &fallback)
{
    const QString k = explicitKind.trimmed().toLower();
    if (k == QLatin1String("window") || k == QLatin1String("screen")) return k;
    return targetIsWindow ? QStringLiteral("window") : fallback;
}

bool typingTargetAllowed(const QString &foregroundId, const QString &agentFocusedId,
                         qulonglong foregroundPid, qulonglong selectedPid)
{
    if (agentFocusedId.isEmpty()) return false;
    if (foregroundPid != 0 && selectedPid != 0 && foregroundPid != selectedPid)
        return false;
    if (foregroundPid != 0 && selectedPid != 0 && foregroundPid == selectedPid)
        return true;
    return foregroundId.isEmpty() || foregroundId.compare(agentFocusedId, Qt::CaseInsensitive) == 0;
}

QString keyFocusChangeHint(const QString &beforeId, qulonglong beforePid,
                           const QString &afterId, qulonglong afterPid,
                           qulonglong selectedPid)
{
    const bool idChanged = beforeId.compare(afterId, Qt::CaseInsensitive) != 0;
    const bool pidChanged = beforePid != 0 && afterPid != 0 && beforePid != afterPid;
    if (!idChanged && !pidChanged) return {};

    if (selectedPid != 0 && afterPid != 0 && afterPid != selectedPid) {
        return QStringLiteral(
            " El foco quedó fuera de la aplicación elegida; no escribas todavía. "
            "Observá el estado actual y volvé a resolver el destino.");
    }
    if (selectedPid != 0 && afterPid == selectedPid) {
        return QStringLiteral(
            " El foco cambió dentro de la aplicación elegida. Puede ser un cambio normal de control. "
            "Observá el estado actual antes de seguir; no supongas que se abrió un diálogo ni "
            "presiones Enter para comprobarlo.");
    }
    return QStringLiteral(
        " El foco cambió; observá la ventana actual antes de seguir.");
}

bool typingNeedsRefocus(const QString &foregroundId, const QString &agentFocusedId)
{
    return !agentFocusedId.isEmpty() && !typingTargetAllowed(foregroundId, agentFocusedId);
}

int clampClickCount(int clickCount)
{
    return qBound(1, clickCount, 3);
}

static QString foldForMatch(const QString &s);

QString launchAlias(const QString &app)
{
    const QString key = foldForMatch(app.trimmed()).simplified();
    static const QHash<QString, QString> aliases{
        {QStringLiteral("calculator"), QStringLiteral("calc")},
        {QStringLiteral("calculadora"), QStringLiteral("calc")},
        {QStringLiteral("calculadora de windows"), QStringLiteral("calc")},
        {QStringLiteral("windows calculator"), QStringLiteral("calc")},
        {QStringLiteral("bloc de notas"), QStringLiteral("notepad")},
        {QStringLiteral("notas"), QStringLiteral("notepad")},
        {QStringLiteral("paint"), QStringLiteral("mspaint")},
        {QStringLiteral("explorador"), QStringLiteral("explorer")},
        {QStringLiteral("explorador de archivos"), QStringLiteral("explorer")},
        {QStringLiteral("file explorer"), QStringLiteral("explorer")},
        {QStringLiteral("configuracion"), QStringLiteral("ms-settings:")},
        {QStringLiteral("settings"), QStringLiteral("ms-settings:")},
        {QStringLiteral("terminal"), QStringLiteral("wt")},
        {QStringLiteral("simbolo del sistema"), QStringLiteral("cmd")},
        {QStringLiteral("administrador de tareas"), QStringLiteral("taskmgr")},
        {QStringLiteral("task manager"), QStringLiteral("taskmgr")},
    };
    const auto it = aliases.constFind(key);
    return it != aliases.constEnd() ? it.value() : app.trimmed();
}

QStringList splitLaunchArguments(const QString &args)
{
    return QProcess::splitCommand(args.trimmed());
}

QString launchTargetIdentity(const QString &app, const QString &args)
{
    QString canonicalApp = launchAlias(app).trimmed().toCaseFolded();
    if (canonicalApp.endsWith(QLatin1String(".exe"))) canonicalApp.chop(4);

    QJsonArray canonicalArguments;
    for (QString argument : splitLaunchArguments(args)) {
        const QFileInfo path(argument);
        if (path.isAbsolute()) argument = QDir::cleanPath(argument).toCaseFolded();
        canonicalArguments.append(argument);
    }

    QJsonArray identity;
    identity.append(canonicalApp);
    identity.append(canonicalArguments);
    return QString::fromUtf8(QJsonDocument(identity).toJson(QJsonDocument::Compact));
}

// Palabras que aparecen en el título de la ventana de una app conocida.
static QStringList launchTitleHints(const QString &app)
{
    const QString alias = launchAlias(app);
    QStringList hints{foldForMatch(app.trimmed()), foldForMatch(alias)};
    static const QHash<QString, QStringList> titles{
        {QStringLiteral("calc"), {QStringLiteral("calculadora"), QStringLiteral("calculator")}},
        {QStringLiteral("notepad"), {QStringLiteral("bloc de notas"), QStringLiteral("notepad")}},
        {QStringLiteral("mspaint"), {QStringLiteral("paint")}},
        {QStringLiteral("explorer"), {QStringLiteral("explorador"), QStringLiteral("explorer")}},
        {QStringLiteral("ms-settings:"), {QStringLiteral("configuracion"), QStringLiteral("settings")}},
        {QStringLiteral("taskmgr"), {QStringLiteral("administrador de tareas"), QStringLiteral("task manager")}},
        {QStringLiteral("wt"), {QStringLiteral("terminal")}},
    };
    hints += titles.value(foldForMatch(alias));
    // Ruta a un .exe: el nombre base sin extensión.
    QString base = alias.section(QLatin1Char('/'), -1).section(QLatin1Char('\\'), -1);
    if (base.endsWith(QLatin1String(".exe"), Qt::CaseInsensitive)) base.chop(4);
    hints << foldForMatch(base);
    hints.removeAll(QString());
    hints.removeDuplicates();
    return hints;
}

static bool titleMatchesApp(const QVariantMap &row, const QStringList &hints)
{
    const QString title = foldForMatch(row.value(QStringLiteral("label")).toString());
    if (title.isEmpty()) return false;
    for (const QString &h : hints)
        if (h.size() >= 3 && title.contains(h)) return true;
    return false;
}

QVariantMap pickLaunchedWindow(const QVariantList &before, const QVariantList &after,
                               const QString &app)
{
    QSet<QString> known;
    for (const QVariant &v : before) known.insert(v.toMap().value(QStringLiteral("id")).toString());
    const QStringList hints = launchTitleHints(app);
    QVariantMap best, dialog;
    int bestScore = -1;
    for (const QVariant &v : after) {
        const QVariantMap row = v.toMap();
        if (known.contains(row.value(QStringLiteral("id")).toString())) continue;
        if (row.value(QStringLiteral("className")).toString() == QLatin1String("#32770")) {
            if (dialog.isEmpty()) dialog = row;
            continue;
        }
        const qint64 area = qint64(row.value(QStringLiteral("width")).toInt())
                            * row.value(QStringLiteral("height")).toInt();
        // La coincidencia de título manda; el área desempata.
        const int score = (titleMatchesApp(row, hints) ? 1 << 30 : 0)
                          + int(qMin<qint64>(area, (1 << 30) - 1) >> 4);
        if (score > bestScore) { bestScore = score; best = row; }
    }
    if (!best.isEmpty()) {
        best.insert(QStringLiteral("titleMatch"), titleMatchesApp(best, hints));
        return best;
    }
    if (!dialog.isEmpty()) {
        dialog.insert(QStringLiteral("dialog"), true);
        return dialog;
    }
    for (const QVariant &v : after) {
        QVariantMap row = v.toMap();
        if (titleMatchesApp(row, hints)) {
            row.insert(QStringLiteral("existing"), true);
            return row;
        }
    }
    return {};
}

QVariantMap largestWindowForProcess(const QVariantList &windows, qulonglong pid,
                                    const QString &excludeId)
{
    if (pid == 0) return {};
    QVariantMap best;
    qint64 bestArea = 0;
    for (const QVariant &value : windows) {
        const QVariantMap row = value.toMap();
        if (row.value(QStringLiteral("pid")).toULongLong() != pid
            || row.value(QStringLiteral("id")).toString() == excludeId)
            continue;
        const qint64 area = qint64(row.value(QStringLiteral("width")).toInt())
                            * row.value(QStringLiteral("height")).toInt();
        if (area > bestArea) {
            best = row;
            bestArea = area;
        }
    }
    return best;
}

QVariantMap resolveSelectedWindow(const QVariantList &windows, const QString &selectedId,
                                  qulonglong pid)
{
    if (pid == 0) return {};
    for (const QVariant &value : windows) {
        const QVariantMap row = value.toMap();
        if (row.value(QStringLiteral("id")).toString() == selectedId
            && row.value(QStringLiteral("pid")).toULongLong() == pid)
            return row;
    }
    return largestWindowForProcess(windows, pid, selectedId);
}

qulonglong selectedWindowProcessId(const QVariantList &windows, const QString &selectedId,
                                   qulonglong knownPid)
{
    if (knownPid != 0) return knownPid;
    for (const QVariant &value : windows) {
        const QVariantMap row = value.toMap();
        if (row.value(QStringLiteral("id")).toString() == selectedId)
            return row.value(QStringLiteral("pid")).toULongLong();
    }
    return 0;
}

int clampControlLimit(int requested, int fallback)
{
    const int value = requested > 0 ? requested : fallback;
    return qBound(1, value, 80);
}

QString formatLaunchResult(const QString &app, const QVariantMap &window, bool background,
                           bool *ok)
{
    if (ok) *ok = true;
    const QString id = window.value(QStringLiteral("id")).toString();
    const QString title = window.value(QStringLiteral("label")).toString();
    if (window.isEmpty() || id.isEmpty()) {
        if (ok) *ok = false;
        return QStringLiteral(
            "[desktop_launch: lancé '%1' pero no apareció una ventana interactiva en el tiempo "
            "esperado. No escribas en otra app; espera y vuelve a buscar una sola vez con "
            "desktop_windows.]").arg(app);
    }
    if (window.value(QStringLiteral("dialog")).toBool()) {
        if (ok) *ok = false;
        return QStringLiteral(
            "[desktop_launch: en vez de la app apareció un diálogo del sistema \"%1\" (id=\"%2\"): "
            "probablemente Windows no pudo abrir '%3'. NO escribas en ese diálogo. Probá con el "
            "ejecutable (ej. 'calc', 'notepad') o una ruta completa.]").arg(title, id, app);
    }
    const QString which = window.value(QStringLiteral("existing")).toBool()
        ? QStringLiteral("ya estaba abierta (no apareció otra)")
        : QStringLiteral("se abrió");
    const bool existing = window.value(QStringLiteral("existing")).toBool();
    const QString next = background
        ? QStringLiteral("Seguí con desktop_controls target_id=\"%1\" y desktop_control_action.").arg(id)
        : existing
            ? QStringLiteral("La ventana ya existía y no se seleccionó automáticamente. "
                             "Confirma primero el título con desktop_read_text target_id=\"%1\"; "
                             "después elígela con desktop_focus target_id=\"%1\" antes de "
                             "escribir o pulsar teclas. También puedes pasar ese target_id "
                             "explícitamente a desktop_type/desktop_key.").arg(id)
        : QStringLiteral("Ya está en primer plano: podés usar desktop_type/desktop_key directo "
                         "(o desktop_controls target_id=\"%1\" para botones). Si una lectura "
                         "informa que el HWND fue reemplazado, usa el id nuevo y llama "
                         "desktop_focus antes de cualquier desktop_key/desktop_type; desktop_key "
                         "actúa sobre la última ventana enfocada. Para leer el resultado: "
                         "desktop_read_text target_id=\"%1\".").arg(id);
    // La Calculadora no resuelve hasta el '=': el agente tecleaba "3*3", la pantalla
    // quedaba en "3 ×  3" y el modelo informaba "9" sin que existiera.
    QString calcHint;
    const QString launched = launchAlias(app).toLower();
    if (launched == QLatin1String("calc") || launched == QLatin1String("calc.exe"))
        calcHint = background
            ? QStringLiteral(" Calculadora: el resultado aparece recién al accionar el botón "
                             "\"Es igual a\"; leelo después con desktop_read_text.")
            : QStringLiteral(" Calculadora: la cuenta se resuelve recién con '=': tipeá la "
                             "expresión terminada en '=' (ej. \"3*3=\") y leé el resultado.");
    return QStringLiteral("[desktop_launch: ok — la ventana %1: id=%2 \"%3\". Usa ese "
                          "valor exacto como target_id (sin agregar comillas al valor); el "
                          "JSON ya delimita el string. NO hace falta desktop_windows. %4%5]")
        .arg(which, id, title, next, calcHint);
}

bool usesUserInput(const QString &tool)
{
    static const QSet<QString> input{
        QStringLiteral("desktop_click"), QStringLiteral("desktop_click_text"),
        QStringLiteral("desktop_click_image"), QStringLiteral("desktop_hover"),
        QStringLiteral("desktop_key"), QStringLiteral("desktop_type"),
        QStringLiteral("desktop_scroll"), QStringLiteral("desktop_stroke"),
        QStringLiteral("desktop_focus"), QStringLiteral("desktop_resize"),
        QStringLiteral("desktop_clipboard")};
    return input.contains(tool);
}

QString computerUseChoice(const QString &approvalMode, const QString &sessionMode,
                          bool wantsDesktop)
{
    if (!wantsDesktop) return QString();
    const QString mode = sessionMode.trimmed().toLower();
    if (mode == QLatin1String("background") || mode == QLatin1String("foreground"))
        return mode;
    if (approvalMode.trimmed().toLower() == QLatin1String("super"))
        return QStringLiteral("foreground");
    return QStringLiteral("ask");
}

bool launchTargetIsPathOrUri(const QString &program)
{
    const QString p = program.trimmed();
    if (p.contains(QLatin1Char('/')) || p.contains(QLatin1Char('\\'))) return true;
    // "ms-settings:", "https:", "C:" ... (un esquema sin barras también vale).
    const int colon = p.indexOf(QLatin1Char(':'));
    return colon > 0;
}

static QString foldForMatch(const QString &s)
{
    QString d = s.normalized(QString::NormalizationForm_D);
    QString out;
    out.reserve(d.size());
    for (const QChar c : d)
        if (c.category() != QChar::Mark_NonSpacing) out.append(c.toLower());
    return out;
}

QString expectedDocumentNameFromLaunchArguments(const QString &args,
                                                const QString &workingDirectory)
{
    const QStringList tokens = splitLaunchArguments(args);
    QString expectedName;
    for (QString token : tokens) {
        const qsizetype equals = token.indexOf(QLatin1Char('='));
        if (equals >= 0) token = token.mid(equals + 1);
        if (token.isEmpty()) continue;
        if (token.startsWith(QStringLiteral("http://"), Qt::CaseInsensitive)
            || token.startsWith(QStringLiteral("https://"), Qt::CaseInsensitive))
            continue;
        QFileInfo candidate(token);
        if (candidate.isRelative() && !workingDirectory.isEmpty())
            candidate = QFileInfo(QDir(workingDirectory).filePath(token));
        if (candidate.exists() && candidate.isFile())
            expectedName = candidate.fileName();
        else if (!candidate.exists() && !candidate.suffix().isEmpty()
                 && (token.contains(QLatin1Char('/')) || token.contains(QLatin1Char('\\'))))
            // Keep the guard active for a path-like file argument that is mistyped
            // or stale. A missing file must not make the launch look like an app-only
            // launch and allow input into a generic empty window.
            expectedName = candidate.fileName();
    }
    return expectedName;
}

namespace {
bool documentNameIsVisible(const QString &expectedName, const QString &windowTitle,
                           const QString &visibleText)
{
    Q_UNUSED(visibleText);
    const QString expected = foldForMatch(expectedName.trimmed());
    if (expected.isEmpty()) return false;

    static const QStringList openErrors{
        QStringLiteral("no hemos encontrado"), QStringLiteral("no se encuentra"),
        QStringLiteral("no encontrado"), QStringLiteral("could not find"),
        QStringLiteral("cannot find"), QStringLiteral("can't find"),
        QStringLiteral("not found"), QStringLiteral("failed to open"),
        QStringLiteral("unable to open")};
    // El cuerpo del documento puede contener literalmente el nombre pedido
    // (por ejemplo, una pestaña restaurada con "CU19-alpha.txt" dentro de un
    // documento CU19-beta.txt). Sólo el título identifica qué archivo está
    // realmente abierto para esta guarda.
    const QString foldedTitle = foldForMatch(windowTitle.trimmed());
    if (!foldedTitle.contains(expected)) return false;
    for (const QString &marker : openErrors) {
        if (foldedTitle.contains(marker)) return false;
    }
    return true;
}
} // namespace

void LaunchDocumentGuard::reset()
{
    m_expectedName.clear();
    m_targetId.clear();
}

void LaunchDocumentGuard::arm(const QString &expectedName, const QString &targetId,
                              const QString &initialWindowTitle)
{
    reset();
    const QString name = QFileInfo(expectedName).fileName().trimmed();
    if (name.isEmpty() || targetId.isEmpty()
        || documentNameIsVisible(name, initialWindowTitle, QString()))
        return;
    m_expectedName = name;
    m_targetId = targetId;
}

void LaunchDocumentGuard::rebindTarget(const QString &oldTargetId, const QString &newTargetId)
{
    if (pending() && !newTargetId.isEmpty() && m_targetId == oldTargetId)
        m_targetId = newTargetId;
}

bool LaunchDocumentGuard::observe(const QString &targetId, const QString &windowTitle,
                                  const QString &visibleText)
{
    if (!pending() || targetId != m_targetId
        || !documentNameIsVisible(m_expectedName, windowTitle, visibleText))
        return false;
    reset();
    return true;
}

bool LaunchDocumentGuard::blocks(const QString &tool) const
{
    return pending() && isDesktopActionTool(tool)
        && tool != QLatin1String("desktop_launch")
        && tool != QLatin1String("desktop_focus");
}

QString LaunchDocumentGuard::pendingNote(const QString &windowTitle) const
{
    if (!pending()) return {};
    const QString title = windowTitle.trimmed().isEmpty()
        ? QStringLiteral("(sin título visible)") : windowTitle.trimmed();
    return QStringLiteral("[desktop_document_guard: archivo solicitado '%1' aún no confirmado; "
                          "ventana actual '%2'. No interactúes con el documento. Usa "
                          "desktop_windows para ubicar una ventana cuyo título identifique "
                          "ese archivo; desktop_focus puede seleccionarla y desktop_read_text "
                          "puede verificar el título. Si no aparece, detente sin modificar nada.]")
        .arg(m_expectedName, title);
}

QString LaunchDocumentGuard::blockedActionMessage(const QString &tool) const
{
    if (!pending()) return {};
    return QStringLiteral("[%1: NO ejecuté la acción — el archivo solicitado '%2' todavía no "
                          "está confirmado en la ventana iniciada. Usa desktop_windows para "
                          "ubicar el target correcto, enfócalo con desktop_focus y verifica el "
                          "título con desktop_read_text; no continúes hasta ver el nombre exacto.]")
        .arg(tool, m_expectedName, m_targetId);
}

QString formatReadText(const QList<TextLine> &lines, const QRect &bounds,
                       const QString &query, int maxLines)
{
    const QString q = foldForMatch(query.trimmed());
    const int cap = qBound(1, maxLines, 400);
    QStringList out;
    int matched = 0;
    for (const TextLine &l : lines) {
        const QString text = l.text.simplified();
        if (text.isEmpty()) continue;
        if (!q.isEmpty() && !foldForMatch(text).contains(q)) continue;
        ++matched;
        if (out.size() >= cap) continue;
        // QRectF: QRect::center() redondea hacia abajo (convención de píxeles
        // inclusivos) y corre el punto medio un píxel.
        const QPointF c = QRectF(l.rect).center();
        const double nx = bounds.width() > 0 ? (c.x() - bounds.x()) / double(bounds.width()) : 0.0;
        const double ny = bounds.height() > 0 ? (c.y() - bounds.y()) / double(bounds.height()) : 0.0;
        out << QStringLiteral("(%1, %2)  %3")
                   .arg(qBound(0.0, nx, 1.0), 0, 'f', 3)
                   .arg(qBound(0.0, ny, 1.0), 0, 'f', 3)
                   .arg(text);
    }
    QString head = QStringLiteral("%1 renglón(es)").arg(matched);
    if (matched > out.size())
        head += QStringLiteral(" (mostrando %1; filtrá con query)").arg(out.size());
    return head + QLatin1Char('\n') + out.join(QLatin1Char('\n'));
}

QStringList uiaReadableText(const QVariantList &controls, const QString &query, int max)
{
    const QString q = foldForMatch(query.trimmed());
    const int cap = qBound(1, max, 200);
    QStringList out;
    QSet<QString> seen;
    for (const QVariant &v : controls) {
        if (out.size() >= cap) break;
        const QVariantMap c = v.toMap();
        const QString role = c.value(QStringLiteral("role")).toString();
        const bool dataItem = role == QLatin1String("dataitem");
        const bool document = role == QLatin1String("document");
        if (role != QLatin1String("text") && role != QLatin1String("edit") && !dataItem
            && !document)
            continue;
        // Un "text" invocable suele ser un link/botón disfrazado. DataItem
        // como celdas de grilla también pueden exponer Invoke para selección,
        // pero siguen siendo contenido legible.
        if (role == QLatin1String("text")
            && c.value(QStringLiteral("invokable")).toBool()) continue;
        const QString name = c.value(QStringLiteral("name")).toString().simplified();
        const QString value = c.value(QStringLiteral("value")).toString().simplified();
        const QString documentText = c.value(QStringLiteral("text")).toString().simplified();
        if (document) {
            if (documentText.isEmpty()) continue;
            if (!q.isEmpty() && !foldForMatch(documentText).contains(q)) continue;
            const QString key = foldForMatch(documentText);
            if (seen.contains(key)) continue;
            seen.insert(key);
            out << documentText;
            continue;
        }
        // Grillas como Excel exponen cada celda como DataItem: name suele ser
        // la coordenada (D2) y ValuePattern contiene el contenido. No listar
        // celdas vacías, que pueden ser cientos y no aportan texto legible.
        if (dataItem && value.isEmpty()) continue;
        QString line = name;
        if (!value.isEmpty() && value.compare(name, Qt::CaseInsensitive) != 0)
            line = name.isEmpty() ? value : name + QStringLiteral(": ") + value;
        if (line.isEmpty()) continue;
        if (!q.isEmpty() && !foldForMatch(line).contains(q)) continue;
        const QString key = foldForMatch(line);
        if (seen.contains(key)) continue;
        seen.insert(key);
        out << line;
    }
    return out;
}

bool valueActionReadbackMatches(const QString &requested, const QString &observed)
{
    return !requested.isNull() && requested == observed;
}

bool isDesktopReadTool(const QString &name)
{
    return name == QLatin1String("desktop_windows")
        || name == QLatin1String("desktop_controls")
        || name == QLatin1String("desktop_find_image")
        || name == QLatin1String("desktop_wait_image")
        || name == QLatin1String("desktop_assert_image")
        || name == QLatin1String("desktop_observe")
        || name == QLatin1String("desktop_read_text")
        || name == QLatin1String("desktop_wait")
        || name == QLatin1String("desktop_wait_for")
        || name == QLatin1String("desktop_assert");
}

bool isDesktopActionTool(const QString &name)
{
    return isDesktopTool(name) && !isDesktopReadTool(name);
}

bool isDesktopMutationTool(const QString &name, const QVariantMap &arguments)
{
    if (name == QLatin1String("desktop_control_action"))
        return arguments.value(QStringLiteral("action")).toString().toLower()
            != QLatin1String("read");
    if (name == QLatin1String("desktop_clipboard")) {
        const QString op = arguments.contains(QStringLiteral("op"))
            ? arguments.value(QStringLiteral("op")).toString().toLower()
            : QStringLiteral("get");
        return op == QLatin1String("set");
    }

    static const QSet<QString> mutations{
        QStringLiteral("desktop_click"), QStringLiteral("desktop_click_element"),
        QStringLiteral("desktop_click_text"), QStringLiteral("desktop_click_image"),
        QStringLiteral("desktop_stroke"), QStringLiteral("desktop_type"),
        QStringLiteral("desktop_key"), QStringLiteral("desktop_scroll"),
        QStringLiteral("desktop_launch"), QStringLiteral("desktop_resize")};
    return mutations.contains(name);
}

bool isSensitiveTarget(const QVariantMap &target)
{
    if (target.value(QStringLiteral("password")).toBool()) return true;
    const QString role = target.value(QStringLiteral("role")).toString().toLower();
    const QString name = target.value(QStringLiteral("name")).toString().toLower();
    return role == QLatin1String("password")
        || name.contains(QStringLiteral("password"))
        || name.contains(QStringLiteral("contraseña"))
        || name.contains(QStringLiteral("token"))
        || name.contains(QStringLiteral("secret"));
}

bool isDestructiveLabel(const QString &text)
{
    const QString value = text.toLower();
    static const QStringList markers{
        QStringLiteral("delete"), QStringLiteral("eliminar"), QStringLiteral("borrar"),
        QStringLiteral("remove"), QStringLiteral("quitar"), QStringLiteral("format"),
        QStringLiteral("formatear"), QStringLiteral("wipe"), QStringLiteral("uninstall"),
        QStringLiteral("desinstalar"), QStringLiteral("factory reset"),
        QStringLiteral("restablecer"), QStringLiteral("vaciar"),
        QStringLiteral("empty trash"), QStringLiteral("shred")};
    for (const QString &marker : markers)
        if (value.contains(marker)) return true;
    return false;
}

QString redactForEvidence(const QString &text)
{
    QString result = text;
    static const QRegularExpression secret(
        QStringLiteral("(?i)(password|contraseña|token|secret|api[_ -]?key)\\s*[:=]\\s*[^\\s,;]+"));
    result.replace(secret, QStringLiteral("\\1=[REDACTED]"));
    return result;
}

bool normalizeKeyName(QString *key)
{
    if (!key) return false;
    if (*key != QLatin1String("\n") && *key != QLatin1String("\r")
        && *key != QLatin1String("\r\n")) {
        return false;
    }
    *key = QStringLiteral("ENTER");
    return true;
}

bool normalizeKeyChord(QString *key, QStringList *modifiers)
{
    if (!key || !modifiers) return false;
    const QString originalKey = key->trimmed().toUpper();
    static const QSet<QString> modifierNames{
        QStringLiteral("CTRL"), QStringLiteral("ALT"), QStringLiteral("SHIFT"),
        QStringLiteral("WIN")};
    if (!modifierNames.contains(originalKey)) return false;

    QStringList chordModifiers;
    QStringList chordKeys;
    for (const QString &modifier : *modifiers) {
        const QString normalized = modifier.trimmed().toUpper();
        if (normalized.isEmpty()) continue;
        if (modifierNames.contains(normalized)) chordModifiers.append(normalized);
        else chordKeys.append(normalized);
    }
    if (chordKeys.size() != 1) return false;

    chordModifiers.append(originalKey);
    chordModifiers.removeDuplicates();
    *key = chordKeys.constFirst();
    *modifiers = chordModifiers;
    return true;
}

bool shouldBlockTypingIntoExistingText(bool textEntryControl, bool hasText)
{
    return textEntryControl && hasText;
}

} // namespace DesktopComputerUse
