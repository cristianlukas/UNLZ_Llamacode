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
#include <QRegularExpression>
#include <QTextStream>
#include <QThread>

#ifdef Q_OS_WIN
#include <windows.h>
#endif

static QTextStream out(stdout);
static int fails = 0;

static void check(bool ok, const QString &what)
{
    out << (ok ? "  PASS " : "  FAIL ") << what << Qt::endl;
    if (!ok) ++fails;
}

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
            const QString aid = row.value(QStringLiteral("automationId")).toString();
            if (aid.isEmpty()) continue;
            ids.insert(aid, row.value(QStringLiteral("controlId")).toString());
            if (aid == QLatin1String("CalculatorResults") && display)
                *display = row.value(QStringLiteral("name")).toString();
        }
        if (ids.contains(QStringLiteral("num3Button")) && ids.contains(QStringLiteral("equalButton")))
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
            out << "Uso: qa_background_calc.exe\n"
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
#ifndef Q_OS_WIN
    out << "qa_background_calc: por ahora sólo Windows (Calculadora UWP)." << Qt::endl;
    return 2;
#else
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
    check(ids.contains(QStringLiteral("num3Button")) && ids.contains(QStringLiteral("multiplyButton"))
              && ids.contains(QStringLiteral("equalButton")),
          QStringLiteral("encuentra los botones por UI Automation (%1 controles con id)").arg(ids.size()));

    // 3) desktop_control_action invoke, sin mouse ni teclado.
    for (const char *aid : {"clearButton", "num3Button", "multiplyButton", "num3Button", "equalButton"}) {
        const QString key = QString::fromLatin1(aid);
        if (!ids.contains(key)) { check(false, QStringLiteral("falta el control %1").arg(key)); continue; }
        QString actionError;
        const bool ok = DesktopAutomationBackend::controlAction(id, ids.value(key),
                                                                QStringLiteral("invoke"), QString(),
                                                                &actionError);
        check(ok, QStringLiteral("invoke %1 %2").arg(key, actionError));
        QThread::msleep(120);
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

    // Cerrar la Calculadora que abrimos (sólo esa ventana).
    const HWND hwnd = reinterpret_cast<HWND>(id.toULongLong(nullptr, 16));
    if (hwnd && IsWindow(hwnd)) PostMessageW(hwnd, WM_CLOSE, 0, 0);

    out << (fails == 0 ? "OK: modo segundo plano verificado contra la Calculadora real."
                       : QStringLiteral("FALLÓ: %1 chequeo(s).").arg(fails)) << Qt::endl;
    return fails == 0 ? 0 : 1;
#endif
}
