import QtQuick

Item {
    id: root
    property int selectedPage: 0
    property int loadedCount: 0
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    Loader {
        id: firstPage
        active: root.selectedPage === 0
        sourceComponent: Component { Item {} }
        onLoaded: {
            root.loadedCount++
            // Match Main.qml: pin a page once it has been visited, while keeping
            // the activation binding independent from Loader's loaded state.
            active = true
        }
    }

    Timer {
        interval: 0
        running: true
        onTriggered: {
            root.check(firstPage.status === Loader.Ready, "la página seleccionada se crea")
            root.selectedPage = 1
            Qt.callLater(function() {
                root.selectedPage = 0
                Qt.callLater(function() {
                    root.check(firstPage.active, "la página visitada permanece activa")
                    root.check(root.loadedCount === 1, "volver a la página no la reconstruye")
                    console.log(root.fails === 0 ? "TODO OK" : (root.fails + " FALLAS"))
                    Qt.exit(root.fails === 0 ? 0 : 1)
                })
            })
        }
    }
}
