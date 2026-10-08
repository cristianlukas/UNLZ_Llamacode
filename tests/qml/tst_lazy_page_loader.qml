import QtQuick

Item {
    id: root
    property int selectedPage: 0
    property int loadedCount: 0
    property int fails: 0
    property bool returnedToFirstPage: false

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    Loader {
        id: firstPage
        active: root.selectedPage === 0
        asynchronous: true
        source: Qt.resolvedUrl("LazyProbePage.qml")
        onLoaded: {
            root.loadedCount++
            // Match Main.qml: pin a page once it has been visited, while keeping
            // the activation binding independent from Loader's loaded state.
            active = true
        }
    }

    Timer {
        interval: 10
        repeat: true
        running: true
        onTriggered: {
            if (firstPage.status !== Loader.Ready || root.loadedCount === 0)
                return
            if (!root.returnedToFirstPage) {
                root.check(firstPage.item.marker === "lazy-page-ready",
                           "la página asíncrona seleccionada se crea desde URL")
                root.selectedPage = 1
                root.returnedToFirstPage = true
                Qt.callLater(function() { root.selectedPage = 0 })
                return
            }
            root.check(firstPage.active, "la página visitada permanece activa")
            root.check(root.loadedCount === 1, "volver a la página no la reconstruye")
            console.log(root.fails === 0 ? "TODO OK" : (root.fails + " FALLAS"))
            Qt.exit(root.fails === 0 ? 0 : 1)
            running = false
        }
    }
}
