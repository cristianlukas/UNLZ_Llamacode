import QtQuick
import "MonitorFormat.js" as Fmt

// MonitorFormat.js: formato de números y reparto de las barras del Monitor.
QtObject {
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }
    function near(a, b) { return Math.abs(a - b) < 1e-6 }

    Component.onCompleted: {
        check(Fmt.num(43.84, 1, ",") === "43,8", "decimal con coma")
        check(Fmt.num(43.84, 1, ".") === "43.8", "decimal con punto")
        check(Fmt.num(-1, 1, ",") === "—", "negativo = sin dato")
        check(Fmt.num(undefined, 1, ",") === "—", "undefined = sin dato")
        check(Fmt.int(262144, ".") === "262.144", "miles con punto")
        check(Fmt.int(2716, ",") === "2,716", "miles con coma")
        check(Fmt.int(999, ".") === "999", "sin separador bajo mil")
        check(Fmt.gb(24064, ",") === "23,5", "MB a GB")
        check(Fmt.seconds(500, ",") === "<1 s" && Fmt.seconds(6500, ",") === "6,5 s"
              && Fmt.seconds(-1, ",") === "—", "duraciones")
        check(Fmt.stateLabel("writing") === "Escribiendo" && Fmt.stateLabel("reading") === "Leyendo el prompt"
              && Fmt.stateLabel("whatever") === "Sin servidor", "etiquetas de estado")
        check(Fmt.stateBusy("writing") && !Fmt.stateBusy("idle"), "estados ocupados")

        // GPU con datos por proceso: aparece "Otros programas".
        const g = { totalMb: 24576, usedMb: 20000, weightsMb: 8000, kvMb: 2000,
                    computeMb: 600, restMb: 7900, othersMb: 1500, othersKnown: true }
        const segs = Fmt.gpuSegments(g)
        check(segs.length === 5 && segs[4].key === "others", "cinco segmentos con otros programas")
        check(near(segs[0].frac, 8000 / 24576), "fracción de pesos sobre el total")
        check(segs[1].color === Fmt.colors.kv, "color fijo por tipo")
        // Sin datos por proceso: sin "Otros programas".
        g.othersKnown = false
        check(Fmt.gpuSegments(g).length === 4, "sin otros programas en WDDM")
        // El log reporta más que lo usado: se escala a lo usado.
        const over = Fmt.gpuSegments({ totalMb: 1000, usedMb: 500, weightsMb: 800, kvMb: 200,
                                       computeMb: 0, restMb: 0, othersKnown: false })
        let sum = 0
        for (let i = 0; i < over.length; ++i) sum += over[i].mb
        check(near(sum, 500), "recorta los segmentos a la memoria usada")

        const totals = Fmt.gpuTotals([
            { totalMb: 24576, usedMb: 20000, weightsMb: 8000, kvMb: 100, computeMb: 0, restMb: 0, othersKnown: false },
            { totalMb: 24576, usedMb: 23000, weightsMb: 9000, kvMb: 100, computeMb: 0, restMb: 0, othersKnown: true, othersMb: 50 }
        ])
        check(totals[0].key === "weights" && totals[0].mb === 17000, "suma pesos de todas las GPUs")
        check(totals[totals.length - 1].key === "free" && totals[totals.length - 1].mb === 6152, "libre total")
        check(totals.some(t => t.key === "others"), "otros programas si alguna GPU los reporta")

        const ctx = Fmt.contextSegments({ nCtx: 1000, prompt: 300, cached: 200, written: 100 })
        check(ctx.length === 3 && ctx[0].tokens === 200 && ctx[1].tokens === 100 && ctx[2].tokens === 100,
              "contexto: reusado, prompt nuevo, escrito")
        check(near(ctx[0].frac, 0.2), "fracción de contexto")
        check(Fmt.contextSegments({ nCtx: 0 }).length === 0, "sin n_ctx no hay barra")
        check(Fmt.maxOf([1, 5, 3]) === 5 && Fmt.maxOf(undefined) === 0, "máximo de una serie")

        console.log(fails === 0 ? "ALL PASS" : ("FAIL count=" + fails))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
