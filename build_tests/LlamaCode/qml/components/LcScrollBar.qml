import QtQuick
import QtQuick.Controls

// ScrollBar que respeta los colores del tema activo.
ScrollBar {
    id: root

    contentItem: Rectangle {
        implicitWidth: 6
        implicitHeight: 6
        radius: width / 2
        color: root.pressed ? Theme.accent
                            : (root.hovered ? Theme.textSecondary : Theme.textMuted)
        opacity: root.active ? 0.9 : 0.0
        Behavior on opacity { NumberAnimation { duration: 150 } }
    }

    background: Rectangle {
        color: Theme.borderColor
        opacity: root.active ? 0.25 : 0.0
        radius: width / 2
        Behavior on opacity { NumberAnimation { duration: 150 } }
    }
}
