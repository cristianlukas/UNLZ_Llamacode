#include "TeachSessionRecorder.h"
#include "AutomationArtifactStore.h"
#include "DesktopAutomationBackend.h"
#include "core/agent/BrowserTeach.h"

#include <QCursor>
#include <QDateTime>
#include <QDir>
#include <QFileInfo>

#ifdef Q_OS_WIN
#  define NOMINMAX
#  include <windows.h>

namespace {
// VK no imprimible → nombre canónico (mismo vocabulario que
// DesktopAutomationBackend::keyCode, así el replay vía desktop_key lo reconoce).
// Devuelve vacío si la tecla es imprimible (se captura como texto, no como [key]).
QString vkToName(quint32 vk)
{
    switch (vk) {
    case VK_RETURN:  return QStringLiteral("ENTER");
    case VK_TAB:     return QStringLiteral("TAB");
    case VK_ESCAPE:  return QStringLiteral("ESC");
    case VK_BACK:    return QStringLiteral("BACKSPACE");
    case VK_DELETE:  return QStringLiteral("DELETE");
    case VK_UP:      return QStringLiteral("UP");
    case VK_DOWN:    return QStringLiteral("DOWN");
    case VK_LEFT:    return QStringLiteral("LEFT");
    case VK_RIGHT:   return QStringLiteral("RIGHT");
    case VK_HOME:    return QStringLiteral("HOME");
    case VK_END:     return QStringLiteral("END");
    case VK_PRIOR:   return QStringLiteral("PAGEUP");
    case VK_NEXT:    return QStringLiteral("PAGEDOWN");
    default: break;
    }
    if (vk >= VK_F1 && vk <= VK_F12)
        return QStringLiteral("F%1").arg(vk - VK_F1 + 1);
    return {};
}

// Nombre de la tecla base de un atajo (Ctrl/Alt/Win + X). Letras/dígitos → el
// carácter; el resto delega en vkToName (vacío = atajo no representable, se ignora).
QString shortcutKeyName(quint32 vk)
{
    if ((vk >= 'A' && vk <= 'Z') || (vk >= '0' && vk <= '9'))
        return QString(QChar(static_cast<ushort>(vk)));
    return vkToName(vk);
}

// Instancia que recibe el hook global (sólo hay una sesión Teach a la vez) y el
// callback C del hook de bajo nivel. File-static para mantener windows.h fuera
// del header (TeachSessionRecorder.h lo incluye AppController.h → todo el árbol).
TeachSessionRecorder *g_activeRecorder = nullptr;

LRESULT CALLBACK teachKeyboardProc(int code, WPARAM wParam, LPARAM lParam)
{
    if (code == HC_ACTION && g_activeRecorder
        && (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN)) {
        const auto *kb = reinterpret_cast<const KBDLLHOOKSTRUCT *>(lParam);
        g_activeRecorder->onKeyDown(kb->vkCode, kb->scanCode);
    }
    return CallNextHookEx(nullptr, code, wParam, lParam);
}
}  // namespace
#endif

TeachSessionRecorder::TeachSessionRecorder(QObject *parent) : QObject(parent)
{
    m_timer.setInterval(80);
    connect(&m_timer, &QTimer::timeout, this, &TeachSessionRecorder::sampleDesktop);
}

void TeachSessionRecorder::reset()
{
    m_timer.stop();
#ifdef Q_OS_WIN
    removeKeyHook();
#endif
    m_keys.clear();
    m_error.clear();
    m_events.clear();
    m_evidence.clear();
    m_artifactId.clear();
    m_task.clear();
    m_mode.clear();
    m_scopeKind.clear();
    m_scopeId.clear();
}

