#include "LinuxDesktopBackend.h"

#ifndef Q_OS_WIN

#include "FuzzyMatch.h"

#include <QCoreApplication>
#include <QElapsedTimer>
#include <QProcess>
#include <QProcessEnvironment>
#include <QGuiApplication>
#include <QRegularExpression>
#include <QScreen>
#include <QStandardPaths>
#include <QThread>

#include <climits>
#include <cmath>

namespace {

struct CommandResult {
    int exitCode = -1;
    QString out;
    QString err;
    bool started = false;
};

CommandResult run(const QString &program, const QStringList &arguments, int timeout = 4000)
{
    QProcess process;
    process.setProcessEnvironment(QProcessEnvironment::systemEnvironment());
    process.start(program, arguments);
    CommandResult result;
    result.started = process.waitForStarted(1200);
    if (!result.started) {
        result.err = process.errorString();
        return result;
    }
    if (!process.waitForFinished(timeout)) {
        process.kill();
        process.waitForFinished(500);
        result.err = QStringLiteral("timeout");
        return result;
    }
    result.exitCode = process.exitCode();
    result.out = QString::fromLocal8Bit(process.readAllStandardOutput());
    result.err = QString::fromLocal8Bit(process.readAllStandardError());
    return result;
}

bool has(const QString &program)
{
    return !QStandardPaths::findExecutable(program).isEmpty();
}

QString x11Id(const QString &id)
{
    const QString clean = id.trimmed();
    return clean.startsWith(QLatin1String("0x"), Qt::CaseInsensitive)
        ? clean : QStringLiteral("0x") + clean;
}

bool isValidX11Id(const QString &id)
{
    const QString clean = id.trimmed();
    if (clean.isEmpty()) return false;
    const QString digits = clean.startsWith(QLatin1String("0x"), Qt::CaseInsensitive)
        ? clean.mid(2) : clean;
    if (digits.isEmpty()) return false;
    for (const QChar ch : digits)
        if (!ch.isDigit() && !(ch.toLower() >= QLatin1Char('a')
                               && ch.toLower() <= QLatin1Char('f')))
            return false;
    return digits != QLatin1String("0");
}

QString propertyValue(const QString &text, const QString &property)
{
    const QRegularExpression line(QStringLiteral("^%1[^=]*=\\s*(.*)$")
                                      .arg(QRegularExpression::escape(property)),
                                  QRegularExpression::MultilineOption);
    const auto match = line.match(text);
    if (!match.hasMatch()) return {};
    const QString raw = match.captured(1).trimmed();
    const auto quoted = QRegularExpression(QStringLiteral("\\\"([^\\\"]*)\\\"")).match(raw);
    return quoted.hasMatch() ? quoted.captured(1) : raw;
}

QRect geometryForWindow(const QString &id)
{
    if (!isValidX11Id(id) || !has(QStringLiteral("xwininfo"))) return {};
    const CommandResult r = run(QStringLiteral("xwininfo"), {QStringLiteral("-id"), x11Id(id)});
    if (r.exitCode != 0) return {};
    const auto value = [&](const QString &name) {
        const auto m = QRegularExpression(QStringLiteral("^\\s*%1:\\s*(-?\\d+)")
                                               .arg(QRegularExpression::escape(name)),
                                           QRegularExpression::MultilineOption)
                           .match(r.out);
        return m.hasMatch() ? m.captured(1).toInt() : 0;
    };
    const int x = value(QStringLiteral("Absolute upper-left X"));
    const int y = value(QStringLiteral("Absolute upper-left Y"));
    const int w = value(QStringLiteral("Width"));
    const int h = value(QStringLiteral("Height"));
    return w > 0 && h > 0 ? QRect(x, y, w, h) : QRect();
}

QStringList clientIds()
{
    if (!has(QStringLiteral("xprop"))) return {};
    const CommandResult r = run(QStringLiteral("xprop"), {QStringLiteral("-root"),
                                                            QStringLiteral("_NET_CLIENT_LIST")});
    QStringList ids;
    const auto it = QRegularExpression(QStringLiteral("0x[0-9a-fA-F]+"))
                        .globalMatch(r.out);
    for (auto i = it; i.hasNext();) ids << i.next().captured(0).mid(2).toLower();
    return ids;
}

QVariantMap windowInfo(const QString &id)
{
    const CommandResult p = run(QStringLiteral("xprop"), {QStringLiteral("-id"), x11Id(id),
                                                             QStringLiteral("_NET_WM_NAME"),
                                                             QStringLiteral("WM_NAME"),
                                                             QStringLiteral("WM_CLASS"),
                                                             QStringLiteral("_NET_WM_PID"),
                                                             QStringLiteral("_NET_WM_STATE")});
    if (p.exitCode != 0) return {};
    QString label = propertyValue(p.out, QStringLiteral("_NET_WM_NAME"));
    if (label.isEmpty()) label = propertyValue(p.out, QStringLiteral("WM_NAME"));
    if (label.isEmpty()) return {};
    QString classLine;
    for (const QString &line : p.out.split(QLatin1Char('\n'))) {
        if (line.startsWith(QStringLiteral("WM_CLASS"))) { classLine = line; break; }
    }
    const auto classMatches = QRegularExpression(QStringLiteral("\\\"([^\\\"]*)\\\""))
                                  .globalMatch(classLine);
    QStringList classParts;
    for (auto it = classMatches; it.hasNext();) classParts << it.next().captured(1);
    const auto pidMatch = QRegularExpression(QStringLiteral("_NET_WM_PID[^=]*=\\s*(\\d+)"))
                              .match(p.out);
    const QRect rect = geometryForWindow(id);
    if (!rect.isValid()) return {};
    const QString state = propertyValue(p.out, QStringLiteral("_NET_WM_STATE"));
    return {{QStringLiteral("id"), id}, {QStringLiteral("kind"), QStringLiteral("window")},
            {QStringLiteral("label"), label.trimmed()},
            {QStringLiteral("className"), classParts.join(QStringLiteral(","))},
            {QStringLiteral("pid"), pidMatch.hasMatch() ? pidMatch.captured(1).toLongLong() : 0},
            {QStringLiteral("x"), rect.x()}, {QStringLiteral("y"), rect.y()},
            {QStringLiteral("width"), rect.width()}, {QStringLiteral("height"), rect.height()},
            {QStringLiteral("maximized"), state.contains(QStringLiteral("MAXIMIZED"))},
            {QStringLiteral("minimized"), state.contains(QStringLiteral("HIDDEN"))}};
}

bool toolError(const QString &name, QString *error)
{
    if (!has(name) && error)
        *error = QStringLiteral("Falta '%1'. Ejecutá scripts/bootstrap.sh o instalalo con el gestor de paquetes.")
                     .arg(name);
    return has(name);
}

bool runTool(const QString &name, const QStringList &args, QString *error, int timeout = 4000)
{
    if (!toolError(name, error)) return false;
    const CommandResult r = run(name, args, timeout);
    if (r.exitCode != 0 && error)
        *error = r.err.trimmed().isEmpty() ? QStringLiteral("%1 falló.").arg(name)
                                           : r.err.trimmed();
    return r.exitCode == 0;
}

QString atspiAddress()
{
    if (!has(QStringLiteral("gdbus"))) return {};
    const CommandResult r = run(QStringLiteral("gdbus"), {QStringLiteral("call"),
        QStringLiteral("--session"), QStringLiteral("--dest"), QStringLiteral("org.a11y.Bus"),
        QStringLiteral("--object-path"), QStringLiteral("/org/a11y/bus"),
        QStringLiteral("--method"), QStringLiteral("org.a11y.Bus.GetAddress")});
    const auto m = QRegularExpression(QStringLiteral("'([^']+)'" )).match(r.out);
    return m.hasMatch() ? m.captured(1) : QString();
}

CommandResult atspiCall(const QString &address, const QString &dest, const QString &path,
                        const QString &method, const QStringList &args = {})
{
    QStringList argv{QStringLiteral("call"), QStringLiteral("--address"), address,
                     QStringLiteral("--dest"), dest, QStringLiteral("--object-path"), path,
                     QStringLiteral("--method"), method};
    argv += args;
    return run(QStringLiteral("gdbus"), argv, 3000);
}

struct AtspiRef { QString dest; QString path; };

QList<AtspiRef> refsFrom(const QString &text)
{
    QList<AtspiRef> out;
    const auto it = QRegularExpression(QStringLiteral("\\('([^']+)',\\s*(?:objectpath\\s+)?'([^']+)'\\)"))
                        .globalMatch(text);
    for (auto i = it; i.hasNext();) {
        const auto m = i.next();
        out << AtspiRef{m.captured(1), m.captured(2)};
    }
    return out;
}

QString atspiProperty(const QString &address, const AtspiRef &ref, const QString &name)
{
    const CommandResult r = atspiCall(address, ref.dest, ref.path,
        QStringLiteral("org.freedesktop.DBus.Properties.Get"),
        {QStringLiteral("org.a11y.atspi.Accessible"), name});
    const auto m = QRegularExpression(QStringLiteral("'([^']*)'" )).match(r.out);
    return m.hasMatch() ? m.captured(1) : QString();
}

QString atspiMethodString(const QString &address, const AtspiRef &ref, const QString &method)
{
    const CommandResult r = atspiCall(address, ref.dest, ref.path, method);
    const auto m = QRegularExpression(QStringLiteral("'([^']*)'" )).match(r.out);
    return m.hasMatch() ? m.captured(1) : QString();
}

QRect atspiExtents(const QString &address, const AtspiRef &ref)
{
    const CommandResult r = atspiCall(address, ref.dest, ref.path,
                                       QStringLiteral("org.a11y.atspi.Component.GetExtents"),
                                       {QStringLiteral("0")});
    const auto m = QRegularExpression(QStringLiteral("\\((-?\\d+),\\s*(-?\\d+),\\s*(\\d+),\\s*(\\d+)\\)"))
                       .match(r.out);
    return m.hasMatch() ? QRect(m.captured(1).toInt(), m.captured(2).toInt(),
                                m.captured(3).toInt(), m.captured(4).toInt()) : QRect();
}

QString atspiId(const AtspiRef &ref)
{
    return QStringLiteral("atspi:")
        + QString::fromLatin1((ref.dest + QLatin1Char('\n') + ref.path).toUtf8()
                                  .toBase64(QByteArray::Base64UrlEncoding | QByteArray::OmitTrailingEquals));
}

bool refFromId(const QString &id, AtspiRef *ref)
{
    if (!ref || !id.startsWith(QLatin1String("atspi:"))) return false;
    const QByteArray raw = QByteArray::fromBase64(id.mid(6).toLatin1(), QByteArray::Base64UrlEncoding);
    const QList<QByteArray> parts = raw.split('\n');
    if (parts.size() != 2 || parts.at(0).isEmpty() || parts.at(1).isEmpty()) return false;
    ref->dest = QString::fromUtf8(parts.at(0));
    ref->path = QString::fromUtf8(parts.at(1));
    return true;
}

QVariantList atspiControlsFor(const QRect &window, const QString &query, int max)
{
    QVariantList out;
    const QString address = atspiAddress();
    if (address.isEmpty()) return out;
    const AtspiRef root{QStringLiteral("org.a11y.atspi.Registry"),
                        QStringLiteral("/org/a11y/atspi/accessible/root")};
    const auto roots = refsFrom(atspiCall(address, root.dest, root.path,
                                           QStringLiteral("org.a11y.atspi.Accessible.GetChildren")).out);
    QList<AtspiRef> queue = roots;
    const QString needle = query.trimmed().toLower();
    int visited = 0;
    while (!queue.isEmpty() && out.size() < max && visited++ < 2500) {
        const AtspiRef ref = queue.takeFirst();
        const QString role = atspiMethodString(address, ref,
                                                QStringLiteral("org.a11y.atspi.Accessible.GetRoleName"));
        const QString name = atspiProperty(address, ref, QStringLiteral("Name"));
        const QRect rect = atspiExtents(address, ref);
        const bool useful = !name.trimmed().isEmpty() && rect.isValid()
                            && rect.intersects(window)
                            && (needle.isEmpty() || name.toLower().contains(needle));
        if (useful) {
            const QString interfaces = atspiCall(address, ref.dest, ref.path,
                QStringLiteral("org.a11y.atspi.Accessible.GetInterfaces")).out;
            out.append(QVariantMap{{QStringLiteral("controlId"), atspiId(ref)},
                {QStringLiteral("name"), name}, {QStringLiteral("role"), role},
                {QStringLiteral("x"), rect.x()}, {QStringLiteral("y"), rect.y()},
                {QStringLiteral("width"), rect.width()}, {QStringLiteral("height"), rect.height()},
                {QStringLiteral("enabled"), true},
                {QStringLiteral("invokable"), interfaces.contains(QStringLiteral("Action"))},
                {QStringLiteral("interfaces"), interfaces}});
        }
        const auto children = refsFrom(atspiCall(address, ref.dest, ref.path,
            QStringLiteral("org.a11y.atspi.Accessible.GetChildren")).out);
        queue += children;
    }
    return out;
}

QVariantMap findControl(const QString &windowTargetId, const QString &controlId, bool fuzzy,
                        QString *resolvedId)
{
    const QRect window = LinuxDesktopBackend::targetBounds(QStringLiteral("window"), windowTargetId);
    if (!window.isValid()) return {};
    const QVariantList all = atspiControlsFor(window, QString(), 3000);
    for (const QVariant &v : all) {
        const QVariantMap row = v.toMap();
        if (row.value(QStringLiteral("controlId")).toString() == controlId) {
            if (resolvedId) *resolvedId = controlId;
            return row;
        }
    }
    if (!fuzzy) return {};
    QStringList names;
    for (const QVariant &v : all) names << v.toMap().value(QStringLiteral("name")).toString();
    const FuzzyMatch::Match match = FuzzyMatch::extractOne(controlId, names);
    if (!match.ok() || match.index < 0 || match.index >= all.size()) return {};
    if (resolvedId) *resolvedId = all.at(match.index).toMap().value(QStringLiteral("controlId")).toString();
    return all.at(match.index).toMap();
}

} // namespace

