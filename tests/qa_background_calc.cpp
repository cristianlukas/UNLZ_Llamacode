// QA del modo "segundo plano" de computer use, contra la Calculadora REAL.
// No es un test de ctest: necesita una sesión de escritorio viva (abre una
// ventana). La ayuda y el guard de offscreen sí corren en ctest.
//
// Hace lo mismo que el agente cuando el usuario elige "En segundo plano":
//   desktop_launch calc  → id de la ventana que abrió (waitForLaunchedWindow)
//   desktop_controls     → controles por UI Automation
//   desktop_control_action invoke sobre C, 3, ×, 3, =   (con el input físico
//                          BLOQUEADO: si algún control necesitara el mouse, falla)
//   leer el visor        → tiene que decir 9
// y verifica que el puntero del mouse NO se movió. Al final cierra la ventana.
//
// Uso:  qa_background_calc.exe            (sale 0 si todo pasó, 1 si no, 2 sin escritorio)
// La Calculadora es segura para esto (no tiene documentos del usuario).

#include "core/automation/DesktopAutomationBackend.h"

#include <QCursor>
#include <QElapsedTimer>
#include <QGuiApplication>
#include <QHash>
#include <QProcess>
#include <QRegularExpression>
#include <QTextStream>
#include <QThread>

#ifdef Q_OS_WIN
#include <windows.h>
#endif

static QTextStream out(stdout);

#ifdef Q_OS_WIN
#define kClear "clearButton"
#define kNum3 "num3Button"
#define kTimes "multiplyButton"
#define kEquals "equalButton"
#else
#define kClear ""
#define kNum3 "3"
#define kTimes "\u00d7"
#define kEquals "="
#endif
static int fails = 0;

static void check(bool ok, const QString &what)
{
    out << (ok ? "  PASS " : "  FAIL ") << what << Qt::endl;
    if (!ok) ++fails;
}

// Windows: automationId → controlId. Linux (AT-SPI): GTK no expone automationId,
// así que la clave es el nombre accesible del botón ("3", "×", "=").
// automationId → controlId de la ventana (la UI de la Calculadora tarda en
// poblarse después de abrir).
static QHash<QString, QString> calculatorControls(const QString &window, QString *display)
{
    QHash<QString, QString> ids;
    QElapsedTimer t;
    t.start();
    while (t.elapsed() < 8000) {
        QString error;
        const QVariantList rows = DesktopAutomationBackend::controls(window, QString(), 400, &error);
        ids.clear();
        for (const QVariant &v : rows) {
            const QVariantMap row = v.toMap();
#ifdef Q_OS_WIN
            const QString aid = row.value(QStringLiteral("automationId")).toString();
            if (aid.isEmpty()) continue;
            ids.insert(aid, row.value(QStringLiteral("controlId")).toString());
            if (aid == QLatin1String("CalculatorResults") && display)
                *display = row.value(QStringLiteral("name")).toString();
#else
            const QString role = row.value(QStringLiteral("role")).toString().toLower();
            const QString name = row.value(QStringLiteral("name")).toString();
            if (role.contains(QLatin1String("button")) && !name.isEmpty() && !ids.contains(name))
                ids.insert(name, row.value(QStringLiteral("controlId")).toString());
            if (display && (role.contains(QLatin1String("text")) || role.contains(QLatin1String("edit")))) {
                // El visor: su valor viene en la fila o se lee con la acción "read".
                QString value = row.value(QStringLiteral("value")).toString();
                if (value.isEmpty()) {
                    QVariantMap trace;
                    if (DesktopAutomationBackend::controlAction(window, row.value(QStringLiteral("controlId")).toString(),
                                                                QStringLiteral("read"), QString(), nullptr, &trace))
                        value = trace.value(QStringLiteral("value")).toString();
                }
                if (!value.isEmpty()) *display = value;
            }
#endif
        }
        if (ids.contains(QStringLiteral(kNum3)) && ids.contains(QStringLiteral(kEquals)))
            return ids;
        QThread::msleep(250);
    }
    return ids;
}

