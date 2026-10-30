import QtQuick

Rectangle {
    property string title: ""
    property string subtitle: ""
    property string actionLabel: ""
    property string action2Label: ""
    property bool actionEnabled: true
    signal actionClicked()
    signal action2Clicked()
    height: 56
    color: Theme.baseBg
}
