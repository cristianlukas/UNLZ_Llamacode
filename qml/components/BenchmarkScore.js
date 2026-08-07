.pragma library

// Etiqueta y tono de las celdas de score de la tabla de benchmarks.
//
// Vive acá y no inline en BenchmarkPage.qml porque hay un caso que se leía como
// un fallo sin serlo: cuando la suite no define criterios de aceptación (la
// "Corta" mide sólo velocidad), el total llega en 0 y la celda mostraba "—" en
// rojo. Una corrida perfecta parecía rota. Ahora dice "sin eval." en gris.
//
// El tono se devuelve como string ("muted"/"ok"/"warn"/"error") para que esto no
// dependa de Theme y se pueda testear con el runtime `qml` en offscreen.

function scoreValue(row, scoreKey) {
    return row[scoreKey] !== undefined && row[scoreKey] !== null
        ? row[scoreKey]
        : (row.qualityScore !== undefined && row.qualityScore !== null ? row.qualityScore : 0)
}

function scoreTotal(row, totalKey) {
    return row[totalKey] !== undefined && row[totalKey] !== null
        ? row[totalKey]
        : (row.qualityTotal !== undefined && row.qualityTotal !== null ? row.qualityTotal : 0)
}

// "3/5" cuando hay criterios; "sin eval." cuando la suite no puntúa; "—" cuando
// la corrida falló (ahí el badge de Fallo/Timeout ya dice lo que pasó).
function scoreLabel(row, scoreKey, totalKey) {
    const total = scoreTotal(row, totalKey)
    if (total > 0) return scoreValue(row, scoreKey) + "/" + total
    return row.failed ? "—" : "sin eval."
}

function scoreTone(row, scoreKey, totalKey) {
    const total = scoreTotal(row, totalKey)
    if (total <= 0) return "muted"        // sin criterios: NO es un cero
    const ratio = scoreValue(row, scoreKey) / total
    return ratio >= 0.8 ? "ok" : ratio >= 0.5 ? "warn" : "error"
}

// Estado de la corrida en una palabra, para que la fila no dependa de leer el
// score: una corrida sin criterios igual completó.
function runStatus(row) {
    if (row.timedOut) return "timeout"
    if (row.failed) return "failed"
    return "done"
}

// Orden: las filas sin score van al fondo en vez de mezclarse con los ceros.
function sortKey(row, scoreKey, totalKey) {
    const total = scoreTotal(row, totalKey)
    return total > 0 ? scoreValue(row, scoreKey) / total : -1
}
