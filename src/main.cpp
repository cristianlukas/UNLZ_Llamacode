#include "AppController.h"
#include "core/ControlApi.h"
#include "core/MermaidRenderer.h"
#include "ThemeProvider.h"
#include "core/tasks/AutomationStore.h"
#include "core/tasks/TaskScheduler.h"
#include <QApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QIcon>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QStandardPaths>
#include <QDir>
#include <QtMessageHandler>
#include <QPixmap>
#include <QPainter>
#include <QWindow>
#include <QWidget>
#include <QLabel>
#include <QScreen>
#include <QGuiApplication>
#include <QLocalServer>
#include <QLocalSocket>
#include <QTimer>
#include <QLockFile>
#include <QProcess>
#include <QSettings>

#ifdef Q_OS_WIN
#  define WIN32_LEAN_AND_MEAN
#  define NOMINMAX
#  include <windows.h>
#  include <shobjidl.h>
#endif

static QFile s_logFile;
static QTextStream s_logStream;

static void messageHandler(QtMsgType type, const QMessageLogContext &ctx, const QString &msg)
{
    const char *level = "DEBUG";
    if      (type == QtWarningMsg)  level = "WARN ";
    else if (type == QtCriticalMsg) level = "ERROR";
    else if (type == QtFatalMsg)    level = "FATAL";

    QString line = QStringLiteral("[%1] [%2] %3")
        .arg(QDateTime::currentDateTime().toString("hh:mm:ss.zzz"))
        .arg(QLatin1String(level))
        .arg(msg);

    if (s_logFile.isOpen()) {
        s_logStream << line << "\n";
        s_logStream.flush();
    }

    // Also forward to default output (visible when run from cmd)
    fprintf(type == QtWarningMsg || type == QtCriticalMsg || type == QtFatalMsg ? stderr : stdout,
            "%s\n", qPrintable(line));

    if (type == QtFatalMsg)
        abort();
}

int main(int argc, char *argv[])
{
    // Log file: %APPDATA%\LlamaCode\llamacode.log
    QString logDir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    QDir().mkpath(logDir);
    s_logFile.setFileName(logDir + "/llamacode.log");
    if (s_logFile.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text))
        s_logStream.setDevice(&s_logFile);

    qInstallMessageHandler(messageHandler);
    qDebug() << "=== LlamaCode starting ===" << QDateTime::currentDateTime().toString();

    // Estilo de Qt Quick Controls: forzar "Basic" (customizable). El default en
    // Windows es el estilo NATIVO, que ignora los override de background/contentItem/
    // header/footer con los que toda la UI está themeada → diálogos sin contenido ni
    // botones, checkbox sin pintar y warnings "current style does not support
    // customization". Debe setearse ANTES de cargar cualquier QML.
    QQuickStyle::setStyle(QStringLiteral("Basic"));

    QApplication app(argc, argv);
    app.setQuitOnLastWindowClosed(false);
    app.setApplicationName("LlamaCode");
    app.setOrganizationName("LlamaCode");
    app.setApplicationVersion("0.1.64");
    const bool startedWithWindows = app.arguments().contains(QStringLiteral("--startup"));

    // Companion sin UI: evalúa el mismo AutomationStore/cron y despierta la app
    // por IPC. Un lock evita duplicados; el toggle persistido lo apaga solo.
    if (app.arguments().contains(QStringLiteral("--scheduler-daemon"))) {
        const QString runtimeDir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
        QDir().mkpath(runtimeDir);
        QLockFile lock(runtimeDir + QStringLiteral("/scheduler-daemon.lock"));
        lock.setStaleLockTime(60000);
        if (!lock.tryLock(100)) return 0;
        AutomationStore store;
        TaskScheduler scheduler(&store);
        QObject::connect(&scheduler, &TaskScheduler::automationDue, &app,
                         [&app](const QString &automationId) {
            QLocalSocket socket;
            socket.connectToServer(QStringLiteral("LlamaCode-single-instance"));
            if (socket.waitForConnected(500)) {
                socket.write((QStringLiteral("automation:") + automationId).toUtf8());
                socket.flush();
                socket.waitForBytesWritten(500);
                return;
            }
            QProcess::startDetached(QCoreApplication::applicationFilePath(),
                                    {QStringLiteral("--run-automation"), automationId,
                                     QStringLiteral("--startup")});
        });
        QTimer settingsWatch;
        settingsWatch.setInterval(15000);
        QObject::connect(&settingsWatch, &QTimer::timeout, &app, [&app]() {
            if (!QSettings().value(QStringLiteral("tasks/schedulerEnabled"), false).toBool())
                app.quit();
        });
        if (!QSettings().value(QStringLiteral("tasks/schedulerEnabled"), false).toBool())
            return 0;
        settingsWatch.start();
        scheduler.setEnabled(true);
        return app.exec();
    }

    // ── Instancia única ──
    // Si ya hay una instancia (incluida la del tray), pedirle que se muestre y salir,
    // en vez de abrir una segunda (que duplicaría el botón en la taskbar).
    const QString kInstanceKey = QStringLiteral("LlamaCode-single-instance");
    {
        QLocalSocket probe;
        probe.connectToServer(kInstanceKey);
        if (probe.waitForConnected(250)) {
            probe.write("raise");
            probe.flush();
            probe.waitForBytesWritten(500);
            probe.disconnectFromServer();
            qDebug() << "Otra instancia ya está corriendo — la enfoco y salgo.";
            return 0;
        }
    }

