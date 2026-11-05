#pragma once
#include <QString>

// Texto del agente → texto que un TTS puede leer en voz alta.
//
// El prompt de modo voz pide "nada de markdown ni URLs", pero el modelo igual
// devuelve "**negrita**", URLs que copió de web_search, "24 °C", "12 × 37",
// "$1.245,50" o "05/11/2026". Medido con Piper es_ES + Parakeet (20 respuestas
// típicas, docs/charla-tts-normalizacion-20261105.md): Piper decía "asterisco
// asterisco", "barra", deletreaba las URLs, leía "$" como "dólar" y se comía el
// "×". Acá se convierte todo eso a palabras ANTES del motor, así vale igual
// para Piper, Qwen3-TTS, Pocket o un endpoint HTTP.
//
// Puro y sin estado. Se aplica por oración, justo antes de sintetizar.
namespace SpeechTextNormalizer {

// lang: "es" (default) expande números, fechas, horas, monedas y unidades a
// palabras en español; cualquier otro idioma sólo limpia markdown/URLs/símbolos.
QString normalize(const QString &text, const QString &lang = QStringLiteral("es"));

// Entero no negativo en palabras (es). feminine: "una", "doscientas";
// apocope: "un"/"veintiún" delante de un sustantivo ("un archivo").
// Fuera de rango (>= 10^12) devuelve los dígitos uno por uno.
QString numberToWordsEs(qint64 n, bool feminine = false, bool apocope = false);

} // namespace SpeechTextNormalizer
