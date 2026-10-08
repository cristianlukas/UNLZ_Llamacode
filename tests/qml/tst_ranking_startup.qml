import QtQuick
import LlamaCode 1.0

Item {
    id: test
    property int fails: 0
    property var pageUnderTest: null

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    Component.onCompleted: {
        const component = Qt.createComponent("pages/RankingPage.qml")
        if (component.status !== Component.Ready) {
            console.log("FAIL RankingPage no carga: " + component.errorString())
            Qt.exit(1)
            return
        }
        App.benchmarkRanking = [{
            profileId: "launch-1", profileName: "Perfil de prueba", target: "model",
            he0Has: true, he0Result: { qualityScore: 1, qualityTotal: 1, failed: false },
            he20Has: false, bcbHas: false
        }]
        pageUnderTest = component.createObject(test, { width: 1200, height: 700 })
        if (!pageUnderTest) {
            console.log("FAIL RankingPage no instancia")
            Qt.exit(1)
            return
        }
        pageUnderTest.rebuildRows()
    }

    Timer {
        interval: 300
        running: true
        onTriggered: {
            test.check(test.pageUnderTest && test.pageUnderTest.displayedRows.length === 1,
                       "la tabla procesa la fila de ranking")
            if (test.pageUnderTest) test.pageUnderTest.destroy()
            console.log(test.fails === 0 ? "TODO OK" : (test.fails + " FALLAS"))
            Qt.exit(test.fails === 0 ? 0 : 1)
        }
    }
}