QVariantList LinuxDesktopBackend::windows()
{
    QVariantList out;
    for (const QString &id : clientIds()) {
        const QVariantMap row = windowInfo(id);
        if (!row.isEmpty()) out << row;
    }
    return out;
}

QRect LinuxDesktopBackend::targetBounds(const QString &kind, const QString &targetId)
{
    if (kind == QLatin1String("window")) return geometryForWindow(targetId);
    if (kind == QLatin1String("screen")) {
        bool ok = false;
        const int index = targetId.toInt(&ok);
        const auto screenList = QGuiApplication::screens();
        if (ok && index >= 0 && index < screenList.size()) return screenList.at(index)->geometry();
        return QGuiApplication::primaryScreen() ? QGuiApplication::primaryScreen()->geometry() : QRect();
    }
    return {};
}

bool LinuxDesktopBackend::interactiveSessionAvailable()
{
    return !qEnvironmentVariableIsEmpty("DISPLAY") && has(QStringLiteral("xprop"));
}

bool LinuxDesktopBackend::launchApp(const QString &app, const QString &args, QString *error)
{
    const QString program = app.trimmed();
    if (program.isEmpty()) { if (error) *error = QStringLiteral("Falta el nombre de la app a lanzar."); return false; }
    QString actual = program;
    QStringList argv = QProcess::splitCommand(args);
    if (program.contains(QLatin1String("://")) || program.endsWith(QLatin1Char(':'))) {
        actual = QStringLiteral("xdg-open"); argv.prepend(program);
    }
    if (!has(actual)) { if (error) *error = QStringLiteral("No se encontró el programa: %1").arg(actual); return false; }
    if (!QProcess::startDetached(actual, argv)) {
        if (error) *error = QStringLiteral("No se pudo lanzar: %1").arg(program); return false;
    }
    return true;
}

