#include "CronSchedule.h"
#include <QRegularExpression>

bool CronSchedule::parseField(const QString &field, int lo, int hi, QSet<int> *out, bool dowField)
{
    out->clear();
    const QStringList parts = field.split(QLatin1Char(','), Qt::SkipEmptyParts);
    if (parts.isEmpty()) return false;

    for (QString part : parts) {
        part = part.trimmed();
        int step = 1;
        const int slash = part.indexOf(QLatin1Char('/'));
        if (slash >= 0) {
            bool ok = false;
            step = part.mid(slash + 1).toInt(&ok);
            if (!ok || step <= 0) return false;
            part = part.left(slash);
        }

        int rlo = lo, rhi = hi;
        if (part == QLatin1String("*")) {
            // rango completo
        } else if (part.contains(QLatin1Char('-'))) {
            const QStringList r = part.split(QLatin1Char('-'));
            if (r.size() != 2) return false;
            bool a = false, b = false;
            rlo = r[0].toInt(&a);
            rhi = r[1].toInt(&b);
            if (!a || !b) return false;
        } else {
            bool ok = false;
            rlo = rhi = part.toInt(&ok);
            if (!ok) return false;
        }

        for (int v = rlo; v <= rhi; v += step) {
            int nv = v;
            if (dowField && nv == 7) nv = 0;   // domingo = 0 o 7
            if (nv < lo || nv > hi) return false;
            out->insert(nv);
        }
    }
    return !out->isEmpty();
}

CronSchedule CronSchedule::parse(const QString &expr, QString *error)
{
    CronSchedule c;
    const QStringList f = expr.trimmed().split(QRegularExpression(QStringLiteral("\\s+")),
                                               Qt::SkipEmptyParts);
    if (f.size() != 5) {
        if (error) *error = QStringLiteral("Cron debe tener 5 campos: min hora díaMes mes díaSem");
        return c;
    }
    if (!parseField(f[0], 0, 59, &c.m_min)
        || !parseField(f[1], 0, 23, &c.m_hour)
        || !parseField(f[2], 1, 31, &c.m_dom)
        || !parseField(f[3], 1, 12, &c.m_month)
        || !parseField(f[4], 0, 6, &c.m_dow, /*dowField=*/true)) {
        if (error) *error = QStringLiteral("Campo cron inválido");
        return c;
    }
    c.m_domRestricted = f[2].trimmed() != QLatin1String("*");
    c.m_dowRestricted = f[4].trimmed() != QLatin1String("*");
    c.m_valid = true;
    return c;
}

bool CronSchedule::matches(const QDateTime &dt) const
{
    if (!m_valid || !dt.isValid()) return false;
    const QDate d = dt.date();
    const QTime t = dt.time();

    if (!m_min.contains(t.minute())) return false;
    if (!m_hour.contains(t.hour())) return false;
    if (!m_month.contains(d.month())) return false;

    const bool domOk = m_dom.contains(d.day());
    const int dow = d.dayOfWeek() % 7;   // Qt: 1=Lun..7=Dom → 0=Dom..6=Sáb
    const bool dowOk = m_dow.contains(dow);

    if (m_domRestricted && m_dowRestricted)
        return domOk || dowOk;          // cron estándar: OR si ambos restringidos
    return domOk && dowOk;
}
