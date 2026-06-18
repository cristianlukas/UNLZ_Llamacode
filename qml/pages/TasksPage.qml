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
            prePromptField.text = t.prePrompt || ""
            postPromptField.text = t.postPrompt || ""
            silentUnlessError.checked = t.silentUnlessError || false
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
            prePromptField.text = ""
            postPromptField.text = ""
            silentUnlessError.checked = false
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
                        Layout.preferredHeight: 88
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
                                Text {
                                    visible: App.runningTaskId === taskId
                                    text: App.runningTaskPhase === "verificando" ? "Verificando con postprompt..." : "Ejecutando..."
                                    color: Theme.accent
                                    font.pixelSize: 11
                                }
                            }

                            LcButton {
                                text: App.runningTaskId === taskId
                                      ? "Ejecutando..."
                                      : (!App.canRunTask && (App.agentStarting || (App.serverRunning && !App.serverReady))
                                         ? "Cargando..."
                                         : "▶ Ejecutar")
                                enabled: App.canRunTask
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
    Popup {
        id: editor
        modal: true
        parent: Overlay.overlay
        closePolicy: Popup.CloseOnEscape
        width: Math.min(760, Math.max(520, root.width - 80))
        height: Math.min(760, Math.max(520, root.height - 80))
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        padding: 0

        function saveAndClose() {
            App.taskStore.save(root.editId, {
                name: nameField.text,
                description: descField.text,
                prePrompt: prePromptField.text,
                postPrompt: postPromptField.text,
                silentUnlessError: silentUnlessError.checked,
                profileId: profileCombo.selectedProfileId,
                steps: root.collectSteps(),
                scheduleEnabled: schedEnabled.checked,
                scheduleCron: cronField.text
            })
            close()
        }

        background: Rectangle {
            color: Theme.popupBg
            radius: 12
            border.color: Theme.popupBorderColor
            border.width: 1
        }
        Overlay.modal: Rectangle { color: Theme.overlayColor }

        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                color: Theme.popupHeaderBg
                radius: 12
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 12; color: Theme.popupHeaderBg }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.popupHeaderBorder }
                Text {
                    anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                    text: root.editId.length > 0 ? "Editar Task" : "Nueva Task"
                    font { pixelSize: 14; bold: true }
                    color: Theme.textPrimary
                }
            }

            ScrollView {
                id: editorScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: Math.max(0, editorScroll.width - 36)
                    spacing: 10
                    x: 18
                    Item { Layout.preferredHeight: 6; Layout.fillWidth: true }

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

                    Text { text: "Preprompt opcional"; color: Theme.textSecondary; font.pixelSize: 12 }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        TextArea {
                            id: prePromptField
                            wrapMode: TextArea.Wrap
                            color: Theme.textPrimary
                            placeholderText: "Contexto o reglas previas antes de ejecutar la Task."
                            background: Rectangle { radius: 6; color: Theme.inputBg; border.color: Theme.inputBorderColor }
                        }
                    }

                    Text { text: "Postprompt opcional"; color: Theme.textSecondary; font.pixelSize: 12 }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        TextArea {
                            id: postPromptField
                            wrapMode: TextArea.Wrap
                            color: Theme.textPrimary
                            placeholderText: "Chequeo posterior, validación o resumen que el agente debe hacer al terminar."
                            background: Rectangle { radius: 6; color: Theme.inputBg; border.color: Theme.inputBorderColor }
                        }
                    }

                    CheckBox {
                        id: silentUnlessError
                        text: "Ejecutar en silencio salvo error"
                        contentItem: Text {
                            text: silentUnlessError.text
                            color: Theme.textSecondary
                            font.pixelSize: 12
                            leftPadding: silentUnlessError.indicator.width + 6
                            verticalAlignment: Text.AlignVCenter
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
                            const idx = indexOfValue(pid)
                            currentIndex = idx >= 0 ? idx : 0
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
                                    placeholderText: "Referencia (URL, comando, nombre de skill grabado...)"
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
                            placeholderText: "0 9 * * *  (min hora dia mes diaSem)"
                        }
                    }

                    Text {
                        visible: schedEnabled.checked
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Theme.textMuted
                        font.pixelSize: 11
                        text: "Formato: min hora diaMes mes diaSem. Ej: 0 9 * * * = 9:00 todos los dias · "
                            + "*/15 9-17 * * 1-5 = cada 15 min, 9-17h, lun-vie · 0 0 1 * * = dia 1 de cada mes. "
                            + "Domingo = 0 o 7."
                    }

                    LcButton {
                        text: "Previsualizar prompt del agente"
                        secondary: true
                        onClicked: {
                            previewArea.text = composePreview()
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
                    Item { Layout.preferredHeight: 8; Layout.fillWidth: true }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                color: Theme.popupHeaderBg
                radius: 12
                Rectangle { anchors.top: parent.top; width: parent.width; height: 12; color: Theme.popupHeaderBg }
                Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.popupHeaderBorder }
                Row {
                    anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                    spacing: 10
                    LcButton { text: "Cancelar"; secondary: true; onClicked: editor.close() }
                    LcButton { text: "Guardar"; onClicked: editor.saveAndClose() }
                }
            }
        }
    }

    // Compone una vista previa local equivalente a TaskStore::composePrompt.
    function composePreview() {
        let out = "Ejecutá la siguiente Task guardada de forma autónoma.\n"
        if (prePromptField.text) out += "\nPreprompt operativo:\n" + prePromptField.text + "\n"
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
        if (postPromptField.text) out += "\n\nPostprompt de verificación posterior:\n" + postPromptField.text
        return out
    }

    Connections {
        target: App
        function onTaskRunFinished(id, name, status, summary, silentUnlessError) {
            if (silentUnlessError && status !== "error")
                return
            resultDialog.taskId = id
            resultDialog.taskName = name || id
            resultDialog.status = status
            resultDialog.summary = summary
            resultDialog.open()
        }
    }

    LcDialog {
        id: resultDialog
        title: status === "error" ? "Task con error" : "Task finalizada"
        property string taskId: ""
        property string taskName: ""
        property string status: ""
        property string summary: ""
        implicitWidth: 520
        footer: Rectangle {
            color: Theme.popupHeaderBg
            height: 56
            radius: 12
            Rectangle { anchors.top: parent.top; width: parent.width; height: 12; color: Theme.popupHeaderBg }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.popupHeaderBorder }
            Row {
                anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                spacing: 10
                LcButton {
                    text: "Ver trabajo"
                    secondary: true
                    enabled: resultDialog.taskId.length > 0
                    onClicked: workDialog.openFor(resultDialog.taskId, resultDialog.taskName)
                }
                LcButton {
                    text: "Reintentar"
                    secondary: true
                    enabled: !App.taskRunning
                    onClicked: { resultDialog.close(); App.runTask(resultDialog.taskId) }
                }
                LcButton { text: "Cerrar"; onClicked: resultDialog.close() }
            }
        }
        contentItem: ColumnLayout {
            spacing: 8
            Text {
                Layout.fillWidth: true
                text: resultDialog.taskName
                color: Theme.textPrimary
                font { pixelSize: 14; bold: true }
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "Estado: " + (resultDialog.status === "ok" ? "correcto" : resultDialog.status)
                color: resultDialog.status === "error" ? Theme.errorText : Theme.accent
                font.pixelSize: 12
            }
            Text {
                Layout.fillWidth: true
                text: resultDialog.summary || "Sin resumen disponible."
                color: Theme.textSecondary
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }
        }
    }

    Popup {
        id: workDialog
        modal: true
        parent: Overlay.overlay
        closePolicy: Popup.CloseOnEscape
        width: Math.min(980, Math.max(640, root.width - 120))
        height: Math.min(760, Math.max(520, root.height - 100))
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        padding: 0

        property string taskId: ""
        property string taskName: ""
        property string workText: ""

        function openFor(id, name) {
            taskId = id
            taskName = name || id
            workText = App.taskRunWorkLog(id)
            open()
        }

        background: Rectangle {
            color: Theme.popupBg
            radius: 12
            border.color: Theme.popupBorderColor
            border.width: 1
        }
        Overlay.modal: Rectangle { color: Theme.overlayColor }

        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                color: Theme.popupHeaderBg
                radius: 12
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 12; color: Theme.popupHeaderBg }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.popupHeaderBorder }
                Text {
                    anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                    text: "Trabajo de la Task"
                    font { pixelSize: 14; bold: true }
                    color: Theme.textPrimary
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 18
                spacing: 10
                Text {
                    Layout.fillWidth: true
                    text: workDialog.taskName
                    color: Theme.textPrimary
                    font { pixelSize: 13; bold: true }
                    wrapMode: Text.Wrap
                }
                Text {
                    Layout.fillWidth: true
                    text: "Traza registrada: prompts enviados, eventos del agente, llamadas/resultados de tools, errores y respuesta final cuando el backend los emite."
                    color: Theme.textMuted
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    TextArea {
                        text: workDialog.workText
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextArea.Wrap
                        color: Theme.textPrimary
                        font.family: "Consolas"
                        font.pixelSize: 11
                        background: Rectangle {
                            radius: 6
                            color: Theme.inputBg
                            border.color: Theme.inputBorderColor
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                color: Theme.popupHeaderBg
                radius: 12
                Rectangle { anchors.top: parent.top; width: parent.width; height: 12; color: Theme.popupHeaderBg }
                Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.popupHeaderBorder }
                Row {
                    anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                    spacing: 10
                    LcButton {
                        text: "Copiar"
                        secondary: true
                        enabled: workDialog.workText.length > 0
                        onClicked: App.copyToClipboard(workDialog.workText)
                    }
                    LcButton { text: "Cerrar"; onClicked: workDialog.close() }
                }
            }
        }
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
