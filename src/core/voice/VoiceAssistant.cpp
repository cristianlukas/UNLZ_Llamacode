#include "VoiceAssistant.h"
#include <QFileInfo>
#include <QRegularExpression>
#include <QStringList>

namespace {

bool english(const QString &lang)
{
    return lang.trimmed().toLower().startsWith(QLatin1String("en"));
}

// Minúsculas, sin tildes y sin puntuación: el STT no es consistente con "sí"/"si"
// ni con las comas, y la respuesta se compara por palabras.
QString normalize(const QString &text)
{
    QString s = text.toLower().normalized(QString::NormalizationForm_D);
    QString out;
    out.reserve(s.size());
    for (const QChar c : s) {
        if (c.category() == QChar::Mark_NonSpacing) continue;
        out.append(c.isLetterOrNumber() || c == QLatin1Char('\'') ? c : QLatin1Char(' '));
    }
    return QLatin1Char(' ') + out.simplified() + QLatin1Char(' ');
}

bool hasPhrase(const QString &norm, const QStringList &phrases)
{
    for (const QString &p : phrases)
        if (norm.contains(QLatin1Char(' ') + p + QLatin1Char(' '))) return true;
    return false;
}

}  // namespace

VoiceAssistant::Confirmation VoiceAssistant::parseConfirmation(const QString &text)
{
    const QString n = normalize(text);
    if (n.trimmed().isEmpty()) return Confirmation::Unknown;
    // "No sé" / "no estoy seguro" no es un no: es duda, y no se ejecuta ni se
    // descarta por eso. Se vuelve a preguntar.
    if (hasPhrase(n, {QStringLiteral("no se"), QStringLiteral("no estoy seguro"),
                      QStringLiteral("no estoy segura"), QStringLiteral("i don't know"),
                      QStringLiteral("not sure"), QStringLiteral("no idea")}))
        return Confirmation::Unknown;
    // Afirmaciones que contienen un "no" literal.
    if (hasPhrase(n, {QStringLiteral("no hay problema"), QStringLiteral("no problem"),
                      QStringLiteral("why not"), QStringLiteral("por que no")}))
        return Confirmation::Yes;
    // ("pará" no figura: normalizado es "para", que también es la preposición.)
    // La negación gana sobre cualquier afirmación de la misma frase ("sí, pero no
    // lo borres"): ante la duda, una acción irreversible NO se ejecuta.
    static const QStringList negatives{
        QStringLiteral("no"), QStringLiteral("nop"), QStringLiteral("nope"),
        QStringLiteral("nah"), QStringLiteral("negativo"), QStringLiteral("cancela"),
        QStringLiteral("cancelar"), QStringLiteral("cancelalo"), QStringLiteral("cancel"),
        QStringLiteral("frena"), QStringLiteral("detente"),
        QStringLiteral("deten"), QStringLiteral("ni loco"), QStringLiteral("ni loca"),
        QStringLiteral("don't"), QStringLiteral("dont"), QStringLiteral("stop"),
        QStringLiteral("abort"), QStringLiteral("never"), QStringLiteral("jamas"),
        QStringLiteral("nunca")};
    if (hasPhrase(n, negatives)) return Confirmation::No;
    // Una frase larga sin negación probablemente es otra orden, no un "sí".
    if (n.simplified().split(QLatin1Char(' ')).size() > 10) return Confirmation::Unknown;
    static const QStringList positives{
        QStringLiteral("si"), QStringLiteral("dale"), QStringLiteral("ok"),
        QStringLiteral("okay"), QStringLiteral("okey"), QStringLiteral("oka"),
        QStringLiteral("hacelo"), QStringLiteral("hazlo"), QStringLiteral("adelante"),
        QStringLiteral("confirmo"), QStringLiteral("confirmado"), QStringLiteral("de una"),
        QStringLiteral("claro"), QStringLiteral("por supuesto"), QStringLiteral("afirmativo"),
        QStringLiteral("obvio"), QStringLiteral("segui"), QStringLiteral("sigue"),
        QStringLiteral("continua"), QStringLiteral("procede"), QStringLiteral("proceda"),
        QStringLiteral("yes"), QStringLiteral("yeah"), QStringLiteral("yep"),
        QStringLiteral("sure"), QStringLiteral("go ahead"), QStringLiteral("do it"),
        QStringLiteral("proceed"), QStringLiteral("confirm"), QStringLiteral("affirmative")};
    if (hasPhrase(n, positives)) return Confirmation::Yes;
    return Confirmation::Unknown;
}

