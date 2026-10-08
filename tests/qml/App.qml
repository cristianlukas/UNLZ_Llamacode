pragma Singleton
import QtQuick

// Stub del AppController (context property en el app).
QtObject {
    property int langV: 0
    property QtObject dataLab: QtObject {
        property var jobs: [{ id: "job-1", name: "Facturas", status: "created" }]
        signal jobChanged(string id)
        signal extractionFinished(string jobId, string documentId, bool ok, string message)
        function job(id) { return { id: id, name: "Facturas", documents: [{ id: "doc-1", path: "factura.txt" }] } }
        function jobMetrics(id) { return { total: 1, extracted: 1, valid: 0, needsReview: 0, failed: 0 } }
        function processJob(id) { return { ok: true, extracted: 1, failed: 0 } }
        function deleteJob(id) { return true }
        function extractionPrompt(jobId, documentId) { return "{}" }
        function validateRecord(jobId, documentId, json) { return { status: "valid", errors: [] } }
        function validateRecords(jobId, documentId, json) { return { status: "valid", records: JSON.parse(json), errors: [] } }
        function exportJob(jobId, path, format) { return path }
        function runExtraction(jobId, documentId, url, model) {}
        function createJob(name, schema, files) { return "job-2" }
    }
    property bool serverRunning: false
    property string serverBaseUrl: ""
    property string activeLaunchId: ""
    property bool agentRunning: false
    property var benchmarkRanking: []
    property QtObject profileManager: QtObject {
        function getLaunchProfile(id) { return { modelProfileId: "model", runtimePresetId: "runtime", backendProfileId: "backend" } }
        function getModelProfile(id) { return { name: "Test model", specType: "none" } }
        function getRuntimePreset(id) { return { name: "Test runtime", ctx: 32768, cacheType: "q8_0" } }
        function getBackend(id) { return { name: "Test backend" } }
    }
    property var engineeringWorkflows: [
        { id: "qa", name: "QA", description: "pruebas" },
        { id: "review", name: "Review", description: "revisión" }
    ]
    function l(k) { return k }
    function readSetting(key, fallback) { return fallback }
    function writeSetting(key, value) {}
    signal benchmarkResultsChanged()
    function installEngineeringWorkflow(id) { return id === "qa" ? "qa-task" : "" }
}
