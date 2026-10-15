import QtQuick
import LlamaCode 1.0

// Carga la NavBar real y mide la fila de "Configuración": el texto tiene que
// quedar centrado verticalmente en la franja de 48 px (quedaba pegado arriba),
// con y sin el botón verde de actualización.
Item {
    id: root
    width: 200
    height: 800
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    function find(item, name) {
        if (!item) return null
        if (item.objectName === name) return item
        const kids = item.children || []
        for (let i = 0; i < kids.length; ++i) {
            const hit = find(kids[i], name)
            if (hit) return hit
        }
        // contentItem/background de los Controls no siempre cuelgan de children.
        if (item.contentItem && item.contentItem !== item) {
            const hit = find(item.contentItem, name)
            if (hit) return hit
        }
        return null
    }

    function checkCentered(label) {
        const row = find(nav, "navSettings")
        const text = find(nav, "navSettingsText")
        check(row !== null && text !== null, label + ": encuentra la fila y el texto")
        if (!row || !text) return
        check(Math.abs(row.height - 48) < 0.5, label + ": la fila mide 48 px (mide " + row.height + ")")
        // Centro del glifo (contentHeight) contra el centro de la fila.
        const p = text.mapToItem(row, 0, 0)
        const glyphTop = p.y + (text.height - text.contentHeight) / 2
        const glyphCenter = glyphTop + text.contentHeight / 2
        check(Math.abs(glyphCenter - row.height / 2) <= 1.5,
              label + ": texto centrado (centro " + glyphCenter.toFixed(1)
              + " vs " + (row.height / 2).toFixed(1) + ")")
        check(p.x >= 15 && p.x <= 17, label + ": margen izquierdo 16 px (es " + p.x + ")")
    }

    NavBar {
        id: nav
        anchors.fill: parent
    }

    Timer {
        interval: 50
        running: true
        onTriggered: {
            root.checkCentered("sin update")
            App.updateAvailable = true
            Qt.callLater(function() {
                root.checkCentered("con botón de update")
                console.log(root.fails === 0 ? "ALL PASS" : ("FAIL count=" + root.fails))
                Qt.exit(root.fails === 0 ? 0 : 1)
            })
        }
    }
}