#ifdef Q_OS_WIN
    // Identidad de taskbar explícita: sin esto Windows no asocia el icono a la
    // ventana frameless y muestra el icono genérico (splash y app).
    SetCurrentProcessExplicitAppUserModelID(L"LlamaCode.Desktop.App");
#endif

    // Icono según build: Debug = rojo (debug_icon), Release = normal. Coincide
    // con el icono embebido en el .exe (app_icon.rc).
#ifdef LC_DEBUG_ICON
    const QString appIconSource = QStringLiteral("qrc:/assets/debug_icon.ico");
    const QString trayIconSource = appIconSource;
    const QIcon appIcon(QStringLiteral(":/assets/debug_icon.ico"));
#else
    const QString appIconSource = QStringLiteral("qrc:/assets/app_icon.ico");
    const QString trayIconSource = QStringLiteral("qrc:/assets/tray_icon.png");
    const QIcon appIcon(QStringLiteral(":/assets/app_icon.ico"));
#endif
    app.setWindowIcon(appIcon);
    qDebug() << "QApplication ready";

    // Splash nativo: se muestra ANTES de cargar QML y cubre el escaneo pesado de
    // arranque (runStartupScan). Se cierra cuando la ventana principal aparece.
    QPixmap splashPix(360, 160);
    splashPix.fill(QColor(0x1e, 0x1e, 0x22));
    {
        QPainter p(&splashPix);
        const QPixmap icon = appIcon.pixmap(64, 64);
        if (!icon.isNull())
            p.drawPixmap((360 - 64) / 2, 28, icon);
        p.setPen(QColor(0xe0, 0xe0, 0xe0));
        QFont f = p.font(); f.setPointSize(11); p.setFont(f);
        p.drawText(QRect(0, 104, 360, 24), Qt::AlignCenter, "UNLZ_Llamacode");
        p.setPen(QColor(0x9a, 0x9a, 0x9a));
        f.setPointSize(9); p.setFont(f);
        p.drawText(QRect(0, 128, 360, 20), Qt::AlignCenter, "Cargando…");
    }
    // Splash como QWidget frameless NORMAL (no QSplashScreen): el flag
    // Qt::SplashScreen no aplica el icono al botón de taskbar (queda genérico).
    // Una ventana frameless común sí lo usa, igual que la ventana principal.
    QWidget splash;
    // Qt::Tool → el splash NO crea su propio botón en la taskbar. SIN
    // WindowStaysOnTopHint: queda por encima de la ventana de LlamaCode (transient
    // parent, seteado abajo) pero NO se fuerza sobre otras apps.
    splash.setWindowFlags(Qt::FramelessWindowHint | Qt::Tool);
    splash.setWindowIcon(appIcon);
    splash.setFixedSize(360, 160);
    splash.setAttribute(Qt::WA_DeleteOnClose, false);
    {
        QLabel *lbl = new QLabel(&splash);
        lbl->setPixmap(splashPix);
        lbl->setGeometry(0, 0, 360, 160);
    }
    if (QScreen *scr = QGuiApplication::primaryScreen()) {
        const QRect g = scr->availableGeometry();
        splash.move(g.center() - QPoint(180, 80));
    }
    // NOTA: el splash se muestra DESPUÉS de cargar la ventana (abajo), y el escaneo
    // pesado se difiere para que la interfaz abra de inmediato.

    AppController controller;
    ThemeProvider theme;
    MermaidRenderer mermaid;

    // Servidor de instancia única: cuando otra instancia intente abrirse, recibe
    // su "raise" y le pide a la UI que restaure/enfoque la ventana existente.
    QLocalServer::removeServer(kInstanceKey);   // limpiar socket huérfano de un crash
    auto *instanceServer = new QLocalServer(&app);
    if (instanceServer->listen(kInstanceKey)) {
        QObject::connect(instanceServer, &QLocalServer::newConnection, &controller, [instanceServer, &controller]() {
            if (QLocalSocket *c = instanceServer->nextPendingConnection()) {
                QObject::connect(c, &QLocalSocket::readyRead, &controller, [c, &controller]() {
                    const QString command = QString::fromUtf8(c->readAll()).trimmed();
                    if (command.startsWith(QStringLiteral("automation:")))
                        controller.runAutomation(command.mid(11));
                    else
                        controller.notifySecondInstance();
                    c->disconnectFromServer();
                    c->deleteLater();
                });
            }
        });
    }

    qDebug() << "Controllers ready";

    // El escaneo pesado (binaries/roots/hardware/catálogo) se DIFIERE a después de
    // mostrar la ventana (ver abajo), para que la interfaz abra de inmediato.

    QQmlApplicationEngine engine;

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() {
                         qCritical() << "QML object creation failed — aborting";
                         QCoreApplication::exit(-1);
                     }, Qt::QueuedConnection);

    engine.rootContext()->setContextProperty("App", &controller);
    engine.rootContext()->setContextProperty("Theme", &theme);
    engine.rootContext()->setContextProperty("Mermaid", &mermaid);
    engine.rootContext()->setContextProperty("AppIconSource", appIconSource);
    engine.rootContext()->setContextProperty("TrayIconSource", trayIconSource);
    engine.rootContext()->setContextProperty("StartedWithWindows", startedWithWindows);

    // Control API headless (espejo de AppController) para tests sin GUI.
    // Puerto: env LLAMACODE_CONTROL_PORT (default 8765). 0 = desactivado. Localhost.
    {
        const QByteArray pEnv = qgetenv("LLAMACODE_CONTROL_PORT");
        const quint16 port = pEnv.isEmpty() ? 8765 : static_cast<quint16>(pEnv.toUInt());
        auto *ctl = new ControlApi(&controller, &controller);
        ctl->start(port);
    }
    engine.addImportPath(QStringLiteral("qrc:/"));

    qDebug() << "Loading Main.qml";
    engine.loadFromModule("LlamaCode", "Main");

    if (engine.rootObjects().isEmpty()) {
        qCritical() << "No root objects — QML load failed";
        return -1;
    }

    const int runArg = app.arguments().indexOf(QStringLiteral("--run-automation"));
    if (runArg >= 0 && runArg + 1 < app.arguments().size()) {
        const QString automationId = app.arguments().at(runArg + 1);
        QTimer::singleShot(1500, &controller,
                           [&controller, automationId]() { controller.runAutomation(automationId); });
    }

    // Apertura rápida: la ventana se muestra primero; el escaneo pesado se difiere
    // (QTimer 0) para correr DESPUÉS del primer pintado. El splash aparece sobre la
    // ventana (transient parent → no se fuerza sobre otras apps) y se cierra al
    // terminar el escaneo, que dispara el refresco de la UI (setupStateChanged).
    QWindow *win = qobject_cast<QWindow *>(engine.rootObjects().constFirst());
    const bool startHidden = AppController::shouldStartHidden(
        startedWithWindows,
        controller.readSetting(QStringLiteral("window/minimizeToTray"), false).toBool());

    auto runDeferredStartup = [&controller, &splash, win, appIcon, startHidden]() {
        static bool done = false;
        if (done) return;
        done = true;
        if (win) win->setIcon(appIcon);
        if (win && win->isVisible() && !startHidden) {
            splash.show();
            if (QWindow *sh = splash.windowHandle()) {
                sh->setIcon(appIcon);
                sh->setTransientParent(win);   // arriba de LlamaCode, no de otras apps
            }
        }
        QTimer::singleShot(0, &controller, [&controller, &splash]() {
            controller.runStartupScan();       // escaneo pesado, ventana ya visible
            splash.close();                    // refresca UI (signals de runStartupScan)
        });
    };

    if (win && (win->isVisible() || startHidden))
        runDeferredStartup();
    else if (win)
        QObject::connect(win, &QWindow::visibleChanged, &controller,
                         [runDeferredStartup](bool v) { if (v) runDeferredStartup(); });
    else
        QTimer::singleShot(0, &controller, [&controller, &splash]() {
            controller.runStartupScan();
            splash.close();
        });

    qDebug() << "QML loaded OK — entering event loop";
    int ret = app.exec();
    qDebug() << "Event loop exited with code" << ret;
    return ret;
}
