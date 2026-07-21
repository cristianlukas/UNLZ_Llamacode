#include "VisualMatcher.h"

#include <QtMath>
#include <algorithm>
#include <limits>

namespace {
struct Candidate { QRect rect; double score = 0.0; double scale = 1.0; };

double sampledSimilarity(const QImage &haystack, const QImage &needle, int left, int top)
{
    // Hasta 12x12 muestras uniformes: costo predecible incluso con templates grandes.
    const int sx = qMax(1, needle.width() / 12);
    const int sy = qMax(1, needle.height() / 12);
    qint64 difference = 0;
    int count = 0;
    for (int y = sy / 2; y < needle.height(); y += sy) {
        const uchar *n = needle.constScanLine(y);
        const uchar *h = haystack.constScanLine(top + y) + left;
        for (int x = sx / 2; x < needle.width(); x += sx) {
            difference += qAbs(int(h[x]) - int(n[x]));
            ++count;
        }
    }
    return count > 0 ? 1.0 - double(difference) / (255.0 * count) : 0.0;
}

bool overlapsSameObject(const QRect &a, const QRect &b)
{
    const QRect overlap = a.intersected(b);
    const int smaller = qMin(a.width() * a.height(), b.width() * b.height());
    return smaller > 0 && overlap.width() * overlap.height() > smaller / 3;
}
}

QVariantMap VisualMatcher::Result::toVariantMap(const QSize &size) const
{
    QVariantMap out{{QStringLiteral("found"), found},
                    {QStringLiteral("ambiguous"), ambiguous},
                    {QStringLiteral("confidence"), confidence},
                    {QStringLiteral("secondConfidence"), secondConfidence},
                    {QStringLiteral("scale"), scale}};
    if (!error.isEmpty()) out[QStringLiteral("error")] = error;
    if (found && size.width() > 0 && size.height() > 0) {
        out[QStringLiteral("rect")] = QVariantMap{
            {QStringLiteral("x"), double(rect.x()) / size.width()},
            {QStringLiteral("y"), double(rect.y()) / size.height()},
            {QStringLiteral("width"), double(rect.width()) / size.width()},
            {QStringLiteral("height"), double(rect.height()) / size.height()}};
    }
    return out;
}

VisualMatcher::Result VisualMatcher::find(const QImage &haystackSource,
                                          const QImage &needleSource,
                                          const Options &rawOptions)
{
    Result result;
    if (haystackSource.isNull() || needleSource.isNull()) {
        result.error = QStringLiteral("La captura o la plantilla visual es inválida.");
        return result;
    }
    if (needleSource.width() < 3 || needleSource.height() < 3) {
        result.error = QStringLiteral("La plantilla visual debe medir al menos 3x3 píxeles.");
        return result;
    }

    const double threshold = qBound(0.5, rawOptions.threshold, 1.0);
    const double minScale = qBound(0.5, qMin(rawOptions.minScale, rawOptions.maxScale), 2.0);
    const double maxScale = qBound(minScale, qMax(rawOptions.minScale, rawOptions.maxScale), 2.0);
    const QImage haystack = haystackSource.convertToFormat(QImage::Format_Grayscale8);
    const QImage original = needleSource.convertToFormat(QImage::Format_Grayscale8);

    QList<double> scales{minScale};
    if (maxScale - minScale > 0.01) {
        for (double s = minScale + 0.10; s < maxScale - 0.01; s += 0.10) scales << s;
        scales << maxScale;
    }
    if (minScale < 1.0 && maxScale > 1.0) scales << 1.0;
    std::sort(scales.begin(), scales.end());
    scales.erase(std::unique(scales.begin(), scales.end(),
                             [](double a, double b) { return qAbs(a - b) < 0.01; }), scales.end());

    Candidate best;
    Candidate second;
    bool anyFits = false;
    for (double scale : scales) {
        const QSize scaledSize(qMax(3, qRound(original.width() * scale)),
                               qMax(3, qRound(original.height() * scale)));
        if (scaledSize.width() > haystack.width() || scaledSize.height() > haystack.height())
            continue;
        anyFits = true;
        const QImage needle = scale == 1.0
            ? original
            : original.scaled(scaledSize, Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
        const qint64 positions = qint64(haystack.width() - needle.width() + 1)
                               * qint64(haystack.height() - needle.height() + 1);
        const int stride = qMax(1, int(qCeil(qSqrt(double(positions) / 750000.0))));
        for (int y = 0; y <= haystack.height() - needle.height(); y += stride) {
            for (int x = 0; x <= haystack.width() - needle.width(); x += stride) {
                const Candidate candidate{QRect(x, y, needle.width(), needle.height()),
                                          sampledSimilarity(haystack, needle, x, y), scale};
                if (candidate.score > best.score) {
                    if (!overlapsSameObject(candidate.rect, best.rect)) second = best;
                    best = candidate;
                } else if (!overlapsSameObject(candidate.rect, best.rect)
                           && candidate.score > second.score) {
                    second = candidate;
                }
            }
        }
    }
    if (!anyFits) {
        result.error = QStringLiteral("La plantilla es más grande que el alcance capturado.");
        return result;
    }

    result.confidence = best.score;
    result.secondConfidence = second.score;
    result.scale = best.scale;
    result.rect = best.rect;
    result.found = best.score >= threshold;
    // Una alternativa casi igual vuelve inseguro el objetivo. El margen absoluto
    // evita que dos íconos repetidos terminen en un click elegido al azar.
    result.ambiguous = result.found && rawOptions.requireUnique
        && second.score >= threshold && best.score - second.score < 0.025;
    if (result.ambiguous)
        result.error = QStringLiteral("Hay más de una coincidencia visual igualmente probable.");
    else if (!result.found)
        result.error = QStringLiteral("No se encontró la plantilla con la confianza requerida.");
    return result;
}
