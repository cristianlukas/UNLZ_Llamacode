#pragma once
#include <QString>
#include <QDateTime>
#include <QSet>
#include <QVector>

// CronSchedule — parser PURO de expresiones cron de 5 campos:
//   minuto hora díaDelMes mes díaDeSemana
// Soporta: '*', listas (a,b,c), rangos (a-b), pasos (*/n y a-b/n). Día de semana
// 0-7 (0 y 7 = domingo). Convención cron estándar: si díaDelMes Y díaDeSemana
// están ambos restringidos (no '*'), matchea si CUALQUIERA coincide.
//
// Sin disco ni reloj propio: matches(dt) decide contra un QDateTime dado →
// unit-testeable de forma determinista.
class CronSchedule
{
public:
    CronSchedule() = default;

    // Parsea una expresión. Si falla, isValid()==false (y opcional error).
    static CronSchedule parse(const QString &expr, QString *error = nullptr);

    bool isValid() const { return m_valid; }
    // ¿La expresión dispara en ese instante (resolución de minuto)?
    bool matches(const QDateTime &dt) const;

private:
    bool m_valid = false;
    bool m_domRestricted = false;
    bool m_dowRestricted = false;
    QSet<int> m_min, m_hour, m_dom, m_month, m_dow;

    // Parsea un campo a su set de valores válidos en [lo,hi]. dowField normaliza 7→0.
    static bool parseField(const QString &field, int lo, int hi, QSet<int> *out, bool dowField = false);
};