bool VoiceAssistant::isStopCommand(const QString &text)
{
    const QString n = normalize(text);
    const QStringList words = n.simplified().split(QLatin1Char(' '), Qt::SkipEmptyParts);
    if (words.isEmpty() || words.size() > 4) return false;
    static const QStringList stops{
        QStringLiteral("basta"), QStringLiteral("stop"), QStringLiteral("cancela"),
        QStringLiteral("cancelalo"), QStringLiteral("cancelar"), QStringLiteral("cancel"),
        QStringLiteral("frena"), QStringLiteral("detente"), QStringLiteral("detenete"),
        QStringLiteral("deten"), QStringLiteral("callate"), QStringLiteral("silencio"),
        QStringLiteral("olvidalo"), QStringLiteral("dejalo"), QStringLiteral("dejala"),
        QStringLiteral("abort"), QStringLiteral("nevermind"), QStringLiteral("never mind"),
        QStringLiteral("forget it"), QStringLiteral("shut up"), QStringLiteral("quiet")};
    if (hasPhrase(n, stops)) return true;
    // "pará" normaliza a "para", que también es preposición ("para mañana"):
    // sólo vale sola o con un refuerzo ("pará ya", "pará che").
    if (words.first() != QLatin1String("para")) return false;
    static const QStringList fillers{QStringLiteral("ya"), QStringLiteral("che"),
                                     QStringLiteral("ahi"), QStringLiteral("para"),
                                     QStringLiteral("porfa"), QStringLiteral("ahora")};
    for (int i = 1; i < words.size(); ++i)
        if (!fillers.contains(words.at(i))) return false;
    return true;
}

QString VoiceAssistant::toolCue(const QString &tool, const QString &lang)
{
    const bool en = english(lang);
    auto say = [en](const char *es, const char *eng) {
        return QString::fromUtf8(en ? eng : es);
    };
    if (tool == QLatin1String("web_search"))
        return say("Lo busco.", "Searching.");
    if (tool == QLatin1String("deep_research"))
        return say("Investigo un momento.", "Researching, one moment.");
    if (tool == QLatin1String("web_fetch"))
        return say("Leo la página.", "Reading the page.");
    if (tool == QLatin1String("desktop_launch"))
        return say("Abro la aplicación.", "Opening the app.");
    if (tool == QLatin1String("desktop_observe") || tool == QLatin1String("desktop_snapshot"))
        return say("Miro la pantalla.", "Looking at the screen.");
    if (tool.startsWith(QLatin1String("desktop_")))
        return say("Lo hago en pantalla.", "Doing it on screen.");
    if (tool.startsWith(QLatin1String("browser_")))
        return say("Uso el navegador.", "Using the browser.");
    if (tool == QLatin1String("run_shell"))
        return say("Lo ejecuto.", "Running it.");
    if (tool == QLatin1String("email_list") || tool == QLatin1String("email_read"))
        return say("Reviso el correo.", "Checking your email.");
    if (tool == QLatin1String("task"))
        return say("Lo reparto en una subtarea.", "Delegating a subtask.");
    if (tool == QLatin1String("ask_teacher"))
        return say("Consulto al supervisor.", "Asking the supervisor.");
    if (tool.startsWith(QLatin1String("mcp")) || tool == QLatin1String("worker_call"))
        return say("Consulto la herramienta.", "Checking the tool.");
    // Lectura de archivos, memoria, grep...: tardan milisegundos. Hablar un aviso
    // ahí agrega latencia (el TTS) en vez de tapar un silencio.
    return {};
}

QString VoiceAssistant::approvalQuestion(const QVariantMap &call, const QString &lang)
{
    const bool en = english(lang);
    const QString tool = call.value(QStringLiteral("tool")).toString();
    QString detail = call.value(QStringLiteral("detail")).toString().simplified();
    // El detalle se lee en voz alta: más de una línea corta no se entiende.
    if (detail.size() > 90) detail = detail.left(87) + QStringLiteral("...");

    QString action;
    if (tool == QLatin1String("run_shell"))
        action = en ? QStringLiteral("run the command %1").arg(detail)
                    : QStringLiteral("ejecutar el comando %1").arg(detail);
    else if (tool == QLatin1String("email_send"))
        action = en ? QStringLiteral("send an email") : QStringLiteral("enviar un correo");
    else if (tool == QLatin1String("write_file") || tool == QLatin1String("edit_file"))
        action = en ? QStringLiteral("modify the file %1").arg(QFileInfo(detail).fileName())
                    : QStringLiteral("modificar el archivo %1").arg(QFileInfo(detail).fileName());
    else if (tool.startsWith(QLatin1String("desktop_")))
        action = en ? QStringLiteral("act on the screen") : QStringLiteral("hacer una acción en pantalla");
    else
        action = en ? QStringLiteral("use %1").arg(tool) : QStringLiteral("usar %1").arg(tool);

    const QString reason = call.value(QStringLiteral("reason")).toString();
    QString why;
    if (reason == QLatin1String("destructive"))
        why = en ? QStringLiteral(" It can't be undone.") : QStringLiteral(" No se puede deshacer.");
    else if (reason == QLatin1String("email") || reason == QLatin1String("external_write"))
        why = en ? QStringLiteral(" It goes outside this PC.") : QStringLiteral(" Sale de esta PC.");

    return en ? QStringLiteral("I need your OK to %1.%2 Should I do it?").arg(action, why)
              : QStringLiteral("Necesito tu confirmación para %1.%2 ¿Lo hago?").arg(action, why);
}
