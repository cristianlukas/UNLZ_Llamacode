import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0
import "../components/MonitorFormat.js" as Fmt

// Monitor: el modelo, su contexto y esta máquina, en vivo. Todo sale de
// App.monitor (ServerMonitor en C++): /slots de llama-server, el log de carga
// y nvidia-smi / /proc. La página sólo formatea.
Item {
    id: root

    readonly property var m: App.monitor || ({})
    readonly property var hist: m.history || ({})
    readonly property var ctxInfo: m.context || ({})
    readonly property var gpus: m.gpus || []
    readonly property var totals: m.gpuTotals || ({})
    readonly property var sys: m.system || ({})
    readonly property var requests: m.requests || []
    readonly property bool hasData: m.available === true || gpus.length > 0
    readonly property string dp: Qt.locale().decimalPoint
    readonly property string gs: Qt.locale().groupSeparator
    property bool showAllRequests: false
    property bool copied: false

    function n(v, d) { return Fmt.num(v, d, dp) }
    function i(v) { return Fmt.int(v, gs) }

    Timer { id: copiedTimer; interval: 1800; onTriggered: root.copied = false }

    // ── Piezas ────────────────────────────────────────────────────────────
    component Card: Rectangle {
        default property alias content: inner.data
        property int pad: 20
        color: Theme.surfaceBg
        radius: 12
        border.color: Theme.borderColor
        border.width: 1
        implicitHeight: inner.implicitHeight + pad * 2
        ColumnLayout {
            id: inner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: parent.pad }
            spacing: 14
        }
    }

    component CardTitle: RowLayout {
        id: cardTitle
        property string title
        property string note
        Layout.fillWidth: true
        Text { text: cardTitle.title; color: Theme.textPrimary; font { pixelSize: 15; bold: true } }
        Item { Layout.fillWidth: true }
        Text { text: cardTitle.note; color: Theme.textMuted; font.pixelSize: 12; visible: text.length > 0 }
    }

    component BigStat: Column {
        id: bigStat
        property string caption
        property string value
        property string unit
        property color swatch: "transparent"
        property int size: 30
        spacing: 2
        Row {
            spacing: 6
            Rectangle {
                visible: bigStat.swatch.a > 0
                width: 12; height: 3; radius: 1.5
                anchors.verticalCenter: parent.verticalCenter
                color: bigStat.swatch
            }
            Text { text: bigStat.caption; color: Theme.textMuted; font.pixelSize: 12 }
        }
        Row {
            spacing: 5
            Text {
                id: bigValue
                text: bigStat.value
                color: Theme.textPrimary
                font { pixelSize: bigStat.size; bold: true }
            }
            Text {
                text: bigStat.unit
                color: Theme.textMuted
                font.pixelSize: 13
                anchors.baseline: bigValue.baseline
            }
        }
    }

    component KeyValue: RowLayout {
        id: kv
        property string label
        property string value
        Layout.fillWidth: true
        Text { text: kv.label; color: Theme.textMuted; font.pixelSize: 12; Layout.fillWidth: true }
        Text { text: kv.value; color: Theme.textPrimary; font { pixelSize: 13; bold: true } }
    }

    component StatePill: Rectangle {
        id: pill
        property string status: "none"
        readonly property bool busy: Fmt.stateBusy(status)
        implicitWidth: pillRow.implicitWidth + 20
        implicitHeight: 26
        radius: 13
        color: busy ? Qt.rgba(0.55, 0.49, 0.96, 0.18) : Theme.inputBg
        border.color: busy ? Fmt.colors.decode : Theme.borderColor
        Row {
            id: pillRow
            anchors.centerIn: parent
            spacing: 6
            Rectangle {
                width: 7; height: 7; radius: 3.5
                anchors.verticalCenter: parent.verticalCenter
                color: pill.busy ? Fmt.colors.decode
                     : pill.status === "idle" ? Theme.successText : Theme.textMuted
                SequentialAnimation on opacity {
                    running: pill.busy
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 600 }
                    NumberAnimation { to: 1.0; duration: 600 }
                }
            }
            Text {
                text: Fmt.stateLabel(pill.status)
                color: pill.busy ? Fmt.colors.decode : Theme.textSecondary
                font { pixelSize: 12; bold: true }
            }
        }
    }

    component Legend: Row {
        id: legend
        property color swatch
        property string label
        property string value
        property bool hollow: false
        spacing: 6
        Rectangle {
            width: 10; height: 10; radius: 2
            anchors.verticalCenter: parent.verticalCenter
            color: legend.hollow ? "transparent" : legend.swatch
            border.color: legend.hollow ? Theme.textMuted : "transparent"
        }
        Text { text: legend.label; color: Theme.textSecondary; font.pixelSize: 12 }
        Text { text: legend.value; color: Theme.textPrimary; font { pixelSize: 12; bold: true } }
    }

    component Tile: Rectangle {
        id: tile
        property string caption
        property string value
        property string unit
        property string sub
        property var series: []
        property real seriesMax: 0
        property color lineColor: Fmt.colors.decode
        color: Theme.inputBg
        radius: 10
        border.color: Theme.borderColor
        implicitHeight: 138
        ColumnLayout {
            anchors { fill: parent; margins: 14 }
            spacing: 4
            Text { text: tile.caption; color: Theme.textMuted; font.pixelSize: 12 }
            Row {
                spacing: 4
                Text { id: tileValue; text: tile.value; color: Theme.textPrimary; font { pixelSize: 22; bold: true } }
                Text {
                    text: tile.unit
                    color: Theme.textMuted; font.pixelSize: 12
                    anchors.baseline: tileValue.baseline
                }
            }
            Text {
                text: tile.sub
                color: Theme.textMuted; font.pixelSize: 11
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Item { Layout.fillHeight: true }
            LcSparkline {
                Layout.fillWidth: true
                Layout.preferredHeight: 30
                values: tile.series
                maxValue: tile.seriesMax
                lineColor: tile.lineColor
            }
        }
    }

    // ── Página ────────────────────────────────────────────────────────────
    PageHeader {
        id: header
        anchors { left: parent.left; right: parent.right; top: parent.top }
        title: "Monitor"
        subtitle: "El modelo, su contexto y esta máquina, en vivo."
        actionLabel: root.copied ? "Copiado ✓" : "Copiar reporte"
        actionEnabled: root.hasData
        onActionClicked: {
            App.copyMonitorReport()
            root.copied = true
            copiedTimer.restart()
        }
    }

    Flickable {
        id: flick
        anchors { left: parent.left; right: parent.right; top: header.bottom; bottom: parent.bottom }
        contentWidth: width
        contentHeight: body.implicitHeight + 48
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: LcScrollBar {}

        ColumnLayout {
            id: body
            width: Math.min(flick.width - 48, 1240)
            x: (flick.width - width) / 2
            y: 24
            spacing: 18

            // Sin servidor: qué muestra esto y cómo verlo.
            Card {
                Layout.fillWidth: true
                visible: !root.hasData
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.textSecondary
                    font.pixelSize: 13
                    text: "Iniciá un servidor desde Lanzar para ver acá la velocidad de lectura y escritura, "
                        + "cuánto contexto ocupa el request, qué llena cada GPU y los últimos requests."
                }
            }

            // ── Velocidad + ahora mismo ──────────────────────────────────
            GridLayout {
                Layout.fillWidth: true
                visible: root.hasData
                columns: body.width > 900 ? 2 : 1
                columnSpacing: 18
                rowSpacing: 18

                Card {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 760
                    Layout.fillHeight: true

                    Flow {
                        Layout.fillWidth: true
                        spacing: 36
                        BigStat {
                            caption: Fmt.decodeCaption(root.m.state)
                            swatch: Fmt.colors.decode
                            value: root.n(root.m.decodeTps, 1)
                            unit: "tok/s"
                            size: 40
                        }
                        BigStat {
                            caption: "Prefill · lectura"
                            swatch: Fmt.colors.prefill
                            value: (root.m.prefillTps || 0) > 0 ? root.n(root.m.prefillTps, 0) : "—"
                            unit: "tok/s"
                        }
                        BigStat {
                            caption: "Pico decode" + ((root.m.peakDecodeAt || 0) > 0
                                ? " · " + Qt.formatTime(new Date(root.m.peakDecodeAt), "HH:mm") : "")
                            value: (root.m.peakDecodeTps || 0) > 0 ? root.n(root.m.peakDecodeTps, 1) : "—"
                            unit: "tok/s"
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        LcSparkline {
                            anchors.fill: parent
                            values: root.hist.prefill || []
                            lineColor: Fmt.colors.prefill
                            fillOpacity: 0.08
                            maxValue: Fmt.maxOf(root.hist.prefill)
                        }
                        LcSparkline {
                            anchors.fill: parent
                            values: root.hist.decode || []
                            lineColor: Fmt.colors.decode
                            fillOpacity: 0.22
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 4
                        columnSpacing: 12
                        BigStat {
                            Layout.fillWidth: true
                            caption: "Tiempo por token"; size: 20
                            value: root.n(root.m.msPerToken, 1); unit: "ms"
                        }
                        BigStat {
                            Layout.fillWidth: true
                            caption: "Prompt reusado de caché"; size: 20
                            value: root.n(root.m.cacheReusePct, 1); unit: "%"
                        }
                        BigStat {
                            Layout.fillWidth: true
                            caption: "Requests vistos"; size: 20
                            value: root.i(root.m.requestsServed || 0)
                        }
                        BigStat {
                            Layout.fillWidth: true
                            // Con MTP/draft, lo que importa es cuánto del borrador se acepta.
                            readonly property bool hasAcc: (root.m.draftAcceptancePct ?? -1) >= 0
                            caption: hasAcc ? "Draft aceptado" : "Especulación"; size: 20
                            value: hasAcc ? root.n(root.m.draftAcceptancePct, 1)
                                          : (root.m.speculative ? "Activa" : "Off")
                            unit: hasAcc ? "%" : ""
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 380
                    Layout.fillHeight: true

                    Text { text: "Ahora mismo"; color: Theme.textPrimary; font { pixelSize: 15; bold: true } }
                    RowLayout {
                        spacing: 10
                        StatePill { status: root.m.state || "none" }
                        Text {
                            visible: (root.ctxInfo.prompt || 0) > 0
                            text: root.i(root.ctxInfo.prompt) + " tokens de prompt"
                            color: Theme.textSecondary; font.pixelSize: 13
                        }
                    }
                    KeyValue { label: "Reusados de la caché"; value: root.i(root.ctxInfo.cached || 0) + " tokens" }
                    KeyValue { label: "Escritos en este request"; value: root.i(root.ctxInfo.written || 0) }
                    KeyValue { label: "Respondiendo a la vez"; value: root.i(root.m.processing || 0) + " de " + root.i(root.m.slots || 0) }
                    KeyValue {
                        label: "En espera"
                        value: (root.m.deferred ?? -1) < 0 ? "—" : (root.m.deferred === 0 ? "ninguno" : root.i(root.m.deferred))
                    }
                    KeyValue { label: "Modelo"; value: root.m.model || "—" }
                }
            }

            // ── Contexto ─────────────────────────────────────────────────
            Card {
                Layout.fillWidth: true
                visible: root.hasData && (root.ctxInfo.nCtx || 0) > 0
                CardTitle {
                    title: "Contexto"
                    note: root.ctxInfo.active ? "el request que se está respondiendo" : "el último request"
                }
                Row {
                    spacing: 8
                    Text { id: ctxBig; text: root.i(root.ctxInfo.used || 0); color: Theme.textPrimary; font { pixelSize: 30; bold: true } }
                    Text {
                        anchors.baseline: ctxBig.baseline
                        text: "/ " + root.i(root.ctxInfo.nCtx) + " tokens"
                        color: Theme.textMuted; font.pixelSize: 14
                    }
                    Text {
                        anchors.baseline: ctxBig.baseline
                        leftPadding: 10
                        text: root.n(root.ctxInfo.pct || 0, 1) + " % usado · "
                              + root.i(Math.max(0, (root.ctxInfo.nCtx || 0) - (root.ctxInfo.used || 0))) + " libres"
                        color: Theme.textSecondary; font.pixelSize: 13
                    }
                }
                Rectangle {
                    id: ctxBar
                    Layout.fillWidth: true
                    height: 12; radius: 6
                    color: Theme.inputBg
                    clip: true
                    Row {
                        height: parent.height
                        Repeater {
                            model: Fmt.contextSegments(root.ctxInfo)
                            Rectangle {
                                required property var modelData
                                height: ctxBar.height
                                width: Math.max(modelData.tokens > 0 ? 3 : 0, ctxBar.width * modelData.frac)
                                color: modelData.color
                                Behavior on width { NumberAnimation { duration: 300 } }
                            }
                        }
                    }
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 18
                    Repeater {
                        model: Fmt.contextSegments(root.ctxInfo)
                        Legend {
                            required property var modelData
                            swatch: modelData.color; label: modelData.label; value: root.i(modelData.tokens)
                        }
                    }
                    Legend {
                        hollow: true; label: "Libre"
                        value: root.i(Math.max(0, (root.ctxInfo.nCtx || 0) - (root.ctxInfo.used || 0)))
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    color: Theme.inputBg
                    radius: 8
                    implicitHeight: ctxHelp.implicitHeight + 20
                    Text {
                        id: ctxHelp
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 12 }
                        wrapMode: Text.WordWrap
                        color: Theme.textSecondary
                        font.pixelSize: 12
                        text: "Lo que el modelo tiene presente a la vez: el chat, sus archivos y los resultados de tools. "
                            + "Un chat más largo que esto se recorta o falla: empezá uno nuevo o subí el contexto (-c) del perfil en Perfiles. "
                            + "Lo reusado de caché no se vuelve a leer: por eso un prompt largo que repite el anterior responde rápido."
                    }
                }
            }

            // ── Qué llena las GPUs ───────────────────────────────────────
            Card {
                Layout.fillWidth: true
                visible: root.gpus.length > 0
                CardTitle {
                    title: "Qué llena las GPUs"
                    note: root.gpus.length + (root.gpus.length === 1 ? " GPU · " : " GPUs · ")
                          + Fmt.gb(root.totals.usedMb || 0, root.dp) + " de " + Fmt.gb(root.totals.totalMb || 0, root.dp) + " GB en uso"
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 18
                    Repeater {
                        model: Fmt.gpuTotals(root.gpus)
                        Legend {
                            required property var modelData
                            swatch: modelData.color || "transparent"
                            hollow: modelData.key === "free"
                            label: modelData.label
                            value: Fmt.gb(modelData.mb, root.dp) + " GB"
                        }
                    }
                }
                Repeater {
                    model: root.gpus
                    delegate: RowLayout {
                        id: gpuRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 16
                        Column {
                            Layout.preferredWidth: 170
                            Text { text: "GPU " + gpuRow.modelData.index; color: Theme.textPrimary; font { pixelSize: 13; bold: true } }
                            Text {
                                width: 170
                                text: String(gpuRow.modelData.name || "").replace(/^NVIDIA (GeForce )?/, "")
                                color: Theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Rectangle {
                                id: gpuBar
                                Layout.fillWidth: true
                                height: 16; radius: 5
                                color: Theme.inputBg
                                clip: true
                                Row {
                                    height: parent.height
                                    Repeater {
                                        model: Fmt.gpuSegments(gpuRow.modelData)
                                        Rectangle {
                                            required property var modelData
                                            height: gpuBar.height
                                            width: gpuBar.width * modelData.frac
                                            color: modelData.color
                                            Behavior on width { NumberAnimation { duration: 400 } }
                                            ToolTip.visible: segHover.hovered
                                            ToolTip.text: modelData.label + ": " + Fmt.gb(modelData.mb, root.dp) + " GB"
                                            HoverHandler { id: segHover }
                                        }
                                    }
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                                color: Theme.textMuted
                                font.pixelSize: 11
                                textFormat: Text.StyledText
                                readonly property var g: gpuRow.modelData
                                text: [
                                    (g.util ?? -1) >= 0 ? "<b>" + Math.round(g.util) + " %</b> carga" : "",
                                    (g.limitW || 0) > 0 ? "<b>" + Math.round(g.drawW) + "</b> / " + Math.round(g.limitW) + " W" : "",
                                    (g.tempC ?? -1) >= 0 ? "<b>" + Math.round(g.tempC) + " °C</b>" : "",
                                    (g.pcieGen ?? -1) > 0 ? "PCIe <b>Gen" + g.pcieGen + "</b> x" + g.pcieWidth : ""
                                ].filter(s => s.length > 0).join("  ·  ")
                            }
                        }
                        Row {
                            Layout.preferredWidth: 110
                            layoutDirection: Qt.RightToLeft
                            spacing: 4
                            Text { text: "/ " + Math.round(gpuRow.modelData.totalMb / 1024) + " GB"; color: Theme.textMuted; font.pixelSize: 12; anchors.baseline: usedTxt.baseline }
                            Text { id: usedTxt; text: Fmt.gb(gpuRow.modelData.usedMb, root.dp); color: Theme.textPrimary; font { pixelSize: 15; bold: true } }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: Fmt.gpuTotals(root.gpus)[0].mb <= 0
                    wrapMode: Text.WordWrap
                    color: Theme.textMuted
                    font.pixelSize: 11
                    text: "Pesos, KV y activaciones salen del log de carga de llama-server. Este build no los informa "
                        + "con la verbosidad por defecto, así que todo lo del servidor figura como «CUDA y resto»."
                }
            }

            // ── Hardware ─────────────────────────────────────────────────
            Text {
                visible: root.hasData
                text: "Hardware"
                color: Theme.textPrimary
                font { pixelSize: 15; bold: true }
                Layout.topMargin: 4
            }
            GridLayout {
                Layout.fillWidth: true
                visible: root.hasData
                columns: body.width > 1000 ? 4 : body.width > 560 ? 2 : 1
                columnSpacing: 14
                rowSpacing: 14

                Tile {
                    Layout.fillWidth: true
                    visible: root.gpus.length > 0
                    caption: "GPU activa"
                    value: Math.round(Math.max(0, root.totals.utilPct ?? 0)); unit: "%"
                    sub: root.gpus.length > 1 ? "promedio de " + root.gpus.length + " placas" : "uso del motor de cómputo"
                    series: root.hist.gpuUtil || []; seriesMax: 100
                }
                Tile {
                    Layout.fillWidth: true
                    visible: root.gpus.length > 0
                    caption: "VRAM"
                    value: Fmt.gb(root.totals.usedMb || 0, root.dp)
                    unit: "/ " + Math.round((root.totals.totalMb || 0) / 1024) + " GB"
                    sub: root.n(root.totals.pct || 0, 0) + " % ocupado"
                    series: root.hist.vramGb || []; seriesMax: (root.totals.totalMb || 0) / 1024
                    lineColor: Fmt.colors.decode
                }
                Tile {
                    Layout.fillWidth: true
                    visible: (root.totals.limitW || 0) > 0
                    caption: "Potencia"
                    value: Math.round(root.totals.drawW || 0); unit: "W"
                    sub: "de " + Math.round(root.totals.limitW || 0) + " W de límite"
                    series: root.hist.powerW || []; seriesMax: root.totals.limitW || 0
                }
                Tile {
                    Layout.fillWidth: true
                    visible: (root.totals.maxTempC ?? -1) >= 0
                    caption: "Temperatura GPU"
                    value: Math.round(root.totals.maxTempC ?? 0); unit: "°C"
                    sub: root.gpus.length > 1 ? "la más caliente de " + root.gpus.length : "núcleo"
                    series: root.hist.tempC || []; seriesMax: 100
                    lineColor: Fmt.colors.compute
                }
                Tile {
                    Layout.fillWidth: true
                    visible: root.gpus.length > 0 && (root.gpus[0].pcieGen ?? -1) > 0
                    caption: "PCIe"
                    value: root.gpus.length > 0 ? "Gen" + root.gpus[0].pcieGen : "—"
                    unit: root.gpus.length > 0 ? "x" + root.gpus[0].pcieWidth : ""
                    sub: "enlace actual (baja en reposo)"
                    series: []
                }
                Tile {
                    Layout.fillWidth: true
                    visible: (root.sys.cpuPct ?? -1) >= 0
                    caption: "CPU"
                    value: Math.round(root.sys.cpuPct ?? 0); unit: "%"
                    sub: (root.sys.threads || 0) + " hilos"
                    series: root.hist.cpu || []; seriesMax: 100
                    lineColor: Fmt.colors.prefill
                }
                Tile {
                    Layout.fillWidth: true
                    visible: (root.sys.ramTotalGb ?? -1) > 0
                    caption: "RAM del sistema"
                    value: root.n(root.sys.ramUsedGb, 1)
                    unit: "/ " + Math.round(root.sys.ramTotalGb || 0) + " GB"
                    sub: "en uso (sin caché de disco)"
                    series: root.hist.ramGb || []; seriesMax: root.sys.ramTotalGb || 0
                    lineColor: Fmt.colors.prefill
                }
                Tile {
                    Layout.fillWidth: true
                    visible: (root.sys.diskReadMBs ?? -1) >= 0
                    caption: "Lectura de disco"
                    value: root.n(root.sys.diskReadMBs, 1); unit: "MB/s"
                    sub: "escritura " + root.n(root.sys.diskWriteMBs, 1) + " MB/s"
                    series: root.hist.diskRead || []
                    lineColor: Fmt.colors.prefill
                }
            }

            // ── Requests recientes ───────────────────────────────────────
            Card {
                id: reqCard
                Layout.fillWidth: true
                visible: root.hasData
                readonly property var cols: [
                    { title: "Hora", w: 80, left: true },
                    { title: "Estado", w: 80, left: true },
                    { title: "Prompt", w: 70 }, { title: "Reusado", w: 70 },
                    { title: "Prefill", w: 70 }, { title: "Salida", w: 70 },
                    { title: "Decode", w: 70 }, { title: "Draft", w: 70 },
                    { title: "Contexto", w: 70 }, { title: "Duró", w: 70 }
                ]
                function cellsFor(r) {
                    return [
                        Qt.formatTime(new Date(r.at), "HH:mm:ss"), "Listo",
                        root.i(r.prompt), root.i(r.reused), root.i(r.prefill), root.i(r.output),
                        root.n(r.decodeTps, 1),
                        (r.draftAcceptance ?? -1) >= 0 ? root.n(r.draftAcceptance, 0) + " %" : "—",
                        root.n(r.contextPct, 1) + " %",
                        Fmt.seconds(r.tookMs, root.dp)
                    ]
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Requests recientes"; color: Theme.textPrimary; font { pixelSize: 15; bold: true } }
                    Item { Layout.fillWidth: true }
                    LcButton {
                        visible: root.requests.length > 12
                        secondary: true
                        text: root.showAllRequests ? "Ver menos" : "Ver los " + root.requests.length
                        onClicked: root.showAllRequests = !root.showAllRequests
                    }
                }
                Text {
                    visible: root.requests.length === 0
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.textMuted
                    font.pixelSize: 12
                    text: root.m.available
                          ? "Todavía no terminó ningún request desde que se abrió el monitor."
                          : "Este servidor no expone /slots (cloud, o lanzado con --no-slots): no hay detalle por request."
                }
                Flickable {
                    Layout.fillWidth: true
                    visible: root.requests.length > 0
                    Layout.preferredHeight: reqTable.implicitHeight
                    contentWidth: Math.max(width, reqTable.implicitWidth)
                    contentHeight: reqTable.implicitHeight
                    flickableDirection: Flickable.HorizontalFlick
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true
                    interactive: contentWidth > width

                    Column {
                        id: reqTable
                        width: Math.max(parent.width, implicitWidth)
                        Row {
                            height: 32
                            Repeater {
                                model: reqCard.cols
                                Text {
                                    required property var modelData
                                    width: modelData.w * Math.max(1, reqTable.width / 720)
                                    height: 32
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: modelData.left ? Text.AlignLeft : Text.AlignRight
                                    rightPadding: modelData.left ? 0 : 8
                                    text: modelData.title
                                    color: Theme.textMuted
                                    font.pixelSize: 12
                                }
                            }
                        }
                        Repeater {
                            model: root.showAllRequests ? root.requests : root.requests.slice(0, 12)
                            delegate: Column {
                                id: reqRow
                                required property var modelData
                                readonly property var cells: reqCard.cellsFor(modelData)
                                Rectangle { width: reqTable.width; height: 1; color: Theme.divider }
                                Row {
                                    height: 38
                                    Repeater {
                                        model: reqCard.cols.length
                                        Item {
                                            required property int index
                                            readonly property var col: reqCard.cols[index]
                                            width: col.w * Math.max(1, reqTable.width / 720)
                                            height: 38
                                            Rectangle {
                                                visible: index === 1
                                                anchors.verticalCenter: parent.verticalCenter
                                                width: badge.implicitWidth + 14; height: 20; radius: 5
                                                color: Theme.successBg
                                                Text {
                                                    id: badge
                                                    anchors.centerIn: parent
                                                    text: reqRow.cells[1]
                                                    color: Theme.successText
                                                    font { pixelSize: 11; bold: true }
                                                }
                                            }
                                            Text {
                                                visible: index !== 1
                                                anchors.fill: parent
                                                verticalAlignment: Text.AlignVCenter
                                                horizontalAlignment: col.left ? Text.AlignLeft : Text.AlignRight
                                                rightPadding: col.left ? 0 : 8
                                                text: reqRow.cells[index]
                                                color: Theme.textPrimary
                                                font { pixelSize: 13; bold: index === 6 }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    visible: root.requests.length > 0
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.textDim
                    font.pixelSize: 11
                    text: "Prefill, salida, decode, draft y duración salen del log de llama-server (exactos); "
                        + "lo demás, de /slots cada segundo. Todos los clientes cuentan: chat, agente, gateway LAN y apps externas."
                }
            }
        }
    }
}
