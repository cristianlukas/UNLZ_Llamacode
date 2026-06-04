import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            title: (App.langV, App.l("settings.title"))
        }

        ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: scroll.availableWidth

            Item {
                width: scroll.availableWidth
                implicitHeight: col.implicitHeight + 48

                ColumnLayout {
                    id: col
                    anchors { left: parent.left; right: parent.right; top: parent.top }
                    anchors.margins: 24
                    spacing: 28

                    // ── Appearance ───────────────────────────────────────────
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: (App.langV, App.l("settings.appearance")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: themeInner.implicitHeight + 32

                            ColumnLayout {
                                id: themeInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 14

                                Text {
                                    text: (App.langV, App.l("settings.theme"))
                                    color: Theme.textPrimary
                                    font.pixelSize: 14
                                    font.bold: true
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Repeater {
                                        model: [
                                            { key: "dark",  labelKey: "settings.dark",  bg: "#1e1e2e", dotColor: "#313244" },
                                            { key: "light", labelKey: "settings.light", bg: "#eff1f5", dotColor: "#ccd0da" },
                                            { key: "oled",  labelKey: "settings.oled",  bg: "#000000", dotColor: "#111111" },
                                        ]

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            height: 70
                                            radius: 8
                                            color: modelData.bg
                                            border.color: Theme.theme === modelData.key ? Theme.accent : Theme.divider
                                            border.width: Theme.theme === modelData.key ? 2 : 1

                                            Rectangle {
                                                visible: Theme.theme === modelData.key
                                                anchors { top: parent.top; right: parent.right; margins: 6 }
                                                width: 18; height: 18; radius: 9
                                                color: Theme.accent
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "✓"
                                                    color: "#000000"
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                }
                                            }

                                            ColumnLayout {
                                                anchors.centerIn: parent
                                                spacing: 6

                                                Row {
                                                    Layout.alignment: Qt.AlignHCenter
                                                    spacing: 4
                                                    Repeater {
                                                        model: 3
                                                        Rectangle {
                                                            width: 7; height: 7; radius: 4
                                                            color: modelData.dotColor
                                                        }
                                                    }
                                                }

                                                Text {
                                                    Layout.alignment: Qt.AlignHCenter
                                                    text: (App.langV, App.l(modelData.labelKey))
                                                    color: modelData.key === "light" ? "#4c4f69" : "#cdd6f4"
                                                    font.pixelSize: 12
                                                    font.bold: Theme.theme === modelData.key
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: Theme.theme = modelData.key
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ── Language ─────────────────────────────────────────────
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: (App.langV, App.l("settings.language")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: langInner.implicitHeight + 32

                            ColumnLayout {
                                id: langInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 14

                                Text {
                                    text: (App.langV, App.l("settings.language"))
                                    color: Theme.textPrimary
                                    font.pixelSize: 14
                                    font.bold: true
                                }

                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 3
                                    rowSpacing: 8
                                    columnSpacing: 8

                                    Repeater {
                                        model: [
                                            { code: "es", label: "Español",  flag: "🇦🇷" },
                                            { code: "en", label: "English",  flag: "🇺🇸" },
                                            { code: "zh", label: "中文",       flag: "🇨🇳" },
                                            { code: "fr", label: "Français", flag: "🇫🇷" },
                                            { code: "it", label: "Italiano", flag: "🇮🇹" },
                                            { code: "de", label: "Deutsch",  flag: "🇩🇪" },
                                        ]

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            height: 48
                                            radius: 8
                                            color: App.language === modelData.code ? Theme.accent : Theme.inputBg
                                            border.color: App.language === modelData.code ? Theme.accent : Theme.borderColor
                                            border.width: 1

                                            Row {
                                                anchors.centerIn: parent
                                                spacing: 8
                                                Text { text: modelData.flag; font.pixelSize: 20 }
                                                Text {
                                                    text: modelData.label
                                                    color: App.language === modelData.code
                                                        ? Theme.btnPrimaryText : Theme.textPrimary
                                                    font.pixelSize: 13
                                                    font.bold: App.language === modelData.code
                                                    anchors.verticalCenter: parent.verticalCenter
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: App.language = modelData.code
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
