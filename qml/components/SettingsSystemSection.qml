import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import LlamaCode 1.0

// Sección "systemSection" de Configuración, extraída de SettingsPage.qml (antes
// 3.500 líneas en un solo archivo). La visibilidad la decide la página.
ColumnLayout {
    id: section
    Layout.fillWidth: true
    spacing: 10

    Text {
        text: (App.langV, App.l("settings.system")).toUpperCase()
        color: Theme.accent
        font.pixelSize: 11
        font.bold: true
    }

    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: Theme.borderColor
        radius: 10
        implicitHeight: updateChannelRow.implicitHeight + 32

        RowLayout {
            id: updateChannelRow
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 16 }
            spacing: 16

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: "Canal de actualizaciones"
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    font.bold: true
                }
                Text {
                    text: "Prod ofrece versiones estables. Debug avisa de candidatos de prueba y al actualizar instala la configuración Debug. Build actual: "
                          + (App.buildChannel === "debug" ? "Debug" : "Prod") + "."
                    color: Theme.textMuted
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            LcComboBox {
                Layout.preferredWidth: 210
                model: [
                    { id: "prod", name: "Prod · estable" },
                    { id: "debug", name: "Debug · pruebas" }
                ]
                textRole: "name"
                valueRole: "id"
                currentIndex: App.updateChannel === "debug" ? 1 : 0
                onActivated: App.updateChannel = currentValue
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: Theme.borderColor
        radius: 10
        implicitHeight: trayInner.implicitHeight + 32

        ColumnLayout {
            id: trayInner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: (App.langV, App.l("settings.minimizeToTray"))
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: (App.langV, App.l("settings.minimizeToTrayDesc"))
                        color: Theme.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                LcSwitch {
                    checked: App.readSetting("window/minimizeToTray", false)
                    onToggled: {
                        App.writeSetting("window/minimizeToTray", checked)
                        if (Window.window)
                            Window.window.minimizeToTray = checked
                    }
                }
            }

            // Inicio automático: registro Run en Windows, ~/.config/autostart
            // en Linux (Debug y Prod con entradas separadas).
            Rectangle {
                Layout.fillWidth: true; height: 1; color: Theme.borderColor
                visible: Qt.platform.os === "windows" || Qt.platform.os === "linux"
            }

            RowLayout {
                Layout.fillWidth: true
                visible: Qt.platform.os === "windows" || Qt.platform.os === "linux"
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: (App.langV, App.l(Qt.platform.os === "windows" ? "settings.startWithWindows" : "settings.startWithSystem"))
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: (App.langV, App.l("settings.startWithWindowsDesc"))
                        color: Theme.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                LcSwitch {
                    checked: App.startWithWindowsEnabled()
                    onToggled: {
                        const error = App.setStartWithWindowsEnabled(checked)
                        if (error.length > 0)
                            checked = App.startWithWindowsEnabled()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: "Iniciar el agente al abrir la app"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "Levanta el server y el agente del último perfil al arrancar, así las Tasks programadas (cron) disparan a horario sin esperar la carga del modelo."
                        color: Theme.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                LcSwitch {
                    checked: App.autoStartAgentOnLaunch
                    onToggled: App.autoStartAgentOnLaunch = checked
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: "Iniciar el agente cuando el servidor esté listo"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "Si el modelo se carga sin agente (\"Iniciar solo servidor\" o un cliente LAN que lo pidió), el agente de esta PC arranca solo al quedar listo."
                        color: Theme.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
                LcSwitch {
                    checked: App.agentStartWithServer
                    onToggled: App.agentStartWithServer = checked
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: "Auto-stop por inactividad"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: "Descarga el modelo y libera VRAM tras N minutos sin chat/agente/API. 0 = nunca."
                        color: Theme.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                LcSpinBox {
                    from: 0; to: 1440; stepSize: 5
                    value: App.idleAutoStopMin
                    onValueModified: App.idleAutoStopMin = value
                    textFromValue: function(v) { return v === 0 ? "off" : v + " min" }
                }
            }
        }
    }
}
