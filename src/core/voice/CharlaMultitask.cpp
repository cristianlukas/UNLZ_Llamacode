#include "CharlaMultitask.h"
#include <QLocale>
#include <QRegularExpression>
#include <QStringList>
#include <algorithm>

namespace CharlaMultitask {
namespace {

bool english(const QString &lang) { return lang.startsWith(QLatin1String("en"), Qt::CaseInsensitive); }

// Primeras 1-2 oraciones, sin markdown, hasta ~220 caracteres.
QString spokenSummary(QString text)
{
    text.remove(QRegularExpression(QStringLiteral("<think>[\\s\\S]*?</think>")));
    text.remove(QRegularExpression(QStringLiteral("\\[[^\\]]*\\]")));   // "[corte: ...]"
    text.replace(QRegularExpression(QStringLiteral("[*#`_>|]")), QStringLiteral(" "));
    text = text.simplified();
    QStringList sentences;
    int start = 0;
    for (int i = 0; i < text.size() && sentences.size() < 2; ++i) {
        const QChar c = text.at(i);
        if ((c == QLatin1Char('.') || c == QLatin1Char('!') || c == QLatin1Char('?'))
            && (i + 1 == text.size() || text.at(i + 1).isSpace())) {
            sentences << text.mid(start, i - start + 1).trimmed();
            start = i + 1;
        }
    }
    if (sentences.isEmpty()) sentences << text;
    QString out = sentences.join(QLatin1Char(' '));
    if (out.size() > 220) {
        out.truncate(220);
        const int sp = out.lastIndexOf(QLatin1Char(' '));
        if (sp > 120) out.truncate(sp);
        out += QStringLiteral("…");
    }
    return out;
}

} // namespace

int backgroundCapacity(int parallelSlots, int activeBackground)
{
    return std::max(0, parallelSlots - 1 - std::max(0, activeBackground));
}

QString backgroundSystemPrompt(const QString &workDir, const QDate &today, const QString &lang)
{
    if (english(lang))
        return QStringLiteral(
            "You are a background agent of Ingi Charla (voice assistant). Today is %1. "
            "Solve the user's request completely and on your own: do not ask questions. "
            "Use web_search/web_fetch for research and current data, files and run_shell "
            "inside %2. Do NOT use desktop_* tools: the mouse and keyboard belong to the "
            "main agent. When done, answer with ONE or TWO short spoken sentences with the "
            "result (no markdown, lists or URLs); if something needs the desktop, say so.")
            .arg(today.toString(Qt::ISODate), workDir);
    return QStringLiteral(
        "Sos un agente en segundo plano de Ingi Charla (asistente de voz). Hoy es %1. "
        "Resolvé el pedido del usuario completo y por tu cuenta: no hagas preguntas. "
        "Usá web_search/web_fetch para investigar o datos actuales, y archivos o "
        "run_shell dentro de %2. NO uses las tools desktop_*: el mouse y el teclado "
        "los usa el agente principal. Al terminar respondé con UNA o DOS frases cortas "
        "para decir en voz alta con el resultado (sin markdown, listas ni URLs); si "
        "algo necesita operar el escritorio, decilo.")
        .arg(QLocale(QLocale::Spanish).toString(today, QStringLiteral("dddd d 'de' MMMM 'de' yyyy")), workDir);
}

QString startCue(int runningAfterStart, const QString &lang)
{
    if (english(lang))
        return runningAfterStart > 1
            ? QStringLiteral("Sure, I'll do that in parallel too; %1 tasks running.").arg(runningAfterStart)
            : QStringLiteral("Sure, I'll do that in parallel.");
    return runningAfterStart > 1
        ? QStringLiteral("Dale, eso también lo hago en paralelo; van %1 tareas.").arg(runningAfterStart)
        : QStringLiteral("Dale, lo hago en paralelo.");
}

QString shortLabel(const QString &request)
{
    QString r = request.simplified();
    // Fórmulas de cortesía que no nombran nada.
    r.remove(QRegularExpression(QStringLiteral("^(?:che,?\\s+|ingi,?\\s+|por favor,?\\s+|dale,?\\s+)+"),
                                QRegularExpression::CaseInsensitiveOption));
    r.remove(QRegularExpression(QStringLiteral("[¿?¡!.,;:]+$")));
    QStringList words = r.split(QLatin1Char(' '), Qt::SkipEmptyParts);
    const bool cut = words.size() > 6;
    while (words.size() > 6) words.removeLast();
    QString out = words.join(QLatin1Char(' '));
    if (!out.isEmpty()) out[0] = out.at(0).toLower();
    return cut ? out + QStringLiteral("…") : out;
}

QString completionAnnouncement(const QString &request, const QString &result, bool ok,
                               const QString &lang)
{
    const QString label = shortLabel(request);
    const QString summary = spokenSummary(result);
    if (english(lang)) {
        if (!ok) return QStringLiteral("I couldn't finish \"%1\".").arg(label)
                        + (summary.isEmpty() ? QString() : QLatin1Char(' ') + summary);
        return summary.isEmpty() ? QStringLiteral("Done with \"%1\".").arg(label)
                                 : QStringLiteral("Done with \"%1\": %2").arg(label, summary);
    }
    if (!ok) return QStringLiteral("No pude terminar lo de %1.").arg(label)
                    + (summary.isEmpty() ? QString() : QLatin1Char(' ') + summary);
    return summary.isEmpty() ? QStringLiteral("Listo lo de %1.").arg(label)
                             : QStringLiteral("Listo lo de %1: %2").arg(label, summary);
}

bool isStatusQuery(const QString &text)
{
    static const QRegularExpression re(QStringLiteral(
        "^(?:che,?\\s+)?(?:¿\\s*)?(?:c[oó]mo\\s+van\\s+(?:las\\s+)?tareas|qu[eé]\\s+tareas\\s+(?:ten[eé]s|hay)|"
        "en\\s+qu[eé]\\s+(?:est[aá]s|and[aá]s)|qu[eé]\\s+est[aá]s\\s+haciendo|"
        "how\\s+are\\s+the\\s+tasks|what\\s+are\\s+you\\s+(?:doing|working\\s+on))\\b"),
        QRegularExpression::CaseInsensitiveOption | QRegularExpression::UseUnicodePropertiesOption);
    return re.match(text.trimmed()).hasMatch();
}

QString statusReport(const QStringList &runningRequests, const QString &lang)
{
    if (runningRequests.isEmpty())
        return english(lang) ? QStringLiteral("No tasks running in the background.")
                             : QStringLiteral("No tengo tareas en segundo plano.");
    QStringList labels;
    for (const QString &r : runningRequests) labels << shortLabel(r);
    if (english(lang))
        return QStringLiteral("%1 in the background: %2.").arg(runningRequests.size()).arg(labels.join(QStringLiteral("; ")));
    if (runningRequests.size() == 1)
        return QStringLiteral("Estoy con una tarea: %1.").arg(labels.first());
    return QStringLiteral("Estoy con %1 tareas: %2.")
        .arg(runningRequests.size()).arg(labels.join(QStringLiteral("; ")));
}

} // namespace CharlaMultitask
