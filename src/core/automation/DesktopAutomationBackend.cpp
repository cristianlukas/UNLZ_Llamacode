#include "DesktopAutomationBackend.h"

#include <QCursor>
#include <QDir>
#include <QFileInfo>
#include <QGuiApplication>
#include <QScreen>
#include <QWindow>

#ifdef Q_OS_WIN
#  define NOMINMAX
#  include <windows.h>
#endif

namespace {
QRect targetBounds(const QString &kind, const QString &targetId)
{
    if (kind == QLatin1String("screen")) {
        const auto list = QGuiApplication::screens();
        bool ok = false;
        const int index = targetId.toInt(&ok);
        if (ok && index >= 0 && index < list.size()) return list.at(index)->geometry();
        for (QScreen *screen : list)
            if (screen->name() == targetId) return screen->geometry();
        return QGuiApplication::primaryScreen() ? QGuiApplication::primaryScreen()->geometry() : QRect();
    }
#ifdef Q_OS_WIN
    bool ok = false;
    const quintptr raw = targetId.toULongLong(&ok, 16);
    HWND hwnd = ok ? reinterpret_cast<HWND>(raw) : nullptr;
    RECT r{};
    if (hwnd && IsWindow(hwnd) && GetWindowRect(hwnd, &r))
        return QRect(r.left, r.top, r.right - r.left, r.bottom - r.top);
#else
    Q_UNUSED(targetId)
#endif
    return {};
}

#ifdef Q_OS_WIN
struct WindowCollector { QVariantList rows; };
BOOL CALLBACK collectWindow(HWND hwnd, LPARAM param)
{
    if (!IsWindowVisible(hwnd) || GetWindow(hwnd, GW_OWNER)) return TRUE;
    wchar_t title[512]{};
    GetWindowTextW(hwnd, title, 511);
    const QString text = QString::fromWCharArray(title).trimmed();
    RECT r{};
    if (text.isEmpty() || !GetWindowRect(hwnd, &r) || r.right <= r.left || r.bottom <= r.top)
        return TRUE;
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    auto *collector = reinterpret_cast<WindowCollector *>(param);
    collector->rows.append(QVariantMap{
        {QStringLiteral("id"), QString::number(reinterpret_cast<quintptr>(hwnd), 16)},
        {QStringLiteral("kind"), QStringLiteral("window")},
        {QStringLiteral("label"), text},
        {QStringLiteral("pid"), static_cast<qulonglong>(pid)},
        {QStringLiteral("x"), static_cast<int>(r.left)},
        {QStringLiteral("y"), static_cast<int>(r.top)},
        {QStringLiteral("width"), static_cast<int>(r.right - r.left)},
        {QStringLiteral("height"), static_cast<int>(r.bottom - r.top)}});
    return TRUE;
}

WORD keyCode(const QString &key)
{
    const QString k = key.trimmed().toUpper();
    if (k.size() == 1) return static_cast<WORD>(VkKeyScanW(k.at(0).unicode()) & 0xff);
    static const QHash<QString, WORD> keys{
        {"ENTER", VK_RETURN}, {"TAB", VK_TAB}, {"ESC", VK_ESCAPE},
        {"ESCAPE", VK_ESCAPE}, {"BACKSPACE", VK_BACK}, {"DELETE", VK_DELETE},
        {"SPACE", VK_SPACE}, {"UP", VK_UP}, {"DOWN", VK_DOWN},
        {"LEFT", VK_LEFT}, {"RIGHT", VK_RIGHT}, {"HOME", VK_HOME},
        {"END", VK_END}, {"PAGEDOWN", VK_NEXT}, {"PAGEUP", VK_PRIOR},
        {"F1", VK_F1}, {"F2", VK_F2}, {"F3", VK_F3}, {"F4", VK_F4},
        {"F5", VK_F5}, {"F6", VK_F6}, {"F7", VK_F7}, {"F8", VK_F8},
        {"F9", VK_F9}, {"F10", VK_F10}, {"F11", VK_F11}, {"F12", VK_F12}};
    return keys.value(k, 0);
}

void sendKey(WORD vk, bool down)
{
    INPUT input{};
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = vk;
    input.ki.dwFlags = down ? 0 : KEYEVENTF_KEYUP;
    SendInput(1, &input, sizeof(INPUT));
}
#endif
}

