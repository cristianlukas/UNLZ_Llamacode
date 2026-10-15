#include "DesktopComputerUse.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QSet>
#include <QHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QLockFile>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QStringList>
#include <QUuid>

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

bool typingTargetAllowed(const QString &foregroundId, const QString &agentFocusedId)
{
    if (agentFocusedId.isEmpty()) return false;
    return foregroundId.isEmpty() || foregroundId.compare(agentFocusedId, Qt::CaseInsensitive) == 0;
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

} // namespace DesktopComputerUse
