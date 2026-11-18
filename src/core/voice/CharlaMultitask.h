#pragma once
#include <QDate>
#include <QString>

// Ingi Charla multitarea: mientras el agente principal trabaja, un pedido nuevo
// arranca un agente en segundo plano en otro slot del mismo llama-server, en
// vez de esperar en cola ("Anotado, sigo con eso después").
//
// Medido en 2× RTX 3090 con Qwen3.8-27B UD-Q4 (docs/charla-multitarea-computer-use-20261105.md):
// con 1 slot la voz tardaba 46,9 s en decir la primera oración mientras tres
// agentes generaban; con 4 slots y los prompts de agente precalentados, 1,09 s
// (TTFT 0,38 s), y los agentes juntos rindieron 44,8 tok/s contra 35,8.
//
// Funciones puras: la orquestación (SubAgentRunner, avisos por voz) vive en
// AppController.
namespace CharlaMultitask {

// Agentes de fondo que todavía entran: un slot queda siempre para la voz/el
// agente principal. parallelSlots <= 1 → 0 (comportamiento de cola de siempre).
int backgroundCapacity(int parallelSlots, int activeBackground);

// System prompt del agente de fondo: sin escritorio, resultado en 1-2 frases
// habladas. workDir es su carpeta de trabajo.
QString backgroundSystemPrompt(const QString &workDir, const QDate &today, const QString &lang);

// Lo que dice la voz al lanzar la tarea ("Dale, lo hago en paralelo.").
QString startCue(int runningAfterStart, const QString &lang);

// Aviso al terminar: "Listo lo de <pedido>: <resultado>" en 1-2 frases.
QString completionAnnouncement(const QString &request, const QString &result, bool ok,
                               const QString &lang);

// "¿Cómo van las tareas?" / "qué estás haciendo": se contesta sin el LLM.
bool isStatusQuery(const QString &text);
QString statusReport(const QStringList &runningRequests, const QString &lang);

// Etiqueta corta de un pedido para nombrarlo al hablar (≤ 6 palabras).
QString shortLabel(const QString &request);

} // namespace CharlaMultitask