int main(int argc, char *argv[])
{
    for (int i = 1; i < argc; ++i) {
        const QString arg = QString::fromLocal8Bit(argv[i]);
        if (arg == QLatin1String("--help") || arg == QLatin1String("-h")) {
            out << "Uso: qa_background_calc[.exe]\n"
                << "  Abre la Calculadora y hace 3*3= SOLO por UI Automation, con el\n"
                << "  input fisico bloqueado (modo \"segundo plano\" del agente).\n"
                << "  Verifica que el visor diga 9 y que el mouse no se haya movido.\n"
                << "  Necesita escritorio vivo; cierra la Calculadora al terminar.\n"
                << Qt::endl;
            return 0;
        }
    }
    if (qEnvironmentVariable("QT_QPA_PLATFORM").compare(QStringLiteral("offscreen"),
                                                         Qt::CaseInsensitive) == 0) {
        out << "ERROR: qa_background_calc requiere un escritorio real; "
               "QUITAR QT_QPA_PLATFORM=offscreen." << Qt::endl;
        return 2;
    }
    QGuiApplication app(argc, argv);
    if (!DesktopAutomationBackend::interactiveSessionAvailable()) {
        out << "ERROR: no hay sesión de escritorio interactiva (¿pantalla bloqueada?)." << Qt::endl;
        return 2;
    }
    out << "== qa_background_calc (modo segundo plano) ==" << Qt::endl;
    DesktopAutomationBackend::setPhysicalInputBlocked(true);
    const QPoint cursorBefore = QCursor::pos();

    // 1) desktop_launch: la ventana que abrió, con su id.
    const QVariantList before = DesktopAutomationBackend::windows();
    QString error;
    const bool launched = DesktopAutomationBackend::launchApp(QStringLiteral("calculator"), QString(), &error);
    check(launched, QStringLiteral("lanza 'calculator' (alias de calc) %1").arg(error));
    if (!launched) return 1;
    const QVariantMap window = DesktopAutomationBackend::waitForLaunchedWindow(
        before, QStringLiteral("calculator"), 8000);
    const QString id = window.value(QStringLiteral("id")).toString();
    check(!id.isEmpty() && !window.value(QStringLiteral("dialog")).toBool(),
          QStringLiteral("devuelve la ventana de la Calculadora, no un diálogo (id=%1 \"%2\")")
              .arg(id, window.value(QStringLiteral("label")).toString()));
    if (id.isEmpty()) return 1;

    // 2) desktop_controls: los botones por automationId (no depende del idioma).
    QString display;
    QHash<QString, QString> ids = calculatorControls(id, &display);
    check(ids.contains(QStringLiteral(kNum3)) && ids.contains(QString::fromUtf8(kTimes))
              && ids.contains(QStringLiteral(kEquals)),
          QStringLiteral("encuentra los botones por UI Automation (%1 controles con id)").arg(ids.size()));

    // 3) desktop_control_action invoke, sin mouse ni teclado.
    QElapsedTimer taskTimer;
    taskTimer.start();
    for (const char *aid : {kClear, kNum3, kTimes, kNum3, kEquals}) {
        const QString key = QString::fromUtf8(aid);
        if (key.isEmpty()) continue;
        if (!ids.contains(key)) { check(false, QStringLiteral("falta el control %1").arg(key)); continue; }
        QString actionError;
        const bool ok = DesktopAutomationBackend::controlAction(id, ids.value(key),
                                                                QStringLiteral("invoke"), QString(),
                                                                &actionError);
        check(ok, QStringLiteral("invoke %1 %2").arg(key, actionError));
        // GTK4 descarta un segundo clic al mismo botón a menos de ~250 ms.
        QThread::msleep(300);
    }

    // 4) leer el visor.
    QThread::msleep(300);
    display.clear();
    calculatorControls(id, &display);
    const QRegularExpressionMatch m = QRegularExpression(QStringLiteral("(\\d+)\\s*$")).match(display.trimmed());
    check(m.hasMatch() && m.captured(1) == QLatin1String("9"),
          QStringLiteral("el visor dice 9 (\"%1\")").arg(display));

    // 5) el mouse del usuario no se tocó.
    check(QCursor::pos() == cursorBefore,
          QStringLiteral("el puntero no se movió (%1,%2)").arg(QCursor::pos().x()).arg(QCursor::pos().y()));

    out << "  tiempo de la tarea (controles + clics + visor): " << taskTimer.elapsed() << " ms" << Qt::endl;

    // Cerrar la Calculadora que abrimos (sólo esa ventana).
#ifdef Q_OS_WIN
    const HWND hwnd = reinterpret_cast<HWND>(id.toULongLong(nullptr, 16));
    if (hwnd && IsWindow(hwnd)) PostMessageW(hwnd, WM_CLOSE, 0, 0);
#else
    QProcess::execute(QStringLiteral("wmctrl"), {QStringLiteral("-ic"), id});
#endif

    out << (fails == 0 ? "OK: modo segundo plano verificado contra la Calculadora real."
                       : QStringLiteral("FALLÓ: %1 chequeo(s).").arg(fails)) << Qt::endl;
    return fails == 0 ? 0 : 1;
}
