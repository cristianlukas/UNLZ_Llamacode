#include "OcrEngine.h"

#ifdef Q_OS_WIN

#include <QElapsedTimer>
#include <QMutex>
#include <QThread>

// C++/WinRT viene con el Windows SDK; no agrega dependencias al proyecto.
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Globalization.h>
#include <winrt/Windows.Graphics.Imaging.h>
#include <winrt/Windows.Media.Ocr.h>
#include <winrt/Windows.Security.Cryptography.h>
#include <winrt/Windows.Storage.Streams.h>

#include <exception>
#include <functional>

namespace {

using winrt::Windows::Graphics::Imaging::BitmapPixelFormat;
using winrt::Windows::Graphics::Imaging::SoftwareBitmap;
// Alias: la clase WinRT se llama igual que NUESTRO namespace OcrEngine, así que
// sin renombrar el nombre no resuelve adentro del namespace.
using WinrtOcrEngine = winrt::Windows::Media::Ocr::OcrEngine;

// Corre `fn` en un hilo MTA propio y espera el resultado.
//
// No es ceremonia: el hilo de la GUI de Qt es STA, y bloquear ahí un
// IAsyncOperation.get() de WinRT deadlockea (la continuación necesita bombear el
// mensaje del mismo hilo que está esperando). Un hilo MTA efímero por llamada es
// barato al lado del OCR en sí, y deja `recognize()` con una firma sincrónica
// simple para todos los llamadores.
void runOnMta(const std::function<void()> &fn)
{
    struct Worker : QThread
    {
        const std::function<void()> *fn;
        void run() override
        {
            winrt::init_apartment(winrt::apartment_type::multi_threaded);
            try {
                (*fn)();
            } catch (...) {
                // La excepción ya quedó registrada por `fn` en su propio `error`.
            }
            winrt::uninit_apartment();
        }
    } w;
    w.fn = &fn;
    w.start();
    w.wait();
}

SoftwareBitmap toSoftwareBitmap(const QImage &src)
{
    // Windows.Media.Ocr quiere BGRA8. QImage::Format_ARGB32 tiene ese mismo orden
    // de bytes en little-endian, así que la conversión es un memcpy del buffer.
    const QImage img = src.convertToFormat(QImage::Format_ARGB32);
    const uint8_t *bytes = img.constBits();
    const int len = int(img.sizeInBytes());
    auto buf = winrt::Windows::Security::Cryptography::CryptographicBuffer::CreateFromByteArray(
        winrt::array_view<uint8_t const>(bytes, bytes + len));
    return SoftwareBitmap::CreateCopyFromBuffer(buf, BitmapPixelFormat::Bgra8,
                                                img.width(), img.height());
}

// Motor elegido una sola vez: primero los idiomas del usuario (así "Guardar" se
// lee con el paquete español si lo tiene), con fallback a cualquiera disponible.
WinrtOcrEngine makeEngine()
{
    if (auto e = WinrtOcrEngine::TryCreateFromUserProfileLanguages()) return e;
    for (const auto &lang : WinrtOcrEngine::AvailableRecognizerLanguages())
        if (auto e = WinrtOcrEngine::TryCreateFromLanguage(lang)) return e;
    return nullptr;
}

struct EngineProbe
{
    bool ok = false;
    QString tag;    // BCP-47, ej "es-MX"
    QString name;   // legible para la UI, ej "Español (México)"
};

EngineProbe probe()
{
    EngineProbe p;
    runOnMta([&p] {
        try {
            if (auto e = makeEngine()) {
                p.ok = true;
                const auto lang = e.RecognizerLanguage();
                p.tag = QString::fromStdWString(std::wstring(lang.LanguageTag()));
                p.name = QString::fromStdWString(std::wstring(lang.DisplayName()));
            }
        } catch (...) {
            p.ok = false;
        }
    });
    return p;
}

EngineProbe currentProbe()
{
    static QMutex mutex;
    static EngineProbe cached;
    static bool haveResult = false;
    static QElapsedTimer lastTry;
    QMutexLocker lock(&mutex);

    // Positivo → cachear para siempre: un paquete de idioma no se desinstala solo,
    // y levantar el motor en cada chequeo de la UI sería un desperdicio.
    if (haveResult && cached.ok) return cached;
    // Negativo → re-probar. El usuario PUEDE instalar el paquete con la app
    // abierta (es justo lo que le pide el mensaje de error), y cachear el "no" para
    // siempre lo dejaría en un callejón sin salida: instala el paquete, sigue sin
    // andar, y nada le dice que hay que reiniciar. Throttled porque el path
    // negativo se consulta seguido y cada intento arma un hilo MTA.
    if (haveResult && lastTry.isValid() && lastTry.elapsed() < 5000) return cached;

    cached = probe();
    haveResult = true;
    lastTry.restart();
    return cached;
}

}   // namespace

