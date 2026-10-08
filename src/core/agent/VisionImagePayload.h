#pragma once

#include <QString>

namespace VisionImagePayload {

// Encodes an image for an OpenAI-compatible multimodal request. Very wide
// captures use a smaller wire representation because some vision backends are
// unstable when they receive an ultra-wide screenshot at its native size.
// The source file is never modified.
QString dataUri(const QString &path);

} // namespace VisionImagePayload
