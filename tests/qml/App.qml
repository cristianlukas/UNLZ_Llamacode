pragma Singleton
import QtQuick

// Stub del AppController (context property en el app).
QtObject {
    property int langV: 0
    property var dataLab: null
    property bool serverRunning: false
    property string serverBaseUrl: ""
    property string activeLaunchId: ""
    property bool agentRunning: false
    property var engineeringWorkflows: [
        { id: "qa", name: "QA", description: "pruebas" },
        { id: "review", name: "Review", description: "revisión" }
    ]
    function l(k) { return k }
    function installEngineeringWorkflow(id) { return id === "qa" ? "qa-task" : "" }
}