namespace OcrEngine {

bool available() { return currentProbe().ok; }
QString languageTag() { return currentProbe().tag; }
QString languageName() { return currentProbe().name; }

QList<OcrLine> recognize(const QImage &image, QString *error)
{
    if (error) error->clear();
    QList<OcrLine> out;
    if (image.isNull()) {
        if (error) *error = QStringLiteral("Captura vacía.");
        return out;
    }
    if (!available()) {
        if (error) *error = QStringLiteral(
            "Windows no tiene ningún paquete de idioma OCR instalado "
            "(Configuración → Hora e idioma → Idioma → Opciones → OCR).");
        return out;
    }
    // Windows.Media.Ocr rechaza bitmaps enormes; el tope real del motor es
    // MaxImageDimension. Escalar antes rompería el mapeo de coords, así que
    // preferimos fallar claro a devolver rects mentirosos.
    QString err;
    runOnMta([&] {
        try {
            auto engine = makeEngine();
            if (!engine) {
                err = QStringLiteral("No se pudo crear el motor OCR.");
                return;
            }
            const int maxDim = int(WinrtOcrEngine::MaxImageDimension());
            if (image.width() > maxDim || image.height() > maxDim) {
                err = QStringLiteral("La captura (%1x%2) supera el máximo del motor OCR (%3).")
                          .arg(image.width()).arg(image.height()).arg(maxDim);
                return;
            }
            const auto result = engine.RecognizeAsync(toSoftwareBitmap(image)).get();
            for (const auto &line : result.Lines()) {
                OcrLine ol;
                ol.text = QString::fromStdWString(std::wstring(line.Text()));
                for (const auto &word : line.Words()) {
                    const auto r = word.BoundingRect();
                    OcrWord ow;
                    ow.text = QString::fromStdWString(std::wstring(word.Text()));
                    ow.rect = QRect(qRound(r.X), qRound(r.Y), qRound(r.Width), qRound(r.Height));
                    ol.words.append(ow);
                }
                if (!ol.words.isEmpty()) out.append(ol);
            }
        } catch (const winrt::hresult_error &e) {
            err = QStringLiteral("OCR falló: %1")
                      .arg(QString::fromStdWString(std::wstring(e.message())));
        } catch (const std::exception &e) {
            err = QStringLiteral("OCR falló: %1").arg(QString::fromUtf8(e.what()));
        }
    });
    if (!err.isEmpty()) {
        if (error) *error = err;
        return {};
    }
    return out;
}

}   // namespace OcrEngine

#else   // !Q_OS_WIN

#include <QDir>
#include <QFile>
#include <QProcess>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QTemporaryFile>

