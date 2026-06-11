#include "AppController.h"
#include "core/ControlApi.h"
#include "ThemeProvider.h"
#include <QApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QIcon>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QStandardPaths>
#include <QDir>
#include <QtMessageHandler>
#include <QSplashScreen>
#include <QPixmap>
#include <QPainter>
#include <QWindow>

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

    QApplication app(argc, argv);
    app.setWindowIcon(QIcon(":/assets/app_icon.png"));
    app.setApplicationName("LlamaCode");
    app.setOrganizationName("LlamaCode");
    app.setApplicationVersion("0.1.0");

    qDebug() << "QApplication ready";

    // Splash nativo: se muestra ANTES de cargar QML y cubre el escaneo pesado de
    // arranque (runStartupScan). Se cierra cuando la ventana principal aparece.
    QPixmap splashPix(360, 160);
    splashPix.fill(QColor(0x1e, 0x1e, 0x22));
    {
        QPainter p(&splashPix);
        QPixmap icon(":/assets/app_icon.png");
        if (!icon.isNull())
            p.drawPixmap((360 - 64) / 2, 28, icon.scaled(64, 64, Qt::KeepAspectRatio, Qt::SmoothTransformation));
        p.setPen(QColor(0xe0, 0xe0, 0xe0));
        QFont f = p.font(); f.setPointSize(11); p.setFont(f);
        p.drawText(QRect(0, 104, 360, 24), Qt::AlignCenter, "LlamaCode");
        p.setPen(QColor(0x9a, 0x9a, 0x9a));
        f.setPointSize(9); p.setFont(f);
        p.drawText(QRect(0, 128, 360, 20), Qt::AlignCenter, "Cargando…");
    }
    QSplashScreen splash(splashPix);
    splash.show();
    app.processEvents();

    AppController controller;
    ThemeProvider theme;

    qDebug() << "Controllers ready";

    // Escaneo pesado (binaries/roots/hardware/catálogo) con el splash visible.
    controller.runStartupScan();
    qDebug() << "Startup scan done";

    QQmlApplicationEngine engine;

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() {
                         qCritical() << "QML object creation failed — aborting";
                         QCoreApplication::exit(-1);
                     }, Qt::QueuedConnection);

    engine.rootContext()->setContextProperty("App", &controller);
    engine.rootContext()->setContextProperty("Theme", &theme);

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

    // Cerrar el splash cuando la ventana principal se haga visible (la geometría
    // se restaura en Main.qml Component.onCompleted → visible=true / showMaximized).
    if (auto *win = qobject_cast<QWindow *>(engine.rootObjects().constFirst())) {
        if (win->isVisible()) {
            splash.close();
        } else {
            QObject::connect(win, &QWindow::visibleChanged, &splash, [&splash](bool v) {
                if (v) splash.close();
            });
        }
    } else {
        splash.close();
    }

    qDebug() << "QML loaded OK — entering event loop";
    int ret = app.exec();
    qDebug() << "Event loop exited with code" << ret;
    return ret;
}
