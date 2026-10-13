// Unit tests de OcrTextLocator: ubicar un texto pedido dentro de líneas OCR y
// devolver su caja. PURO — las líneas se fabrican a mano, no hay OCR ni pantalla
// (el motor WinRT real es QA manual: necesita una sesión de escritorio viva).
//
// Cubre lo que importa: frases multi-palabra, el cutoff alto (un click a ciegas
// es irreversible) y la detección de ambigüedad.

#include <QtTest>
#include "core/automation/OcrTextLocator.h"
#include "core/automation/OcrEngine.h"
#include <QImage>
#include <QPainter>
#include <QFont>

namespace {

// Arma una línea con palabras de 60x20 px espaciadas, arrancando en (x,y).
OcrLine makeLine(const QStringList &words, int x, int y)
{
    OcrLine line;
    line.text = words.join(QLatin1Char(' '));
    int cx = x;
    for (const QString &w : words) {
        OcrWord ow;
        ow.text = w;
        ow.rect = QRect(cx, y, 60, 20);
        line.words.append(ow);
        cx += 70;
    }
    return line;
}

}   // namespace

class OcrLocatorTests : public QObject
{
    Q_OBJECT
private slots:
    void find_singleWordReturnsItsBox();
    void find_multiWordPhraseUnitesBoxes();
    void find_toleratesOcrNoiseAndVariants();
    void find_returnsNothingWhenTextAbsent();
    void find_prefersShortestPhraseOnTie();
    void find_doesNotSpanAcrossLines();
    void findAll_reportsAmbiguityWhenTextRepeats();
    void find_emptyInputs();
    void opaqueForOcr_fixesZeroAlphaCaptures();
    void ocr_readsZeroAlphaWindowCapture();
    void ocr_blankImageDoesNotCrash();
};

void OcrLocatorTests::find_singleWordReturnsItsBox()
{
    const QList<OcrLine> lines{makeLine({QStringLiteral("Guardar")}, 100, 200)};
    const auto hit = OcrTextLocator::find(lines, QStringLiteral("Guardar"));
    QVERIFY(hit.ok());
    QCOMPARE(hit.score, 100);
    QCOMPARE(hit.rect, QRect(100, 200, 60, 20));
    // QRect tiene bordes inclusivos (x2 = x + w - 1), así que el centro cae en
    // (129,209), no en (130,210). Es el punto al que se manda el clic: dentro de
    // la palabra, que es lo único que importa.
    QCOMPARE(hit.center(), QRect(100, 200, 60, 20).center());
    QVERIFY(hit.rect.contains(hit.center()));
    QCOMPARE(hit.lineIndex, 0);
}

void OcrLocatorTests::find_multiWordPhraseUnitesBoxes()
{
    // "Guardar como" son dos OcrWord: la caja devuelta tiene que abarcar ambas,
    // porque el centro de una sola palabra puede caer fuera del botón real.
    const QList<OcrLine> lines{
        makeLine({QStringLiteral("Guardar"), QStringLiteral("como")}, 100, 200)};
    const auto hit = OcrTextLocator::find(lines, QStringLiteral("Guardar como"));
    QVERIFY(hit.ok());
    QCOMPARE(hit.score, 100);
    // Une (100,200,60,20) con (170,200,60,20).
    QCOMPARE(hit.rect, QRect(100, 200, 130, 20));
    QCOMPARE(hit.text, QStringLiteral("Guardar como"));
}

void OcrLocatorTests::find_toleratesOcrNoiseAndVariants()
{
    const QList<OcrLine> lines{
        makeLine({QStringLiteral("&Guardar"), QStringLiteral("como...")}, 10, 10)};
    // Acelerador y elipsis: el usuario dice el label limpio.
    QVERIFY(OcrTextLocator::find(lines, QStringLiteral("Guardar como")).ok());

    // Tilde perdida por el STT/OCR.
    const QList<OcrLine> conf{makeLine({QStringLiteral("Configuración")}, 10, 40)};
    QVERIFY(OcrTextLocator::find(conf, QStringLiteral("Configuracion")).ok());
}

void OcrLocatorTests::find_returnsNothingWhenTextAbsent()
{
    const QList<OcrLine> lines{
        makeLine({QStringLiteral("Guardar")}, 10, 10),
        makeLine({QStringLiteral("Cancelar")}, 10, 40)};
    const auto hit = OcrTextLocator::find(lines, QStringLiteral("Imprimir"));
    QVERIFY(!hit.ok());
    QVERIFY(hit.rect.isEmpty());
    // El cutoff por defecto (85) es más exigente que el de FuzzyMatch (75):
    // un click a ciegas no se arriesga con un parecido flojo.
    QVERIFY(!OcrTextLocator::find(lines, QStringLiteral("Guardando")).ok());
    QVERIFY(OcrTextLocator::find(lines, QStringLiteral("Guardando"), 60).ok());
}

void OcrLocatorTests::find_prefersShortestPhraseOnTie()
{
    // "Guardar" solo y "Guardar como" en la misma línea: pedir "Guardar" tiene que
    // dar la palabra sola (match exacto), no arrastrar la frase larga.
    const QList<OcrLine> lines{
        makeLine({QStringLiteral("Guardar"), QStringLiteral("como")}, 100, 200)};
    const auto hit = OcrTextLocator::find(lines, QStringLiteral("Guardar"));
    QVERIFY(hit.ok());
    QCOMPARE(hit.text, QStringLiteral("Guardar"));
    QCOMPARE(hit.rect, QRect(100, 200, 60, 20));
}

