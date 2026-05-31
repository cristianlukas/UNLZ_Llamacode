#pragma once
#include <QString>
#include <QStringList>
#include <QVariantMap>
#include <QProcessEnvironment>

// Contexto para arrancar un backend de agente.
struct AgentContext {
    QString adapter;          // "opencode" | "goose" | "raw" | ...
    QString launchProfileId;
    QString exePath;          // binario del harness (vacío para raw)
    QString cwd;              // carpeta del proyecto
    QString serverBaseUrl;    // URL del llama-server (OpenAI-compatible), sin /v1
    QString modelId;          // modelo servido / alias
    QProcessEnvironment env;  // env ya armado para el proceso del harness
};

// Mensaje de chat del agente (rol + contenido + estado).
struct AgentMessage {
    QString role;             // "user" | "assistant" | "system"
    QString content;
    bool    typing = false;

    QVariantMap toMap() const {
        return { {"role", role}, {"content", content}, {"typing", typing} };
    }
};

// Sesión de agente (chat persistente, opcionalmente ligada a un proyecto).
struct AgentSession {
    QString id;
    QString title;
    double  created = 0;
    QString projectId;
    QString projectName;
    QString projectDir;

    QVariantMap toMap() const {
        return {
            {"id", id}, {"title", title}, {"created", created},
            {"projectId", projectId}, {"projectName", projectName},
            {"projectDir", projectDir}
        };
    }
};

// Pedido de aprobación de una tool (human-in-the-loop).
struct ToolCall {
    QString id;
    QString sessionId;
    QString name;             // "bash" | "edit" | "write" | ...
    QString summary;          // comando / archivo / descripción corta
    QString detail;           // diff o cuerpo completo

    QVariantMap toMap() const {
        return { {"id", id}, {"sessionId", sessionId}, {"name", name},
                 {"summary", summary}, {"detail", detail} };
    }
};
