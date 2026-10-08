#include "VisionImagePayload.h"

#include <QBuffer>
#include <QFile>
#include <QFileInfo>
#include <QImage>
#include <QImageReader>
#include <QtMath>

namespace {

constexpr int kRegularMaxEdge = 1536;
constexpr int kUltraWideMaxEdge = 768;
constexpr double kUltraWideAspectRatio = 2.4;

QString mimeForExtension(const QString &extension)
{
    const QString ext = extension.toLower();
    if (ext == QLatin1String("png")) return QStringLiteral("image/png");
    if (ext == QLatin1String("jpg") || ext == QLatin1String("jpeg"))
        return QStringLiteral("image/jpeg");
    if (ext == QLatin1String("webp")) return QStringLiteral("image/webp");
    if (ext == QLatin1String("gif")) return QStringLiteral("image/gif");
    if (ext == QLatin1String("bmp")) return QStringLiteral("image/bmp");
    if (ext == QLatin1String("tif") || ext == QLatin1String("tiff"))
        return QStringLiteral("image/tiff");
    return {};
}

QString encode(const QString &mime, const QByteArray &bytes)
{
    if (mime.isEmpty() || bytes.isEmpty()) return {};
    return QStringLiteral("data:%1;base64,%2")
        .arg(mime, QString::fromLatin1(bytes.toBase64()));
}

} // namespace

QString VisionImagePayload::dataUri(const QString &path)
{
    const QString mime = mimeForExtension(QFileInfo(path).suffix());
    if (mime.isEmpty()) return {};

    QFile source(path);
    if (!source.open(QIODevice::ReadOnly)) return {};
    const QByteArray original = source.readAll();
    if (original.isEmpty()) return {};

    // Keep already-small images byte-for-byte compatible with the previous
    // path. This avoids needless recompression and preserves animated formats.
    QImageReader probe(path);
    const QSize sourceSize = probe.size();
    if (!sourceSize.isValid()) return encode(mime, original);

    const int longEdge = qMax(sourceSize.width(), sourceSize.height());
    const int shortEdge = qMax(1, qMin(sourceSize.width(), sourceSize.height()));
    const double aspect = static_cast<double>(longEdge) / shortEdge;
    const int maxEdge = aspect >= kUltraWideAspectRatio
        ? kUltraWideMaxEdge : kRegularMaxEdge;
    if (longEdge <= maxEdge) return encode(mime, original);

    QImage image;
    if (!image.loadFromData(original)) return encode(mime, original);

    // Compute the dimensions explicitly instead of letting QSize::scaled()
    // round twice. That keeps the configured long-edge limit deterministic
    // for ultra-wide screenshots (for example 2271x751 -> 768x254).
    const QSize targetSize = image.width() >= image.height()
        ? QSize(maxEdge,
                qMax(1, qRound(static_cast<double>(image.height()) * maxEdge
                               / image.width())))
        : QSize(qMax(1, qRound(static_cast<double>(image.width()) * maxEdge
                               / image.height())),
                maxEdge);
    const QImage resized = image.scaled(targetSize, Qt::IgnoreAspectRatio,
                                        Qt::SmoothTransformation);
    if (resized.isNull()) return encode(mime, original);

    // PNG keeps text in screenshots sharp. The normalized representation is
    // sent only on the wire; the original attachment remains untouched.
    QByteArray normalized;
    QBuffer buffer(&normalized);
    if (!buffer.open(QIODevice::WriteOnly) || !resized.save(&buffer, "PNG"))
        return encode(mime, original);
    return encode(QStringLiteral("image/png"), normalized);
}