bool LinuxDesktopBackend::focusWindow(const QString &targetId, QString *error)
{
    if (has(QStringLiteral("wmctrl")))
        return runTool(QStringLiteral("wmctrl"), {QStringLiteral("-ia"), x11Id(targetId)}, error);
    return runTool(QStringLiteral("xdotool"), {QStringLiteral("windowactivate"),
                                                QStringLiteral("--sync"), x11Id(targetId)}, error);
}

bool LinuxDesktopBackend::setWindowMaximized(const QString &targetId, bool maximized, QString *error)
{
    if (!toolError(QStringLiteral("wmctrl"), error)) return false;
    return runTool(QStringLiteral("wmctrl"), {QStringLiteral("-ir"), x11Id(targetId),
        QStringLiteral("-b"), maximized ? QStringLiteral("add,maximized_vert,maximized_horz")
                                        : QStringLiteral("remove,maximized_vert,maximized_horz")}, error);
}

bool LinuxDesktopBackend::setWindowSize(const QString &targetId, int width, int height, QString *error)
{
    if (width <= 0 || height <= 0) { if (error) *error = QStringLiteral("El tamaño de ventana no es válido."); return false; }
    return runTool(QStringLiteral("wmctrl"), {QStringLiteral("-ir"), x11Id(targetId),
        QStringLiteral("-e"), QStringLiteral("0,-1,-1,%1,%2").arg(width).arg(height)}, error);
}

