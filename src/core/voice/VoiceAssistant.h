#pragma once
#include <QString>
#include <QVariantMap>

// Ingi Charla en modo asistente (agente + voz + computer use). Lógica pura del
// diálogo hablado alrededor del agente: qué decir mientras trabaja y cómo
// resolver por voz una aprobación de tool. Sin estado ni Qt-GUI → testeable.
namespace VoiceAssistant {

enum class Confirmation { Yes, No, Unknown };

// Interpreta la respuesta hablada a "¿lo hago?". Conservador: una negación en
// cualquier parte gana ("sí, pero no lo borres" = No) y una frase larga que no
// es una respuesta corta se trata como Unknown (probablemente es otra orden).
Confirmation parseConfirmation(const QString &text);

// ¿El usuario pidió frenar lo que el agente está haciendo? ("pará", "cancelá",
// "basta", "olvidalo"). Sólo frases cortas: "pará de buscar vuelos y buscá
// hoteles" es un pedido nuevo, no una orden de frenar.
bool isStopCommand(const QString &text);

// Frase corta para hablar apenas el agente arranca una tool lenta, así no hay
// silencio mientras busca/opera la PC. Vacío = la tool es rápida o interna y no
// merece aviso. `lang` es el idioma de la app ("es", "en", ...).
QString toolCue(const QString &toolName, const QString &lang);

// Pregunta hablada para una aprobación pendiente (payload de toolApprovalNeeded).
QString approvalQuestion(const QVariantMap &toolCall, const QString &lang);

}  // namespace VoiceAssistant
