// Tests de TrayController: el menu contextual del icono de bandeja.
#include <QtTest>
#include <QAction>
#include <QApplication>
#include <QCloseEvent>
#include <QImage>
#include <QMenu>
#include <QStyle>
#include <QSettings>
#include <QStandardPaths>
#include <QStyleFactory>
#include <QWindow>
#include "TrayController.h"

class TrayTests : public QObject
{
    Q_OBJECT
private slots:
    void initTestCase();
    void menuTextStartsNearLeftEdge_data();
    void menuTextStartsNearLeftEdge();
    void teachActionsOnlyWhileRecording();
    void closeHidesToTrayUntilQuit();
    void quitClosesWindowEvenIfEarlierSlotCloses();
};

namespace {
// Distancia entre el borde izquierdo de la accion y el primer pixel de su texto.
int textLeftGap(QMenu *menu, QAction *action)
{
    menu->adjustSize();
    const QImage img = menu->grab().toImage();
    const QRect r = menu->actionGeometry(action);
    const QRgb bg = img.pixel(r.right() - 3, r.center().y());
    auto differs = [bg](QRgb c) {
        return qAbs(qRed(c) - qRed(bg)) + qAbs(qGreen(c) - qGreen(bg))
             + qAbs(qBlue(c) - qBlue(bg)) > 90;
    };
    for (int x = r.left() + 1; x < r.right(); ++x) {
        for (int y = r.top() + 2; y < r.bottom() - 1; ++y) {
            if (differs(img.pixel(x, y)))
                return x - r.left();
        }
    }
    return -1;
}
} // namespace

void TrayTests::initTestCase()
{
    // El app fija estos nombres en main.cpp. Sin ellos, en Windows un QSettings()
    // por defecto no puede escribir en el registro (AccessError): el filtro leía
    // minimizeToTray=false y closeHidesToTrayUntilQuit fallaba sólo en el CI de
    // Windows (en Linux cae a "Unknown Organization" y anda).
    QCoreApplication::setOrganizationName(QStringLiteral("LlamaCodeTests"));
    QCoreApplication::setApplicationName(QStringLiteral("test_tray"));
    QStandardPaths::setTestModeEnabled(true);
    QSettings probe;
    probe.setValue(QStringLiteral("probe"), 1);
    probe.sync();
    QCOMPARE(probe.status(), QSettings::NoError);
    probe.remove(QStringLiteral("probe"));
}

void TrayTests::menuTextStartsNearLeftEdge_data()
{
    QTest::addColumn<QString>("style");
    const QStringList keys = QStyleFactory::keys();
    for (const QString &k : keys)
        QTest::newRow(qPrintable(k)) << k;
}

void TrayTests::menuTextStartsNearLeftEdge()
{
    // El estilo nativo de Windows 11/Vista reserva una columna para iconos y
    // checks aunque ninguna accion tenga: el menu del tray quedaba con un
    // hueco grande a la izquierda de "Abrir"/"Salir".
    QFETCH(QString, style);
    QApplication::setStyle(style);
    TrayController tray(QIcon{});
    QMenu *menu = tray.menuForTest();
    QAction *open = menu->actions().constFirst();
    QVERIFY(open->isVisible());
    const int gap = textLeftGap(menu, open);
    qInfo().noquote() << style << "gap =" << gap << "menu width =" << menu->width();
    QVERIFY2(gap >= 0, "no se encontro el texto");
    QVERIFY2(gap <= 24, qPrintable(QStringLiteral("hueco de %1 px antes del texto").arg(gap)));
}

void TrayTests::teachActionsOnlyWhileRecording()
{
    TrayController tray(QIcon{});
    QMenu *menu = tray.menuForTest();
    auto visibleTexts = [menu]() {
        QStringList out;
        for (QAction *a : menu->actions())
            if (a->isVisible() && !a->isSeparator()) out << a->text();
        return out;
    };
    QCOMPARE(visibleTexts().size(), 2);   // Abrir + Salir
    tray.setTeachState(QStringLiteral("recording"));
    QCOMPARE(visibleTexts().size(), 5);
    tray.setTeachState(QString());
    QCOMPARE(visibleTexts().size(), 2);
}

namespace {
// Lo mismo que hace QCoreApplication::quit() en Qt 6: un Close sincrónico a cada
// ventana; si alguna lo rechaza, la salida se cancela.
bool sendClose(QWindow *window)
{
    QCloseEvent close;
    QCoreApplication::sendEvent(window, &close);
    return close.isAccepted();
}
} // namespace

void TrayTests::closeHidesToTrayUntilQuit()
{
    QStandardPaths::setTestModeEnabled(true);
    QSettings().setValue(QStringLiteral("window/minimizeToTray"), true);
    TrayController tray(QIcon{});
    tray.setAvailableForTest(true);
    QWindow window;
    TrayWindowCloseFilter filter(&tray);
    window.installEventFilter(&filter);
    QVERIFY(!sendClose(&window));      // cerrar la ventana = minimizar a la bandeja
    QVERIFY(!tray.isQuitting());
    QSettings().remove(QStringLiteral("window/minimizeToTray"));
}

void TrayTests::quitClosesWindowEvenIfEarlierSlotCloses()
{
    // Main.qml se conecta a quitRequested antes que main.cpp y su handler hace
    // Qt.quit() en el acto. Ese cierre tiene que pasar el filtro: antes lo
    // rechazaba, la salida se cancelaba y LlamaCode quedaba vivo y oculto.
    QStandardPaths::setTestModeEnabled(true);
    QSettings().setValue(QStringLiteral("window/minimizeToTray"), true);
    TrayController tray(QIcon{});
    tray.setAvailableForTest(true);
    QWindow window;
    TrayWindowCloseFilter filter(&tray);
    window.installEventFilter(&filter);
    bool acceptedInSlot = false;
    connect(&tray, &TrayController::quitRequested, &window,
            [&]() { acceptedInSlot = sendClose(&window); });
    QAction *quit = tray.menuForTest()->actions().constLast();
    QCOMPARE(quit->text(), QStringLiteral("Salir"));
    quit->trigger();
    QVERIFY(tray.isQuitting());
    QVERIFY2(acceptedInSlot, "el filtro rechazó el cierre durante Salir");
    QSettings().remove(QStringLiteral("window/minimizeToTray"));
}

QTEST_MAIN(TrayTests)
#include "test_tray.moc"