bool LinuxDesktopBackend::click(const QString &kind, const QString &targetId, double x, double y,
                                const QString &button, QString *error, QVariantMap *trace)
{
    const QRect bounds = targetBounds(kind, targetId);
    if (!bounds.isValid()) { if (error) *error = QStringLiteral("Alcance visual no disponible."); return false; }
    const QPoint p(bounds.x() + qRound(x * bounds.width()), bounds.y() + qRound(y * bounds.height()));
    if (kind == QLatin1String("window") && !focusWindow(targetId, error)) return false;
    const QString b = button.trimmed().toLower();
    const QString n = b == QLatin1String("right") ? QStringLiteral("3")
                      : b == QLatin1String("middle") ? QStringLiteral("2") : QStringLiteral("1");
    if (!runTool(QStringLiteral("xdotool"), {QStringLiteral("mousemove"),
        QString::number(p.x()), QString::number(p.y()), QStringLiteral("click"), n}, error)) return false;
    if (trace) *trace = {{QStringLiteral("surface"), QStringLiteral("desktop")},
        {QStringLiteral("action"), QStringLiteral("click")},
        {QStringLiteral("strategy"), QStringLiteral("x11-xtest")},
        {QStringLiteral("pointer"), QVariantMap{{QStringLiteral("button"), b},
            {QStringLiteral("xAbs"), p.x()}, {QStringLiteral("yAbs"), p.y()},
            {QStringLiteral("xNorm"), x}, {QStringLiteral("yNorm"), y}}}};
    return true;
}

