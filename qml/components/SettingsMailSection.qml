import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import LlamaCode 1.0

// Sección "mailSection" de Configuración, extraída de SettingsPage.qml (antes
// 3.500 líneas en un solo archivo). La visibilidad la decide la página.
ColumnLayout {
    id: section
    Layout.fillWidth: true
    spacing: 10

    // Lista de cuentas (se refresca con bump()).
    property var accounts: App.listMailAccounts()
    property int bump: 0
    function refresh() { accounts = App.listMailAccounts(); bump++ }

    Text {
        text: (App.langV, App.l("settings.sec.mail")).toUpperCase()
        color: Theme.accent
        font.pixelSize: 11
        font.bold: true
    }

    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: Theme.borderColor
        radius: 10
        implicitHeight: mailInner.implicitHeight + 32

        ColumnLayout {
            id: mailInner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 12

            Text {
                text: "Cuentas que el agente puede usar para enviar (SMTP) y leer (IMAP/POP3) correo. Para Gmail/Outlook usá una CONTRASEÑA DE APLICACIÓN (no la del login normal). La contraseña se guarda cifrada, fuera del repo."
                color: Theme.textSecondary
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            // Toggle auto-enviar
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: "Permitir auto-enviar sin aprobación"; color: Theme.textPrimary; font.pixelSize: 13 }
                    Text {
                        text: "Riesgo: el agente manda correos sin pedirte confirmación. Por defecto, email_send siempre pide aprobación."
                        color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true
                    }
                }
                LcSwitch {
                    checked: App.mailAutoSend
                    onToggled: App.mailAutoSend = checked
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

            // Cuentas existentes
            Repeater {
                model: section.accounts
                delegate: Rectangle {
                    Layout.fillWidth: true
                    color: Theme.inputBg
                    border.color: Theme.borderColor
                    radius: 8
                    implicitHeight: acctRow.implicitHeight + 16
                    RowLayout {
                        id: acctRow
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 8 }
                        spacing: 8
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: modelData.name + "  ·  " + modelData.email; color: Theme.textPrimary; font.pixelSize: 13 }
                            Text {
                                text: (modelData.provider || "custom") + "  ·  " + (modelData.recvProto || "imap")
                                      + (modelData.hasPassword ? "" : "  ·  ⚠ sin contraseña")
                                color: Theme.textMuted; font.pixelSize: 11
                            }
                            Text {
                                visible: section.bump >= 0 && testMsg.length > 0
                                property string testMsg: ""
                                id: acctTest
                                text: testMsg
                                color: text.indexOf("OK") === 0 ? Theme.accent : Theme.btnDangerBg
                                font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                        }
                        LcButton {
                            text: "Probar"
                            implicitHeight: 30
                            onClicked: {
                                var err = App.testMailAccount(modelData.name)
                                acctTest.testMsg = (err.length === 0) ? "OK · conexión y login correctos" : ("Error: " + err)
                            }
                        }
                        LcButton {
                            text: "✕"
                            implicitHeight: 30
                            onClicked: { App.removeMailAccount(modelData.name); section.refresh() }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

            // Alta de cuenta
            Text { text: "Agregar cuenta"; color: Theme.textPrimary; font.pixelSize: 13; font.bold: true }

            LcTextField { id: maName;  Layout.fillWidth: true; placeholderText: "Nombre interno (ej. trabajo)" }
            LcTextField { id: maEmail; Layout.fillWidth: true; placeholderText: "Dirección (ej. yo@gmail.com)" }
            LcTextField { id: maDisplay; Layout.fillWidth: true; placeholderText: "Nombre a mostrar (opcional)" }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: "Proveedor"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: maProvider
                    Layout.preferredWidth: 200
                    model: [
                        { label: "Auto (por dominio)", value: "auto" },
                        { label: "Gmail",   value: "gmail" },
                        { label: "Outlook/Hotmail", value: "outlook" },
                        { label: "Personalizado", value: "custom" },
                    ]
                    textRole: "label"
                    valueRole: "value"
                }
                Text { text: "Recepción"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: maRecvProto
                    Layout.preferredWidth: 110
                    model: [ { label: "IMAP", value: "imap" }, { label: "POP3", value: "pop3" } ]
                    textRole: "label"
                    valueRole: "value"
                }
            }

            // Campos avanzados (sólo personalizado / override)
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: maProvider.currentValue === "custom"
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    LcTextField { id: maSmtpHost; Layout.fillWidth: true; placeholderText: "SMTP host (ej. mail.dominio.com)" }
                    LcTextField { id: maSmtpPort; Layout.preferredWidth: 90; placeholderText: "puerto" }
                    LcComboBox {
                        id: maSmtpSec
                        Layout.preferredWidth: 130
                        model: [ { label: "SSL/TLS", value: "ssl" }, { label: "STARTTLS", value: "starttls" } ]
                        textRole: "label"; valueRole: "value"
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    LcTextField { id: maRecvHost; Layout.fillWidth: true; placeholderText: "IMAP/POP3 host" }
                    LcTextField { id: maRecvPort; Layout.preferredWidth: 90; placeholderText: "puerto" }
                }
            }

            LcTextField { id: maUser; Layout.fillWidth: true; placeholderText: "Usuario (vacío = la dirección)" }
            LcTextField {
                id: maPass; Layout.fillWidth: true
                placeholderText: "Contraseña / app password"
                echoMode: TextInput.Password
            }

            LcButton {
                text: "Agregar cuenta"
                enabled: maName.text.trim().length > 0 && maEmail.text.trim().length > 0
                onClicked: {
                    var def = {
                        "email": maEmail.text.trim(),
                        "displayName": maDisplay.text.trim(),
                        "provider": maProvider.currentValue,
                        "recvProto": maRecvProto.currentValue,
                        "smtpHost": maSmtpHost.text.trim(),
                        "smtpPort": parseInt(maSmtpPort.text) || 0,
                        "smtpSecurity": maSmtpSec.currentValue,
                        "recvHost": maRecvHost.text.trim(),
                        "recvPort": parseInt(maRecvPort.text) || 0,
                        "recvSsl": true,
                        "user": maUser.text.trim(),
                        "password": maPass.text
                    }
                    if (App.setMailAccount(maName.text.trim(), def)) {
                        maName.text = ""; maEmail.text = ""; maDisplay.text = ""
                        maSmtpHost.text = ""; maSmtpPort.text = ""; maRecvHost.text = ""
                        maRecvPort.text = ""; maUser.text = ""; maPass.text = ""
                        section.refresh()
                    }
                }
            }
        }
    }
}
