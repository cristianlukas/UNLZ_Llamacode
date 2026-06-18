import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0

Item {
    id: root

    // Estado del editor (dialog). editId vacío = creando.
    property string editId: ""

    function openEditor(id) {
        editId = id
        stepsModel.clear()
        previewBox.visible = false
        previewArea.text = ""
        if (id.length > 0) {
            const t = App.taskStore.get(id)
            nameField.text = t.name || ""
            descField.text = t.description || ""
            cronField.text = t.scheduleCron || ""
            schedEnabled.checked = t.scheduleEnabled || false
            const steps = t.steps || []
            for (var i = 0; i < steps.length; ++i)
                stepsModel.append({ kind: steps[i].kind || "instruction",
                                    intent: steps[i].intent || "",
                                    ref: steps[i].ref || "" })
            profileCombo.selectProfile(t.profileId || "")
        } else {
            nameField.text = ""
            descField.text = ""
            cronField.text = ""
            schedEnabled.checked = false
            profileCombo.currentIndex = 0
        }
        editor.open()
    }

    function collectSteps() {
        const arr = []
        for (var i = 0; i < stepsModel.count; ++i) {
            const s = stepsModel.get(i)
            arr.push({ kind: s.kind, intent: s.intent, ref: s.ref })
        }
        return arr
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            title: (App.langV, App.l("nav.tasks"))
            subtitle: App.taskStore.count + " task(s) · macros que el agente ejecuta y adapta"
            actionLabel: "Nueva Task"
            onActionClicked: root.openEditor("")
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: Theme.navBg
            RowLayout {
                anchors { fill: parent; leftMargin: 24; rightMargin: 16 }
                spacing: 10
                Switch {
                    id: schedSwitch
                    text: ""
                    Layout.preferredWidth: 44
                    Layout.alignment: Qt.AlignVCenter
                    checked: App.tasksSchedulerEnabled
                    onToggled: App.tasksSchedulerEnabled = checked
                }
                Text {
                    text: "Scheduler cron " + (App.tasksSchedulerEnabled ? "activo" : "apagado")
                    color: App.tasksSchedulerEnabled ? Theme.accent : Theme.textSecondary
                    font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    Layout.fillWidth: true
                    text: "Dispara las Tasks programadas mientras la app esté abierta. Si el agente ya corre lo usa; si no, lo auto-inicia, ejecuta y lo apaga al terminar."
                    color: Theme.textMuted
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.divider }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: 10
                anchors { topMargin: 16; leftMargin: 24; rightMargin: 24 }

                Item { Layout.preferredHeight: 8; Layout.fillWidth: true }

                Text {
                    visible: App.taskStore.count === 0
                    Layout.leftMargin: 24
                    text: "No hay Tasks todavía. Creá una: definí un objetivo en lenguaje natural\ny pasos de referencia; el agente los ejecuta y se adapta si algo cambió."
                    color: Theme.textMuted
                    font.pixelSize: 13
                }

                Repeater {
                    model: App.taskStore
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: 78
                        radius: 8
                        color: Theme.surfaceBg
                        border.color: Theme.borderColor
                        property string taskId: model.id || ""
                        property string taskName: model.name || ""

                        RowLayout {
                            anchors { fill: parent; leftMargin: 16; rightMargin: 12 }
                            spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text {
                                    text: model.name || "(sin nombre)"
                                    color: Theme.textPrimary
                                    font { pixelSize: 15; bold: true }
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: (model.description || "").length > 0 ? model.description : "—"
                                    color: Theme.textSecondary
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: model.stepCount + " paso(s)"
                                        + (model.scheduleEnabled ? "  ·  ⏱ " + (model.scheduleCron || "cron") : "")
                                        + (model.lastRunStatus ? "  ·  última: " + model.lastRunStatus : "")
                                    color: Theme.textMuted
                                    font.pixelSize: 11
                                }
                            }

                            LcButton {
                                text: "▶ Ejecutar"
                                onClicked: App.runTask(taskId)
                            }
                            LcButton {
                                text: "Editar"
                                secondary: true
                                onClicked: root.openEditor(taskId)
                            }
                            LcButton {
                                text: "✕"
                                secondary: true
                                onClicked: { delConfirm.taskId = taskId; delConfirm.taskName = taskName; delConfirm.open() }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true; Layout.fillWidth: true }
            }
        }
    }

    ListModel { id: stepsModel }

    // ── Editor de Task ──
    LcDialog {
        id: editor
        title: root.editId.length > 0 ? "Editar Task" : "Nueva Task"
        implicitWidth: 700
        implicitHeight: 600

        onAccepted: {
            App.taskStore.save(root.editId, {
                name: nameField.text,
                description: descField.text,
                profileId: profileCombo.selectedProfileId,
                steps: root.collectSteps(),
                scheduleEnabled: schedEnabled.checked,
                scheduleCron: cronField.text
            })
        }

        contentItem: ScrollView {
            clip: true
            ColumnLayout {
                width: editor.availableWidth
                spacing: 10

                Text { text: "Nombre"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: nameField; Layout.fillWidth: true; placeholderText: "Ej: Extraer cotización del dólar" }

                Text { text: "Objetivo (qué se busca y por qué)"; color: Theme.textSecondary; font.pixelSize: 12 }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    TextArea {
                        id: descField
                        wrapMode: TextArea.Wrap
                        color: Theme.textPrimary
                        placeholderText: "Describí el objetivo en lenguaje natural. El agente lo usa para adaptarse."
                        background: Rectangle { radius: 6; color: Theme.inputBg; border.color: Theme.inputBorderColor }
                    }
                }

                Text { text: "Perfil del agente (opcional)"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: profileCombo
                    Layout.fillWidth: true
                    textRole: "name"
                    valueRole: "profileId"
                    property string selectedProfileId: currentValue || ""
                    model: App.profileManager
                    function selectProfile(pid) {
                        for (var i = 0; i < count; ++i) {
                            if (App.profileManager.data(App.profileManager.index(i,0), 0x0101) === pid) { currentIndex = i; return }
                        }
                        currentIndex = 0
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Pasos de referencia"; color: Theme.textSecondary; font.pixelSize: 12; Layout.fillWidth: true }
                    LcButton {
                        text: "+ Paso"
                        secondary: true
                        onClicked: stepsModel.append({ kind: "instruction", intent: "", ref: "" })
                    }
                }

                Repeater {
                    model: stepsModel
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 88
                        radius: 6
                        color: Theme.inputBg
                        border.color: Theme.borderColor
                        ColumnLayout {
                            anchors { fill: parent; margins: 8 }
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                LcComboBox {
                                    Layout.preferredWidth: 140
                                    model: ["instruction", "browser", "shell", "mail", "desktop"]
                                    currentIndex: Math.max(0, model.indexOf(stepsModel.get(index).kind))
                                    onActivated: stepsModel.setProperty(index, "kind", currentText)
                                }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: model.intent
                                    placeholderText: "Qué hacer en este paso (intención)"
                                    onTextChanged: stepsModel.setProperty(index, "intent", text)
                                }
                                LcButton {
                                    text: "⏺ Browser"
                                    secondary: true
                                    visible: model.kind === "browser"
                                    onClicked: {
                                        const slug = App.recordTaskBrowserStep(nameField.text + "-" + (index + 1),
                                                                               model.ref.length > 0 ? model.ref : "https://")
                                        if (slug.length > 0) stepsModel.setProperty(index, "ref", slug)
                                    }
                                }
                                LcButton {
                                    text: "✕"
                                    secondary: true
                                    onClicked: stepsModel.remove(index)
                                }
                            }
                            LcTextField {
                                Layout.fillWidth: true
                                text: model.ref
                                placeholderText: "Referencia (URL, comando, nombre de skill grabado…)"
                                onTextChanged: stepsModel.setProperty(index, "ref", text)
                            }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    CheckBox {
                        id: schedEnabled
                        text: "Programar (cron)"
                        contentItem: Text {
                            text: schedEnabled.text; color: Theme.textSecondary; font.pixelSize: 12
                            leftPadding: schedEnabled.indicator.width + 6; verticalAlignment: Text.AlignVCenter
                        }
                    }
                    LcTextField {
                        Layout.fillWidth: true
                        id: cronField
                        enabled: schedEnabled.checked
                        placeholderText: "0 9 * * *  (min hora día mes díaSem)"
                    }
                }

                Text {
                    visible: schedEnabled.checked
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.textMuted
                    font.pixelSize: 11
                    text: "Formato: min hora díaMes mes díaSem. Ej: «0 9 * * *» = 9:00 todos los días · "
                        + "«*/15 9-17 * * 1-5» = cada 15 min, 9-17h, lun-vie · «0 0 1 * *» = día 1 de cada mes. "
                        + "Domingo = 0 o 7."
                }

                LcButton {
                    text: "Previsualizar prompt del agente"
                    secondary: true
                    onClicked: {
                        // Guarda temporalmente para componer con datos actuales.
                        previewArea.text = App.taskStore.count >= 0
                            ? composePreview() : ""
                        previewBox.visible = true
                    }
                }
                Rectangle {
                    id: previewBox
                    visible: false
                    Layout.fillWidth: true
                    Layout.preferredHeight: 140
                    radius: 6
                    color: Theme.inputBg
                    border.color: Theme.borderColor
                    ScrollView {
                        anchors { fill: parent; margins: 8 }
                        TextArea {
                            id: previewArea
                            readOnly: true
                            wrapMode: TextArea.Wrap
                            color: Theme.textSecondary
                            font { family: "Consolas"; pixelSize: 12 }
                            background: null
                        }
                    }
                }
            }
        }
    }

    // Compone una vista previa local equivalente a TaskStore::composePrompt.
    function composePreview() {
        let out = "Ejecutá la siguiente Task guardada de forma autónoma.\n"
        if (nameField.text) out += "Task: " + nameField.text + "\n"
        if (descField.text) out += "Objetivo: " + descField.text + "\n"
        if (stepsModel.count > 0) {
            out += "\nPasos de referencia (grabados en una corrida previa):\n"
            for (var i = 0; i < stepsModel.count; ++i) {
                const s = stepsModel.get(i)
                out += (i + 1) + ". [" + s.kind + "] " + s.intent + (s.ref ? " (ref: " + s.ref + ")" : "") + "\n"
            }
        }
        out += "\nIMPORTANTE: los pasos son una guía, no un guion literal. Entendé QUÉ se busca y POR QUÉ; si algo cambió de lugar, adaptate y logrueá el objetivo igual."
        return out
    }

    LcDialog {
        id: delConfirm
        title: "Eliminar Task"
        property string taskId: ""
        property string taskName: ""
        implicitWidth: 420
        onAccepted: App.taskStore.remove(taskId)
        contentItem: Text {
            text: "¿Eliminar la Task \"" + delConfirm.taskName + "\"? No se puede deshacer."
            color: Theme.textPrimary
            wrapMode: Text.Wrap
            padding: 8
        }
    }
}