bool LinuxDesktopBackend::stroke(const QString &kind, const QString &targetId,
                                 const QVariantList &points, const QString &button, int holdMs,
                                 QString *error, QVariantMap *trace)
{
    if (points.size() < 2) { if (error) *error = QStringLiteral("Una traza necesita al menos 2 puntos."); return false; }
    const QRect bounds = targetBounds(kind, targetId);
    if (!bounds.isValid()) { if (error) *error = QStringLiteral("Alcance visual no disponible."); return false; }
    if (kind == QLatin1String("window") && !focusWindow(targetId, error)) return false;
    const QString n = button.trimmed().toLower() == QLatin1String("right") ? QStringLiteral("3")
                      : button.trimmed().toLower() == QLatin1String("middle") ? QStringLiteral("2") : QStringLiteral("1");
    auto point = [&](const QVariant &v) { const auto m = v.toMap(); return QPoint(
        bounds.x() + qRound(m.value(QStringLiteral("x")).toDouble() * bounds.width()),
        bounds.y() + qRound(m.value(QStringLiteral("y")).toDouble() * bounds.height())); };
    const QPoint first = point(points.first()), last = point(points.last());
    if (!runTool(QStringLiteral("xdotool"), {QStringLiteral("mousemove"), QString::number(first.x()), QString::number(first.y()),
        QStringLiteral("mousedown"), n}, error)) return false;
    for (int i = 1; i < points.size(); ++i) {
        const QPoint a = point(points.at(i - 1)), c = point(points.at(i));
        const int steps = qBound(1, qMax(qAbs(c.x() - a.x()), qAbs(c.y() - a.y())) / 4, 400);
        for (int s = 1; s <= steps; ++s) {
            const QPoint p(a.x() + (c.x() - a.x()) * s / steps, a.y() + (c.y() - a.y()) * s / steps);
            if (!runTool(QStringLiteral("xdotool"), {QStringLiteral("mousemove"), QString::number(p.x()), QString::number(p.y())}, error)) return false;
            QThread::msleep(qBound(1, holdMs, 200));
        }
    }
    if (!runTool(QStringLiteral("xdotool"), {QStringLiteral("mouseup"), n}, error)) return false;
    if (trace) *trace = {{QStringLiteral("surface"), QStringLiteral("desktop")},
        {QStringLiteral("action"), QStringLiteral("stroke")}, {QStringLiteral("strategy"), QStringLiteral("x11-xtest")},
        {QStringLiteral("pointer"), QVariantMap{{QStringLiteral("button"), button}, {QStringLiteral("points"), points.size()},
            {QStringLiteral("xAbsStart"), first.x()}, {QStringLiteral("yAbsStart"), first.y()},
            {QStringLiteral("xAbsEnd"), last.x()}, {QStringLiteral("yAbsEnd"), last.y()}}}};
    return true;
}