namespace OcrEngine {

namespace {

struct Probe {
    bool ok = false;
    QString tag;
    QString name;
};

Probe probe()
{
    Probe p;
    const QString tesseract = QStandardPaths::findExecutable(QStringLiteral("tesseract"));
    if (tesseract.isEmpty()) return p;
    QProcess process;
    process.start(tesseract, {QStringLiteral("--list-langs")});
    if (!process.waitForFinished(2500) || process.exitCode() != 0) return p;
    const QString langs = QString::fromLocal8Bit(process.readAllStandardOutput());
    const QStringList available = langs.split(QRegularExpression(QStringLiteral("[\\r\\n]+")), Qt::SkipEmptyParts);
    if (available.contains(QStringLiteral("spa"))) { p.tag = QStringLiteral("spa"); p.name = QStringLiteral("Español (Tesseract)"); }
    else if (available.contains(QStringLiteral("eng"))) { p.tag = QStringLiteral("eng"); p.name = QStringLiteral("English (Tesseract)"); }
    else if (available.size() > 1) { p.tag = available.at(1).trimmed(); p.name = p.tag; }
    p.ok = !p.tag.isEmpty();
    return p;
}

const Probe &currentProbe()
{
    static const Probe p = probe();
    return p;
}

} // namespace

bool available() { return currentProbe().ok; }
QString languageTag() { return currentProbe().tag; }
QString languageName() { return currentProbe().name; }

QList<OcrLine> recognize(const QImage &image, QString *error)
{
    if (error) error->clear();
    if (image.isNull()) { if (error) *error = QStringLiteral("Captura vacía."); return {}; }
    if (!available()) {
        if (error) *error = QStringLiteral("OCR Linux requiere tesseract-ocr y un idioma instalado (spa o eng).");
        return {};
    }
    QTemporaryFile input(QDir::tempPath() + QStringLiteral("/llamacode-ocr-XXXXXX.png"));
    input.setAutoRemove(true);
    if (!input.open() || !image.save(input.fileName(), "PNG")) {
        if (error) *error = QStringLiteral("No se pudo preparar la captura para OCR.");
        return {};
    }
    input.close();
    QProcess process;
    process.start(QStandardPaths::findExecutable(QStringLiteral("tesseract")),
                  {input.fileName(), QStringLiteral("stdout"), QStringLiteral("--psm"),
                   QStringLiteral("6"), QStringLiteral("-l"), currentProbe().tag,
                   QStringLiteral("tsv")});
    if (!process.waitForFinished(15000) || process.exitCode() != 0) {
        if (error) *error = QString::fromLocal8Bit(process.readAllStandardError()).trimmed();
        if (error && error->isEmpty()) *error = QStringLiteral("Tesseract no pudo reconocer la captura.");
        return {};
    }

    QList<OcrLine> out;
    QHash<QString, int> lineIndexes;
    const QString tsv = QString::fromLocal8Bit(process.readAllStandardOutput());
    for (const QString &raw : tsv.split(QLatin1Char('\n'))) {
        if (raw.startsWith(QStringLiteral("level\t"))) continue;
        const QStringList fields = raw.split(QLatin1Char('\t'));
        if (fields.size() < 12 || fields.at(0) != QLatin1String("5")) continue;
        bool ok = false;
        const int left = fields.at(6).toInt(&ok); if (!ok) continue;
        const int top = fields.at(7).toInt(&ok); if (!ok) continue;
        const int width = fields.at(8).toInt(&ok); if (!ok) continue;
        const int height = fields.at(9).toInt(&ok); if (!ok) continue;
        const QString word = fields.mid(11).join(QLatin1Char('\t')).trimmed();
        if (word.isEmpty() || width <= 0 || height <= 0) continue;
        const QString key = fields.mid(1, 4).join(QLatin1Char('/'));
        int index = lineIndexes.value(key, -1);
        if (index < 0) {
            index = out.size();
            lineIndexes.insert(key, index);
            out.append(OcrLine{});
        }
        out[index].words.append({word, QRect(left, top, width, height)});
        if (!out[index].text.isEmpty()) out[index].text += QLatin1Char(' ');
        out[index].text += word;
    }
    return out;
}
}   // namespace OcrEngine

#endif
