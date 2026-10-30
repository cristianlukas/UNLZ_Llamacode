.pragma library

// Formato y reparto de la pantalla Monitor. Puro (sin App/Theme): lo prueba
// tests/qml/tst_monitor_format.qml. Los separadores se pasan para que el test
// no dependa del locale de la máquina; la página usa los de Qt.locale().

// Colores de las series. Fijos (no del tema) para que "pesos" o "KV" sean el
// mismo color en cualquier tema y en el reporte.
var colors = {
    weights: "#4f86f7",
    kv: "#1fae7a",
    compute: "#e3a008",
    rest: "#7b8190",
    others: "#e5603e",
    decode: "#8b7cf6",
    prefill: "#22b8cf",
    reused: "#3d6fd6",
    prompt: "#22b8cf",
    written: "#1fae7a"
}

function num(v, decimals, decimalPoint) {
    if (v === undefined || v === null || isNaN(v) || v < 0) return "—"
    var s = Number(v).toFixed(decimals)
    return decimalPoint && decimalPoint !== "." ? s.replace(".", decimalPoint) : s
}

function int(v, groupSeparator) {
    if (v === undefined || v === null || isNaN(v) || v < 0) return "—"
    var s = String(Math.round(v))
    var sep = groupSeparator === undefined ? "." : groupSeparator
    return s.replace(/\B(?=(\d{3})+(?!\d))/g, sep)
}

function gb(mb, decimalPoint) {
    return num(mb / 1024, 1, decimalPoint)
}

function seconds(ms, decimalPoint) {
    if (ms === undefined || ms < 0) return "—"
    if (ms < 1000) return "<1 s"
    return num(ms / 1000, 1, decimalPoint) + " s"
}

function stateLabel(state) {
    switch (state) {
    case "writing": return "Escribiendo"
    case "reading": return "Leyendo el prompt"
    case "idle": return "Libre"
    case "loading": return "Cargando"
    case "stopped": return "Detenido"
    case "unknown": return "En vivo"
    default: return "Sin servidor"
    }
}

// Qué está haciendo el número grande de decode ("escribiendo", "último pico"...).
function decodeCaption(state) {
    if (state === "writing") return "Decode · escribiendo ahora"
    if (state === "reading") return "Decode · leyendo el prompt"
    return "Decode"
}

function stateBusy(state) {
    return state === "writing" || state === "reading" || state === "loading"
}

// Segmentos de la barra de una GPU, en orden, con MB y fracción del total.
// "Otros programas" sólo aparece si nvidia-smi dio la memoria por proceso.
function gpuSegments(g) {
    var total = Number(g.totalMb) || 0
    var used = Number(g.usedMb) || 0
    var segs = [
        { key: "weights", label: "Pesos del modelo", mb: Number(g.weightsMb) || 0 },
        { key: "kv", label: "Caché KV", mb: Number(g.kvMb) || 0 },
        { key: "compute", label: "Activaciones", mb: Number(g.computeMb) || 0 },
        { key: "rest", label: "CUDA y resto", mb: Number(g.restMb) || 0 }
    ]
    if (g.othersKnown) segs.push({ key: "others", label: "Otros programas", mb: Number(g.othersMb) || 0 })
    // Si el log reportó más de lo que nvidia-smi ve usado (otra GPU con el
    // mismo índice, o el log de un server anterior), se recorta a lo usado.
    var sum = 0
    for (var i = 0; i < segs.length; ++i) sum += segs[i].mb
    if (sum > used && sum > 0) {
        for (var j = 0; j < segs.length; ++j) segs[j].mb = segs[j].mb * used / sum
    }
    var out = []
    for (var k = 0; k < segs.length; ++k) {
        var s = segs[k]
        s.color = colors[s.key]
        s.frac = total > 0 ? s.mb / total : 0
        out.push(s)
    }
    return out
}

// Totales por tipo sobre todas las GPUs, para la leyenda.
function gpuTotals(gpus) {
    var keys = ["weights", "kv", "compute", "rest", "others"]
    var labels = { weights: "Pesos del modelo", kv: "Caché KV", compute: "Activaciones",
                   rest: "CUDA y resto", others: "Otros programas" }
    var sums = {}, othersKnown = false, free = 0
    for (var i = 0; i < gpus.length; ++i) {
        var segs = gpuSegments(gpus[i])
        if (gpus[i].othersKnown) othersKnown = true
        free += Math.max(0, Number(gpus[i].totalMb) - Number(gpus[i].usedMb))
        for (var j = 0; j < segs.length; ++j)
            sums[segs[j].key] = (sums[segs[j].key] || 0) + segs[j].mb
    }
    var out = []
    for (var k = 0; k < keys.length; ++k) {
        if (keys[k] === "others" && !othersKnown) continue
        out.push({ key: keys[k], label: labels[keys[k]], mb: sums[keys[k]] || 0, color: colors[keys[k]] })
    }
    out.push({ key: "free", label: "Libre", mb: free, color: "" })
    return out
}

// Contexto: reusado de caché, prompt nuevo, escrito, libre (fracciones de n_ctx).
function contextSegments(ctx) {
    var n = Number(ctx.nCtx) || 0
    if (n <= 0) return []
    var cached = Math.min(Number(ctx.cached) || 0, Number(ctx.prompt) || 0)
    var fresh = Math.max(0, (Number(ctx.prompt) || 0) - cached)
    var written = Number(ctx.written) || 0
    return [
        { key: "reused", label: "Reusado de caché", tokens: cached, frac: cached / n, color: colors.reused },
        { key: "prompt", label: "Prompt nuevo", tokens: fresh, frac: fresh / n, color: colors.prompt },
        { key: "written", label: "Escrito", tokens: written, frac: written / n, color: colors.written }
    ]
}

function maxOf(values) {
    var m = 0
    for (var i = 0; i < (values ? values.length : 0); ++i) m = Math.max(m, Number(values[i]) || 0)
    return m
}
