#pragma once

#include <QFileInfo>
#include <QRegularExpression>
#include <QString>

namespace MtpDetection {

// Heurística conservadora para GGUFs que transportan el cabezal MTP junto al
// modelo principal: el publisher debe marcar MTP como token del filename.
inline bool isSelfContained(const QString &fileName)
{
    const QString base = QFileInfo(fileName).completeBaseName();
    static const QRegularExpression marker(
        QStringLiteral(R"((^|[-_.])mtp($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    return marker.match(base).hasMatch();
}

} // namespace MtpDetection
