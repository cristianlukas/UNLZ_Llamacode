import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0
import "../components/BenchmarkScore.js" as BenchmarkScore

Item {
    id: root

    property string sortColumn: "profile"
    property int sortDirection: 1
    property string targetFilter: "Todos"
    property bool onlyComplete: false

    readonly property var columns: [
        { key: "profile", title: "Perfil", width: 250 },
        { key: "target", title: "Modo", width: 72 },
        { key: "agent", title: "Nivel", width: 125 },
        { key: "he0", title: "HE0", width: 86 },
        { key: "he20", title: "HE20", width: 92 },
        { key: "bcb", title: "BCB", width: 86 },
        { key: "he0Time", title: "T HE0", width: 88 },
        { key: "he20Time", title: "T HE20", width: 88 },
        { key: "bcbTime", title: "T BCB", width: 88 },
        { key: "he0Tps", title: "TPS HE0", width: 88 },
        { key: "he20Tps", title: "TPS HE20", width: 94 },
        { key: "bcbTps", title: "TPS BCB", width: 88 },
        { key: "ram", title: "RAM", width: 86 },
        { key: "vram", title: "VRAM", width: 86 },
        { key: "date", title: "Última fecha", width: 112 }
    ]

    function sortIndicator(key) {
        if (sortColumn !== key || sortDirection === 0) return "↕"
        return sortDirection > 0 ? "▲" : "▼"
    }

    function cycleSort(key) {
        if (sortColumn !== key) {
            sortColumn = key
            sortDirection = 1
        } else if (sortDirection === 1) {
            sortDirection = -1
        } else {
            sortColumn = ""
            sortDirection = 0
        }
    }

    function stageRow(row, stage) { return row[stage + "Result"] || ({}) }
    function stageScore(row, stage) {
        return BenchmarkScore.sortKey(stageRow(row, stage), "qualityScore", "qualityTotal")
    }

    function sortValue(row, key) {
        if (key === "profile") return String(row.profileName || "").toLowerCase()
        if (key === "target") return String(row.target || "").toLowerCase()
        if (key === "agent") return String(row.agentProfileName || "").toLowerCase()
        if (key === "he0" || key === "he20" || key === "bcb") return stageScore(row, key)
        if (key === "he0Time") return Number(row.he0ElapsedSec || -1)
        if (key === "he20Time") return Number(row.he20ElapsedSec || -1)
        if (key === "bcbTime") return Number(row.bcbElapsedSec || -1)
        if (key === "he0Tps") return Number(row.he0Tps || -1)
        if (key === "he20Tps") return Number(row.he20Tps || -1)
        if (key === "bcbTps") return Number(row.bcbTps || -1)
        if (key === "ram") return Math.max(Number(row.he0RamMb || 0), Number(row.he20RamMb || 0), Number(row.bcbRamMb || 0))
        if (key === "vram") return Math.max(Number(row.he0VramMb || 0), Number(row.he20VramMb || 0), Number(row.bcbVramMb || 0))
        if (key === "date") return Number(row.latestTimestamp || 0)
        return ""
    }

    function rows() {
        const source = App.benchmarkRanking || []
        const filtered = []
        for (let i = 0; i < source.length; ++i) {
            const row = source[i]
            if (targetFilter !== "Todos" && String(row.target || "").toLowerCase() !== targetFilter)
                continue
            if (onlyComplete && !row.complete) continue
            filtered.push(row)
        }
        if (sortDirection === 0 || sortColumn === "") return filtered
        filtered.sort(function(a, b) {
            const av = sortValue(a, sortColumn), bv = sortValue(b, sortColumn)
            let cmp = 0
            if (typeof av === "number" && typeof bv === "number")
                cmp = av === bv ? 0 : (av < bv ? -1 : 1)
            else
                cmp = String(av).localeCompare(String(bv))
            if (cmp === 0) cmp = String(a.profileName || "").localeCompare(String(b.profileName || ""))
            return sortDirection > 0 ? cmp : -cmp
        })
        return filtered
    }

    function scoreText(row, stage) {
        if (!row[stage + "Has"]) return "—"
        const r = stageRow(row, stage)
        const status = BenchmarkScore.runStatus(r)
        if (status !== "done") return BenchmarkScore.statusLabel(r)
        return BenchmarkScore.scoreLabel(r, "qualityScore", "qualityTotal")
    }

    function scoreColor(row, stage) {
        if (!row[stage + "Has"]) return Theme.textMuted
        const r = stageRow(row, stage)
        const status = BenchmarkScore.runStatus(r)
        if (status !== "done") return Theme.errorText
        const tone = BenchmarkScore.scoreTone(r, "qualityScore", "qualityTotal")
        return tone === "ok" ? Theme.successText
             : tone === "warn" ? Theme.warnText
             : tone === "muted" ? Theme.textMuted : Theme.errorText
    }

    function seconds(value) { return Number(value || 0) > 0 ? Number(value).toFixed(1) + " s" : "—" }
    function tps(value) { return Number(value || 0) > 0 ? Number(value).toFixed(1) : "—" }
    function memory(value) { return Number(value || 0) > 0 ? Math.round(Number(value)) + " MB" : "—" }
    function date(value) {
        const n = Number(value || 0)
        if (!n) return "—"
        const d = new Date(n < 1000000000000 ? n * 1000 : n)
        return isNaN(d) ? "—" : Qt.formatDate(d, "yyyy-MM-dd")
    }

    function cellText(row, key) {
        if (key === "profile") return String(row.profileName || row.profileId || "—")
        if (key === "target") return String(row.target || "model") === "agent" ? "Agente" : "Chat"
        if (key === "agent") return String(row.agentProfileName || "—")
        if (key === "he0" || key === "he20" || key === "bcb") return scoreText(row, key)
        if (key === "he0Time") return seconds(row.he0ElapsedSec)
        if (key === "he20Time") return seconds(row.he20ElapsedSec)
        if (key === "bcbTime") return seconds(row.bcbElapsedSec)
        if (key === "he0Tps") return tps(row.he0Tps)
        if (key === "he20Tps") return tps(row.he20Tps)
        if (key === "bcbTps") return tps(row.bcbTps)
        if (key === "ram") return memory(Math.max(Number(row.he0RamMb || 0), Number(row.he20RamMb || 0), Number(row.bcbRamMb || 0)))
        if (key === "vram") return memory(Math.max(Number(row.he0VramMb || 0), Number(row.he20VramMb || 0), Number(row.bcbVramMb || 0)))
        if (key === "date") return date(row.latestTimestamp)
        return "—"
    }

    function cellColor(row, key) {
        if (key === "he0" || key === "he20" || key === "bcb") return scoreColor(row, key)
        if (key === "profile") return Theme.textPrimary
        return Theme.textSecondary
    }

    readonly property int tableWidth: {
        let total = 0
        for (let i = 0; i < columns.length; ++i) total += columns[i].width
        return total
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            title: (App.langV, App.l("nav.ranking"))
            subtitle: "Compará las últimas corridas HE0, HE20 y BCB por perfil"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 16
            spacing: 10

            Text {
                text: "RESULTADOS AGRUPADOS"
                color: Theme.textSecondary
                font.pixelSize: 10
                font.bold: true
            }
            LcComboBox {
                id: targetCombo
                Layout.preferredWidth: 130
                model: ["Todos", "model", "agent"]
                currentIndex: targetFilter === "Todos" ? 0 : (targetFilter === "model" ? 1 : 2)
                onActivated: root.targetFilter = currentText
                contentItem: Text {
                    text: targetCombo.displayText === "model" ? "Chat" : targetCombo.displayText === "agent" ? "Agente" : "Todos"
                    color: Theme.textPrimary
                    font.pixelSize: 12
                    leftPadding: 8
                    verticalAlignment: Text.AlignVCenter
                }
            }
            CheckBox {
                id: completeCheck
                text: "Sólo las 3 etapas"
                checked: root.onlyComplete
                onToggled: root.onlyComplete = checked
                contentItem: Text {
                    text: completeCheck.text
                    color: Theme.textPrimary
                    font.pixelSize: 12
                    leftPadding: completeCheck.indicator.width + 6
                    verticalAlignment: Text.AlignVCenter
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: (root.rows().length) + " perfil(es)"
                color: Theme.textMuted
                font.pixelSize: 11
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

        Flickable {
            id: tableFlick
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: root.tableWidth
            contentHeight: tableContent.height
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
            ScrollBar.vertical: LcScrollBar {}

            Column {
                id: tableContent
                width: root.tableWidth
                height: 36 + root.rows().length * 36

                Rectangle {
                    width: root.tableWidth
                    height: 36
                    color: Theme.surfaceBg
                    Row {
                        anchors.fill: parent
                        Repeater {
                            model: root.columns
                            delegate: Item {
                                required property var modelData
                                width: modelData.width
                                height: 36
                                Text {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 5
                                    text: modelData.title + " " + root.sortIndicator(modelData.key)
                                    color: root.sortColumn === modelData.key ? Theme.textPrimary : Theme.textSecondary
                                    font.pixelSize: 11
                                    font.bold: root.sortColumn === modelData.key
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                                TapHandler { onTapped: root.cycleSort(modelData.key) }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                            }
                        }
                    }
                }

                Repeater {
                    model: root.rows()
                    delegate: Rectangle {
                        id: rankingRowDelegate
                        required property var modelData
                        required property int index
                        property var rankingRow: modelData
                        width: root.tableWidth
                        height: 36
                        color: index % 2 ? Theme.baseBg : "transparent"
                        Row {
                            anchors.fill: parent
                            Repeater {
                                model: root.columns
                                delegate: Item {
                                    required property var modelData
                                    width: modelData.width
                                    height: 36
                                    Text {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 5
                                        id: cellTextLabel
                                        text: root.cellText(rankingRowDelegate.rankingRow, modelData.key)
                                        color: root.cellColor(rankingRowDelegate.rankingRow, modelData.key)
                                        font.pixelSize: 11
                                        font.bold: modelData.key === "profile"
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }
                                    ToolTip.visible: cellHover.hovered && cellTextLabel.text.length > 0
                                    ToolTip.text: cellTextLabel.text
                                    HoverHandler { id: cellHover }
                                }
                            }
                        }
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: root.rows().length === 0
                text: "Todavía no hay resultados HE0, HE20 o BCB para mostrar."
                color: Theme.textMuted
                font.pixelSize: 13
            }
        }
    }
}
