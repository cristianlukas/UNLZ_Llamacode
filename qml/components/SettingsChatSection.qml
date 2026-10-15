import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import LlamaCode 1.0

// Sección "chatSection" de Configuración, extraída de SettingsPage.qml (antes
// 3.500 líneas en un solo archivo). La visibilidad la decide la página.
ColumnLayout {
    id: section
    Layout.fillWidth: true
    spacing: 10

    Text {
        text: (App.langV, App.l("settings.sec.chat")).toUpperCase()
        color: Theme.accent
        font.pixelSize: 11
        font.bold: true
    }

    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: Theme.borderColor
        radius: 10
        implicitHeight: mermaidInner.implicitHeight + 32

        RowLayout {
            id: mermaidInner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: "Diagramas Mermaid"
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    font.bold: true
                }
                Text {
                    text: Mermaid.available
                        ? "Renderiza bloques ```mermaid del chat como imagen."
                        : "Requiere mermaid-cli (npm i -g @mermaid-js/mermaid-cli)."
                    color: Theme.textMuted
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            LcSwitch {
                checked: App.mermaidEnabled
                enabled: Mermaid.available
                onToggled: App.mermaidEnabled = checked
            }
        }
    }

    // ── Privacidad de herramientas del agente ────────────
    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: App.privacyModeEnabled ? Theme.accent : Theme.borderColor
        radius: 10
        implicitHeight: privacyInner.implicitHeight + 32

        ColumnLayout {
            id: privacyInner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: "Modo privacidad"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "Bloquea búsquedas web/semánticas, browser, correo, MCP, plugins externos y delegación " +
                              "del agente; agrega una instrucción para no transmitir datos. No es un firewall: " +
                              "un modelo remoto o comandos de shell pueden abrir conexiones por su cuenta."
                        color: Theme.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
                LcSwitch {
                    checked: App.privacyModeEnabled
                    onToggled: App.privacyModeEnabled = checked
                }
            }
        }
    }

    // ── Automatización de browser (MCP Playwright) ───────
    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: Theme.borderColor
        radius: 10
        implicitHeight: browserInner.implicitHeight + 32

        ColumnLayout {
            id: browserInner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: "Automatización de browser"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "Da al agente tools de navegador vía MCP Playwright " +
                              "(navegar, click, escribir, snapshot). Requiere Node/npx. " +
                              "Override on/off por perfil en Perfiles."
                        color: Theme.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
                LcSwitch {
                    checked: App.browserAutomationEnabled
                    onToggled: App.browserAutomationEnabled = checked
                }
            }

            LcTextField {
                Layout.fillWidth: true
                visible: App.browserAutomationEnabled
                placeholderText: "Comando del server MCP"
                text: App.browserMcpCommand
                onEditingFinished: App.browserMcpCommand = text
            }

        }
    }
}
