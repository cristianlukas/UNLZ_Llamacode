#include "AppController.h"
#include "core/ControlApi.h"
#include "core/MermaidRenderer.h"
#include "ThemeProvider.h"
#include "TrayController.h"
#include "core/tasks/AutomationStore.h"
#include "core/tasks/TaskScheduler.h"
#include "core/tasks/SchedulerDaemonRegistration.h"
#include "core/diag/StartupDiagnostics.h"
#include <QApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QIcon>
#include <QFile>
#include <QDateTime>
#include <QEvent>
#include <QFileInfo>
#include <QStandardPaths>
#include <QDir>
#include <QPixmap>
#include <QPainter>
#include <QPointer>
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
#include <QElapsedTimer>
#include <memory>

#ifdef Q_OS_WIN
#  define WIN32_LEAN_AND_MEAN
#  define NOMINMAX
#  include <windows.h>
#  include <shobjidl.h>
#endif

class TrayWindowCloseFilter final : public QObject
{
public:
    TrayWindowCloseFilter(const TrayController *tray, QObject *parent = nullptr)
        : QObject(parent), m_tray(tray) {}

    void setForceQuit(bool forceQuit) { m_forceQuit = forceQuit; }

protected:
    bool eventFilter(QObject *watched, QEvent *event) override
    {
        if (!m_forceQuit && event->type() == QEvent::Close) {
            auto *window = qobject_cast<QWindow *>(watched);
            if (window
                && m_tray && m_tray->isAvailable()
                && QSettings().value(QStringLiteral("window/minimizeToTray"), false).toBool()) {
                // Ignorar el cierre antes de que QQuickWindow destruya su handle
                // nativo. Así el tray puede volver a mapear la misma ventana.
                event->ignore();
                window->hide();
                return true;
            }
        }
        return QObject::eventFilter(watched, event);
    }

private:
    const TrayController *m_tray = nullptr;
    bool m_forceQuit = false;
};