bool LinuxDesktopBackend::typeText(const QString &text, QString *error)
{
    return runTool(QStringLiteral("xdotool"), {QStringLiteral("type"), QStringLiteral("--clearmodifiers"),
                                                QStringLiteral("--delay"), QStringLiteral("0"), text}, error);
}

bool LinuxDesktopBackend::pressKey(const QString &key, const QStringList &modifiers, QString *error)
{
    QStringList chord;
    for (const QString &raw : modifiers) {
        const QString m = raw.trimmed().toLower();
        chord << (m == QLatin1String("ctrl") ? QStringLiteral("ctrl")
                  : m == QLatin1String("alt") ? QStringLiteral("alt")
                  : m == QLatin1String("shift") ? QStringLiteral("shift")
                  : m == QLatin1String("win") || m == QLatin1String("meta") ? QStringLiteral("super") : m);
    }
    QString k = key.trimmed().toLower();
    if (k == QLatin1String("escape")) k = QStringLiteral("esc");
    if (k == QLatin1String("return")) k = QStringLiteral("enter");
    chord << k;
    return runTool(QStringLiteral("xdotool"), {QStringLiteral("key"), chord.join(QLatin1Char('+'))}, error);
}

bool LinuxDesktopBackend::scroll(int delta, QString *error)
{
    const int count = qMax(1, qAbs(delta) / 120);
    const QString button = delta >= 0 ? QStringLiteral("4") : QStringLiteral("5");
    return runTool(QStringLiteral("xdotool"), {QStringLiteral("click"), QStringLiteral("--repeat"), QString::number(count), button}, error);
}

