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
#endif

TeachSessionRecorder::TeachSessionRecorder(QObject *parent) : QObject(parent)
{
    m_timer.setInterval(80);
    connect(&m_timer, &QTimer::timeout, this, &TeachSessionRecorder::sampleDesktop);
}

void TeachSessionRecorder::reset()
{
    m_timer.stop();
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
        const QPointF p = DesktopAutomationBackend::normalizePoint(cursor, bounds);
        appendEvent({{QStringLiteral("kind"), QStringLiteral("click")},
                     {QStringLiteral("intent"), QStringLiteral("Click izquierdo")},
                     {QStringLiteral("x"), p.x()}, {QStringLiteral("y"), p.y()}}, true);
    }
    if (right && !m_rightDown && bounds.contains(cursor)) {
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
    m_state = QStringLiteral("cancelled");
    emit changed();
}