QVariantList DesktopAutomationBackend::screens()
{
    QVariantList out;
    const auto list = QGuiApplication::screens();
    for (int i = 0; i < list.size(); ++i) {
        QScreen *s = list.at(i);
        const QRect r = s->geometry();
        out.append(QVariantMap{
            {QStringLiteral("id"), QString::number(i)},
            {QStringLiteral("kind"), QStringLiteral("screen")},
            {QStringLiteral("label"), s->name().isEmpty()
                 ? QStringLiteral("Pantalla %1").arg(i + 1) : s->name()},
            {QStringLiteral("x"), r.x()}, {QStringLiteral("y"), r.y()},
            {QStringLiteral("width"), r.width()}, {QStringLiteral("height"), r.height()},
            {QStringLiteral("dpi"), s->logicalDotsPerInch()},
            {QStringLiteral("primary"), s == QGuiApplication::primaryScreen()}});
    }
    return out;
}

QVariantList DesktopAutomationBackend::windows()
{
#ifdef Q_OS_WIN
    WindowCollector collector;
    EnumWindows(collectWindow, reinterpret_cast<LPARAM>(&collector));
    return collector.rows;
#else
    return {};
#endif
}

QVariantMap DesktopAutomationBackend::targetInfo(const QString &kind, const QString &targetId)
{
    const QVariantList list = kind == QLatin1String("window") ? windows() : screens();
    for (const QVariant &item : list) {
        const QVariantMap row = item.toMap();
        if (row.value(QStringLiteral("id")).toString() == targetId) return row;
    }
    return {};
}

QImage DesktopAutomationBackend::capture(const QString &kind, const QString &targetId, QString *error)
{
    if (error) error->clear();
    const QRect bounds = targetBounds(kind, targetId);
    if (!bounds.isValid()) {
        if (error) *error = QStringLiteral("El alcance visual ya no está disponible.");
        return {};
    }
    QScreen *screen = QGuiApplication::screenAt(bounds.center());
    if (!screen) screen = QGuiApplication::primaryScreen();
    if (!screen) {
        if (error) *error = QStringLiteral("No hay una pantalla disponible.");
        return {};
    }
    const QRect sg = screen->geometry();
    const QPixmap pix = screen->grabWindow(0, bounds.x() - sg.x(), bounds.y() - sg.y(),
                                           bounds.width(), bounds.height());
    if (pix.isNull() && error) *error = QStringLiteral("No se pudo capturar el escritorio.");
    return pix.toImage();
}

QString DesktopAutomationBackend::saveCapture(const QString &kind, const QString &targetId,
                                              const QString &path, QString *error)
{
    const QImage image = capture(kind, targetId, error);
    if (image.isNull()) return {};
    QDir().mkpath(QFileInfo(path).absolutePath());
    if (!image.save(path, "JPG", 82)) {
        if (error) *error = QStringLiteral("No se pudo guardar la captura.");
        return {};
    }
    return path;
}

QPointF DesktopAutomationBackend::normalizePoint(const QPoint &absolute, const QRect &bounds)
{
    if (bounds.width() <= 0 || bounds.height() <= 0) return {};
    return QPointF(qBound(0.0, double(absolute.x() - bounds.x()) / bounds.width(), 1.0),
                   qBound(0.0, double(absolute.y() - bounds.y()) / bounds.height(), 1.0));
}

QPoint DesktopAutomationBackend::denormalizePoint(const QPointF &normalized, const QRect &bounds)
{
    return QPoint(bounds.x() + qRound(qBound(0.0, normalized.x(), 1.0) * bounds.width()),
                  bounds.y() + qRound(qBound(0.0, normalized.y(), 1.0) * bounds.height()));
}

bool DesktopAutomationBackend::interactiveSessionAvailable()
{
#ifdef Q_OS_WIN
    HDESK desk = OpenInputDesktop(0, FALSE, DESKTOP_SWITCHDESKTOP);
    if (!desk) return false;
    const BOOL available = SwitchDesktop(desk);
    CloseDesktop(desk);
    return available != FALSE;
#else
    return true;
#endif
}

bool DesktopAutomationBackend::focusWindow(const QString &targetId, QString *error)
{
#ifdef Q_OS_WIN
    bool ok = false;
    HWND hwnd = reinterpret_cast<HWND>(targetId.toULongLong(&ok, 16));
    if (!ok || !hwnd || !IsWindow(hwnd)) {
        if (error) *error = QStringLiteral("Ventana no encontrada.");
        return false;
    }
    if (IsIconic(hwnd)) ShowWindow(hwnd, SW_RESTORE);
    if (!SetForegroundWindow(hwnd)) {
        if (error) *error = QStringLiteral("Windows no permitió enfocar la ventana.");
        return false;
    }
    return true;
#else
    Q_UNUSED(targetId)
    if (error) *error = QStringLiteral("Control de ventanas disponible sólo en Windows.");
    return false;
#endif
}

