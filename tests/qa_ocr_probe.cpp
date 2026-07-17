// Harness de QA manual del OCR. NO es un test de ctest: necesita una sesión de
// escritorio viva, una app abierta y el paquete de idioma OCR de Windows.
//
// Verifica lo que ningún unit test puede: que los rects que devuelve
// DesktopAutomationBackend::readText() caigan REALMENTE sobre el texto en
// pantalla. Y lo hace sin depender de que un humano mire: cruza el OCR contra UI
// Automation. Si el OCR ubica "Archivo" en (x,y) y controlAtPoint(x,y) también
// dice "Archivo", dos fuentes independientes coinciden → el punto cae donde debe.
//
// Corré esto con un monitor ESCALADO (125/150%) y una app con menús abierta ahí:
// es el único caso donde un error de espacio de coordenadas se manifiesta (a 100%
// lógico y físico coinciden y taparían el bug). Así se encontró y se verificó el
// fix de coords físicas: el acuerdo en el monitor al 150% pasó de 10% a 80%.
//
// Uso:  qa_ocr_probe.exe [texto-a-buscar]
// Sale 0 si todas las pantallas acuerdan >=70%, 1 si alguna no, 2 sin muestra.

#include "core/automation/DesktopAutomationBackend.h"
#include "core/automation/OcrEngine.h"
#include "core/automation/OcrTextLocator.h"
#include "core/automation/FuzzyMatch.h"

#include <QGuiApplication>
#include <QScreen>
#include <QTextStream>


