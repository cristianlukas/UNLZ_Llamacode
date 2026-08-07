import QtQuick
import "BenchmarkScore.js" as BenchmarkScore

// Regresión "el benchmark termina en vacío": la suite Corta no define criterios
// de aceptación (sólo mide velocidad), así que qualityTotal llega en 0. La tabla
// mostraba "—" EN ROJO, o sea una corrida perfecta se leía como un fallo.
QtObject {
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    Component.onCompleted: {
        // Suite sin criterios (la Corta): completó, no falló, no hay nada que puntuar.
        const sinCriterios = { qualityScore: 0, qualityTotal: 0, failed: false, avgTps: 8.6 }
        check(BenchmarkScore.scoreLabel(sinCriterios, "qualityScore", "qualityTotal") === "sin eval.",
              "Sin criterios dice 'sin eval.' y no un guion mudo")
        check(BenchmarkScore.scoreTone(sinCriterios, "qualityScore", "qualityTotal") === "muted",
              "Sin criterios va en gris, NO en rojo (antes parecia un fallo)")
        check(BenchmarkScore.runStatus(sinCriterios) === "done",
              "Sin criterios el estado sigue siendo 'done'")

        // Suite con criterios: se muestra el score y el tono sale del ratio.
        const bien = { qualityScore: 5, qualityTotal: 5, failed: false }
        check(BenchmarkScore.scoreLabel(bien, "qualityScore", "qualityTotal") === "5/5", "5/5")
        check(BenchmarkScore.scoreTone(bien, "qualityScore", "qualityTotal") === "ok", "5/5 en verde")

        const medio = { qualityScore: 3, qualityTotal: 5, failed: false }
        check(BenchmarkScore.scoreTone(medio, "qualityScore", "qualityTotal") === "warn", "3/5 en amarillo")

        const mal = { qualityScore: 1, qualityTotal: 5, failed: false }
        check(BenchmarkScore.scoreTone(mal, "qualityScore", "qualityTotal") === "error", "1/5 en rojo")

        // Falló de verdad: ahí el badge Fallo/Timeout ya lo dice, la celda no compite.
        const fallo = { qualityScore: 0, qualityTotal: 0, failed: true }
        check(BenchmarkScore.scoreLabel(fallo, "qualityScore", "qualityTotal") === "—",
              "Una corrida fallada no dice 'sin eval.'")
        check(BenchmarkScore.runStatus(fallo) === "failed", "Estado failed")
        const timeout = { qualityScore: 0, qualityTotal: 0, failed: true, timedOut: true }
        check(BenchmarkScore.runStatus(timeout) === "timeout", "Timeout se distingue de failed")

        // Fallback a qualityScore cuando la fila no trae las claves específicas.
        const soloQuality = { qualityScore: 4, qualityTotal: 4, failed: false }
        check(BenchmarkScore.scoreLabel(soloQuality, "finalScore", "finalTotal") === "4/4",
              "Final cae a qualityScore/qualityTotal si no hay claves propias")

        // Orden: las filas sin score van al fondo, no mezcladas con los ceros.
        check(BenchmarkScore.sortKey(sinCriterios, "qualityScore", "qualityTotal") === -1,
              "Sin criterios ordena al fondo")
        check(BenchmarkScore.sortKey(mal, "qualityScore", "qualityTotal") > -1,
              "Un score bajo ordena por encima de 'sin evaluar'")

        console.log(fails === 0 ? "TODO OK" : (fails + " FALLAS"))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
