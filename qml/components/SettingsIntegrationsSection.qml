import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import LlamaCode 1.0

// Sección "intgSection" de Configuración, extraída de SettingsPage.qml (antes
// 3.500 líneas en un solo archivo). La visibilidad la decide la página.
ColumnLayout {
    id: section
    Layout.fillWidth: true
    spacing: 10

    property var items: []
    property string testMsgId: ""
    property string testMsg: ""
    property bool testOk: false
    function reload() { items = App.integrations() }
    Component.onCompleted: reload()

    Connections {
        target: App
        function onIntegrationsChanged() { section.reload() }
        function onIntegrationTestResult(id, ok, message) {
            section.testMsgId = id; section.testOk = ok; section.testMsg = message
        }
    }

    Text {
        text: (App.langV, App.l("settings.sec.integrations")).toUpperCase()
        color: Theme.accent
        font.pixelSize: 11
        font.bold: true
    }

    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: Theme.borderColor
        radius: 10
        implicitHeight: intgInner.implicitHeight + 32

        ColumnLayout {
            id: intgInner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 14

            Text {
                text: "Conexiones a servicios externos en un solo lugar (MCP + API)."
                color: Theme.textSecondary
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            // Lista de integraciones
            Text {
                visible: section.items.length === 0
                text: "Sin integraciones configuradas."
                color: Theme.textMuted
                font.pixelSize: 12
            }

            Repeater {
                model: section.items
                delegate: Rectangle {
                    Layout.fillWidth: true
                    radius: 8
                    color: Theme.inputBg
                    border.color: Theme.borderColor
                    implicitHeight: rowCol.implicitHeight + 20

                    ColumnLayout {
                        id: rowCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: modelData.type === "mcp" ? "🧩" : "🔌"
                                font.pixelSize: 14
                            }
                            Text {
                                text: modelData.name
                                color: Theme.textPrimary
                                font.pixelSize: 13
                                font.bold: true
                            }
                            Rectangle {
                                radius: 4
                                color: Theme.surfaceBg
                                implicitWidth: tBadge.width + 12
                                implicitHeight: tBadge.height + 6
                                Text {
                                    id: tBadge
                                    anchors.centerIn: parent
                                    text: modelData.type === "mcp" ? "MCP" : "API"
                                    color: Theme.textSecondary
                                    font.pixelSize: 10
                                }
                            }
                            Item { Layout.fillWidth: true }
                            LcSwitch {
                                checked: modelData.enabled
                                onToggled: App.setIntegrationEnabled(modelData.id, checked)
                            }
                            LcButton {
                                text: "Test"
                                secondary: true
                                implicitHeight: 30
                                onClicked: App.testIntegration(modelData.id)
                            }
                            LcButton {
                                text: "✕"
                                danger: true
                                implicitHeight: 30
                                onClicked: App.removeIntegration(modelData.id)
                            }
                        }
                        Text {
                            text: modelData.summary
                            color: Theme.textMuted
                            font.pixelSize: 11
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Text {
                            visible: section.testMsgId === modelData.id && section.testMsg.length > 0
                            text: section.testMsg
                            color: section.testOk ? Theme.accent : Theme.btnDangerBg
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

            // Add integration
            Text {
                text: "Agregar integración"
                color: Theme.textPrimary
                font.pixelSize: 13
                font.bold: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: "Tipo"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: typeCombo
                    Layout.preferredWidth: 200
                    model: [
                        { label: "MCP Tool Server", value: "mcp" },
                        { label: "API Service",     value: "api_service" },
                    ]
                    textRole: "label"
                    valueRole: "value"
                }
            }

            // Campos MCP
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: typeCombo.currentValue === "mcp"
                LcTextField { id: mcpName; Layout.fillWidth: true; placeholderText: "Nombre (ej. filesystem)" }
                LcTextField { id: mcpCmd;  Layout.fillWidth: true; placeholderText: "Comando stdio (ej. npx -y @modelcontextprotocol/server-filesystem .)" }
                LcButton {
                    text: "Agregar MCP"
                    enabled: mcpName.text.trim().length > 0 && mcpCmd.text.trim().length > 0
                    onClicked: {
                        if (App.saveMcpIntegration(mcpName.text.trim(), "local", mcpCmd.text.trim())) {
                            mcpName.text = ""; mcpCmd.text = ""
                        }
                    }
                }
            }

            // Campos API Service
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: typeCombo.currentValue === "api_service"
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Uso"; color: Theme.textSecondary; font.pixelSize: 12 }
                    LcComboBox {
                        id: apiProvider
                        Layout.fillWidth: true
                        model: [
                            { label: "API genérica", value: "generic" },
                            { label: "Camofox (web_fetch opcional)", value: "camofox" },
                            { label: "CloakBrowser (externo/manual)", value: "cloakbrowser" }
                        ]
                        textRole: "label"
                        valueRole: "value"
                    }
                }
                LcTextField { id: apiName; Layout.fillWidth: true; placeholderText: "Nombre" }
                LcTextField {
                    id: apiUrl
                    Layout.fillWidth: true
                    placeholderText: apiProvider.currentValue === "camofox"
                                     ? "Base URL (ej. http://127.0.0.1:9377)"
                                     : "Base URL (https://…)"
                }
                LcTextField { id: apiKey;  Layout.fillWidth: true; placeholderText: "API key (opcional)"; echoMode: TextInput.Password }
                Text {
                    visible: apiProvider.currentValue === "cloakbrowser"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.textMuted
                    font.pixelSize: 11
                    text: "Se guarda desactivado. LlamaCode no descarga su binario ni lo usa automáticamente; registralo sólo para documentar una instalación externa revisada."
                }
                LcButton {
                    text: "Agregar API Service"
                    enabled: apiName.text.trim().length > 0 && apiUrl.text.trim().length > 0
                    onClicked: {
                        if (App.saveApiService("", apiName.text.trim(), apiUrl.text.trim(),
                                               apiKey.text, true, apiProvider.currentValue)) {
                            apiName.text = ""; apiUrl.text = ""; apiKey.text = ""
                        }
                    }
                }
            }
        }
    }
}
