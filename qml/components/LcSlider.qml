import QtQuick
import QtQuick.Controls

// Slider con los colores del tema. El nativo dibujaba una perilla blanca grande
// y el tramo "lleno" a la DERECHA de la perilla (claro sobre oscuro), así que
// 250 W de 375 parecía casi al máximo.
Slider {
    id: root
    implicitHeight: 26
    opacity: enabled ? 1.0 : 0.45

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: 4
        radius: 2
        color: Theme.borderColor
        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: Theme.accent
        }
    }

    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: 16
        height: 16
        radius: 8
        color: root.pressed ? Theme.accentPressed : Theme.accent
        border.color: Theme.baseBg
        border.width: 2
    }
}
