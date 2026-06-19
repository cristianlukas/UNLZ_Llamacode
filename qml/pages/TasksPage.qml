import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import LlamaCode 1.0

Item {
    id: root

    // Estado del editor (dialog). editId vacío = creando.
    property string editId: ""
    property string teachTaskId: ""
    property var teachTargets: []

    function openEditor(id) {
        editId = id
        stepsModel.clear()
        previewBox.visible = false
        previewArea.text = ""
        permFoldersModel.clear()
        if (id.length > 0) {
            const t = App.taskStore.get(id)
            nameField.text = t.name || ""
            descField.text = t.description || ""
            prePromptField.text = t.prePrompt || ""
            postPromptField.text = t.postPrompt || ""
            silentUnlessError.checked = t.silentUnlessError || false
            executionMode.currentIndex = Math.max(0, ["agent", "desktop", "browserBackground"].indexOf(t.executionMode || "agent"))
            approvalPolicy.currentIndex = Math.max(0, ["always", "sensitive", "autonomous"].indexOf(t.approvalPolicy || "sensitive"))
            timeoutSec.value = t.timeoutSec || 300
            maxActions.value = t.maxActions || 50
            maxRetries.value = t.maxRetries === undefined ? 2 : t.maxRetries
            cronField.text = t.scheduleCron || ""
            schedEnabled.checked = t.scheduleEnabled || false
            loadScheduleSpec(t.scheduleSpec || {}, t.scheduleCron || "")
            loadPermissions(t.permScope || "project", t.permFolders || [])
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
            executionMode.currentIndex = 0
            approvalPolicy.currentIndex = 1
            timeoutSec.value = 300
            maxActions.value = 50
            maxRetries.value = 2
            cronField.text = ""
            schedEnabled.checked = false
            loadScheduleSpec({}, "")
            loadPermissions("project", [])
            profileCombo.currentIndex = 0
        }
        editor.open()
    }

    // ── Permisos ──
    function loadPermissions(scope, folders) {
        const idx = scope === "folder" ? 1 : (scope === "full" ? 2 : 0)
        permScopeCombo.currentIndex = idx
        permFoldersModel.clear()
        for (var i = 0; i < (folders ? folders.length : 0); ++i)
            permFoldersModel.append({ path: folders[i] })
    }
    function collectPermScope() {
        return ["project", "folder", "full"][permScopeCombo.currentIndex] || "project"
    }
    function collectPermFolders() {
        const arr = []
        for (var i = 0; i < permFoldersModel.count; ++i)
            arr.push(permFoldersModel.get(i).path)
        return arr
    }

    // ── Schedule builder ──
    // Modos: 0 Diario · 1 Semanal · 2 Mensual · 3 Cada N meses · 4 Avanzado (cron)
    function loadScheduleSpec(spec, cronFallback) {
        const mode = (spec && spec.mode) ? spec.mode : (cronFallback ? "cron" : "daily")
        const modeIdx = { daily: 0, weekly: 1, monthly: 2, everyNMonths: 3, cron: 4 }[mode]
        freqCombo.currentIndex = modeIdx === undefined ? 0 : modeIdx
        schedHour.value = spec && spec.hour !== undefined ? spec.hour : 9
        schedMinute.value = spec && spec.minute !== undefined ? spec.minute : 0
        for (var d = 0; d < 7; ++d)
            weekdayChecks.itemAt(d).checked = spec && spec.weekdays ? (spec.weekdays.indexOf(d) >= 0) : (d === 1)
        monthlyKindCombo.currentIndex = (spec && spec.monthlyKind === "nthWeekday") ? 1 : 0
        monthDaySpin.value = spec && spec.monthDay ? spec.monthDay : 1
        nthCombo.currentIndex = spec && spec.nth ? (spec.nth - 1) : 0
        nthWeekdayCombo.currentIndex = spec && spec.nthWeekday !== undefined ? spec.nthWeekday : 1
        everyNSpin.value = spec && spec.everyN ? spec.everyN : 2
        startMonthSpin.value = spec && spec.startMonth ? spec.startMonth : 1
    }
    function buildScheduleSpec() {
        const mode = ["daily", "weekly", "monthly", "everyNMonths", "cron"][freqCombo.currentIndex]
        if (mode === "cron") return { mode: "cron", cron: cronField.text }
        const s = { mode: mode, hour: schedHour.value, minute: schedMinute.value }
        if (mode === "weekly") {
            const wd = []
            for (var d = 0; d < 7; ++d) if (weekdayChecks.itemAt(d).checked) wd.push(d)
            s.weekdays = wd
        } else if (mode === "monthly") {
            if (monthlyKindCombo.currentIndex === 1) {
                s.monthlyKind = "nthWeekday"
                s.nth = nthCombo.currentIndex + 1
                s.nthWeekday = nthWeekdayCombo.currentIndex
            } else {
                s.monthlyKind = "date"
                s.monthDay = monthDaySpin.value
            }
        } else if (mode === "everyNMonths") {
            s.everyN = everyNSpin.value
            s.monthDay = monthDaySpin.value
            s.startMonth = startMonthSpin.value
        }
        return s
    }

    // Resumen legible del schedule para la fila de la lista (espejo de TaskSchedule::describe).
    function scheduleSummary(spec, cron) {
        if (!spec || !spec.mode) return cron || "cron"
        const dn = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
        const hh = ("0" + (spec.hour || 0)).slice(-2) + ":" + ("0" + (spec.minute || 0)).slice(-2)
        if (spec.mode === "cron") return "cron · " + (spec.cron || cron || "")
        if (spec.mode === "daily") return "Diario · " + hh
        if (spec.mode === "weekly") {
            const days = (spec.weekdays || []).map(function(d) { return dn[d] })
            return "Semanal · " + days.join(", ") + " · " + hh
        }
        if (spec.mode === "monthly") {
            if (spec.monthlyKind === "nthWeekday") {
                const ord = ["", "primer", "segundo", "tercer", "cuarto", "último"]
                return "Mensual · " + ord[spec.nth || 1] + " " + dn[spec.nthWeekday || 0] + " · " + hh
            }
            return "Mensual · día " + (spec.monthDay || 1) + " · " + hh
        }
        if (spec.mode === "everyNMonths")
            return "Cada " + (spec.everyN || 1) + " mes(es) · día " + (spec.monthDay || 1) + " · " + hh
        return cron || "cron"
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
            Layout.preferredHeight: 50
            color: Theme.navBg
            RowLayout {
                anchors { fill: parent; leftMargin: 24; rightMargin: 16 }
                spacing: 8
                Text {
                    Layout.fillWidth: true
                    text: "Teach aprende una demostración y guarda una receta adaptable, no coordenadas rígidas."
                    color: Theme.textMuted
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
                LcButton {
                    text: "Enseñar escritorio"
                    secondary: true
                    onClicked: {
                        root.teachTaskId = ""
                        teachMode.currentIndex = 0
                        teachPopup.open()
                    }
                }
                LcButton {
                    text: "Enseñar navegador"
                    secondary: true
                    onClicked: {
                        root.teachTaskId = ""
                        teachMode.currentIndex = 1
                        teachPopup.open()
                    }
                }
                LcButton {
                    text: "Importar skill"
                    secondary: true
                    onClicked: importPopup.open()
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.divider }
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

        // Aviso de tool-calling del perfil activo (deriva del cookbook + chat-template).
        ToolSupportBanner {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 12
            support: App.activeProfileToolSupport
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
                                        + "  ·  " + (model.executionMode === "desktop" ? "Escritorio"
                                                       : (model.executionMode === "browserBackground" ? "Browser background" : "Agente"))
                                        + (model.automationStatus ? "  ·  " + model.automationStatus : "")
                                        + (model.scheduleEnabled ? "  ·  ⏱ " + root.scheduleSummary(model.scheduleSpec, model.scheduleCron) : "")
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
                                text: model.teachArtifactId ? "Reentrenar" : "Teach"
                                secondary: true
                                onClicked: {
                                    root.teachTaskId = taskId
                                    teachMode.currentIndex = model.executionMode === "browserBackground" ? 1 : 0
                                    teachPopup.open()
                                }
                            }
                            LcButton {
                                text: "Detener"
                                secondary: true
                                visible: App.runningTaskId === taskId
                                onClicked: App.stopAutomation()
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
    ListModel { id: permFoldersModel }

    FolderDialog {
        id: permFolderDlg
        title: "Elegir carpeta permitida para la Task"
        onAccepted: permFoldersModel.append({ path: selectedFolder.toString().replace("file:///", "") })
    }

    Popup {
        id: teachPopup
        modal: true
        parent: Overlay.overlay
        width: Math.min(680, root.width - 80)
        height: Math.min(620, root.height - 80)
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        padding: 18
        onOpened: {
            teachError.text = ""
            teachNote.text = ""
            teachTaskCombo.currentIndex = root.teachTaskId.length > 0
                ? teachTaskCombo.indexOfValue(root.teachTaskId) : 0
            refreshTargets()
        }
        function refreshTargets() {
            root.teachTargets = scopeKind.currentIndex === 0
                ? App.automationScreens() : App.automationWindows()
            targetCombo.currentIndex = root.teachTargets.length > 0 ? 0 : -1
        }
        background: Rectangle {
            color: Theme.popupBg; radius: 12
            border.color: Theme.popupBorderColor
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                text: "Modo Teach"
                color: Theme.textPrimary
                font { pixelSize: 16; bold: true }
            }
            Text {
                Layout.fillWidth: true
                text: "Mostrá la tarea y agregá notas. La automatización guardará evidencia y una receta semántica adaptable."
                wrapMode: Text.Wrap
                color: Theme.textMuted
                font.pixelSize: 11
            }
            Text { text: "Automatización"; color: Theme.textSecondary; font.pixelSize: 12 }
            LcComboBox {
                id: teachTaskCombo
                Layout.fillWidth: true
                model: App.taskStore
                textRole: "name"
                valueRole: "id"
            }
            Text { text: "Modalidad"; color: Theme.textSecondary; font.pixelSize: 12 }
            LcComboBox {
                id: teachMode
                Layout.fillWidth: true
                model: ["Escritorio foreground", "Navegador background"]
            }
            RowLayout {
                Layout.fillWidth: true
                visible: teachMode.currentIndex === 0
                LcComboBox {
                    id: scopeKind
                    Layout.preferredWidth: 150
                    model: ["Pantalla", "Ventana"]
                    onActivated: teachPopup.refreshTargets()
                }
                LcComboBox {
                    id: targetCombo
                    Layout.fillWidth: true
                    model: root.teachTargets
                    textRole: "label"
                    valueRole: "id"
                }
                LcButton { text: "Actualizar"; secondary: true; onClicked: teachPopup.refreshTargets() }
            }
            LcTextField {
                id: teachUrl
                Layout.fillWidth: true
                visible: teachMode.currentIndex === 1
                placeholderText: "URL inicial (https://...)"
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }
            Text {
                text: "Estado: " + App.teachState
                color: App.teachState === "failed" ? Theme.btnDangerBg : Theme.accent
                font.pixelSize: 12
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: App.teachTimeline
                delegate: Text {
                    width: ListView.view.width
                    text: (index + 1) + ". [" + (modelData.kind || "paso") + "] "
                          + (modelData.intent || "")
                    color: Theme.textSecondary
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
            }
            RowLayout {
                Layout.fillWidth: true
                LcTextField {
                    id: teachNote
                    Layout.fillWidth: true
                    placeholderText: "Nota sobre lo que estás haciendo…"
                }
                LcButton {
                    text: "Agregar nota"
                    secondary: true
                    enabled: teachNote.text.trim().length > 0
                    onClicked: { App.addTeachNote(teachNote.text); teachNote.text = "" }
                }
            }
            Text {
                id: teachError
                Layout.fillWidth: true
                visible: text.length > 0 || App.teachError.length > 0
                text: text.length > 0 ? text : App.teachError
                color: Theme.btnDangerBg
                wrapMode: Text.Wrap
                font.pixelSize: 11
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                LcButton {
                    text: "Iniciar"
                    visible: App.teachState !== "recording" && App.teachState !== "paused"
                    enabled: teachTaskCombo.currentValue && (teachMode.currentIndex === 1 || targetCombo.currentIndex >= 0)
                    onClicked: {
                        const err = teachMode.currentIndex === 0
                            ? App.startDesktopTeach(teachTaskCombo.currentValue,
                                scopeKind.currentIndex === 0 ? "screen" : "window",
                                targetCombo.currentValue)
                            : App.startBrowserTeach(teachTaskCombo.currentValue, teachUrl.text)
                        teachError.text = err
                    }
                }
                LcButton {
                    text: App.teachState === "paused" ? "Continuar" : "Pausar"
                    secondary: true
                    visible: App.teachState === "recording" || App.teachState === "paused"
                    onClicked: App.pauseTeach(App.teachState !== "paused")
                }
                LcButton {
                    text: "Finalizar"
                    visible: App.teachState === "recording" || App.teachState === "paused"
                    onClicked: {
                        const artifact = App.finishTeach()
                        if (artifact.length > 0) teachPopup.close()
                    }
                }
                LcButton {
                    text: "Cancelar"
                    secondary: true
                    onClicked: { App.cancelTeach(); teachPopup.close() }
                }
            }
        }
    }

    Popup {
        id: importPopup
        modal: true
        parent: Overlay.overlay
        width: 460
        height: 300
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        padding: 18
        property var skills: []
        onOpened: { skills = App.listBrowserSkills(); importError.text = "" }
        background: Rectangle { color: Theme.popupBg; radius: 12; border.color: Theme.popupBorderColor }
        contentItem: ColumnLayout {
            Text { text: "Importar skill Playwright"; color: Theme.textPrimary; font { pixelSize: 15; bold: true } }
            Text {
                Layout.fillWidth: true
                text: "Crea una Task de navegador background sin modificar el skill existente."
                color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.Wrap
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: importPopup.skills
                delegate: RowLayout {
                    width: ListView.view.width
                    Text { Layout.fillWidth: true; text: modelData; color: Theme.textSecondary }
                    LcButton {
                        text: "Importar"
                        onClicked: {
                            const id = App.importBrowserSkillAsTask(modelData)
                            if (id.length > 0) importPopup.close()
                            else importError.text = "No se pudo importar el skill."
                        }
                    }
                }
            }
            Text { id: importError; color: Theme.btnDangerBg; font.pixelSize: 11 }
            LcButton { text: "Cerrar"; secondary: true; onClicked: importPopup.close() }
        }
    }

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
                executionMode: ["agent", "desktop", "browserBackground"][executionMode.currentIndex],
                approvalPolicy: ["always", "sensitive", "autonomous"][approvalPolicy.currentIndex],
                timeoutSec: timeoutSec.value,
                maxActions: maxActions.value,
                maxRetries: maxRetries.value,
                profileId: profileCombo.selectedProfileId,
                steps: root.collectSteps(),
                scheduleEnabled: schedEnabled.checked,
                scheduleCron: cronField.text,
                scheduleSpec: root.buildScheduleSpec(),
                permScope: root.collectPermScope(),
                permFolders: root.collectPermFolders()
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
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "Modo de ejecución"; color: Theme.textSecondary; font.pixelSize: 12 }
                            LcComboBox {
                                id: executionMode
                                Layout.fillWidth: true
                                model: ["Agente general", "Escritorio foreground", "Navegador background"]
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "Aprobaciones"; color: Theme.textSecondary; font.pixelSize: 12 }
                            LcComboBox {
                                id: approvalPolicy
                                Layout.fillWidth: true
                                model: ["Confirmar siempre", "Sólo acciones sensibles", "Autónoma"]
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text { text: "Timeout (s)"; color: Theme.textSecondary; font.pixelSize: 11 }
                        SpinBox { id: timeoutSec; from: 30; to: 3600; value: 300; editable: true }
                        Text { text: "Máx. acciones"; color: Theme.textSecondary; font.pixelSize: 11 }
                        SpinBox { id: maxActions; from: 1; to: 500; value: 50; editable: true }
                        Text { text: "Reintentos"; color: Theme.textSecondary; font.pixelSize: 11 }
                        SpinBox { id: maxRetries; from: 0; to: 10; value: 2; editable: true }
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

                    // ── Permisos de acceso ──
                    Text { text: "Permisos de acceso a archivos"; color: Theme.textSecondary; font.pixelSize: 12 }
                    LcComboBox {
                        id: permScopeCombo
                        Layout.fillWidth: true
                        model: ["Solo el proyecto (seguro)", "Una o varias carpetas específicas", "Toda la PC"]
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Theme.textMuted
                        font.pixelSize: 11
                        text: permScopeCombo.currentIndex === 2
                              ? "El agente podrá leer y escribir en cualquier ruta del disco. Usalo solo si confiás en la Task."
                              : (permScopeCombo.currentIndex === 1
                                 ? "El agente podrá leer/escribir dentro de las carpetas elegidas (además del proyecto)."
                                 : "El agente queda confinado a la carpeta de trabajo del perfil/agente.")
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: permScopeCombo.currentIndex === 1
                        spacing: 6
                        Repeater {
                            model: permFoldersModel
                            delegate: RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Text {
                                    Layout.fillWidth: true
                                    text: model.path
                                    color: Theme.textPrimary
                                    font.pixelSize: 12
                                    elide: Text.ElideMiddle
                                }
                                LcButton { text: "✕"; secondary: true; onClicked: permFoldersModel.remove(index) }
                            }
                        }
                        LcButton {
                            text: "+ Agregar carpeta…"
                            secondary: true
                            onClicked: permFolderDlg.open()
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.divider }

                    // ── Programación ──
                    CheckBox {
                        id: schedEnabled
                        text: "Programar ejecución automática"
                        contentItem: Text {
                            text: schedEnabled.text; color: Theme.textSecondary; font.pixelSize: 12
                            leftPadding: schedEnabled.indicator.width + 6; verticalAlignment: Text.AlignVCenter
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: schedEnabled.checked
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "Frecuencia"; color: Theme.textSecondary; font.pixelSize: 12; Layout.preferredWidth: 90 }
                            LcComboBox {
                                id: freqCombo
                                Layout.fillWidth: true
                                model: ["Diario", "Semanal", "Mensual", "Cada N meses", "Avanzado (cron)"]
                            }
                        }

                        // Hora (todas las frecuencias menos cron)
                        RowLayout {
                            Layout.fillWidth: true
                            visible: freqCombo.currentIndex !== 4
                            spacing: 10
                            Text { text: "Hora"; color: Theme.textSecondary; font.pixelSize: 12; Layout.preferredWidth: 90 }
                            SpinBox { id: schedHour; from: 0; to: 23; value: 9; editable: true }
                            Text { text: ":"; color: Theme.textSecondary }
                            SpinBox { id: schedMinute; from: 0; to: 59; value: 0; editable: true }
                        }

                        // Semanal: días
                        RowLayout {
                            Layout.fillWidth: true
                            visible: freqCombo.currentIndex === 1
                            spacing: 6
                            Text { text: "Días"; color: Theme.textSecondary; font.pixelSize: 12; Layout.preferredWidth: 90 }
                            Repeater {
                                id: weekdayChecks
                                model: ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
                                delegate: CheckBox {
                                    property bool checkedProxy: checked
                                    text: modelData
                                    contentItem: Text {
                                        text: modelData; color: Theme.textSecondary; font.pixelSize: 11
                                        leftPadding: parent.indicator.width + 3; verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }

                        // Mensual
                        RowLayout {
                            Layout.fillWidth: true
                            visible: freqCombo.currentIndex === 2
                            spacing: 10
                            Text { text: "Cuándo"; color: Theme.textSecondary; font.pixelSize: 12; Layout.preferredWidth: 90 }
                            LcComboBox {
                                id: monthlyKindCombo
                                Layout.preferredWidth: 150
                                model: ["Por fecha (día N)", "Por posición"]
                            }
                            SpinBox {
                                id: monthDaySpin
                                visible: monthlyKindCombo.currentIndex === 0 || freqCombo.currentIndex === 3
                                from: 1; to: 31; value: 1; editable: true
                            }
                            LcComboBox {
                                id: nthCombo
                                visible: monthlyKindCombo.currentIndex === 1 && freqCombo.currentIndex === 2
                                Layout.preferredWidth: 110
                                model: ["primer", "segundo", "tercer", "cuarto", "último"]
                            }
                            LcComboBox {
                                id: nthWeekdayCombo
                                visible: monthlyKindCombo.currentIndex === 1 && freqCombo.currentIndex === 2
                                Layout.preferredWidth: 90
                                model: ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
                            }
                        }

                        // Cada N meses
                        RowLayout {
                            Layout.fillWidth: true
                            visible: freqCombo.currentIndex === 3
                            spacing: 10
                            Text { text: "Cada"; color: Theme.textSecondary; font.pixelSize: 12; Layout.preferredWidth: 90 }
                            SpinBox { id: everyNSpin; from: 1; to: 24; value: 2; editable: true }
                            Text { text: "mes(es), desde el mes"; color: Theme.textSecondary; font.pixelSize: 12 }
                            SpinBox { id: startMonthSpin; from: 1; to: 12; value: 1; editable: true }
                        }

                        // Avanzado (cron)
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: freqCombo.currentIndex === 4
                            spacing: 4
                            LcTextField {
                                id: cronField
                                Layout.fillWidth: true
                                placeholderText: "0 9 * * *  (min hora dia mes diaSem)"
                            }
                            Text {
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                color: Theme.textMuted
                                font.pixelSize: 11
                                text: "Formato: min hora diaMes mes diaSem. Ej: 0 9 * * * = 9:00 todos los días · "
                                    + "*/15 9-17 * * 1-5 = cada 15 min, 9-17h, lun-vie. Domingo = 0 o 7."
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: Theme.textMuted
                            font.pixelSize: 11
                            text: "El scheduler solo dispara mientras la app está abierta y con server+agente encendidos."
                        }
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