int main(int argc, char *argv[])
{
    // Modo test: redirige AppData/AppLocalData a una ubicación de prueba. Es la
    // misma perilla que usan los tests C++ (QStandardPaths::setTestModeEnabled),
    // expuesta por env var para los smokes headless que levantan el binario:
    // Qt resuelve esas rutas por la API de shell de Windows, así que pisar
    // %LOCALAPPDATA% NO alcanza y un smoke terminaba escribiendo memoria,
    // directivas y catálogo en la instalación real del usuario.
    if (qgetenv("LLAMACODE_TEST_MODE").trimmed() == "1")
        QStandardPaths::setTestModeEnabled(true);

    bool forceExpandedLog = false;
    for (int i = 1; i < argc; ++i) {
        if (QString::fromLocal8Bit(argv[i]) == QStringLiteral("--expanded-log")) {
            forceExpandedLog = true;
            break;
        }
    }
    QCoreApplication::setApplicationVersion(QStringLiteral("0.1.118"));
    StartupDiagnostics::initializeEarly(
        QFileInfo(QString::fromLocal8Bit(argv[0])).absoluteFilePath(), forceExpandedLog);
    QElapsedTimer startupClock;
    startupClock.start();
    qDebug() << "=== LlamaCode starting ===" << QDateTime::currentDateTime().toString()
             << "elapsedMs=0";

    // Estilo de Qt Quick Controls: forzar "Basic" (customizable). El default en
    // Windows es el estilo NATIVO, que ignora los override de background/contentItem/
    // header/footer con los que toda la UI está themeada → diálogos sin contenido ni
    // botones, checkbox sin pintar y warnings "current style does not support
    // customization". Debe setearse ANTES de cargar cualquier QML.
    StartupDiagnostics::record(QStringLiteral("phase_begin"),
                               {{QStringLiteral("phase"), QStringLiteral("QQuickStyle")}});
    QQuickStyle::setStyle(QStringLiteral("Basic"));
    StartupDiagnostics::record(QStringLiteral("phase_complete"),
                               {{QStringLiteral("phase"), QStringLiteral("QQuickStyle")},
                                {QStringLiteral("elapsedMs"), startupClock.elapsed()}});

    StartupDiagnostics::record(QStringLiteral("phase_begin"),
                               {{QStringLiteral("phase"), QStringLiteral("QApplication")}});
    QApplication app(argc, argv);
    StartupDiagnostics::record(QStringLiteral("phase_complete"),
                               {{QStringLiteral("phase"), QStringLiteral("QApplication")},
                                {QStringLiteral("elapsedMs"), startupClock.elapsed()}});
    app.setQuitOnLastWindowClosed(false);
    app.setApplicationName("LlamaCode");
    app.setOrganizationName("LlamaCode");
    app.setApplicationVersion("0.1.118");
    const bool startedWithWindows = app.arguments().contains(QStringLiteral("--startup"));
    const bool handoffUi = app.arguments().contains(QStringLiteral("--handoff-ui"));
    const bool headlessAgent = app.arguments().contains(QStringLiteral("--headless"))
        || app.arguments().contains(QStringLiteral("--agent-daemon"));
    const bool forceDevMode = app.arguments().contains(QStringLiteral("--dev-mode"));
    const bool forceNormalMode = app.arguments().contains(QStringLiteral("--normal-mode"));
    const bool devModeAtLaunch = !forceNormalMode
        && (forceDevMode || QSettings().value(QStringLiteral("app/devMode"), false).toBool());

    // Pulso del event loop GUI. El modo ampliado registra el último pulso y
    // cualquier pausa >=250 ms, para diagnosticar bloqueos síncronos al volver.
    QTimer *eventLoopProbe = nullptr;
    auto eventLoopClock = std::make_shared<QElapsedTimer>();
    auto eventLoopStartedStorage = std::make_shared<bool>(false);
    auto lastTickStorage = std::make_shared<qint64>(0);
    auto lastHeartbeatStorage = std::make_shared<qint64>(0);
    if (!headlessAgent) {
        eventLoopClock->start();
        eventLoopProbe = new QTimer(&app);
        eventLoopProbe->setInterval(100);
        *lastTickStorage = eventLoopClock->elapsed();
        *lastHeartbeatStorage = *lastTickStorage;
        QObject::connect(eventLoopProbe, &QTimer::timeout, &app,
                         [eventLoopClock, lastTickStorage, lastHeartbeatStorage]() {
            const qint64 now = eventLoopClock->elapsed();
            const qint64 gap = now - *lastTickStorage;
            *lastTickStorage = now;
            if (StartupDiagnostics::expandedEnabled() && gap >= 250) {
                StartupDiagnostics::record(QStringLiteral("gui_event_loop_stall"),
                    {{QStringLiteral("gapMs"), gap}});
                qWarning() << "GUI event-loop pause ms=" << gap;
            }
            if (StartupDiagnostics::expandedEnabled() && now - *lastHeartbeatStorage >= 5000) {
                *lastHeartbeatStorage = now;
                StartupDiagnostics::record(QStringLiteral("gui_heartbeat"),
                    {{QStringLiteral("sincePreviousTickMs"), gap}});
            }
        });
    }

    // Companion sin UI: evalúa el mismo AutomationStore/cron y despierta la app
    // por IPC. Un lock evita duplicados; el toggle persistido lo apaga solo.
    if (app.arguments().contains(QStringLiteral("--scheduler-daemon"))) {
        const bool schedulerSmoke = qEnvironmentVariableIsSet("LLAMACODE_SCHEDULER_SMOKE");
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
        if (!schedulerSmoke
            && !QSettings().value(QStringLiteral("tasks/schedulerEnabled"), false).toBool())
            return 0;
        settingsWatch.start();
        auto writeHeartbeat = []() {
            QFile file(SchedulerDaemonRegistration::heartbeatPath());
            if (file.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text))
                file.write(QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs).toUtf8());
        };
        QTimer heartbeat;
        heartbeat.setInterval(15000);
        QObject::connect(&heartbeat, &QTimer::timeout, &app, writeHeartbeat);
        QObject::connect(&app, &QCoreApplication::aboutToQuit, &app, []() {
            QFile::remove(SchedulerDaemonRegistration::heartbeatPath());
        });
        writeHeartbeat();
        heartbeat.start();
        scheduler.setEnabled(true);
        return app.exec();
    }

    // ── Instancia única ──
    // Si ya hay una instancia (incluida la del tray), pedirle que se muestre y salir,
    // en vez de abrir una segunda (que duplicaría el botón en la taskbar).
