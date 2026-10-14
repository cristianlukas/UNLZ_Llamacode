import QtQuick
import QtQuick.Controls
import LlamaCode 1.0

// SpinBox con estilo del tema. Con el estilo Basic el campo y los botones son
// claros: en tema oscuro un contentItem con Theme.textPrimary (claro) quedaba
// invisible sobre fondo blanco. Hereda SpinBox: cualquier propiedad/handler/id
// existente sigue funcionando, y un override per-uso gana sobre estos defaults.
SpinBox {
    id: control

    implicitHeight: 34
    leftPadding: down.indicator.width
    rightPadding: up.indicator.width

    contentItem: TextInput {
        z: 2
        text: control.displayText
        color: Theme.theme === "oled" ? "white" : Theme.textPrimary
        selectionColor: Theme.accent
        selectedTextColor: Theme.baseBg
        font.pixelSize: 13
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: Qt.AlignVCenter
        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: control.inputMethodHints
        clip: true
    }

    background: Rectangle {
        implicitWidth: 120
        color: Theme.inputBg
        radius: 6
        border.color: control.activeFocus ? Theme.inputBorderFocus : Theme.borderColor
    }

    down.indicator: Rectangle {
        x: control.mirrored ? parent.width - width : 0
        height: control.height
        implicitWidth: 30
        radius: 6
        color: control.down.pressed ? Theme.highlight
             : control.down.hovered ? Theme.hoverBg : "transparent"
        opacity: control.enabled && control.value > control.from ? 1.0 : 0.35
        Text {
            anchors.centerIn: parent
            text: "−"
            color: Theme.textSecondary
            font.pixelSize: 15
        }
    }

    up.indicator: Rectangle {
        x: control.mirrored ? 0 : parent.width - width
        height: control.height
        implicitWidth: 30
        radius: 6
        color: control.up.pressed ? Theme.highlight
             : control.up.hovered ? Theme.hoverBg : "transparent"
        opacity: control.enabled && control.value < control.to ? 1.0 : 0.35
        Text {
            anchors.centerIn: parent
            text: "+"
            color: Theme.textSecondary
            font.pixelSize: 15
        }
    }
}
