#pragma once
#include <QString>

// KNOWLEDGE GRAPH liviano para el agente. Entidades + relaciones tipadas,
// persistidas como JSONL en <cwd>/.llamacode/graph.jsonl (un objeto por línea).
// Complementa la memoria atómica de [[MemoryStore]]: ahí guardamos hechos sueltos,
// acá guardamos CÓMO se conectan (entidad -[predicado]-> entidad).
//
// Cada línea es uno de dos tipos:
//   {"kind":"entity","id":..,"name":..,"etype":..,"ts":..}
//   {"kind":"relation","id":..,"subj":<entId>,"pred":..,"obj":<entId>,"ts":..}
// Entidades se identifican por nombre NORMALIZADO (lowercase/trim) → id estable.
// etype: file|module|decision|bug|person|concept|other.
namespace GraphStore {

QString jsonlPath(const QString &cwd);

// Crea/asegura una entidad por nombre. Devuelve estado (incluye su id).
QString addEntity(const QString &cwd, const QString &name, const QString &etype);

// Crea una relación subj -[pred]-> obj (auto-crea las entidades por nombre).
QString link(const QString &cwd, const QString &subj, const QString &pred,
             const QString &obj);

// Consulta el vecindario de una entidad por nombre. depth=1 (default) o 2
// (graph expansion: incluye vecinos de vecinos). Devuelve markdown.
QString query(const QString &cwd, const QString &name, int depth);

}  // namespace GraphStore
