#pragma once

#include <QJsonObject>
#include <QString>

// Bitacora append-only del agente nativo. Complementa MemoryStore/GraphStore:
// aca no guardamos "verdades" consolidadas, sino evidencia operacional tipada
// de lo que el agente intento, rechazo, ejecuto y observo.
namespace AgentEventLog {

QString jsonlPath(const QString &cwd);

// Agrega metadata comun (kind/id/ts/sessionId) y persiste un objeto JSONL.
// Devuelve true si pudo escribir. El log es mejor-esfuerzo: nunca debe romper
// el turno del agente.
bool append(const QString &cwd, const QString &sessionId, const QString &kind,
            QJsonObject data = {});

}  // namespace AgentEventLog
