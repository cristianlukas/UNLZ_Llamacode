#include "ModelLoadProgress.h"

#include <QStringList>

namespace {
// Tramos del porcentaje total: arranque 0-5, pesos 5-90, contexto/warmup 90-99.
constexpr int kLoadStart = 5;
constexpr int kLoadSpan = 85;
constexpr int kEstimateCap = 89;   // sin confirmacion del log no pasa de aca
constexpr int kWarmup = 95;

int stateRank(const QString &state)
{
    if (state == QLatin1String("starting")) return 1;
    if (state == QLatin1String("loading")) return 2;
    if (state == QLatin1String("warmup")) return 3;
    if (state == QLatin1String("ready")) return 4;
    return 0;
}
} // namespace

void ModelLoadProgress::reset(qint64 nowMs, qint64 expectedMs)
{
    m_state = QStringLiteral("starting");
    m_detail.clear();
    m_startMs = nowMs;
    m_expectedMs = qMax<qint64>(0, expectedMs);
    m_dots = 0;
}

bool ModelLoadProgress::active() const
{
    return m_state == QLatin1String("starting") || m_state == QLatin1String("loading")
        || m_state == QLatin1String("warmup");
}

void ModelLoadProgress::advance(const QString &state)
{
    // Nunca retroceder: el loader vuelve a loguear al cargar draft/mmproj.
    if (stateRank(state) > stateRank(m_state))
        m_state = state;
}

void ModelLoadProgress::feed(const QString &chunk)
{
    if (!active())
        return;
    const QStringList pieces = chunk.split(QLatin1Char('\n'));
    for (const QString &raw : pieces) {
        const QString piece = raw.trimmed();
        if (piece.isEmpty())
            continue;
        bool onlyDots = true;
        for (const QChar c : piece) {
            if (c != QLatin1Char('.')) { onlyDots = false; break; }
        }
        if (onlyDots) {
            if (m_state == QLatin1String("loading"))
                m_dots = qMin(100, m_dots + int(piece.size()));
            continue;
        }
        if (piece.contains(QLatin1String("loading model"))
            || piece.contains(QLatin1String("llama_model_loader:"))
            || piece.contains(QLatin1String("load_tensors:"))) {
            advance(QStringLiteral("loading"));
        } else if (piece.contains(QLatin1String("llama_context:"))
                   || piece.contains(QLatin1String("warming up"))
                   || piece.contains(QLatin1String("initializing slots"))) {
            advance(QStringLiteral("warmup"));
        }
    }
}

qint64 ModelLoadProgress::markReady(qint64 nowMs)
{
    const qint64 took = (active() && m_startMs > 0) ? qMax<qint64>(0, nowMs - m_startMs) : 0;
    m_state = QStringLiteral("ready");
    m_detail.clear();
    return took;
}

void ModelLoadProgress::markFailed(const QString &detail)
{
    m_state = QStringLiteral("failed");
    m_detail = detail;
}

void ModelLoadProgress::markIdle()
{
    m_state = QStringLiteral("idle");
    m_detail.clear();
    m_dots = 0;
    m_startMs = 0;
}

int ModelLoadProgress::progress(qint64 nowMs) const
{
    if (m_state == QLatin1String("ready")) return 100;
    if (!active()) return -1;
    if (m_state == QLatin1String("warmup")) return kWarmup;
    if (m_dots > 0)
        return kLoadStart + (m_dots * kLoadSpan) / 100;
    if (m_expectedMs <= 0) return m_state == QLatin1String("loading") ? kLoadStart : 0;
    const qint64 elapsed = qMax<qint64>(0, nowMs - m_startMs);
    const int byTime = int(qMin<qint64>(100, (elapsed * 100) / m_expectedMs));
    return qMin(kEstimateCap, (byTime * 90) / 100);
}

QJsonObject ModelLoadProgress::toJson(qint64 nowMs) const
{
    QJsonObject o{{QStringLiteral("state"), m_state},
                  {QStringLiteral("progress"), progress(nowMs)},
                  {QStringLiteral("estimated"), active() && estimated()}};
    if (!m_detail.isEmpty())
        o.insert(QStringLiteral("detail"), m_detail);
    return o;
}

qint64 ModelLoadProgress::expectedMsForFileSize(qint64 bytes)
{
    // ~1 GB/s efectivo (disco + subida a VRAM) mas el arranque del proceso.
    constexpr qint64 kBaseMs = 3000;
    if (bytes <= 0) return 0;
    return kBaseMs + bytes / (1024 * 1024);   // 1 ms por MiB
}

QString ModelLoadProgress::label(const QString &state, int progress, bool remote)
{
    const QString where = remote ? QStringLiteral(" remoto") : QString();
    const QString pct = progress >= 0 ? QStringLiteral(" %1%").arg(progress) : QString();
    if (state == QLatin1String("connecting"))
        return QStringLiteral("Conectando con el servidor LAN...");
    if (state == QLatin1String("starting"))
        return QStringLiteral("Iniciando servidor%1").arg(where) + pct;
    if (state == QLatin1String("loading"))
        return QStringLiteral("Cargando modelo%1").arg(where) + pct;
    if (state == QLatin1String("warmup"))
        return QStringLiteral("Preparando contexto%1").arg(where) + pct;
    if (state == QLatin1String("ready"))
        return QStringLiteral("Modelo%1 listo").arg(where);
    if (state == QLatin1String("failed"))
        return QStringLiteral("Falló la carga del modelo%1").arg(where);
    return QString();
}
