#pragma once
#include <QString>
#include <QStringList>

// Memoria PERSISTENTE por capas para el agente. Hechos atómicos con metadata,
// guardados como JSONL en <cwd>/.llamacode/memory.jsonl (un objeto por línea).
// Convive con el viejo memory.md (append-only) que sigue manejando la tool
// 'memory' para back-compat; este store es la capa estructurada (scope/type/
// confidence + recall por relevancia).
//
// Capas (scope):
//   - "session"  : contexto de la sesión actual (volátil semánticamente).
//   - "project"  : reglas, arquitectura, decisiones, paths, bugs del repo.
//   - "personal" : preferencias/estilo del usuario (transversal a proyectos).
// type: preference | decision | fact | bug | other.
namespace MemoryStore {

// Ruta del JSONL estructurado para un cwd dado.
QString jsonlPath(const QString &cwd);

// Guarda un hecho atómico. Devuelve un mensaje de estado para la tool.
QString save(const QString &cwd, const QString &content, const QString &scope,
             const QString &type, double confidence);

// Recupera hechos. Si query != "", rankea por solapamiento de keywords;
// si scope != "", filtra por capa. Devuelve top-k formateado (markdown).
QString recall(const QString &cwd, const QString &query, const QString &scope, int k);

}  // namespace MemoryStore