QString TeachSessionRecorder::startDesktop(const QVariantMap &task,
                                           const QString &scopeKind,
                                           const QString &scopeId)
{
    if (m_state == QLatin1String("recording") || m_state == QLatin1String("paused"))
        return QStringLiteral("Ya hay una sesión Teach activa.");
    reset();
    if (!DesktopAutomationBackend::interactiveSessionAvailable())
        return QStringLiteral("La sesión de Windows no está disponible para grabar.");
    if (DesktopAutomationBackend::targetInfo(scopeKind, scopeId).isEmpty())
        return QStringLiteral("Seleccioná una pantalla o ventana válida.");
    m_task = task;
    m_mode = QStringLiteral("desktop");
    m_scopeKind = scopeKind;
    m_scopeId = scopeId;
    m_clock.start();
    m_lastCursor = QCursor::pos();
    m_state = QStringLiteral("recording");
    appendEvent({{QStringLiteral("kind"), QStringLiteral("start")},
                 {QStringLiteral("intent"), QStringLiteral("Inicio de demostración de escritorio")}}, true);
    m_timer.start();
#ifdef Q_OS_WIN
    installKeyHook();   // capturar tipeo del usuario (texto + teclas/atajos)
#endif
    emit changed();
    return {};
}

QString TeachSessionRecorder::startBrowser(const QVariantMap &task, const QString &url)
{
    if (m_state == QLatin1String("recording") || m_state == QLatin1String("paused"))
        return QStringLiteral("Ya hay una sesión Teach activa.");
    reset();
    const QString skill = task.value(QStringLiteral("id")).toString();
    if (BrowserTeach::recordCommand(skill, url).isEmpty())
        return QStringLiteral("La Task necesita un nombre válido.");
    m_task = task;
    m_mode = QStringLiteral("browserBackground");
    m_scopeKind = QStringLiteral("browser");
    m_scopeId = url;
    m_clock.start();
    m_state = QStringLiteral("recording");
    appendEvent({{QStringLiteral("kind"), QStringLiteral("browser")},
                 {QStringLiteral("intent"), QStringLiteral("Demostración Playwright instrumentada")},
                 {QStringLiteral("ref"), url}}, false);
    emit changed();
    return {};
}

void TeachSessionRecorder::setPaused(bool paused)
{
    if (paused && m_state == QLatin1String("recording")) {
        flushKeys();   // cerrar el texto pendiente antes de pausar
        m_state = QStringLiteral("paused");
        m_timer.stop();
    } else if (!paused && m_state == QLatin1String("paused")) {
        m_state = QStringLiteral("recording");
        if (m_mode == QLatin1String("desktop")) m_timer.start();
    }
    emit changed();
}

void TeachSessionRecorder::addNote(const QString &note)
{
    if (m_state != QLatin1String("recording") && m_state != QLatin1String("paused")) return;
    const QString clean = AutomationArtifactStore::redact(note.trimmed());
    if (clean.isEmpty()) return;
    appendEvent({{QStringLiteral("kind"), QStringLiteral("note")},
                 {QStringLiteral("intent"), clean}}, true);
}

QString TeachSessionRecorder::captureEvidence()
{
    if (m_mode != QLatin1String("desktop")) return {};
    const QString tempId = m_task.value(QStringLiteral("id")).toString();
    const QString dir = AutomationArtifactStore::artifactDir(tempId)
                        + QStringLiteral("/evidence");
    QDir().mkpath(dir);
    const QString name = QStringLiteral("%1.jpg").arg(m_evidence.size() + 1, 4, 10, QLatin1Char('0'));
    QString error;
    const QString path = DesktopAutomationBackend::saveCapture(
        m_scopeKind, m_scopeId, dir + QLatin1Char('/') + name, &error);
    if (path.isEmpty()) m_error = error;
    else m_evidence << name;
    return name;
}

void TeachSessionRecorder::appendEvent(const QVariantMap &source, bool capture)
{
    QVariantMap event = source;
    event[QStringLiteral("atMs")] = m_clock.isValid() ? m_clock.elapsed() : 0;
    if (capture) {
        const QString evidence = captureEvidence();
        if (!evidence.isEmpty()) event[QStringLiteral("evidence")] = evidence;
    }
    m_events.append(event);
    emit changed();
}

