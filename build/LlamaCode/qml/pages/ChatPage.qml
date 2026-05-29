import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0

Item {
    id: root

    property bool generating: false
    property var currentXhr: null

    ListModel { id: messagesModel }

    function scrollToBottom() { Qt.callLater(() => { msgList.positionViewAtEnd() }) }

    function clearChat() {
        if (currentXhr) { currentXhr.abort(); currentXhr = null }
        generating = false
        messagesModel.clear()
    }

    function sendMessage() {
        const text = inputField.text.trim()
        if (!text.length || generating) return
        inputField.text = ""

        messagesModel.append({ role: "user", content: text })
        messagesModel.append({ role: "assistant", content: "" })
        const assistantIdx = messagesModel.count - 1

        generating = true
        scrollToBottom()

        const msgs = []
        for (let i = 0; i < messagesModel.count - 1; ++i)
            msgs.push({ role: messagesModel.get(i).role, content: messagesModel.get(i).content })

        const url = App.serverBaseUrl + "/v1/chat/completions"
        messagesModel.setProperty(assistantIdx, "content", "[connecting to " + url + "]")

        const xhr = new XMLHttpRequest()
        currentXhr = xhr
        xhr.open("POST", url, true)
        xhr.setRequestHeader("Content-Type", "application/json")

        const payload = JSON.stringify({ model: "default", messages: msgs, stream: true })

        let processedLength = 0
        xhr.onreadystatechange = function() {
            if (xhr.readyState >= 3 && xhr.status === 200) {
                if (processedLength === 0) messagesModel.setProperty(assistantIdx, "content", "")
                const chunk = xhr.responseText.substring(processedLength)
                processedLength = xhr.responseText.length
                const lines = chunk.split("\n")
                for (let i = 0; i < lines.length; ++i) {
                    const trimmed = lines[i].trim()
                    if (!trimmed.startsWith("data: ")) continue
                    const data = trimmed.substring(6).trim()
                    if (data === "[DONE]") continue
                    try {
                        const obj = JSON.parse(data)
                        const delta = (obj.choices?.[0]?.delta?.content) ?? ""
                        if (delta) {
                            messagesModel.setProperty(assistantIdx, "content",
                                messagesModel.get(assistantIdx).content + delta)
                            scrollToBottom()
                        }
                    } catch(e) {}
                }
            }
            if (xhr.readyState === 4) {
                if (xhr.status !== 200 && messagesModel.count > assistantIdx) {
                    const cur = messagesModel.get(assistantIdx).content
                    if (!cur.length) {
                        let errMsg = "Error " + xhr.status
                        try {
                            const e = JSON.parse(xhr.responseText)
                            if (e.error?.message) errMsg = e.error.message
                        } catch(_) {}
                        messagesModel.setProperty(assistantIdx, "content", "[" + errMsg + "]")
                    }
                }
                generating = false
                currentXhr = null
                scrollToBottom()
            }
        }
        xhr.send(payload)
    }

    function stopGeneration() {
        if (currentXhr) { currentXhr.abort(); currentXhr = null }
        generating = false
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            height: 48
            color: Theme.baseBg
            RowLayout {
                anchors { fill: parent; leftMargin: 16; rightMargin: 12 }
                spacing: 10
                Text { text: "Chat"; color: Theme.textPrimary; font.pixelSize: 15; font.bold: true }
                Rectangle { width: 8; height: 8; radius: 4; color: App.serverRunning ? Theme.successText : Theme.errorText }
                Text {
                    text: {
                        const _lang = App.langV
                        return App.serverRunning ? App.activeLaunchId : App.l("chat.serverStopped")
                    }
                    color: App.serverRunning ? Theme.textSecondary : Theme.errorText
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                LcButton {
                    text: (App.langV, App.l("chat.clear"))
                    secondary: true
                    visible: messagesModel.count > 0
                    onClicked: clearChat()
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

        ListView {
            id: msgList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            topMargin: 12
            bottomMargin: 12
            model: messagesModel
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            Text {
                anchors.centerIn: parent
                visible: messagesModel.count === 0
                text: {
                    const _lang = App.langV
                    return App.serverRunning ? App.l("chat.startMessage") : App.l("chat.startServer")
                }
                color: Theme.textMuted
                font.pixelSize: 14
            }

            delegate: Item {
                id: delegateRoot
                width: msgList.width
                height: bubbleRect.height + 8

                readonly property bool isUser: model.role === "user"

                Rectangle {
                    id: bubbleRect
                    anchors {
                        top: parent.top
                        right: delegateRoot.isUser ? parent.right : undefined
                        rightMargin: delegateRoot.isUser ? 16 : undefined
                        left: delegateRoot.isUser ? undefined : parent.left
                        leftMargin: delegateRoot.isUser ? undefined : 16
                    }
                    width: Math.min(delegateRoot.width - 80, delegateRoot.width * 0.78)
                    height: msgText.implicitHeight + 22
                    radius: 10
                    color: delegateRoot.isUser ? Theme.chatUserBubble : Theme.chatAsstBubble
                    border.width: delegateRoot.isUser ? 0 : 1
                    border.color: Theme.borderColor

                    TextEdit {
                        id: msgText
                        anchors { top: parent.top; left: parent.left; right: parent.right; margins: 11 }
                        text: {
                            const c = model.content
                            if (c.length === 0 && model.role === "assistant" && root.generating) return "▌"
                            return c
                        }
                        color: delegateRoot.isUser ? Theme.chatUserText : Theme.chatAsstText
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        wrapMode: TextEdit.WrapAtWordBoundaryOrAnywhere
                        readOnly: true
                        selectByMouse: true
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

        Rectangle {
            Layout.fillWidth: true
            color: Theme.baseBg
            height: 60

            RowLayout {
                anchors { fill: parent; leftMargin: 12; rightMargin: 12; topMargin: 10; bottomMargin: 10 }
                spacing: 8

                TextField {
                    id: inputField
                    Layout.fillWidth: true
                    placeholderText: {
                        const _lang = App.langV
                        return generating ? App.l("chat.generating") : App.l("chat.placeholder")
                    }
                    enabled: App.serverRunning
                    color: Theme.textPrimary
                    placeholderTextColor: Theme.textMuted
                    font.pixelSize: 13
                    leftPadding: 12
                    rightPadding: 12
                    verticalAlignment: TextInput.AlignVCenter
                    background: Rectangle {
                        color: Theme.inputBg
                        radius: 8
                        border.width: inputField.activeFocus ? 1 : 0
                        border.color: Theme.inputBorderFocus
                    }
                    Keys.onReturnPressed: (event) => {
                        if (!(event.modifiers & Qt.ShiftModifier)) sendMessage()
                    }
                }

                LcButton {
                    text: {
                        const _lang = App.langV
                        return generating ? App.l("chat.stop") : App.l("chat.send")
                    }
                    enabled: App.serverRunning && (generating || inputField.text.trim().length > 0)
                    onClicked: generating ? stopGeneration() : sendMessage()
                }
            }
        }
    }
}