bool DesktopAutomationBackend::click(const QString &kind, const QString &targetId,
                                     double x, double y, QString *error)
{
    if (!interactiveSessionAvailable()) {
        if (error) *error = QStringLiteral("La sesión de escritorio está bloqueada.");
        return false;
    }
    const QRect bounds = targetBounds(kind, targetId);
    if (!bounds.isValid()) {
        if (error) *error = QStringLiteral("Alcance visual no disponible.");
        return false;
    }
#ifdef Q_OS_WIN
    if (kind == QLatin1String("window") && !focusWindow(targetId, error)) return false;
    const QPoint p = denormalizePoint(QPointF(x, y), bounds);
    SetCursorPos(p.x(), p.y());
    INPUT inputs[2]{};
    inputs[0].type = inputs[1].type = INPUT_MOUSE;
    inputs[0].mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
    inputs[1].mi.dwFlags = MOUSEEVENTF_LEFTUP;
    return SendInput(2, inputs, sizeof(INPUT)) == 2;
#else
    Q_UNUSED(x) Q_UNUSED(y)
    if (error) *error = QStringLiteral("Control de escritorio disponible sólo en Windows.");
    return false;
#endif
}

bool DesktopAutomationBackend::typeText(const QString &text, QString *error)
{
#ifdef Q_OS_WIN
    if (!interactiveSessionAvailable()) {
        if (error) *error = QStringLiteral("La sesión está bloqueada.");
        return false;
    }
    for (QChar c : text) {
        INPUT inputs[2]{};
        inputs[0].type = inputs[1].type = INPUT_KEYBOARD;
        inputs[0].ki.wScan = inputs[1].ki.wScan = c.unicode();
        inputs[0].ki.dwFlags = KEYEVENTF_UNICODE;
        inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
        if (SendInput(2, inputs, sizeof(INPUT)) != 2) {
            if (error) *error = QStringLiteral("Falló la inyección de texto.");
            return false;
        }
    }
    return true;
#else
    Q_UNUSED(text)
    if (error) *error = QStringLiteral("Control de escritorio disponible sólo en Windows.");
    return false;
#endif
}

bool DesktopAutomationBackend::pressKey(const QString &key, const QStringList &modifiers,
                                        QString *error)
{
#ifdef Q_OS_WIN
    const WORD vk = keyCode(key);
    if (!vk) {
        if (error) *error = QStringLiteral("Tecla no reconocida: %1").arg(key);
        return false;
    }
    QList<WORD> mods;
    for (const QString &m : modifiers) {
        const QString upper = m.toUpper();
        if (upper == QLatin1String("CTRL")) mods << VK_CONTROL;
        else if (upper == QLatin1String("ALT")) mods << VK_MENU;
        else if (upper == QLatin1String("SHIFT")) mods << VK_SHIFT;
        else if (upper == QLatin1String("WIN")) mods << VK_LWIN;
    }
    for (WORD m : mods) sendKey(m, true);
    sendKey(vk, true); sendKey(vk, false);
    for (auto it = mods.crbegin(); it != mods.crend(); ++it) sendKey(*it, false);
    return true;
#else
    Q_UNUSED(key) Q_UNUSED(modifiers)
    if (error) *error = QStringLiteral("Control de escritorio disponible sólo en Windows.");
    return false;
#endif
}

bool DesktopAutomationBackend::scroll(int delta, QString *error)
{
#ifdef Q_OS_WIN
    INPUT input{};
    input.type = INPUT_MOUSE;
    input.mi.dwFlags = MOUSEEVENTF_WHEEL;
    input.mi.mouseData = static_cast<DWORD>(delta);
    const bool ok = SendInput(1, &input, sizeof(INPUT)) == 1;
    if (!ok && error) *error = QStringLiteral("No se pudo desplazar.");
    return ok;
#else
    Q_UNUSED(delta)
    if (error) *error = QStringLiteral("Control de escritorio disponible sólo en Windows.");
    return false;
#endif
}

QVariantMap DesktopAutomationBackend::cursorState()
{
    const QPoint p = QCursor::pos();
    return {{QStringLiteral("x"), p.x()}, {QStringLiteral("y"), p.y()}};
}
