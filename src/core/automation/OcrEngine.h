#pragma once

#include "OcrTypes.h"

#include <QImage>
#include <QList>
#include <QString>

// OCR local vía Windows.Media.Ocr (WinRT) en Windows o Tesseract en Linux.
//
// En Windows no agrega dependencias: usa el motor y los idiomas del sistema. En
// Linux Tesseract es una dependencia pequeña del sistema y también corre en CPU;
// sólo se usa para labels de UI, no como OCR fotográfico.
//
// Es un ÚLTIMO RECURSO dentro de la automatización: UIA (desktop_controls) ve el
// árbol real de controles y siempre es preferible. Esto es para donde UIA es
// ciego.
namespace OcrEngine {

// ¿Hay un motor OCR utilizable? Depende de que Windows tenga un idioma instalado
// o de que Linux tenga tesseract-ocr y spa/eng. Barato: cachea el resultado.
bool available();

// Idioma que se va a usar (BCP-47, ej "es-MX"), o "" si no hay motor. Para
// diagnosticar "¿por qué no lee mis botones en español?".
QString languageTag();

// Nombre legible del idioma del motor (ej "Español (México)"), o "" si no hay.
// Es lo que se muestra en la UI: "es-MX" no le dice nada a nadie.
QString languageName();

// Reconoce el texto de `image`. Los rects vuelven en PÍXELES DE LA IMAGEN — el
// llamador los traduce a pantalla (ver DesktopAutomationBackend::readText).
// Devuelve {} y setea `error` si no hay motor o falla el reconocimiento.
//
// Bloquea hasta terminar (decenas de ms para una pantalla): la API de WinRT es
// async y se la espera en un hilo MTA propio, porque bloquear la espera en el
// hilo STA de la GUI deadlockea.
QList<OcrLine> recognize(const QImage &image, QString *error = nullptr);

}   // namespace OcrEngine
