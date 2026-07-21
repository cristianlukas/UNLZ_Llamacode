// Probe E2E opt-in del matcher visual. Abre una ventana Qt propia, captura una
// plantilla real al DPI del monitor elegido y la busca en foreground. Sólo mueve
// el mouse/clickea con --execute-click; nunca se registra en ctest.
#include <QApplication>
#include <QCommandLineParser>
#include <QDebug>
#include <QDir>
#include <QPushButton>
#include <QJsonDocument>
#include <QJsonObject>
#include <QScreen>
#include <QTemporaryDir>
#include <QTextStream>
#include <QTimer>
#include <QVBoxLayout>

#include "core/automation/DesktopAutomationBackend.h"

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    QCommandLineParser parser;
    parser.addHelpOption();
    parser.addOption({QStringLiteral("execute-click"), QStringLiteral("Ejecuta el clic real sobre la ventana del probe.")});
    parser.addOption({QStringLiteral("screen"), QStringLiteral("Índice de monitor para QA DPI/multimonitor."),
                      QStringLiteral("index"), QStringLiteral("0")});
    parser.process(app);

    QWidget window;
    window.setWindowTitle(QStringLiteral("LlamaCode Visual QA Probe"));
    window.resize(640, 380);
    auto *layout = new QVBoxLayout(&window);
    auto *button = new QPushButton(QStringLiteral("◆ OBJETIVO VISUAL ÚNICO 7429 ◆"), &window);
    button->setFixedSize(260, 72);
    button->setStyleSheet(QStringLiteral(
        "QPushButton { color:white; background:#3157c8; border:5px solid #f2b84b; "
        "border-radius:13px; font:700 14px 'Segoe UI'; }"));
    layout->addStretch(); layout->addWidget(button, 0, Qt::AlignCenter); layout->addStretch();
    const QList<QScreen *> screens = QGuiApplication::screens();
    const int screenIndex = screens.isEmpty() ? 0
        : qBound(0, parser.value(QStringLiteral("screen")).toInt(), screens.size() - 1);
    if (!screens.isEmpty()) {
        const QRect area = screens.at(screenIndex)->availableGeometry();
        window.move(area.center() - QPoint(window.width() / 2, window.height() / 2));
    }
    bool clicked = false;
    QObject::connect(button, &QPushButton::clicked, [&clicked]() { clicked = true; });
    window.show();

    QTemporaryDir temp;
    QTimer::singleShot(800, [&]() {
        QString targetId;
        for (const QVariant &v : DesktopAutomationBackend::windows()) {
            const QVariantMap row = v.toMap();
            if (row.value(QStringLiteral("label")).toString().contains(window.windowTitle())) {
                targetId = row.value(QStringLiteral("id")).toString(); break;
            }
        }
        QString error;
        const QString needlePath = temp.filePath(QStringLiteral("needle.png"));
        const QImage full = DesktopAutomationBackend::capture(
            QStringLiteral("window"), targetId, &error);
        const double dpr = screens.isEmpty() ? 1.0 : screens.at(screenIndex)->devicePixelRatio();
        const QPoint relative = button->mapToGlobal(QPoint()) - window.frameGeometry().topLeft();
        const QRect buttonRect(qRound(relative.x() * dpr), qRound(relative.y() * dpr),
                               qRound(button->width() * dpr), qRound(button->height() * dpr));
        full.copy(buttonRect.intersected(full.rect())).save(needlePath, "PNG");
        const QVariantMap match = DesktopAutomationBackend::findImage(
            QStringLiteral("window"), targetId, needlePath, 0.86, 0.8, 1.25, true, &error);
        QTextStream out(stdout);
        out << "screen=" << screenIndex
            << " dpr=" << dpr
            << " target=" << targetId << " match="
            << QString::fromUtf8(QJsonDocument(QJsonObject::fromVariantMap(match)).toJson(QJsonDocument::Compact))
            << " error=" << error << Qt::endl;
        if (!match.value(QStringLiteral("found")).toBool() || match.value(QStringLiteral("ambiguous")).toBool())
            return app.exit(2);
        if (!parser.isSet(QStringLiteral("execute-click"))) return app.exit(0);
        QVariantMap trace;
        if (!DesktopAutomationBackend::clickImage(QStringLiteral("window"), targetId,
                needlePath, 0.86, 0.8, 1.25, QStringLiteral("left"), &error, &trace)) {
            qWarning().noquote() << error;
            return app.exit(3);
        }
        QTimer::singleShot(250, [&]() { app.exit(clicked ? 0 : 4); });
    });
    return app.exec();
}