QPoint LinuxDesktopBackend::cursorPos()
{
    const CommandResult r = run(QStringLiteral("xdotool"), {QStringLiteral("getmouselocation"), QStringLiteral("--shell")});
    const auto x = QRegularExpression(QStringLiteral("(?:^|\\n)X=(\\d+)" )).match(r.out);
    const auto y = QRegularExpression(QStringLiteral("(?:^|\\n)Y=(\\d+)" )).match(r.out);
    return x.hasMatch() && y.hasMatch() ? QPoint(x.captured(1).toInt(), y.captured(1).toInt()) : QPoint();
}

bool LinuxDesktopBackend::moveCursor(const QPoint &physical)
{
    return runTool(QStringLiteral("xdotool"), {QStringLiteral("mousemove"), QString::number(physical.x()), QString::number(physical.y())}, nullptr);
}

QVariantList LinuxDesktopBackend::controls(const QString &windowTargetId, const QString &query,
                                           int max, QString *error)
{
    if (max <= 0) max = 120;
    if (max > 400) max = 400;
    const QRect window = targetBounds(QStringLiteral("window"), windowTargetId);
    if (!window.isValid()) { if (error) *error = QStringLiteral("Ventana no encontrada."); return {}; }
    if (atspiAddress().isEmpty()) { if (error) *error = QStringLiteral("AT-SPI no está disponible; iniciá at-spi2-registryd."); return {}; }
    return atspiControlsFor(window, query, max);
}

bool LinuxDesktopBackend::clickElement(const QString &windowTargetId, const QString &controlId,
                                       bool allowFuzzy, QString *error, QVariantMap *trace)
{
    QString resolved;
    const QVariantMap info = findControl(windowTargetId, controlId, allowFuzzy, &resolved);
    if (info.isEmpty()) { if (error) *error = QStringLiteral("No se encontró el control AT-SPI; generá un snapshot nuevo."); return false; }
    QString actionError;
    if (controlAction(windowTargetId, resolved, QStringLiteral("invoke"), {}, &actionError, trace)) {
        if (allowFuzzy && resolved != controlId && trace) (*trace)[QStringLiteral("matchedBy")] = QStringLiteral("fuzzy-name");
        return true;
    }
    const double x = (info.value(QStringLiteral("x")).toInt() - targetBounds(QStringLiteral("window"), windowTargetId).x()
                      + info.value(QStringLiteral("width")).toInt() / 2.0)
                     / targetBounds(QStringLiteral("window"), windowTargetId).width();
    const double y = (info.value(QStringLiteral("y")).toInt() - targetBounds(QStringLiteral("window"), windowTargetId).y()
                      + info.value(QStringLiteral("height")).toInt() / 2.0)
                     / targetBounds(QStringLiteral("window"), windowTargetId).height();
    if (trace) (*trace)[QStringLiteral("strategy")] = QStringLiteral("atspi-bounds");
    return click(QStringLiteral("window"), windowTargetId, x, y, QStringLiteral("left"), error, trace);
}

bool LinuxDesktopBackend::controlAction(const QString &windowTargetId, const QString &controlId,
                                        const QString &action, const QString &value,
                                        QString *error, QVariantMap *trace)
{
    Q_UNUSED(windowTargetId)
    AtspiRef ref;
    if (!refFromId(controlId, &ref)) { if (error) *error = QStringLiteral("controlId AT-SPI inválido."); return false; }
    const QString address = atspiAddress();
    if (address.isEmpty()) { if (error) *error = QStringLiteral("AT-SPI no está disponible."); return false; }
    const QString op = action.trimmed().toLower().isEmpty() ? QStringLiteral("invoke") : action.trimmed().toLower();
    CommandResult r;
    if (op == QLatin1String("set_value")) {
        r = atspiCall(address, ref.dest, ref.path, QStringLiteral("org.a11y.atspi.EditableText.SetTextContents"), {value});
    } else if (op == QLatin1String("range_set")) {
        r = atspiCall(address, ref.dest, ref.path, QStringLiteral("org.a11y.atspi.Value.SetCurrentValue"), {QStringLiteral("double:%1").arg(value)});
    } else if (op == QLatin1String("read")) {
        if (trace) (*trace)[QStringLiteral("value")] = findControl(windowTargetId, controlId, false, nullptr);
        return true;
    } else {
        r = atspiCall(address, ref.dest, ref.path, QStringLiteral("org.a11y.atspi.Action.DoAction"), {QStringLiteral("0")});
    }
    const bool ok = r.exitCode == 0;
    if (!ok && error) *error = r.err.trimmed().isEmpty() ? QStringLiteral("AT-SPI no pudo ejecutar '%1'.").arg(op) : r.err.trimmed();
    if (ok && trace) *trace = {{QStringLiteral("surface"), QStringLiteral("desktop")}, {QStringLiteral("action"), op},
        {QStringLiteral("strategy"), QStringLiteral("atspi-action")}, {QStringLiteral("controlId"), controlId}};
    return ok;
}