#ifdef LC_DEBUG_ICON
    const QString kInstanceKey = QStringLiteral("LlamaCode-single-instance-debug");
#else
    const QString kInstanceKey = QStringLiteral("LlamaCode-single-instance");
#endif
    if (!handoffUi) {
        QLocalSocket probe;
        probe.connectToServer(kInstanceKey);
        if (probe.waitForConnected(250)) {
            // La instancia existente puede ser headless: el proceso conserva su
            // núcleo y materializa la UI dentro de sí mismo al recibir este comando.
            probe.write("show-ui");
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
#ifdef LC_DEBUG_ICON
    SetCurrentProcessExplicitAppUserModelID(L"LlamaCode.Desktop.Debug");
#else
    SetCurrentProcessExplicitAppUserModelID(L"LlamaCode.Desktop.App");
#endif
#endif

    // Icono según build: Debug = rojo (debug_icon), Release = normal. Coincide
    // con el icono embebido en el .exe (app_icon.rc).
#ifdef LC_DEBUG_ICON
    const QString appIconSource = QStringLiteral("qrc:/assets/debug_icon.ico");
    const QString trayIconSource = appIconSource;
    const QIcon appIcon(QStringLiteral(":/assets/debug_icon.ico"));
#else
#ifdef Q_OS_WIN
    const QString appIconSource = QStringLiteral("qrc:/assets/app_icon.ico");
    const QString trayIconSource = QStringLiteral("qrc:/assets/tray_icon.png");
    const QIcon appIcon(QStringLiteral(":/assets/app_icon.ico"));
#else
    // Linux/GNOME consume mejor el PNG que el contenedor ICO. Ambos recursos
    // siguen embebidos; Windows conserva el ICO para la identidad del .exe.
    const QString appIconSource = QStringLiteral("qrc:/assets/app_icon.png");
    const QString trayIconSource = QStringLiteral("qrc:/assets/tray_icon.png");
    const QIcon appIcon(QStringLiteral(":/assets/app_icon.png"));
#endif
#endif
    app.setWindowIcon(appIcon);
    qDebug() << "QApplication ready elapsedMs=" << startupClock.elapsed();

    // Splash nativo: se muestra ANTES de cargar QML y cubre el escaneo pesado de
    // arranque (runStartupScan). Se cierra cuando startupBusy pasa a false.
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
    QLabel *splashImage = new QLabel(&splash);
    splashImage->setPixmap(splashPix);
    splashImage->setGeometry(0, 0, 360, 160);
    QLabel *splashStatus = new QLabel(QStringLiteral("Cargando…"), &splash);
    splashStatus->setGeometry(12, 128, 336, 20);
    splashStatus->setAlignment(Qt::AlignCenter);
    splashStatus->setStyleSheet(QStringLiteral("color:#9a9a9a; font:9pt 'Segoe UI';"));
    if (QScreen *scr = QGuiApplication::primaryScreen()) {
        const QRect g = scr->availableGeometry();
        splash.move(g.center() - QPoint(180, 80));
    }
    const bool startHidden = AppController::shouldStartHidden(
        startedWithWindows,
        QSettings().value(QStringLiteral("window/minimizeToTray"), false).toBool());
    if (!headlessAgent && !startHidden) {
        splash.show();
        // Fuerza el primer pintado antes de construir el controlador y cargar QML.
        // Así el splash no queda esperando al primer app.exec().
        app.processEvents();
    }
    AppController controller;
    if (eventLoopProbe) {
        auto refreshProbeState = [eventLoopProbe, eventLoopClock, lastTickStorage,
                                  lastHeartbeatStorage, eventLoopStartedStorage,
                                  &controller]() {
            if (!*eventLoopStartedStorage)
                return;
            const bool enabled = controller.devMode() || controller.expandedLogging();
            if (enabled && !eventLoopProbe->isActive()) {
                // El monitor puede activarse mucho después del inicio (por ejemplo,
                // al habilitar log ampliado desde Configuración). No contar ese
                // tiempo dormido como una pausa real de la interfaz.
                const qint64 now = eventLoopClock->elapsed();
                *lastTickStorage = now;
                *lastHeartbeatStorage = now;
                eventLoopProbe->start();
            }
            else if (!enabled && eventLoopProbe->isActive()) eventLoopProbe->stop();
        };
        QObject::connect(&controller, &AppController::devModeChanged, &app, refreshProbeState);
        QObject::connect(&controller, &AppController::expandedLoggingChanged, &app, refreshProbeState);
    }
    if (forceDevMode)
        controller.setDevMode(true);
    else if (forceNormalMode)
        controller.setDevMode(false);
    ThemeProvider theme;
    MermaidRenderer mermaid;
    QString trayIconResource = trayIconSource;
    if (trayIconResource.startsWith(QStringLiteral("qrc:/")))
        trayIconResource = QStringLiteral(":") + trayIconResource.mid(4);
    QIcon trayIcon(trayIconResource);
    if (trayIcon.isNull()) {
        qWarning() << "No se pudo cargar el icono del tray:" << trayIconResource
                   << "se usará el icono principal";
        trayIcon = appIcon;
    }
    TrayController tray(trayIcon, &app);
    qInfo() << "System tray:" << (tray.isAvailable() ? "available" : "unavailable")
            << "iconNull=" << trayIcon.isNull();

    QObject::connect(&controller, &AppController::startupChanged, &app,
                     [&controller, &splash, splashStatus]() {
        if (!splashStatus) return;
        const QString status = controller.startupStatus();
        if (!status.isEmpty())
            splashStatus->setText(status);
        if (!controller.startupBusy() && !status.isEmpty())
            splash.close();
    });
    if (!headlessAgent && !startHidden)
        splash.show();

    // API local para UI externa, CLI y pruebas. En --headless / --agent-daemon
    // se convierte en el único frontend y no se carga QML.
    const QByteArray controlPortEnv = qgetenv("LLAMACODE_CONTROL_PORT");
    const quint16 controlPort = controlPortEnv.isEmpty()
        ? 8765 : static_cast<quint16>(controlPortEnv.toUInt());
    auto *controlApi = new ControlApi(&controller, &controller);
    controlApi->start(controlPort);

    // El canal remoto del asistente sólo se habilita con un token explícito en
    // el entorno. Sin token no se abre ningún listener adicional.
    const QByteArray assistantToken = qgetenv("LLAMACODE_ASSISTANT_TOKEN");
    if (!assistantToken.trimmed().isEmpty()) {
        bool ok = false;
        const int requestedPort = qgetenv("LLAMACODE_ASSISTANT_PORT").toInt(&ok);
        const int assistantPort = ok && requestedPort > 0 ? requestedPort : 8787;
        const bool assistantLan = qgetenv("LLAMACODE_ASSISTANT_LAN") == QByteArrayLiteral("1");
        const QString startedToken = controller.startAssistantGateway(
            assistantPort, QString::fromUtf8(assistantToken), assistantLan);
        qInfo() << "AssistantRuntime:" << (!startedToken.isEmpty() ? "activo" : "no disponible")
                << "port=" << assistantPort << "lan=" << assistantLan;
    }

    // Servidor de instancia única: cuando otra instancia intente abrirse, recibe
    // su "raise" y le pide a la UI que restaure/enfoque la ventana existente.
    // Si la instancia existente es headless no hay QML que restaurar: hacemos un
    // handoff limpio a una instancia gráfica del mismo ejecutable.
    QLocalServer::removeServer(kInstanceKey);   // limpiar socket huérfano de un crash
    auto *instanceServer = new QLocalServer(&app);
    const bool instanceListening = instanceServer->listen(kInstanceKey);
    qInfo() << "Servidor de instancia local:" << (instanceListening ? "activo" : "falló")
            << "key=" << kInstanceKey
            << (instanceListening ? QString() : instanceServer->errorString());
    if (instanceListening) {
        const auto processConnection = [instanceServer, &controller, &app,
                                        headlessAgent, kInstanceKey](QLocalSocket *c) {
            if (!c) return;
            // El cliente escribe y cierra muy rápido (en particular el lanzador
            // de Ubuntu). Esperar aquí evita perder el payload antes de que
            // readyRead sea despachado por el event loop.
            if (c->bytesAvailable() <= 0)
                c->waitForReadyRead(500);
            const QString command = QString::fromUtf8(c->readAll()).trimmed();
            if (command == QStringLiteral("show-ui") && headlessAgent) {
                // Liberar el nombre antes de iniciar la GUI; de lo contrario la
                // GUI recién lanzada se detectaría a sí misma como segunda.
                instanceServer->close();
                QLocalServer::removeServer(kInstanceKey);
                QStringList guiArgs = app.arguments();
                guiArgs.removeAll(QStringLiteral("--headless"));
                guiArgs.removeAll(QStringLiteral("--agent-daemon"));
                guiArgs.append(QStringLiteral("--handoff-ui"));
                QTimer::singleShot(0, &app, [guiArgs, &app]() {
                    if (!QProcess::startDetached(QCoreApplication::applicationFilePath(), guiArgs))
                        qWarning() << "No se pudo convertir la instancia headless a GUI";
                    app.quit();
                });
            } else if (command.startsWith(QStringLiteral("automation:"))) {
                controller.runAutomation(command.mid(11));
            } else if (command == QStringLiteral("show-ui")) {
                controller.notifySecondInstance();
            }
            c->disconnectFromServer();
            c->deleteLater();
        };
        const auto acceptConnections = [instanceServer, processConnection]() {
            while (instanceServer->hasPendingConnections())
                processConnection(instanceServer->nextPendingConnection());
        };
        QObject::connect(instanceServer, &QLocalServer::newConnection, &app,
                         acceptConnections);
        // El polling cubre sesiones X11/Wayland en las que el backend entrega
        // la conexión sin emitir newConnection en el mismo ciclo.
        auto *instancePoller = new QTimer(instanceServer);
        instancePoller->setInterval(50);
        QObject::connect(instancePoller, &QTimer::timeout, &app, acceptConnections);
        instancePoller->start();
    }

    qDebug() << "Controllers ready";
    StartupDiagnostics::record(QStringLiteral("phase_complete"),
                               {{QStringLiteral("phase"), QStringLiteral("controllers_ready")},
                                {QStringLiteral("elapsedMs"), startupClock.elapsed()}});

    // El daemon headless no necesita QML. Además de ahorrar carga y memoria,
    // esto evita que un error visual de una página pueda tumbar la ControlApi
    // antes de que los clientes externos puedan usarla.
    if (headlessAgent) {
        qDebug() << "Agent daemon headless activo en localhost:" << controlPort;
        // En GUI estas colecciones se inicializan durante el flujo de carga de
        // la página Benchmark. El daemon debe dejarlas listas para que la API
        // pueda iniciar benchmarks inmediatamente después de /health.
        controller.loadBenchmarkResults();
        controller.loadCustomBenchmarks();
        QTimer::singleShot(0, &controller, &AppController::runStartupScan);
        return app.exec();
    }

    QQmlApplicationEngine engine;

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() {
                         qCritical() << "QML object creation failed — aborting";
                         QCoreApplication::exit(-1);
                     }, Qt::QueuedConnection);

    engine.rootContext()->setContextProperty("App", &controller);
    engine.rootContext()->setContextProperty("Theme", &theme);
    engine.rootContext()->setContextProperty("Mermaid", &mermaid);
    engine.rootContext()->setContextProperty("Tray", &tray);
    engine.rootContext()->setContextProperty("AppIconSource", appIconSource);
    engine.rootContext()->setContextProperty("TrayIconSource", trayIconSource);
    engine.rootContext()->setContextProperty("StartedWithWindows", startedWithWindows);
    engine.rootContext()->setContextProperty("HeadlessMode", headlessAgent);

    engine.addImportPath(QStringLiteral("qrc:/"));

    qDebug() << "Loading Main.qml elapsedMs=" << startupClock.elapsed();
    StartupDiagnostics::record(QStringLiteral("phase_begin"),
                               {{QStringLiteral("phase"), QStringLiteral("Main.qml")},
                                {QStringLiteral("elapsedMs"), startupClock.elapsed()}});
    engine.loadFromModule("LlamaCode", "Main");

    if (engine.rootObjects().isEmpty()) {
        StartupDiagnostics::record(QStringLiteral("phase_failed"),
                                   {{QStringLiteral("phase"), QStringLiteral("Main.qml")},
                                    {QStringLiteral("elapsedMs"), startupClock.elapsed()}});
        qCritical() << "No root objects — QML load failed";
        splash.close();
        return -1;
    }
    StartupDiagnostics::record(QStringLiteral("phase_complete"),
                               {{QStringLiteral("phase"), QStringLiteral("Main.qml")},
                                {QStringLiteral("elapsedMs"), startupClock.elapsed()},
                                {QStringLiteral("rootObjectCount"), engine.rootObjects().size()}});
    controller.recordPerformanceSample(QStringLiteral("qml_loaded"));

    const int runArg = app.arguments().indexOf(QStringLiteral("--run-automation"));
    if (runArg >= 0 && runArg + 1 < app.arguments().size()) {
        const QString automationId = app.arguments().at(runArg + 1);
        QTimer::singleShot(1500, &controller,
                           [&controller, automationId]() { controller.runAutomation(automationId); });
    }

    // Apertura rápida: la ventana se muestra primero; el escaneo pesado se difiere
    // (QTimer 0) para correr DESPUÉS del primer pintado. El splash permanece sobre
    // la ventana (transient parent → no se fuerza sobre otras apps) hasta terminar
    // el escaneo y el refresco de la UI.
    QWindow *win = qobject_cast<QWindow *>(engine.rootObjects().constFirst());
    // La ventana puede quedar oculta por "minimizar a la bandeja". Restaurarla
    // desde C++ evita depender de que QML procese una señal mientras la ventana
    // está oculta y hace que funcionen igual el click del tray y una segunda
    // apertura desde el lanzador de Ubuntu/Windows.
    const QPointer<QWindow> windowGuard(win);
    auto restoreWindow = [windowGuard]() {
        QWindow *window = windowGuard.data();
        if (!window) return;
        // QWindow puede conservar isVisible=true después de que el WM procesa
        // WM_DELETE_WINDOW y QML oculta la superficie. Forzar hide primero
        // garantiza que la siguiente orden vuelva a mapearla en X11.
        window->hide();
        if (QSettings().value(QStringLiteral("window/maximized"), false).toBool())
            window->showMaximized();
        else
            window->showNormal();
        window->show();
        window->raise();
        window->requestActivate();
    };
    QObject::connect(&controller, &AppController::secondInstanceLaunched,
                     &app, restoreWindow);
    QObject::connect(&tray, &TrayController::openRequested, &app, restoreWindow);
    auto *trayCloseFilter = new TrayWindowCloseFilter(&tray, &app);
    QObject::connect(&tray, &TrayController::quitRequested, &app,
                     [trayCloseFilter]() { trayCloseFilter->setForceQuit(true); });
    if (win)
        win->installEventFilter(trayCloseFilter);

    auto runDeferredStartup = [&controller, &splash, &startupClock,
                               win, appIcon, startHidden]() {
        static bool done = false;
        if (done) return;
        done = true;
        if (win) win->setIcon(appIcon);
        if (win && win->isVisible() && !startHidden) {
            qDebug() << "First window visible elapsedMs=" << startupClock.elapsed();
            controller.recordPerformanceSample(QStringLiteral("first_window_visible"));
            if (!splash.isVisible())
                splash.show();
            if (QWindow *sh = splash.windowHandle()) {
                sh->setIcon(appIcon);
                sh->setTransientParent(win);   // arriba de LlamaCode, no de otras apps
            }
        }
        QTimer::singleShot(0, &controller, [&controller, &splash]() {
            controller.runStartupScan();       // el splash queda hasta startupBusy=false
        });
    };

    if (headlessAgent) {
        qDebug() << "Agent daemon headless activo en localhost:" << controlPort;
        if (win) win->setVisible(false);
        QTimer::singleShot(0, &controller, &AppController::runStartupScan);
    } else if (win && (win->isVisible() || startHidden))
        runDeferredStartup();
    else if (win)
        QObject::connect(win, &QWindow::visibleChanged, &controller,
                         [runDeferredStartup](bool v) { if (v) runDeferredStartup(); });
    else
        QTimer::singleShot(0, &controller, [&controller]() {
            controller.runStartupScan();
        });

    qDebug() << "QML loaded OK — entering event loop elapsedMs=" << startupClock.elapsed();
    if (eventLoopProbe) {
        *eventLoopStartedStorage = true;
        if (devModeAtLaunch || StartupDiagnostics::expandedEnabled()) {
            const qint64 now = eventLoopClock->elapsed();
            *lastTickStorage = now;
            *lastHeartbeatStorage = now;
            eventLoopProbe->start();
        }
    }
    int ret = app.exec();
    qDebug() << "Event loop exited with code" << ret;
    return ret;
}
