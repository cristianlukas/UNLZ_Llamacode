#pragma once
#include <QString>
#include <QJsonArray>

// ToolCallingSupport — inferencia PURA de si el modelo de un perfil soporta
// tool-calling (function calling). Dos señales, ambas derivadas de datos, no de un
// whitelist manual de modelos:
//   1. Cookbook (assets/hwfit/hf_models.json): capabilities[] con "tool_use" /
//      "function_calling".
//   2. chat-template del GGUF (vía /props de llama-server): jinja que referencia
//      `tools` / `tool_calls` → la plantilla realmente sabe emitir tool calls.
//
// Sin disco ni red: recibe el cookbook ya parseado y/o el string del template →
// unit-testeable de forma determinista.
class ToolCallingSupport
{
public:
    enum class Support { Supported, Unsupported, Unknown };

    // Normaliza un nombre/filename de modelo a una clave estable para matchear
    // (minúsculas, sin quant/formato/fecha/tags de rol, separadores colapsados).
    // Es el mismo normalizador que usa el matching de benchmarks.
    static QString normalizeKey(const QString &rawName);

    // Busca la mejor coincidencia de `modelName` en el cookbook (array de objetos
    // estilo hf_models.json con {name, capabilities[]}). Supported si la enticia
    // matcheada declara tool_use/function_calling; Unsupported si matchea pero no lo
    // declara; Unknown si no hay match.
    static Support fromCookbook(const QString &modelName, const QJsonArray &cookbook);

    // ¿El chat-template jinja referencia tools? (tool_calls / tool_call / "tools").
    static bool templateMentionsTools(const QString &chatTemplateJinja);

    // Combina cookbook + señal de template. El template positivo confirma soporte; un
    // cookbook positivo también basta. Solo se concluye Unsupported cuando el cookbook
    // dice Unsupported y el template (si lo hay) tampoco menciona tools.
    static Support combine(Support cookbook, bool haveTemplate, bool templateTools);

    static QString toString(Support s);   // "supported" | "unsupported" | "unknown"
};
