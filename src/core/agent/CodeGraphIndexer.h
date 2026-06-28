#pragma once
#include <QString>
#include <QStringList>

// INDEXADOR DETERMINISTA repo→[[GraphStore]]. Pasada estilo "Graphify pass-1":
// recorre el árbol del proyecto y, por archivo, extrae sus SÍMBOLOS (clases/
// funciones, vía regex por lenguaje) y sus IMPORTS/INCLUDES, volcándolos como
// entidades + relaciones tipadas:
//   <archivo> -[defines]-> <símbolo>
//   <archivo> -[imports]-> <archivo>   (resuelto por basename dentro del repo)
//
// SIN LLM, idempotente (GraphStore deduplica por nombre normalizado), barato:
// usa GraphStore::addBatch para escribir todo en una sola pasada. Después el
// agente consulta el mapa con la tool 'graph' (action='query') en vez de
// re-leer archivos → contexto barato para el loop ReAct. Complementa la carga
// MANUAL del grafo (link/decide); esto la siembra automáticamente.
namespace CodeGraphIndexer {

struct Stats {
    int files = 0;     // archivos indexados (con extensión soportada)
    int symbols = 0;   // símbolos distintos definidos
    int edges = 0;     // relaciones nuevas escritas (defines + imports)
};

// Indexa 'rootCwd'. 'langs' filtra por familia de lenguaje (vacío = todas las
// soportadas: cpp, qml, js, ts, py). Escribe en GraphStore::jsonlPath(rootCwd).
// Si 'report' != nullptr, deja un resumen markdown apto para devolver a la tool.
Stats build(const QString &rootCwd, const QStringList &langs, QString *report);

}  // namespace CodeGraphIndexer