void TeachSessionRecorder::sampleDesktop()
{
    if (m_state != QLatin1String("recording")) return;
    const QPoint cursor = QCursor::pos();
#ifdef Q_OS_WIN
    const bool left = (GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0;
    const bool right = (GetAsyncKeyState(VK_RBUTTON) & 0x8000) != 0;
    const QVariantMap info = DesktopAutomationBackend::targetInfo(m_scopeKind, m_scopeId);
    const QRect bounds(info.value(QStringLiteral("x")).toInt(), info.value(QStringLiteral("y")).toInt(),
                       info.value(QStringLiteral("width")).toInt(), info.value(QStringLiteral("height")).toInt());
    if (left && !m_leftDown && bounds.contains(cursor)) {
        flushKeys();   // el texto tipeado va ANTES del próximo click
        const QPointF p = DesktopAutomationBackend::normalizePoint(cursor, bounds);
        appendEvent({{QStringLiteral("kind"), QStringLiteral("click")},
                     {QStringLiteral("intent"), QStringLiteral("Click izquierdo")},
                     {QStringLiteral("x"), p.x()}, {QStringLiteral("y"), p.y()}}, true);
    }
    if (right && !m_rightDown && bounds.contains(cursor)) {
        flushKeys();
        const QPointF p = DesktopAutomationBackend::normalizePoint(cursor, bounds);
        appendEvent({{QStringLiteral("kind"), QStringLiteral("click")},
                     {QStringLiteral("intent"), QStringLiteral("Click derecho")},
                     {QStringLiteral("button"), QStringLiteral("right")},
                     {QStringLiteral("x"), p.x()}, {QStringLiteral("y"), p.y()}}, true);
    }
    m_leftDown = left;
    m_rightDown = right;
#endif
    m_lastCursor = cursor;
}

QString TeachSessionRecorder::finish()
{
    if (m_state != QLatin1String("recording") && m_state != QLatin1String("paused"))
        return {};
    m_state = QStringLiteral("compiling");
    m_timer.stop();
#ifdef Q_OS_WIN
    removeKeyHook();
#endif
    flushKeys();   // volcar el último texto tipeado antes del paso de verificación
    appendEvent({{QStringLiteral("kind"), QStringLiteral("verification")},
                 {QStringLiteral("intent"), QStringLiteral("Verificar que se cumplió el objetivo")}}, true);
    const QVariantMap scope{
        {QStringLiteral("kind"), m_scopeKind},
        {QStringLiteral("targetId"), m_scopeId},
        {QStringLiteral("target"), DesktopAutomationBackend::targetInfo(m_scopeKind, m_scopeId)}};
    QString browserScript;
    if (m_mode == QLatin1String("browserBackground")
        && BrowserTeach::hasSkill(m_task.value(QStringLiteral("id")).toString()))
        browserScript = BrowserTeach::skillPath(m_task.value(QStringLiteral("id")).toString());
    m_artifactId = AutomationArtifactStore::create(m_task, scope, m_events, m_evidence, browserScript);
    m_state = m_artifactId.isEmpty() ? QStringLiteral("failed") : QStringLiteral("ready");
    if (m_artifactId.isEmpty()) m_error = QStringLiteral("No se pudo guardar el artefacto Teach.");
    emit changed();
    if (!m_artifactId.isEmpty()) emit finished(m_artifactId);
    return m_artifactId;
}

void TeachSessionRecorder::cancel()
{
    if (m_state == QLatin1String("idle")) return;
    m_timer.stop();
#ifdef Q_OS_WIN
    removeKeyHook();
#endif
    m_keys.clear();
    m_state = QStringLiteral("cancelled");
    emit changed();
}

void TeachSessionRecorder::flushKeys()
{
    emitKeySteps(m_keys.flush());
}

void TeachSessionRecorder::emitKeySteps(const QVariantList &steps)
{
    for (const QVariant &v : steps) {
        QVariantMap step = v.toMap();
        // Redactar el texto tipeado (puede contener credenciales) y reconstruir el
        // intent legible a partir del texto ya saneado.
        if (step.value(QStringLiteral("kind")).toString() == QLatin1String("type")) {
            const QString clean = AutomationArtifactStore::redact(
                step.value(QStringLiteral("text")).toString());
            step[QStringLiteral("text")] = clean;
            step[QStringLiteral("intent")] = QStringLiteral("Escribir: \"%1\"").arg(clean);
        }
        appendEvent(step, true);
    }
}

#ifdef Q_OS_WIN
void TeachSessionRecorder::installKeyHook()
{
    if (m_keyHook) return;
    g_activeRecorder = this;
    m_keyHook = SetWindowsHookExW(WH_KEYBOARD_LL, &teachKeyboardProc,
                                  GetModuleHandleW(nullptr), 0);
    if (!m_keyHook) g_activeRecorder = nullptr;   // sin hook: tipeo no capturado (best-effort)
}

void TeachSessionRecorder::removeKeyHook()
{
    if (m_keyHook) {
        UnhookWindowsHookEx(static_cast<HHOOK>(m_keyHook));
        m_keyHook = nullptr;
    }
    if (g_activeRecorder == this) g_activeRecorder = nullptr;
}

void TeachSessionRecorder::onKeyDown(quint32 vk, quint32 scan)
{
    if (m_state != QLatin1String("recording")) return;

    // Modificadores y toggles solos: no generan un paso propio.
    switch (vk) {
    case VK_SHIFT: case VK_LSHIFT: case VK_RSHIFT:
    case VK_CONTROL: case VK_LCONTROL: case VK_RCONTROL:
    case VK_MENU: case VK_LMENU: case VK_RMENU:
    case VK_LWIN: case VK_RWIN:
    case VK_CAPITAL: case VK_NUMLOCK: case VK_SCROLL:
        return;
    default: break;
    }

    // En un hook global LL, GetKeyState lee la cola del hilo instalador (no la del
    // app con foco) → poco fiable. GetAsyncKeyState lee el estado físico real.
    const bool ctrl = (GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0;
    const bool alt  = (GetAsyncKeyState(VK_MENU) & 0x8000) != 0;
    const bool win  = (GetAsyncKeyState(VK_LWIN) & 0x8000) || (GetAsyncKeyState(VK_RWIN) & 0x8000);
    const QString named = vkToName(vk);

    // Atajo (Ctrl/Alt/Win + algo): vaciar texto y emitir [key] con modificadores.
    if (ctrl || alt || win) {
        QStringList mods;
        if (ctrl) mods << QStringLiteral("CTRL");
        if (alt)  mods << QStringLiteral("ALT");
        if (win)  mods << QStringLiteral("WIN");
        const QString key = named.isEmpty() ? shortcutKeyName(vk) : named;
        if (!key.isEmpty()) emitKeySteps(m_keys.feedKey(key, mods));
        return;
    }

    // Tecla nombrada (ENTER, TAB, flechas…): vaciar texto y emitir [key].
    if (!named.isEmpty()) {
        emitKeySteps(m_keys.feedKey(named));
        return;
    }

    // Imprimible: traducir vk+scan a unicode. Llegamos acá sin ctrl/alt/win (los
    // atajos ya retornaron arriba), así que sólo shift+caps afectan el carácter.
    // Construimos el estado a mano con GetAsyncKeyState (el array del hilo del hook
    // no refleja el teclado del app con foco).
    BYTE state[256] = {};
    if (GetAsyncKeyState(VK_SHIFT) & 0x8000) state[VK_SHIFT] = 0x80;
    if (GetKeyState(VK_CAPITAL) & 0x0001)    state[VK_CAPITAL] = 0x01;   // toggle caps
    wchar_t buf[8] = {};
    const HKL layout = GetKeyboardLayout(0);
    const int n = ToUnicodeEx(vk, scan, state, buf, 7, 0, layout);
    for (int i = 0; i < n; ++i) {
        const QChar c(static_cast<ushort>(buf[i]));
        if (c.isPrint()) m_keys.feedChar(c);
    }
}
#endif