void OcrLocatorTests::find_doesNotSpanAcrossLines()
{
    // "Guardar" al final de una línea y "como" al principio de la siguiente NO son
    // un botón "Guardar como": están en renglones distintos de la pantalla.
    const QList<OcrLine> lines{
        makeLine({QStringLiteral("Archivo"), QStringLiteral("Guardar")}, 10, 10),
        makeLine({QStringLiteral("como"), QStringLiteral("plantilla")}, 10, 40)};
    const auto hit = OcrTextLocator::find(lines, QStringLiteral("Guardar como"));
    // Puede matchear "Guardar" o "como plantilla" flojo, pero nunca una caja que
    // cruce las dos líneas.
    if (hit.ok()) QVERIFY(hit.rect.height() <= 20);
}

void OcrLocatorTests::findAll_reportsAmbiguityWhenTextRepeats()
{
    // Dos "Aceptar" en pantalla (dos diálogos). El locator los devuelve a los dos:
    // es el llamador el que debe negarse a adivinar.
    const QList<OcrLine> lines{
        makeLine({QStringLiteral("Aceptar")}, 100, 100),
        makeLine({QStringLiteral("Aceptar")}, 500, 400)};
    const auto hits = OcrTextLocator::findAll(lines, QStringLiteral("Aceptar"));
    QCOMPARE(hits.size(), 2);
    QCOMPARE(hits.at(0).score, hits.at(1).score);
    // Orden estable ante empate: el de más arriba primero.
    QVERIFY(hits.at(0).rect.y() < hits.at(1).rect.y());

    // Un solo match → sin ambigüedad.
    const QList<OcrLine> one{makeLine({QStringLiteral("Aceptar")}, 100, 100),
                             makeLine({QStringLiteral("Cancelar")}, 500, 400)};
    QCOMPARE(OcrTextLocator::findAll(one, QStringLiteral("Aceptar")).size(), 1);
}

void OcrLocatorTests::find_emptyInputs()
{
    const QList<OcrLine> lines{makeLine({QStringLiteral("Guardar")}, 10, 10)};
    QVERIFY(!OcrTextLocator::find(lines, QString()).ok());
    QVERIFY(!OcrTextLocator::find(lines, QStringLiteral("   ")).ok());
    QVERIFY(!OcrTextLocator::find({}, QStringLiteral("Guardar")).ok());
}

// Las capturas de ventana por GDI/PrintWindow traen alfa 0: como ARGB eran
// "transparentes" y el OCR las veía negras (desktop_read_text de una ventana
// devolvía "no se leyó texto"). opaqueForOcr fija el alfa sin tocar colores.
void OcrLocatorTests::opaqueForOcr_fixesZeroAlphaCaptures()
{
    QImage img(4, 2, QImage::Format_ARGB32);
    img.fill(qRgba(200, 100, 50, 0));
    const QImage out = OcrEngine::opaqueForOcr(img);
    QCOMPARE(qAlpha(out.pixel(1, 1)), 255);
    QCOMPARE(qRed(out.pixel(1, 1)), 200);
    QCOMPARE(qGreen(out.pixel(1, 1)), 100);
    QCOMPARE(qBlue(out.pixel(1, 1)), 50);
    QVERIFY(OcrEngine::opaqueForOcr(QImage()).isNull());
}

// Punta a punta con el motor real (si hay idioma OCR instalado): texto negro
// sobre fondo blanco con alfa 0, como sale de PrintWindow.
void OcrLocatorTests::ocr_readsZeroAlphaWindowCapture()
{
    if (!OcrEngine::available()) QSKIP("sin motor OCR en esta máquina");
    QImage img(640, 160, QImage::Format_ARGB32);
    img.fill(qRgba(255, 255, 255, 0));
    {
        QPainter p(&img);
        p.setCompositionMode(QPainter::CompositionMode_Source);
        QFont f(QStringLiteral("Segoe UI"));
        f.setPixelSize(56);
        p.setFont(f);
        p.setPen(QColor(0, 0, 0, 0));          // alfa 0 también en el texto (GDI)
        p.drawText(img.rect(), Qt::AlignCenter, QStringLiteral("Guardar"));
    }
    QString err;
    const QList<OcrLine> lines = OcrEngine::recognize(img, &err);
    QVERIFY2(!lines.isEmpty(), qPrintable(err));
    QVERIFY(lines.first().text.contains(QStringLiteral("Guardar"), Qt::CaseInsensitive));
}

// Una ventana capturada en blanco (o sin texto) no puede tumbar la app.
void OcrLocatorTests::ocr_blankImageDoesNotCrash()
{
    if (!OcrEngine::available()) QSKIP("sin motor OCR en esta máquina");
    QImage img(640, 160, QImage::Format_ARGB32);
    img.fill(qRgba(255, 255, 255, 0));
    QString err;
    const QList<OcrLine> lines = OcrEngine::recognize(img, &err);
    QVERIFY(lines.isEmpty());
}

QTEST_MAIN(OcrLocatorTests)
#include "test_ocr_locator.moc"
