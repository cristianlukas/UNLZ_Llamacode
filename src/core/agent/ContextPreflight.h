#pragma once
#include <QString>

namespace ContextPreflight {
QString build(const QString &root, const QString &request, int maxFiles = 12,
              int tokenBudget = 720, bool expandGraph = true);
}
