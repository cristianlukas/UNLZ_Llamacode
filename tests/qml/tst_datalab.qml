import QtQuick

QtObject {
    id: test
    property int fails: 0
    QtObject {
        id: fakeDataLab
        property var jobs: [{ id: "job-1", name: "Facturas", status: "created" }]
        signal jobsChanged()
        signal jobChanged(string id)
        signal extractionFinished(string jobId, string documentId, bool ok, string message)
        function job(id) { return { id: id, name: "Facturas", documents: [{ id: "doc-1", path: "factura.txt" }] } }
        function jobMetrics(id) { return { total: 1, extracted: 1, valid: 0, needsReview: 0, failed: 0 } }
        function processJob(id) { return { ok: true, extracted: 1, failed: 0 } }
        function deleteJob(id) { return true }
        function extractionPrompt(jobId, documentId) { return "{}" }
        function validateRecord(jobId, documentId, json) { return { status: "valid", errors: [] } }
        function runExtraction(jobId, documentId, url, model) {}
        function createJob(name, schema, files) { return "job-2" }
    }
    Component.onCompleted: {
        App.dataLab = fakeDataLab
        const component = Qt.createComponent("DataLabPage.qml")
        if (component.status !== Component.Ready) {
            console.log("FAIL DataLabPage no carga: " + component.errorString())
            Qt.exit(1)
            return
        }
        const page = component.createObject(null)
        if (!page) { console.log("FAIL DataLabPage no instancia"); Qt.exit(1); return }
        if (page.selectedJobId !== "job-1") { console.log("FAIL seleccion inicial"); fails++ }
        if (page.selectedDocumentId !== "doc-1") { console.log("FAIL documento inicial"); fails++ }
        page.destroy()
        console.log(fails === 0 ? "TODO OK" : (fails + " FALLAS"))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
