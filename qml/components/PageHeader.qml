import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import LlamaCode 1.0

Rectangle {
    id: root
    height: 56
    color: Theme.navBg

    property string title: ""
    property string subtitle: ""
    property alias actionLabel: actionBtn.text
    property alias actionEnabled: actionBtn.enabled
    property string action2Label: ""
    signal actionClicked()
    signal action2Clicked()

    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.divider }

    // La ventana no tiene barra de título: el encabezado de página la reemplaza
    // (arrastrar mueve, doble clic maximiza) y deja libre el ancho de los
    // botones de ventana que Main.qml dibuja encima, arriba a la derecha.
    readonly property int windowControlsReserve: {
        const w = root.Window.window
        return (w && w.windowControlsWidth !== undefined) ? w.windowControlsWidth : 0
    }
    TapHandler {
        onDoubleTapped: {
            const w = root.Window.window
            if (w) w.visibility === Window.Maximized ? w.showNormal() : w.showMaximized()
        }
    }
    DragHandler {
        target: null
        onActiveChanged: if (active && root.Window.window) root.Window.window.startSystemMove()
    }

    RowLayout {
        anchors { fill: parent; leftMargin: 24; rightMargin: 16 + root.windowControlsReserve }

        Column {
            Layout.fillWidth: true
            spacing: 2
            Text {
                text: root.title
                font { pixelSize: 18; bold: true }
                color: Theme.textPrimary
            }
            Text {
                visible: root.subtitle.length > 0
                text: root.subtitle
                font.pixelSize: 12
                color: Theme.textMuted
            }
        }

        LcButton {
            id: action2Btn
            visible: root.action2Label.length > 0
            text: root.action2Label
            secondary: true
            onClicked: root.action2Clicked()
        }

        LcButton {
            id: actionBtn
            visible: text.length > 0
            onClicked: root.actionClicked()
        }
    }
}
