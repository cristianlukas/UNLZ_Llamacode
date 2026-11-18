#include "SpeechTextNormalizer.h"
#include <QRegularExpression>
#include <QSet>
#include <QStringList>
#include <functional>

namespace SpeechTextNormalizer {
namespace {

using Fn = std::function<QString(const QRegularExpressionMatch &)>;

QString replaceEach(const QString &text, const QRegularExpression &re, const Fn &fn)
{
    QString out;
    qsizetype last = 0;
    auto it = re.globalMatch(text);
    while (it.hasNext()) {
        const QRegularExpressionMatch m = it.next();
        out += text.mid(last, m.capturedStart() - last);
        out += fn(m);
        last = m.capturedEnd();
    }
    out += text.mid(last);
    return out;
}

QRegularExpression rx(const char *pattern,
                      QRegularExpression::PatternOptions o = QRegularExpression::NoPatternOption)
{
    return QRegularExpression(QString::fromUtf8(pattern), o | QRegularExpression::UseUnicodePropertiesOption);
}

// "smn.gob.ar" → "smn punto gob punto ar".
QString spellDots(const QString &s, bool es)
{
    QStringList parts = s.split(QLatin1Char('.'), Qt::SkipEmptyParts);
    return parts.join(es ? QStringLiteral(" punto ") : QStringLiteral(" dot "));
}

// ── Números en español ─────────────────────────────────────────────────────
const char *const kUnder30[] = {
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve"};
const char *const kTens[] = {"", "", "", "treinta", "cuarenta", "cincuenta",
                             "sesenta", "setenta", "ochenta", "noventa"};
const char *const kHundreds[] = {"", "ciento", "doscientos", "trescientos", "cuatrocientos",
                                 "quinientos", "seiscientos", "setecientos", "ochocientos",
                                 "novecientos"};

// "uno" final según contexto: "una" (femenino), "un" (delante de sustantivo).
QString fixOne(QString w, bool feminine, bool apocope)
{
    if (!w.endsWith(QLatin1String("uno"))) return w;
    w.chop(3);
    if (feminine) return w + QStringLiteral("una");
    if (apocope) return w.isEmpty() ? QStringLiteral("un") : w + QStringLiteral("ún");
    return w + QStringLiteral("uno");
}

QString under100(int n, bool feminine, bool apocope)
{
    if (n < 30) return fixOne(QString::fromUtf8(kUnder30[n]), feminine, apocope);
    const QString tens = QString::fromUtf8(kTens[n / 10]);
    if (n % 10 == 0) return tens;
    return tens + QStringLiteral(" y ") + fixOne(QString::fromUtf8(kUnder30[n % 10]), feminine, apocope);
}

QString under1000(int n, bool feminine, bool apocope)
{
    if (n == 100) return QStringLiteral("cien");
    const int h = n / 100, r = n % 100;
    QString out;
    if (h > 0) {
        out = QString::fromUtf8(kHundreds[h]);
        if (feminine && h > 1) out.replace(QLatin1String("ientos"), QLatin1String("ientas"));
        if (feminine && h == 5) out = QStringLiteral("quinientas");
    }
    if (r > 0) {
        if (!out.isEmpty()) out += QLatin1Char(' ');
        out += under100(r, feminine, apocope);
    }
    return out;
}

QString digitByDigit(const QString &digits)
{
    QStringList w;
    for (const QChar c : digits)
        if (c.isDigit()) w << QString::fromUtf8(kUnder30[c.digitValue()]);
    return w.join(QLatin1Char(' '));
}

// Sustantivos femeninos frecuentes en respuestas del agente ("1 hora", "21 pestañas").
bool isFeminineNoun(const QString &word)
{
    static const QSet<QString> s = {
        QStringLiteral("hora"), QStringLiteral("horas"), QStringLiteral("vez"), QStringLiteral("veces"),
        QStringLiteral("semana"), QStringLiteral("semanas"), QStringLiteral("persona"), QStringLiteral("personas"),
        QStringLiteral("página"), QStringLiteral("páginas"), QStringLiteral("pestaña"), QStringLiteral("pestañas"),
        QStringLiteral("ventana"), QStringLiteral("ventanas"), QStringLiteral("carpeta"), QStringLiteral("carpetas"),
        QStringLiteral("tarea"), QStringLiteral("tareas"), QStringLiteral("foto"), QStringLiteral("fotos"),
        QStringLiteral("imagen"), QStringLiteral("imágenes"), QStringLiteral("línea"), QStringLiteral("líneas"),
        QStringLiteral("cosa"), QStringLiteral("cosas"), QStringLiteral("opción"), QStringLiteral("opciones"),
        QStringLiteral("llamada"), QStringLiteral("llamadas"), QStringLiteral("noticia"), QStringLiteral("noticias"),
        QStringLiteral("aplicación"), QStringLiteral("aplicaciones"), QStringLiteral("app"), QStringLiteral("apps"),
        QStringLiteral("canción"), QStringLiteral("canciones"), QStringLiteral("película"), QStringLiteral("películas"),
        QStringLiteral("pregunta"), QStringLiteral("preguntas"), QStringLiteral("respuesta"), QStringLiteral("respuestas"),
        QStringLiteral("fila"), QStringLiteral("filas"), QStringLiteral("columna"), QStringLiteral("columnas"),
        QStringLiteral("hoja"), QStringLiteral("hojas"), QStringLiteral("unidad"), QStringLiteral("unidades"),
        QStringLiteral("gpu"), QStringLiteral("gpus"), QStringLiteral("tarjeta"), QStringLiteral("tarjetas"),
        QStringLiteral("versión"), QStringLiteral("versiones"), QStringLiteral("alarma"), QStringLiteral("alarmas"),
        QStringLiteral("nota"), QStringLiteral("notas"), QStringLiteral("reunión"), QStringLiteral("reuniones"),
        QStringLiteral("búsqueda"), QStringLiteral("búsquedas"), QStringLiteral("sesión"), QStringLiteral("sesiones"),
        QStringLiteral("palabra"), QStringLiteral("palabras"), QStringLiteral("tecla"), QStringLiteral("teclas"),
        QStringLiteral("pantalla"), QStringLiteral("pantallas"), QStringLiteral("frase"), QStringLiteral("frases"),
        QStringLiteral("cuota"), QStringLiteral("cuotas"), QStringLiteral("cuenta"), QStringLiteral("cuentas")};
    return s.contains(word);
}

// Palabras tras las que un número NO lleva apócope ("veintiuno y treinta").
bool blocksApocope(const QString &word)
{
    static const QSet<QString> s = {
        QStringLiteral("y"), QStringLiteral("e"), QStringLiteral("o"), QStringLiteral("u"),
        QStringLiteral("a"), QStringLiteral("de"), QStringLiteral("del"), QStringLiteral("en"),
        QStringLiteral("con"), QStringLiteral("por"), QStringLiteral("para"), QStringLiteral("es"),
        QStringLiteral("más"), QStringLiteral("menos"), QStringLiteral("sobre"), QStringLiteral("coma"),
        QStringLiteral("dividido"), QStringLiteral("al"), QStringLiteral("hasta"), QStringLiteral("que"),
        QStringLiteral("son"), QStringLiteral("da"), QStringLiteral("x")};
    return s.contains(word);
}

// Mira las dos palabras que siguen al número para decidir género y apócope.
void agreement(const QString &text, qsizetype after, bool *feminine, bool *apocope)
{
    static const QRegularExpression nextRe = rx("^\\s*(\\p{L}+)(?:\\s+(\\p{L}+))?");
    const QRegularExpressionMatch m = nextRe.match(text.mid(after, 40));
    *feminine = false;
    *apocope = false;
    if (!m.hasMatch()) return;
    const QString w1 = m.captured(1).toLower();
    const QString w2 = m.captured(2).toLower();
    if (w1 == QLatin1String("por") && w2 == QLatin1String("ciento")) { *apocope = true; return; }
    if (blocksApocope(w1)) return;
    *apocope = true;
    *feminine = isFeminineNoun(w1);
}

QString decimalPart(const QString &digits)
{
    // "5" → cinco, "50" → cincuenta, "05" / "141" → dígito a dígito.
    if (digits.size() <= 2 && !digits.startsWith(QLatin1Char('0')))
        return under100(digits.toInt(), false, false);
    return digitByDigit(digits);
}

const char *const kMonths[] = {"", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                               "agosto", "septiembre", "octubre", "noviembre", "diciembre"};

struct Unit { const char *symbol; const char *singular; const char *plural; };
// Orden: los símbolos más largos primero (km/h antes que km).
const Unit kUnits[] = {
    {"km/h", "kilómetro por hora", "kilómetros por hora"},
    {"tok/s", "token por segundo", "tokens por segundo"},
    {"t/s", "token por segundo", "tokens por segundo"},
    {"GiB", "giga", "gigas"}, {"MiB", "mega", "megas"}, {"TiB", "tera", "teras"},
    {"GB", "giga", "gigas"}, {"MB", "mega", "megas"}, {"TB", "tera", "teras"},
    {"KB", "kilobyte", "kilobytes"}, {"kB", "kilobyte", "kilobytes"},
    {"GHz", "gigahercio", "gigahercios"}, {"MHz", "megahercio", "megahercios"},
    {"ms", "milisegundo", "milisegundos"}, {"min", "minuto", "minutos"},
    {"hs", "hora", "horas"}, {"km", "kilómetro", "kilómetros"},
    {"kg", "kilo", "kilos"}, {"cm", "centímetro", "centímetros"},
    {"mm", "milímetro", "milímetros"}};

QString normalizeStructure(QString s, bool es)
{
    // Links markdown [texto](url) → texto.
    s.replace(rx("\\[([^\\]]+)\\]\\((?:[^)\\s]+)\\)"), QStringLiteral("\\1"));
    // Encabezados, viñetas, numeración y filas separadoras de tablas al inicio de línea.
    s.replace(rx("^\\s*#{1,6}\\s*", QRegularExpression::MultilineOption), QString());
    s.replace(rx("^\\s*[-*•+]\\s+", QRegularExpression::MultilineOption), QString());
    s.replace(rx("^\\s*\\d{1,2}[.)]\\s+", QRegularExpression::MultilineOption), QString());
    s.replace(rx("^[ \\t]*\\|?[ \\t:|-]*-{3,}[ \\t:|-]*$\\n?", QRegularExpression::MultilineOption), QString());
    // Filas de tabla: "| a | b |" → "a, b" (cada fila sigue en su línea).
    s = replaceEach(s, rx("^[ \\t]*\\|?([^\\n]*\\|[^\\n]*?)\\|?[ \\t]*$", QRegularExpression::MultilineOption),
                    [](const QRegularExpressionMatch &m) {
        QStringList cells = m.captured(1).split(QLatin1Char('|'));
        for (QString &c : cells) c = c.trimmed();
        cells.removeAll(QString());
        return cells.join(QStringLiteral(", "));
    });

    // Emails antes que URLs (comparten los puntos).
    s = replaceEach(s, rx("\\b([\\w.+-]+)@([\\w-]+(?:\\.[\\w-]+)+)\\b"),
                    [es](const QRegularExpressionMatch &m) {
        return spellDots(m.captured(1), es) + (es ? QStringLiteral(" arroba ") : QStringLiteral(" at "))
               + spellDots(m.captured(2), es);
    });
    // URLs → sólo el dominio, sin www ni ruta. El punto final de la oración se conserva.
    s = replaceEach(s, rx("(?:https?://|www\\.)[^\\s<>()\"]+", QRegularExpression::CaseInsensitiveOption),
                    [es](const QRegularExpressionMatch &m) {
        QString url = m.captured(0);
        QString trail;
        while (!url.isEmpty() && QStringLiteral(".,;:!?").contains(url.back())) {
            trail.prepend(url.back());
            url.chop(1);
        }
        url.remove(rx("^https?://", QRegularExpression::CaseInsensitiveOption));
        url.remove(rx("^www\\.", QRegularExpression::CaseInsensitiveOption));
        const QString host = url.section(QRegularExpression(QStringLiteral("[/?#:]")), 0, 0);
        return spellDots(host, es) + trail;
    });
    // Archivos con extensión conocida: "config.json" → "config punto json".
    s = replaceEach(s, rx("\\b([A-Za-z][\\w-]*)\\.(json|txt|md|py|cpp|hpp|h|js|ts|qml|pdf|docx?|xlsx?|pptx?|csv|png|jpe?g|gif|log|sh|bat|ps1|exe|zip|html?|ya?ml|ini|conf|toml|gguf)\\b",
                       QRegularExpression::CaseInsensitiveOption),
                    [es](const QRegularExpressionMatch &m) {
        return m.captured(1) + (es ? QStringLiteral(" punto ") : QStringLiteral(" dot ")) + m.captured(2);
    });

    // Bare domains ("smn.gob.ar") con TLD conocido.
    s = replaceEach(s, rx("\\b(?:[a-z0-9-]+\\.)+(?:com|org|net|io|ai|dev|ar|es|edu|gov|gob|app|co|uk|tv|mx|cl|uy)\\b",
                          QRegularExpression::CaseInsensitiveOption),
                    [es](const QRegularExpressionMatch &m) { return spellDots(m.captured(0), es); });

    // Énfasis/código inline: los marcadores no se leen; snake_case → espacios.
    // Un "*" entre números es multiplicación, no énfasis.
    s.replace(rx("(?<=\\d)\\s*\\*\\s*(?=\\d)"), QStringLiteral(" × "));
    s.remove(QLatin1Char('`'));
    s.remove(QLatin1Char('*'));
    s.replace(rx("(?<=\\w)_(?=\\w)"), QStringLiteral(" "));
    s.remove(QLatin1Char('_'));
    // Flechas y conectores simbólicos.
    s.replace(rx("\\s*(?:→|->|=>|⇒|➜)\\s*"), QStringLiteral(", "));
    s.replace(rx("\\s+&\\s+"), es ? QStringLiteral(" y ") : QStringLiteral(" and "));
    // Emojis y pictogramas: no se pueden pronunciar.
    s.remove(rx("[\\x{1F000}-\\x{1FAFF}\\x{2600}-\\x{27BF}\\x{FE0F}\\x{200D}]"));
    return s;
}

QString normalizeSpanishSymbols(QString s)
{
    // Fechas dd/mm/aaaa → "5 de noviembre de 2026" (los números se expanden después).
    s = replaceEach(s, rx("\\b(\\d{1,2})/(\\d{1,2})(?:/(\\d{2,4}))?\\b"),
                    [](const QRegularExpressionMatch &m) {
        const int d = m.captured(1).toInt(), mo = m.captured(2).toInt();
        if (d < 1 || d > 31 || mo < 1 || mo > 12 || m.captured(3).isEmpty())
            return m.captured(0);          // fracción o algo que no es fecha: sigue abajo
        QString year = m.captured(3);
        if (year.size() == 2) year.prepend(QStringLiteral("20"));
        return QStringLiteral("%1 de %2 de %3").arg(d).arg(QString::fromUtf8(kMonths[mo]), year);
    });
    // Fechas ISO 2026-11-05.
    s = replaceEach(s, rx("\\b(\\d{4})-(\\d{2})-(\\d{2})\\b"), [](const QRegularExpressionMatch &m) {
        const int mo = m.captured(2).toInt(), d = m.captured(3).toInt();
        if (d < 1 || d > 31 || mo < 1 || mo > 12) return m.captured(0);
        return QStringLiteral("%1 de %2 de %3").arg(d).arg(QString::fromUtf8(kMonths[mo]), m.captured(1));
    });
    // Horas 10:30 → "10 y 30"; 10:00 → "10". "hs"/"h" detrás de una hora sobra.
    s = replaceEach(s, rx("\\b([01]?\\d|2[0-3]):([0-5]\\d)(?:\\s*(?:hs|h)\\b)?"),
                    [](const QRegularExpressionMatch &m) {
        const int h = m.captured(1).toInt(), mi = m.captured(2).toInt();
        return mi == 0 ? QString::number(h) : QStringLiteral("%1 y %2").arg(h).arg(mi);
    });

    const QString num = QStringLiteral("(\\d[\\d.,]*\\d|\\d)");
    // Monedas. En español rioplatense "$" son pesos.
    s.replace(QRegularExpression(QStringLiteral("(?:US\\$|U\\$S|USD)\\s?") + num),
              QStringLiteral("\\1 dólares"));
    s.replace(QRegularExpression(num + QStringLiteral("\\s?(?:USD|dólares)\\b")), QStringLiteral("\\1 dólares"));
    s.replace(QRegularExpression(QStringLiteral("(?:€|EUR)\\s?") + num), QStringLiteral("\\1 euros"));
    s.replace(QRegularExpression(num + QStringLiteral("\\s?(?:€|EUR\\b)")), QStringLiteral("\\1 euros"));
    s.replace(QRegularExpression(QStringLiteral("\\$\\s?") + num), QStringLiteral("\\1 pesos"));

    // Temperatura y porcentaje.
    s.replace(QRegularExpression(num + QStringLiteral("\\s?°\\s?[CF]\\b")), QStringLiteral("\\1 grados"));
    s.replace(QRegularExpression(num + QStringLiteral("\\s?°")), QStringLiteral("\\1 grados"));
    s.replace(QRegularExpression(num + QStringLiteral("\\s?%")), QStringLiteral("\\1 por ciento"));

    // Unidades detrás de un número; singular sólo para "1".
    for (const Unit &u : kUnits) {
        const QRegularExpression ure(num + QStringLiteral("\\s?")
                                     + QRegularExpression::escape(QString::fromUtf8(u.symbol))
                                     + QStringLiteral("(?![\\p{L}\\d])"),
                                     QRegularExpression::UseUnicodePropertiesOption);
        s = replaceEach(s, ure, [&u](const QRegularExpressionMatch &m) {
            const bool one = m.captured(1) == QLatin1String("1");
            return m.captured(1) + QLatin1Char(' ')
                   + QString::fromUtf8(one ? u.singular : u.plural);
        });
    }

    // Aritmética entre números.
    const QString a = QStringLiteral("(?<=\\d)\\s*");
    const QString b = QStringLiteral("\\s*(?=\\d)");
    s.replace(QRegularExpression(QStringLiteral("(?<=\\d)\\s*×\\s*|(?<=\\d)\\s+x\\s+(?=\\d)")), QStringLiteral(" por "));
    s.replace(QRegularExpression(a + QStringLiteral("[÷/]") + b), QStringLiteral(" sobre "));
    s.replace(QRegularExpression(a + QStringLiteral("\\+") + b), QStringLiteral(" más "));
    s.replace(QRegularExpression(QStringLiteral("(?<=\\d)\\s+[-−]\\s+(?=\\d)")), QStringLiteral(" menos "));
    s.replace(QRegularExpression(QStringLiteral("(?<=\\d)[–—-](?=\\d)")), QStringLiteral(" a "));
    s.replace(QRegularExpression(QStringLiteral("\\s*(?:=|≈)\\s*")), QStringLiteral(" es igual a "));
    s.replace(QRegularExpression(QStringLiteral("~\\s*(?=\\d)")), QStringLiteral("unos "));
    s.replace(QRegularExpression(QStringLiteral("#\\s*(?=\\d)")), QStringLiteral("número "));
    return s;
}

QString expandNumbersEs(const QString &s)
{
    // 1.245,50 | 1.245 | 3,5 | 3.5 | 42
    static const QRegularExpression numRe = rx("(?<![\\p{L}\\d])(\\d{1,3}(?:\\.\\d{3})+|\\d+)(?:([.,])(\\d+))?(?![\\p{L}\\d])");
    return replaceEach(s, numRe, [&s](const QRegularExpressionMatch &m) {
        QString intPart = m.captured(1);
        QString sep = m.captured(2);
        QString dec = m.captured(3);
        // "3.500" sin agrupación previa: en español es miles, no decimal.
        if (sep == QLatin1String(".") && dec.size() == 3 && !intPart.contains(QLatin1Char('.'))) {
            intPart += QLatin1Char('.') + dec;
            sep.clear();
            dec.clear();
        }
        intPart.remove(QLatin1Char('.'));
        if (intPart.size() > 12 || (intPart.size() > 1 && intPart.startsWith(QLatin1Char('0'))))
            return digitByDigit(intPart) + (dec.isEmpty() ? QString() : QStringLiteral(" coma ") + digitByDigit(dec));
        const qint64 n = intPart.toLongLong();
        if (!dec.isEmpty())
            return numberToWordsEs(n) + QStringLiteral(" coma ") + decimalPart(dec);
        bool fem = false, apo = false;
        agreement(s, m.capturedEnd(), &fem, &apo);
        return numberToWordsEs(n, fem, apo);
    });
}

} // namespace

QString numberToWordsEs(qint64 n, bool feminine, bool apocope)
{
    if (n < 0) return QStringLiteral("menos ") + numberToWordsEs(-n, feminine, apocope);
    if (n >= 1000000000000LL) return digitByDigit(QString::number(n));
    if (n == 0) return QStringLiteral("cero");

    QStringList parts;
    const qint64 millions = n / 1000000;
    const int thousands = int((n / 1000) % 1000);
    const int rest = int(n % 1000);
    if (millions > 0) {
        parts << (millions == 1 ? QStringLiteral("un millón")
                                : numberToWordsEs(millions, false, true) + QStringLiteral(" millones"));
    }
    if (thousands > 0) {
        parts << (thousands == 1 ? QStringLiteral("mil")
                                 : under1000(thousands, feminine, true) + QStringLiteral(" mil"));
    }
    if (rest > 0) parts << under1000(rest, feminine, apocope);
    return parts.join(QLatin1Char(' '));
}

QString normalize(const QString &text, const QString &lang)
{
    const bool es = !lang.startsWith(QLatin1String("en"), Qt::CaseInsensitive);
    QString s = normalizeStructure(text, es);
    if (es) {
        s = normalizeSpanishSymbols(s);
        s = expandNumbersEs(s);
    }
    // Restos de símbolos que el TTS leería en voz alta.
    s.replace(rx("[#|^<>{}\\[\\]\\\\~]"), QStringLiteral(" "));
    s.replace(rx("[ \\t]+"), QStringLiteral(" "));
    s.replace(rx(" +([,.;:!?])"), QStringLiteral("\\1"));
    s.replace(rx("([,;:])(?:\\s*[,;:])+"), QStringLiteral("\\1"));
    s.replace(rx("\\n\\s*\\n+"), QStringLiteral("\n"));
    if (es) {
        s.replace(rx("\\bun pesos\\b"), QStringLiteral("un peso"));
        s.replace(rx("\\bun dólares\\b"), QStringLiteral("un dólar"));
        s.replace(rx("\\bun euros\\b"), QStringLiteral("un euro"));
    }
    s = s.trimmed();
    while (s.startsWith(QLatin1Char(',')) || s.startsWith(QLatin1Char(';')))
        s = s.mid(1).trimmed();
    return s;
}

} // namespace SpeechTextNormalizer
