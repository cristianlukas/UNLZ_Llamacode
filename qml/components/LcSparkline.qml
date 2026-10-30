import QtQuick

// Línea + área de una serie corta (historial del Monitor). `maxValue` 0 =
// escala automática al máximo de la serie; un techo fijo (100 % de CPU, VRAM
// total) evita que una serie plana se vea como un serrucho.
Canvas {
    id: root
    property var values: []
    property color lineColor: "#8b7cf6"
    property real maxValue: 0
    property real fillOpacity: 0.18
    implicitHeight: 32

    onValuesChanged: requestPaint()
    onLineColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        const ctx = getContext("2d")
        ctx.reset()
        const v = values || []
        if (v.length < 2 || width <= 0 || height <= 0) return
        let top = maxValue
        if (top <= 0) for (let i = 0; i < v.length; ++i) top = Math.max(top, Number(v[i]) || 0)
        if (top <= 0) top = 1
        const pad = 1.5
        const h = height - pad * 2
        const step = width / (v.length - 1)
        const y = i => pad + h - Math.min(1, Math.max(0, (Number(v[i]) || 0) / top)) * h

        ctx.beginPath()
        ctx.moveTo(0, y(0))
        for (let i = 1; i < v.length; ++i) ctx.lineTo(i * step, y(i))
        ctx.lineWidth = 1.5
        ctx.lineJoin = "round"
        ctx.strokeStyle = lineColor
        ctx.stroke()

        ctx.lineTo(width, height)
        ctx.lineTo(0, height)
        ctx.closePath()
        ctx.fillStyle = Qt.rgba(lineColor.r, lineColor.g, lineColor.b, fillOpacity)
        ctx.fill()
    }
}