static QTextStream out(stdout);

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    const QString needle = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QString();

    out << "== Motor OCR ==\n";
    out << "  available : " << (OcrEngine::available() ? "SI" : "NO") << "\n";
    out << "  idioma    : " << OcrEngine::languageName()
        << " (" << OcrEngine::languageTag() << ")\n";
    if (!OcrEngine::available()) {
        out << "  -> sin paquete de idioma OCR; no hay nada que probar.\n";
        return 2;
    }

    out << "\n== Pantallas ==\n";
    const QVariantList screens = DesktopAutomationBackend::screens();
    for (const QVariant &v : screens) {
        const QVariantMap s = v.toMap();
        // El devicePixelRatio es el corazon del bug clasico: si es != 1, las coords
        // del bitmap y las de pantalla NO coinciden y hay que convertir.
        QScreen *qs = QGuiApplication::screens().value(s.value("id").toInt());
        out << "  id=" << s.value("id").toString()
            << "  " << s.value("width").toInt() << "x" << s.value("height").toInt()
            << " @(" << s.value("x").toInt() << "," << s.value("y").toInt() << ")"
            << "  dpr=" << (qs ? qs->devicePixelRatio() : 0.0)
            << (s.value("primary").toBool() ? "  [primaria]" : "") << "\n";
    }
    if (screens.isEmpty()) { out << "  (ninguna)\n"; return 2; }

    // Recorrer TODAS las pantallas, no sólo la primera: el escalado suele diferir
    // entre monitores y es justo el caso que hay que ejercitar. Un monitor a 150%
    // (dpr=1.5) es el único lugar donde un error en la conversión se manifiesta;
    // a 100% la cuenta es identidad y taparía el bug.
    int worstPct = 101;
    for (const QVariant &sv : screens) {
        const QVariantMap sm = sv.toMap();
        const QString target = sm.value("id").toString();
        QScreen *qs = QGuiApplication::screens().value(target.toInt());
        const double dpr = qs ? qs->devicePixelRatio() : 1.0;

        out << "\n== Pantalla " << target << "  (dpr=" << dpr << ", escala "
            << qRound(dpr * 100) << "%) ==\n";
        // Números crudos de la conversión: sin esto, un desvío de coordenadas es
        // adivinanza. Con todo en físico, sx debe dar 1 en TODA pantalla (bounds y
        // captura miden lo mismo); un sx != 1 delata que algo volvió a mezclar
        // espacios.
        {
            QString cerr;
            const QImage probe = DesktopAutomationBackend::capture("screen", target, &cerr);
            const QRect b(sm.value("x").toInt(), sm.value("y").toInt(),
                          sm.value("width").toInt(), sm.value("height").toInt());
            out << "  bounds(fisico)    = (" << b.x() << "," << b.y() << " "
                << b.width() << "x" << b.height() << ")\n";
            out << "  captura(px)       = " << probe.width() << "x" << probe.height()
                << "   dpr(img)=" << probe.devicePixelRatio() << "\n";
            if (!probe.isNull() && probe.width() > 0)
                out << "  sx = bounds.w/img.w = " << (double(b.width()) / probe.width())
                    << "  (debe ser 1)\n";
        }
        QString err;
        const QList<OcrLine> lines = DesktopAutomationBackend::readText("screen", target, &err);
        if (lines.isEmpty()) {
            out << "  sin texto legible" << (err.isEmpty() ? QString() : " (" + err + ")") << "\n";
            continue;
        }
        out << "  lineas leidas: " << lines.size() << "\n";
        for (int i = 0; i < qMin(6, lines.size()); ++i)
            out << "    [" << i << "] \"" << lines.at(i).text << "\"\n";
        if (lines.size() > 6) out << "    ... (" << lines.size() - 6 << " mas)\n";

        // Cruce OCR x UIA: la prueba de fuego de las coordenadas, sin ojo humano.
        // Si readText() ubica "Archivo" en (x,y) y UIA::ElementFromPoint(x,y)
        // también dice "Archivo", dos fuentes independientes coinciden → el punto
        // cae donde debe. Si el espacio de coords estuviera mal, el punto caeria al
        // costado y UIA reportaria otro control: es exactamente lo que pasaba
        // (10% de acuerdo en el monitor al 150%) antes de pasar todo a FISICO.
        int checked = 0, agree = 0, uiaBlind = 0;
        for (const OcrLine &line : lines) {
            for (const OcrWord &w : line.words) {
                if (w.text.size() < 3) continue;      // palabras muy cortas: ruido
                if (checked >= 40) break;
                const QPoint c = w.rect.center();
                const QString name = DesktopAutomationBackend::controlAtPoint(c)
                                         .value("name").toString();
                ++checked;
                if (name.isEmpty()) { ++uiaBlind; continue; }   // UIA ciego ahi
                const int score = FuzzyMatch::partialRatio(w.text, name);
                if (score >= 80) ++agree;
                else if (checked <= 3)
                    out << "    DISCREPA: OCR \"" << w.text << "\" en (" << c.x() << ","
                        << c.y() << ") -> UIA dice \"" << name.left(40) << "\" ["
                        << score << "]\n";
            }
        }
        const int comparable = checked - uiaBlind;
        out << "  comparables: " << comparable << " (probadas " << checked
            << ", UIA ciego " << uiaBlind << ")\n";
        if (comparable >= 3) {
            const int pct = agree * 100 / comparable;
            worstPct = qMin(worstPct, pct);
            out << "  -> acuerdo OCR/UIA: " << pct << "%  "
                << (pct >= 70 ? "OK" : "SOSPECHOSO: revisar targetBounds()/readText()")
                << (dpr != 1.0 ? "   <-- pantalla escalada: ESTA valida el DPI" : "") << "\n";
        } else {
            out << "  -> muestra insuficiente (abri una app con menus en esta pantalla)\n";
        }

        if (!needle.isEmpty()) {
            const QList<OcrTextLocator::Hit> hits = OcrTextLocator::findAll(lines, needle);
            out << "  buscar \"" << needle << "\": " << hits.size() << " hit(s)\n";
            for (const auto &h : hits) {
                const QVariantMap ctl = DesktopAutomationBackend::controlAtPoint(h.center());
                out << "    score=" << h.score << " \"" << h.text << "\" centro=("
                    << h.center().x() << "," << h.center().y() << ")  UIA ahi: \""
                    << ctl.value("name").toString() << "\" ["
                    << ctl.value("role").toString() << "]\n";
            }
        }
    }

    out << "\n== Veredicto ==\n";
    if (worstPct > 100) out << "  sin muestra suficiente en ninguna pantalla.\n";
    else out << "  peor acuerdo OCR/UIA: " << worstPct << "% -> "
             << (worstPct >= 70 ? "coordenadas correctas en todas las pantallas"
                                : "HAY UN PROBLEMA de coordenadas")
             << "\n";
    out.flush();
    return worstPct > 100 ? 2 : (worstPct >= 70 ? 0 : 1);
}