QVariantMap LinuxDesktopBackend::controlAtPoint(const QPoint &absolute)
{
    QVariantMap best;
    int bestArea = INT_MAX;
    for (const QVariant &w : windows()) {
        const QVariantMap window = w.toMap();
        const QRect rect(window.value(QStringLiteral("x")).toInt(), window.value(QStringLiteral("y")).toInt(),
                         window.value(QStringLiteral("width")).toInt(), window.value(QStringLiteral("height")).toInt());
        if (!rect.contains(absolute)) continue;
        for (const QVariant &c : controls(window.value(QStringLiteral("id")).toString(), QString(), 400, nullptr)) {
            const QVariantMap row = c.toMap();
            const QRect cr(row.value(QStringLiteral("x")).toInt(), row.value(QStringLiteral("y")).toInt(),
                           row.value(QStringLiteral("width")).toInt(), row.value(QStringLiteral("height")).toInt());
            if (cr.contains(absolute) && cr.width() * cr.height() < bestArea) {
                best = row; bestArea = cr.width() * cr.height();
            }
        }
        if (!best.isEmpty()) { best[QStringLiteral("windowId")] = window.value(QStringLiteral("id")); best[QStringLiteral("windowLabel")] = window.value(QStringLiteral("label")); }
    }
    return best;
}

#else

QVariantList LinuxDesktopBackend::windows() { return {}; }
QRect LinuxDesktopBackend::targetBounds(const QString &, const QString &) { return {}; }
bool LinuxDesktopBackend::interactiveSessionAvailable() { return false; }
bool LinuxDesktopBackend::launchApp(const QString &, const QString &, QString *) { return false; }
bool LinuxDesktopBackend::focusWindow(const QString &, QString *) { return false; }
bool LinuxDesktopBackend::setWindowMaximized(const QString &, bool, QString *) { return false; }
bool LinuxDesktopBackend::setWindowSize(const QString &, int, int, QString *) { return false; }
bool LinuxDesktopBackend::click(const QString &, const QString &, double, double, const QString &, QString *, QVariantMap *) { return false; }
bool LinuxDesktopBackend::stroke(const QString &, const QString &, const QVariantList &, const QString &, int, QString *, QVariantMap *) { return false; }
bool LinuxDesktopBackend::typeText(const QString &, QString *) { return false; }
bool LinuxDesktopBackend::pressKey(const QString &, const QStringList &, QString *) { return false; }
bool LinuxDesktopBackend::scroll(int, QString *) { return false; }
QPoint LinuxDesktopBackend::cursorPos() { return {}; }
bool LinuxDesktopBackend::moveCursor(const QPoint &) { return false; }
QVariantList LinuxDesktopBackend::controls(const QString &, const QString &, int, QString *) { return {}; }
bool LinuxDesktopBackend::clickElement(const QString &, const QString &, bool, QString *, QVariantMap *) { return false; }
bool LinuxDesktopBackend::controlAction(const QString &, const QString &, const QString &, const QString &, QString *, QVariantMap *) { return false; }
QVariantMap LinuxDesktopBackend::controlAtPoint(const QPoint &) { return {}; }

#endif
