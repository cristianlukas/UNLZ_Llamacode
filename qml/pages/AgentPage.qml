import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0

Item {
    id: root

    // resolved from selected profile
    property string selectedLaunchId: ""
    property string resolvedAdapter: ""
    property string resolvedAdapterLabel: ""

    function resolveHarness(launchId) {
        if (!launchId || launchId.length === 0) {
            resolvedAdapter = "none"
            resolvedAdapterLabel = ""
            return
        }
        const lp = App.profileManager.getLaunchProfile(launchId)
        const harnessId = lp.harnessProfileId ?? ""
        if (harnessId.length > 0) {
            const hp = App.profileManager.getHarness(harnessId)
            resolvedAdapter = hp.adapter ?? "none"
            resolvedAdapterLabel = hp.adapter ?? ""
        } else {
            resolvedAdapter = "none"
            resolvedAdapterLabel = ""
        }
    }

    Component.onCompleted: {
        if (App.profileManager.launchProfiles.rowCount() > 0) {
            const idx = App.profileManager.launchProfiles.index(0, 0)
            selectedLaunchId = App.profileManager.launchProfiles.data(idx, 257) ?? ""
            resolveHarness(selectedLaunchId)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Header ──────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 48
            color: Theme.baseBg

            RowLayout {
                anchors { fill: parent; leftMargin: 16; rightMargin: 12 }
                spacing: 10

                Text { text: "🤖"; font.pixelSize: 16 }
                Text {
                    text: (App.langV, App.l("agent.title"))
                    color: Theme.textPrimary
                    font { pixelSize: 15; bold: true }
                }

                // profile combo
                ComboBox {
                    id: profileCombo
                    Layout.preferredWidth: 200
                    model: App.profileManager.launchProfiles
                    textRole: "name"
                    valueRole: "profileId"
                    enabled: !App.agentRunning
                    background: Rectangle { color: Theme.inputBg; radius: 6; border.color: Theme.borderColor }
                    contentItem: Text {
                        text: profileCombo.displayText.length > 0 ? profileCombo.displayText : "—"
                        color: Theme.textPrimary; font.pixelSize: 12; leftPadding: 8
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    onCurrentValueChanged: {
                        selectedLaunchId = currentValue ?? ""
                        resolveHarness(selectedLaunchId)
                    }
                }

                // harness badge
                Rectangle {
                    visible: resolvedAdapter !== "none" && resolvedAdapterLabel.length > 0
                    height: 22; radius: 4
                    color: Theme.highlight
                    implicitWidth: adapterLabel.implicitWidth + 16

                    Text {
                        id: adapterLabel
                        anchors.centerIn: parent
                        text: resolvedAdapterLabel
                        color: Theme.accent
                        font { pixelSize: 11; bold: true }
                    }
                }

                Rectangle {
                    width: 8; height: 8; radius: 4
                    color: App.agentRunning ? Theme.successText : Theme.errorText
                }
                Text {
                    text: {
                        const _lang = App.langV
                        return App.agentRunning
                            ? (App.activeAgentAdapter + " · " + App.l("agent.running"))
                            : App.l("agent.stopped")
                    }
                    color: App.agentRunning ? Theme.successText : Theme.textMuted
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                LcButton {
                    text: (App.langV, App.l("agent.clear"))
                    secondary: true
                    visible: !App.agentRunning
                    onClicked: App.clearAgentLog()
                }
                LcButton {
                    text: "Ver log nativo"
                    secondary: true
                    visible: resolvedAdapter.length > 0 && resolvedAdapter !== "none"
                    onClicked: App.openAgentLogDir(resolvedAdapter)
                }
                LcButton {
                    text: {
                        const _lang = App.langV
                        return App.agentRunning ? App.l("agent.stop") : App.l("agent.start")
                    }
                    danger: App.agentRunning
                    enabled: selectedLaunchId.length > 0
                    onClicked: App.agentRunning ? App.stopAgent() : App.startAgent(selectedLaunchId)
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

        // ── Warning: no harness on selected profile ──────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 32
            visible: selectedLaunchId.length > 0
                     && (resolvedAdapter === "none" || resolvedAdapterLabel.length === 0)
                     && !App.agentRunning
            color: Theme.surfaceBg

            Text {
                anchors { verticalCenter: parent.verticalCenter; left: parent.left; leftMargin: 16 }
                text: (App.langV, App.l("agent.noHarness"))
                color: Theme.textMuted
                font.pixelSize: 12
            }
        }

        // ── Harness not installed warning ────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 32
            visible: resolvedAdapter !== "none"
                     && resolvedAdapterLabel.length > 0
                     && !(App.harnessCheckV, App.isHarnessInstalled(resolvedAdapter))
                     && !App.agentRunning
            color: Theme.errorBg

            Text {
                anchors { verticalCenter: parent.verticalCenter; left: parent.left; leftMargin: 16 }
                text: (App.langV, App.l("agent.notInstalled"))
                color: Theme.errorText
                font.pixelSize: 12
            }
        }

        // ── Main body ────────────────────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Idle state
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 16
                visible: !App.agentRunning && App.agentLog.length === 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "🤖"
                    font.pixelSize: 48
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: resolvedAdapter !== "none" && resolvedAdapterLabel.length > 0
                        ? resolvedAdapterLabel + " · " + (App.langV, App.l("agent.stopped"))
                        : (App.langV, App.l("agent.stopped"))
                    color: Theme.textMuted
                    font.pixelSize: 14
                }
            }

            // Running in terminal
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 20
                visible: App.agentRunning && App.agentInTerminal

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "🖥️"
                    font.pixelSize: 48
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: App.activeAgentAdapter + " · ejecutándose en terminal externa"
                    color: Theme.successText
                    font { pixelSize: 15; bold: true }
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Interactuá directamente en la ventana de terminal."
                    color: Theme.textMuted
                    font.pixelSize: 12
                }
                LcButton {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Ver log nativo"
                    secondary: true
                    onClicked: App.openAgentLogDir(App.activeAgentAdapter)
                }
            }

            // Status log (launch info + exit messages)
            Rectangle {
                anchors.fill: parent
                color: Theme.logBg
                visible: App.agentLog.length > 0 && (!App.agentRunning || !App.agentInTerminal)

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        anchors.margins: 8
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        TextArea {
                            readOnly: true
                            text: App.agentLog
                            color: Theme.textSecondary
                            font { family: "Consolas,monospace"; pixelSize: 12 }
                            wrapMode: TextArea.WrapAnywhere
                            background: null
                            selectByMouse: true
                            onTextChanged: cursorPosition = length
                        }
                    }

                    // log path hint
                    Rectangle {
                        Layout.fillWidth: true
                        height: 24
                        color: Theme.surfaceBg
                        visible: resolvedAdapter.length > 0 && resolvedAdapter !== "none"

                        Text {
                            anchors { verticalCenter: parent.verticalCenter; left: parent.left; leftMargin: 12 }
                            text: "native log: " + App.agentNativeLogDir(resolvedAdapter)
                            color: Theme.textMuted
                            font { family: "Consolas,monospace"; pixelSize: 10 }
                            elide: Text.ElideLeft
                            width: parent.width - 24
                        }
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

        Rectangle {
            Layout.fillWidth: true
            height: 52
            color: Theme.baseBg
            visible: App.agentRunning && !App.agentInTerminal

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                LcTextField {
                    id: agentInput
                    Layout.fillWidth: true
                    placeholderText: (App.langV, App.l("agent.input"))
                    onAccepted: {
                        const t = text.trim()
                        if (t.length === 0) return
                        App.sendToAgent(t)
                        text = ""
                    }
                }

                LcButton {
                    text: (App.langV, App.l("agent.send"))
                    enabled: agentInput.text.trim().length > 0
                    onClicked: {
                        const t = agentInput.text.trim()
                        if (t.length === 0) return
                        App.sendToAgent(t)
                        agentInput.text = ""
                    }
                }
            }
        }

    }
}
