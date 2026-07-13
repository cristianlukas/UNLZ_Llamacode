import QtQuick
import QtQuick.Controls

Button {
    id: root
    property bool danger: false
    property bool secondary: false

    contentItem: Text {
        text: root.text
        font.pixelSize: 13
        color: root.danger ? Theme.btnDangerText : (root.secondary ? Theme.btnSecondaryText : Theme.btnPrimaryText)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 6
        color: {
            if (root.danger)    return root.pressed ? Theme.btnDangerPrs   : (root.hovered ? Theme.btnDangerHov   : Theme.btnDangerBg)
            if (root.secondary) return root.pressed ? Theme.btnSecondaryBg : (root.hovered ? Theme.btnSecondaryHov : Theme.btnSecondaryBg)
            return root.pressed ? Theme.btnPrimaryPrs : (root.hovered ? Theme.btnPrimaryHover : Theme.btnPrimaryBg)
        }
    }

    implicitHeight: 34
    implicitWidth: contentItem.implicitWidth + 24
    padding: 0
    leftPadding: 12
    rightPadding: 12
}
