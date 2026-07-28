#pragma once

#include <QFileInfo>
#include <QRegularExpression>
#include <QString>

namespace MtpDetection {

// Heurística conservadora para GGUFs que transportan el cabezal MTP junto al
// modelo principal. La mayoría de publishers marca MTP como token del filename.
// BottleCapAI publica ThinkingCap con el cabezal integrado pero conserva nombres
// de quant estándar (p. ej. ThinkingCap-Qwen3.6-27B-Q4_K_M.gguf).
inline bool isSelfContained(const QString &fileName)
{
    const QString base = QFileInfo(fileName).completeBaseName();
    static const QRegularExpression marker(
        QStringLiteral(R"((^|[-_.])mtp($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression thinkingCapQwen36(
        QStringLiteral(R"((^|[-_.])thinkingcap[-_.]qwen3[._-]?6($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    return marker.match(base).hasMatch()
        || thinkingCapQwen36.match(base).hasMatch();
}

} // namespace MtpDetection
