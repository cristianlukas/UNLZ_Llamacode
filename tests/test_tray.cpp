// Tests de TrayController: el menu contextual del icono de bandeja.
#include <QtTest>
#include <QAction>
#include <QApplication>
#include <QImage>
#include <QMenu>
#include <QStyle>
#include <QStyleFactory>
#include "TrayController.h"

class TrayTests : public QObject
{
    Q_OBJECT
private slots:
    void menuTextStartsNearLeftEdge_data();
    void menuTextStartsNearLeftEdge();
    void teachActionsOnlyWhileRecording();
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

QTEST_MAIN(TrayTests)
#include "test_tray.moc"
