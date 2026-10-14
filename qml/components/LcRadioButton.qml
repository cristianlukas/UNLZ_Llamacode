import QtQuick
import QtQuick.Controls
import LlamaCode 1.0

// RadioButton con estilo del tema (el Basic dibuja un círculo blanco grande).
// Hereda RadioButton: ButtonGroup, checked y handlers siguen funcionando, y un
// override per-uso (indicator/contentItem) gana sobre estos defaults.
RadioButton {
    id: control

    spacing: 8

    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: control.leftPadding
        y: control.height / 2 - height / 2
        radius: width / 2
        color: Theme.inputBg
        border.color: control.checked ? Theme.accent : Theme.borderColor
        border.width: control.checked ? 2 : 1

        Rectangle {
            anchors.centerIn: parent
            width: 8; height: 8; radius: 4
            color: Theme.accent
            visible: control.checked
        }
    }

    contentItem: Text {
        text: control.text
        color: Theme.theme === "oled" ? "white" : Theme.textPrimary
        font.pixelSize: 13
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.text.length > 0 ? control.indicator.width + control.spacing : 0
        elide: Text.ElideRight
    }
}
