import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0

// Configuración Google compartida entre Configuración → Correo e Ingi-Charla.
ColumnLayout {
    id: section
    objectName: "googleWorkspaceSettingsSection"
    property bool showClientIdEditor: App.googleWorkspaceClientId.trim().length === 0
    Layout.fillWidth: true
    spacing: 10

    Text {
        text: "Google Workspace · Gmail, Calendar y Tasks"
        color: Theme.textPrimary
        font.pixelSize: 13
        font.bold: true
    }
    Text {
        text: "Conectá Google una vez y autorizá el acceso en el navegador predeterminado. Las versiones configuradas por LlamaCode pueden iniciar con un clic; una build propia puede necesitar configurar el Client ID de escritorio. La app nunca te pide la contraseña de Google."
        color: Theme.textSecondary
        font.pixelSize: 12
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Text {
        visible: App.googleWorkspaceClientId.trim().length === 0
        text: "Esta build no tiene configurado el Client ID OAuth de LlamaCode, así que Google todavía no puede abrir el inicio de sesión. Si mantenés esta build, creá un cliente de tipo Desktop app una vez y pegá su ID aquí."
        color: Theme.warnText
        font.pixelSize: 12
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    RowLayout {
        visible: App.googleWorkspaceClientId.trim().length === 0
        Layout.fillWidth: true
        LcButton {
            text: "Abrir Google Cloud"
            secondary: true
            onClicked: Qt.openUrlExternally("https://console.cloud.google.com/auth/clients")
        }
    }
    LcTextField {
        id: googleClientId
        visible: section.showClientIdEditor
        Layout.fillWidth: true
        placeholderText: "Google OAuth Client ID (Desktop app)"
        text: App.googleWorkspaceClientId
        onEditingFinished: App.googleWorkspaceClientId = text.trim()
    }
    LcButton {
        visible: App.googleWorkspaceClientId.trim().length > 0
                 && !App.googleWorkspaceConnected && !section.showClientIdEditor
        text: "Cambiar Client ID"
        secondary: true
        onClicked: section.showClientIdEditor = true
    }
    Flow {
        Layout.fillWidth: true
        spacing: 8
        LcButton {
            text: App.googleWorkspaceBusy ? "Conectando…" : "Conectar Google"
            enabled: !App.googleWorkspaceBusy && !App.googleWorkspaceConnected
                     && googleClientId.text.trim().length > 0
            onClicked: {
                App.googleWorkspaceClientId = googleClientId.text.trim()
                App.connectGoogleWorkspace()
            }
        }
        LcButton {
            visible: App.googleWorkspaceConnected && !App.googleWorkspaceDraftsEnabled
            text: App.googleWorkspaceBusy ? "Autorizando…" : "Habilitar borradores Gmail"
            enabled: !App.googleWorkspaceBusy
            onClicked: App.connectGoogleWorkspaceDrafts()
        }
        LcButton {
            visible: App.googleWorkspaceConnected && !App.googleWorkspaceTaskCreateEnabled
            text: App.googleWorkspaceBusy ? "Autorizando…" : "Habilitar creación de tareas"
            enabled: !App.googleWorkspaceBusy
            onClicked: App.connectGoogleWorkspaceTaskCreate()
        }
        LcButton {
            visible: App.googleWorkspaceConnected && !App.googleWorkspaceEventCreateEnabled
            text: App.googleWorkspaceBusy ? "Autorizando…" : "Habilitar creación de eventos"
            enabled: !App.googleWorkspaceBusy
            onClicked: App.connectGoogleWorkspaceEventCreate()
        }
        LcButton {
            visible: App.googleWorkspaceConnected
            text: "Desconectar"
            secondary: true
            onClicked: App.disconnectGoogleWorkspace()
        }
    }
    Text {
        Layout.fillWidth: true
        text: App.googleWorkspaceStatus
        color: App.googleWorkspaceConnected ? Theme.accent : Theme.textMuted
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    Text {
        visible: App.googleWorkspaceConnected && !App.googleWorkspaceTaskCreateEnabled
        text: "El permiso adicional de Google Tasks puede ver, editar, organizar y borrar tareas de tus listas. LlamaCode sólo ofrece crear tareas, editar campos puntuales, completarlas y reabrirlas; no publica tools de borrado ni reordenamiento. Cada acción requiere aprobación."
        color: Theme.textMuted
        font.pixelSize: 11
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Text {
        visible: App.googleWorkspaceConnected && !App.googleWorkspaceEventCreateEnabled
        text: "El permiso adicional calendar.events puede leer, editar y borrar eventos de tus calendarios. LlamaCode sólo ofrece crear eventos sin invitados, pide aprobación para cada uno y no publica tools de edición, invitación ni borrado."
        color: Theme.textMuted
        font.pixelSize: 11
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Text {
        Layout.fillWidth: true
        visible: App.googleWorkspaceConnected && !App.googleWorkspaceDraftsEnabled
        text: "Opcional: Gmail compose permite gestionar borradores y enviar correo. LlamaCode sólo ofrece crear borradores; cada uno muestra destinatarios y contenido y requiere tu aprobación. No hay herramienta de envío."
        color: Theme.warnText
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    Text {
        Layout.fillWidth: true
        text: App.googleWorkspaceCanRemember
              ? "El refresh token se guarda cifrado por el sistema. Desconectar elimina la copia local; la autorización remota se revoca desde la configuración de seguridad de tu cuenta Google."
              : "No hay keyring disponible: la conexión dura hasta cerrar LlamaCode y el refresh token no se guarda. Desconectar elimina la sesión local."
        color: Theme.textMuted
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
}
