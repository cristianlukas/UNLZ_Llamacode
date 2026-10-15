import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import LlamaCode 1.0

// Sección "agentProfilesSection" de Configuración, extraída de SettingsPage.qml (antes
// 3.500 líneas en un solo archivo). La visibilidad la decide la página.
ColumnLayout {
    id: section
    Layout.fillWidth: true
    spacing: 10

    // Copia de trabajo del perfil en edición. enabledTools/
    // directives son arrays JS; "*" = todo (presets de sistema).
    property var edit: ({ id: "", name: "", system: false,
                          enabledTools: [], directives: [],
                          approvalMode: "ask", thinking: false,
                          temperature: -1, systemExtra: "",
                          personalityProfileIds: [], styleProfileIds: [],
                          injectStyleExamples: true, styleExampleLimit: 2,
                          styleContextLimit: 6000,
                          thinkingLeakGuard: false,
                          progressCredits: 8, progressMaxCredits: 16,
                          progressReplanAfter: 3, progressStopAfter: 5,
                          quickToolTimeoutSec: 15 })
    property var toolGroups: []     // agrupado por categoría
    property var directiveItems: [] // catálogo de directivas
    property int enabledCount: 0
    property int enabledTokens: 0
    // ── Harness modular ──
    // specEdit espeja los módulos del HarnessSpec resuelto del
    // perfil. Sólo se persiste lo que el usuario toca: guardamos
    // el spec entero, y el backend vuelve a resolver la cadena.
    property var specEdit: ({})
    property var specDiff: []       // {module, field, base, value}
    property var specSummary: ({})  // tools/approxTokens/warnings
    property var packItems: []      // catálogo de packs de tools
    property var skillItems: []     // skills portables disponibles
    property var customDirectiveItems: []  // directivas .md del usuario
    property var parentOptions: []  // candidatos a `extends` (sin ciclos)
    property var styleEdit: ({ id: "", name: "", kind: "writing-style",
                               description: "", styleCard: "", examples: [] })
    readonly property string styleExampleSeparator: "\n\n--- EJEMPLO ---\n\n"
    readonly property bool isSystem: edit.system === true

    function allToolNames() {
        var list = App.agentToolCatalog(), out = []
        for (var i = 0; i < list.length; ++i) out.push(list[i].name)
        return out
    }
    // ── Harness modular ──
    // Los helpers de edicion del spec viven en LcHarnessEditor
    // (ahi son testeables). Aca queda el cableado con App.
    function refreshHarnessInfo() {
        if (!edit.id) return
        specSummary = App.harnessSpecSummary(edit.id) || ({})
        specDiff = App.profileManager.agentProfileDiff(edit.id) || []
        packItems = App.profileManager.harnessPackCatalog() || []
        skillItems = App.portableSkills() || []
        customDirectiveItems = App.profileManager.harnessDirectiveCatalog(App.currentAgentProjectDir()) || []
        // Candidatos a `extends`: el propio perfil y su subarbol
        // quedan afuera (ofrecer un ciclo es ofrecer un error).
        parentOptions = App.profileManager.eligibleParents(edit.id) || []
    }
    function saveHarnessSpec() {
        if (isSystem || !edit.id) return
        var s = JSON.parse(JSON.stringify(specEdit || {}))
        s.extends = harnessEditor.currentExtends()
        App.profileManager.updateAgentProfile({ "id": edit.id, "spec": s,
                                                "extends": s.extends })
        App.profileManager.saveProfiles()
        refreshHarnessInfo()
    }
    function allDirectiveKeys() {
        var cat = App.agentDirectiveCatalog(), out = []
        for (var i = 0; i < cat.length; ++i) out.push(cat[i].key)
        return out
    }
    function isToolOn(name) {
        return edit.enabledTools.indexOf("*") >= 0
            || edit.enabledTools.indexOf(name) >= 0
    }
    function isDirOn(key) {
        // honey es opt-in LITERAL: no lo implica el sentinel "*"
        // (Máximo) — hay que nombrarlo. Coincide con el gateo del
        // backend (buildSystemPrompt sólo lo activa por contains).
        if (key === "honey") return edit.directives.indexOf("honey") >= 0
        return edit.directives.indexOf("*") >= 0
            || edit.directives.indexOf(key) >= 0
    }
    function parseStyleExamples(text) {
        var chunks = text.split(styleExampleSeparator), out = []
        for (var i = 0; i < chunks.length; ++i) {
            var value = chunks[i].trim()
            if (value.length) out.push(value)
        }
        return out
    }
    function formatStyleExamples(examples) {
        var out = []
        for (var i = 0; i < (examples || []).length; ++i) {
            var value = String(examples[i] || "").trim()
            if (value.length) out.push(value)
        }
        return out.join(styleExampleSeparator)
    }
    function selectStyleProfile(id) {
        var p = App.profileManager.getPersonaStyleProfile(id)
        if (!p || !p.id) return
        styleEdit = { id: p.id, name: p.name, kind: p.kind || "writing-style",
                      description: p.description || "", styleCard: p.styleCard || "",
                      examples: (p.examples || []).slice() }
        styleNameField.text = styleEdit.name
        styleDescriptionField.text = styleEdit.description
        styleCardField.text = styleEdit.styleCard
        styleExamplesField.text = formatStyleExamples(styleEdit.examples)
        var ki = styleKindCombo.indexOfValue(styleEdit.kind)
        if (ki >= 0) styleKindCombo.currentIndex = ki
    }
    function saveStyleProfile() {
        if (!styleEdit.id) return
        App.profileManager.updatePersonaStyleProfile({
            id: styleEdit.id, name: styleNameField.text.trim(), kind: styleKindCombo.currentValue,
            description: styleDescriptionField.text, styleCard: styleCardField.text,
            examples: parseStyleExamples(styleExamplesField.text)
        })
    }
    function createStyleProfile() {
        var id = App.profileManager.addPersonaStyleProfile("Nuevo estilo", "writing-style")
        styleProfileSelector.currentIndex = styleProfileSelector.indexOfValue(id)
        selectStyleProfile(id)
    }
    function setToolOn(name, on) {
        var arr = edit.enabledTools.slice()
        if (arr.indexOf("*") >= 0) arr = allToolNames()   // expandir antes de editar
        var i = arr.indexOf(name)
        if (on && i < 0) arr.push(name)
        else if (!on && i >= 0) arr.splice(i, 1)
        edit.enabledTools = arr
        recount()
    }
    function setDirOn(key, on) {
        var arr = edit.directives.slice()
        // Expandir "*" SIN honey: no se debe activar al desmarcar
        // otra directiva de un preset Máximo (honey = opt-in literal).
        if (arr.indexOf("*") >= 0)
            arr = allDirectiveKeys().filter(function(k){ return k !== "honey" })
        var i = arr.indexOf(key)
        if (on && i < 0) arr.push(key)
        else if (!on && i >= 0) arr.splice(i, 1)
        edit.directives = arr
    }
    function recount() {
        var list = App.agentToolCatalog(), cnt = 0, tok = 0
        for (var i = 0; i < list.length; ++i)
            if (isToolOn(list[i].name)) { cnt += 1; tok += list[i].approxTokens }
        enabledCount = cnt; enabledTokens = tok
    }
    function rebuildGroups() {
        var list = App.agentToolCatalog()
        var order = [], byGroup = {}
        for (var i = 0; i < list.length; ++i) {
            var t = list[i]
            if (byGroup[t.group] === undefined) { byGroup[t.group] = []; order.push(t.group) }
            byGroup[t.group].push(t)
        }
        var g = []
        for (var k = 0; k < order.length; ++k)
            g.push({ name: order[k], tools: byGroup[order[k]] })
        toolGroups = g
        directiveItems = App.agentDirectiveCatalog()
        recount()
    }
    function selectProfile(id) {
        var p = App.profileManager.getAgentProfile(id)
        if (!p || !p.id) return
        edit = { id: p.id, name: p.name, system: p.system === true,
                 enabledTools: (p.enabledTools || []).slice(),
                 directives: (p.directives || []).slice(),
                 approvalMode: p.approvalMode || "ask",
                 thinking: p.thinking === true,
                 thinkingLeakGuard: p.thinkingLeakGuard === true,
                 progressCredits: p.progressCredits || 8,
                 progressMaxCredits: p.progressMaxCredits || 16,
                 progressReplanAfter: p.progressReplanAfter || 3,
                 progressStopAfter: p.progressStopAfter || 5,
                 quickToolTimeoutSec: p.quickToolTimeoutSec || 15,
                 temperature: (p.temperature === undefined ? -1 : p.temperature),
                 systemExtra: p.systemExtra || "",
                 personalityProfileIds: (p.personalityProfileIds || []).slice(),
                 styleProfileIds: (p.styleProfileIds || []).slice(),
                 injectStyleExamples: p.injectStyleExamples !== false,
                 styleExampleLimit: p.styleExampleLimit || 2,
                 styleContextLimit: p.styleContextLimit || 6000 }
        apNameField.text = edit.name
        extraField.text = edit.systemExtra
        tempField.text = edit.temperature >= 0 ? String(edit.temperature) : ""
        approvalCombo.currentIndex = Math.max(0, approvalCombo.indexOfValue(edit.approvalMode))
        progressCreditsField.text = String(edit.progressCredits)
        progressMaxField.text = String(edit.progressMaxCredits)
        progressReplanField.text = String(edit.progressReplanAfter)
        progressStopField.text = String(edit.progressStopAfter)
        quickToolTimeoutField.text = String(edit.quickToolTimeoutSec)
        examplesSwitch.checked = edit.injectStyleExamples !== false
        styleExampleLimitField.text = String(edit.styleExampleLimit || 2)
        styleContextLimitField.text = String(edit.styleContextLimit || 6000)
        var pid = (edit.personalityProfileIds || []).length ? edit.personalityProfileIds[0] : ""
        var sid = (edit.styleProfileIds || []).length ? edit.styleProfileIds[0] : ""
        var pi = personalitySelector.indexOfValue(pid); if (pi >= 0) personalitySelector.currentIndex = pi
        var si = styleSelector.indexOfValue(sid); if (si >= 0) styleSelector.currentIndex = si
        // Harness modular: cargar el spec resuelto + info derivada.
        specEdit = App.profileManager.agentProfileSpec(p.id) || ({})
        refreshHarnessInfo()
        harnessEditor.setExtends(specEdit.extends || "")
        rebuildGroups()  // recrea delegates → switches re-evaluan checked
    }
    function save() {
        if (isSystem) return
        App.profileManager.updateAgentProfile({
            "id": edit.id,
            "name": apNameField.text.trim().length ? apNameField.text.trim() : edit.name,
            "enabledTools": edit.enabledTools,
            "directives": edit.directives,
            "approvalMode": approvalCombo.currentValue || "ask",
            "thinking": thinkingSwitch.checked,
            "thinkingLeakGuard": thinkingLeakGuardSwitch.checked,
            "progressCredits": parseInt(progressCreditsField.text) || 8,
            "progressMaxCredits": parseInt(progressMaxField.text) || 16,
            "progressReplanAfter": parseInt(progressReplanField.text) || 3,
            "progressStopAfter": parseInt(progressStopField.text) || 5,
            "quickToolTimeoutSec": parseInt(quickToolTimeoutField.text) || 15,
            "temperature": (tempField.text.trim().length && !isNaN(parseFloat(tempField.text)))
                           ? parseFloat(tempField.text) : -1,
            "systemExtra": extraField.text,
            "personalityProfileIds": section.edit.personalityProfileIds,
            "styleProfileIds": section.edit.styleProfileIds,
            "injectStyleExamples": examplesSwitch.checked,
            "styleExampleLimit": parseInt(styleExampleLimitField.text) || 2,
            "styleContextLimit": parseInt(styleContextLimitField.text) || 6000
        })
        App.profileManager.saveProfiles()
    }

    Component.onCompleted: {
        // Arrancar editando el perfil activo resuelto.
        var id = App.activeAgentProfileId
        var idx = profileSelector.indexOfValue(id)
        if (idx >= 0) profileSelector.currentIndex = idx
        selectProfile(id)
    }

    RowLayout {
        Layout.fillWidth: true
        Text {
            text: (App.langV, App.l("settings.sec.agentProfiles")).toUpperCase()
            color: Theme.accent
            font.pixelSize: 11
            font.bold: true
        }
        Item { Layout.fillWidth: true }
        Text {
            text: section.enabledCount + " tools · ~"
                  + section.enabledTokens + " tok"
            color: Theme.textMuted
            font.pixelSize: 11
        }
    }

    // Selector de perfil + acciones.
    RowLayout {
        Layout.fillWidth: true
        spacing: 8
        LcComboBox {
            id: profileSelector
            Layout.fillWidth: true
            model: App.profileManager.agentProfiles
            textRole: "name"; valueRole: "profileId"
            onActivated: section.selectProfile(currentValue)
            background: Rectangle { color: Theme.inputBg; radius: 6; border.color: Theme.borderColor }
            contentItem: Text { text: profileSelector.displayText; color: Theme.textPrimary; font.pixelSize: 13; leftPadding: 10; verticalAlignment: Text.AlignVCenter }
        }
        LcButton {
            text: "Nuevo"
            secondary: true
            onClicked: {
                var id = App.profileManager.addAgentProfile("Nuevo perfil")
                var idx = profileSelector.indexOfValue(id)
                if (idx >= 0) profileSelector.currentIndex = idx
                section.selectProfile(id)
            }
        }
        LcButton {
            text: "Duplicar"
            secondary: true
            enabled: section.edit.id.length > 0
            onClicked: {
                var id = App.profileManager.duplicateAgentProfile(section.edit.id)
                if (!id) return
                var idx = profileSelector.indexOfValue(id)
                if (idx >= 0) profileSelector.currentIndex = idx
                section.selectProfile(id)
            }
        }
        LcButton {
            text: "Eliminar"
            danger: true
            enabled: section.edit.id.length > 0 && !section.isSystem
            onClicked: {
                App.profileManager.removeAgentProfile(section.edit.id)
                profileSelector.currentIndex = 0
                section.selectProfile(
                    profileSelector.currentValue || App.activeAgentProfileId)
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        color: Theme.surfaceBg
        border.color: Theme.borderColor
        radius: 10
        implicitHeight: profInner.implicitHeight + 32

        ColumnLayout {
            id: profInner
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 14

            // Aviso para perfiles de sistema (solo lectura).
            Rectangle {
                Layout.fillWidth: true
                visible: section.isSystem
                color: Theme.inputBg
                border.color: Theme.warnText
                radius: 8
                implicitHeight: sysNote.implicitHeight + 16
                Text {
                    id: sysNote
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 10 }
                    text: "Perfil de sistema (solo lectura). Duplicalo para crear una copia editable."
                    color: Theme.warnText
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }

            // Ajustes generales del perfil.
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 10
                enabled: !section.isSystem

                Text { text: "Nombre"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: apNameField; Layout.fillWidth: true }

                Text { text: "Aprobación"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: approvalCombo
                    Layout.fillWidth: true
                    textRole: "label"; valueRole: "key"
                    model: [
                        { key: "auto",   label: "Aprobar todo" },
                        { key: "ask",    label: "Pedir escritura" },
                        { key: "manual", label: "Pedir todo" },
                        { key: "super",  label: "Super Agente ⚠" },
                        { key: "plan",   label: "Plan (solo lectura)" }
                    ]
                    background: Rectangle { color: Theme.inputBg; radius: 6; border.color: Theme.borderColor }
                    contentItem: Text { text: approvalCombo.displayText; color: Theme.textPrimary; font.pixelSize: 13; leftPadding: 10; verticalAlignment: Text.AlignVCenter }
                }

                Text { text: "Razonar"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcSwitch {
                    id: thinkingSwitch
                    checked: section.edit.thinking
                }

                Text { text: "Compatibilidad thinking"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcSwitch {
                    id: thinkingLeakGuardSwitch
                    checked: section.edit.thinkingLeakGuard === true
                    ToolTip.visible: hovered
                    ToolTip.text: "Opt-in por perfil: no preserva razonamiento previo y corta colas repetidas después de un </think> huérfano. Dejalo apagado salvo que el modelo presente esa fuga."
                }

                Text { text: "Indicador de escritorio"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcSwitch {
                    checked: App.desktopIndicatorVisible
                    onToggled: App.desktopIndicatorVisible = checked
                    ToolTip.visible: hovered
                    ToolTip.text: "Muestra una señal siempre visible mientras la IA controla mouse, teclado o ventanas."
                }

                Text { text: "Temperatura"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: tempField; Layout.fillWidth: true; placeholderText: "vacío = heredar del modelo" }

                Text { text: "Créditos de progreso"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: progressCreditsField; Layout.fillWidth: true; placeholderText: "8" }

                Text { text: "Máximo renovable"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: progressMaxField; Layout.fillWidth: true; placeholderText: "16" }

                Text { text: "Replantear tras"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: progressReplanField; Layout.fillWidth: true; placeholderText: "3 acciones sin progreso" }

                Text { text: "Cerrar tras replanteo"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: progressStopField; Layout.fillWidth: true; placeholderText: "5 acciones sin progreso" }

                Text { text: "Timeout tool rápida (s)"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: quickToolTimeoutField; Layout.fillWidth: true; placeholderText: "15" }

                Text { text: "Instrucciones extra"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: extraField; Layout.fillWidth: true; placeholderText: "opcional, se añade al system prompt" }

                Text { text: "Personalidad"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: personalitySelector; Layout.fillWidth: true
                    model: App.profileManager.personalityProfiles; textRole: "name"; valueRole: "profileId"
                    onActivated: section.edit.personalityProfileIds = currentValue ? [currentValue] : []
                    background: Rectangle { color: Theme.inputBg; radius: 6; border.color: Theme.borderColor }
                    contentItem: Text { text: personalitySelector.displayText || "Ninguna"; color: Theme.textPrimary; leftPadding: 10; verticalAlignment: Text.AlignVCenter }
                }

                Text { text: "Estilo de escritura"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: styleSelector; Layout.fillWidth: true
                    model: App.profileManager.writingStyleProfiles; textRole: "name"; valueRole: "profileId"
                    onActivated: section.edit.styleProfileIds = currentValue ? [currentValue] : []
                    background: Rectangle { color: Theme.inputBg; radius: 6; border.color: Theme.borderColor }
                    contentItem: Text { text: styleSelector.displayText || "Ninguno"; color: Theme.textPrimary; leftPadding: 10; verticalAlignment: Text.AlignVCenter }
                }

                Text { text: "Inyectar ejemplos"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcSwitch { id: examplesSwitch; checked: section.edit.injectStyleExamples !== false }

                Text { text: "Máximo de ejemplos"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: styleExampleLimitField; Layout.fillWidth: true; text: "2"; placeholderText: "2" }

                Text { text: "Límite de contexto de estilo"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: styleContextLimitField; Layout.fillWidth: true; text: "6000"; placeholderText: "6000 caracteres" }
            }

            Text { text: "PERFILES DE PERSONALIDAD Y ESTILO"; color: Theme.accent; font.pixelSize: 11; font.bold: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                LcComboBox {
                    id: styleProfileSelector; Layout.fillWidth: true
                    model: App.profileManager.personaStyleProfiles; textRole: "name"; valueRole: "profileId"
                    onActivated: section.selectStyleProfile(currentValue)
                    background: Rectangle { color: Theme.inputBg; radius: 6; border.color: Theme.borderColor }
                    contentItem: Text { text: styleProfileSelector.displayText || "Seleccioná un perfil"; color: Theme.textPrimary; leftPadding: 10; verticalAlignment: Text.AlignVCenter }
                }
                LcButton { text: "Nuevo"; secondary: true; onClicked: section.createStyleProfile() }
                LcButton { text: "Guardar estilo"; secondary: true; enabled: !!section.styleEdit.id; onClicked: section.saveStyleProfile() }
                LcButton { text: "Exportar JSON"; secondary: true; enabled: !!section.styleEdit.id; onClicked: styleJsonField.text = App.profileManager.exportPersonaStyleProfile(section.styleEdit.id) }
                LcButton { text: "Importar JSON"; secondary: true; enabled: styleJsonField.text.trim().length > 0; onClicked: { var id = App.profileManager.importPersonaStyleProfile(styleJsonField.text); if (id) { styleProfileSelector.currentIndex = styleProfileSelector.indexOfValue(id); section.selectStyleProfile(id) } } }
            }
            GridLayout {
                Layout.fillWidth: true; columns: 2; columnSpacing: 10; rowSpacing: 8
                enabled: !!section.styleEdit.id && !section.isSystem
                Text { text: "Nombre"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: styleNameField; Layout.fillWidth: true }
                Text { text: "Tipo"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: styleKindCombo; Layout.fillWidth: true; textRole: "label"; valueRole: "value"
                    model: [{label: "Estilo de escritura", value: "writing-style"}, {label: "Personalidad", value: "personality"}]
                    background: Rectangle { color: Theme.inputBg; radius: 6; border.color: Theme.borderColor }
                    contentItem: Text { text: styleKindCombo.displayText; color: Theme.textPrimary; leftPadding: 10; verticalAlignment: Text.AlignVCenter }
                }
                Text { text: "Descripción"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcTextField { id: styleDescriptionField; Layout.fillWidth: true; placeholderText: "Para qué conviene usarlo" }
                Text { text: "Ficha"; color: Theme.textSecondary; font.pixelSize: 12 }
                TextArea { id: styleCardField; Layout.fillWidth: true; Layout.minimumHeight: 72; wrapMode: TextArea.Wrap; color: Theme.textPrimary; placeholderText: "Tono, ritmo, vocabulario, preferencias y cosas a evitar" }
                Text { text: "Muestras"; color: Theme.textSecondary; font.pixelSize: 12 }
                TextArea { id: styleExamplesField; Layout.fillWidth: true; Layout.minimumHeight: 100; wrapMode: TextArea.Wrap; color: Theme.textPrimary; placeholderText: "Pegá una o más muestras. Separalas con --- EJEMPLO ---. Se usan sólo como referencia y quedan locales." }
            }
            TextArea {
                id: styleJsonField; Layout.fillWidth: true; Layout.minimumHeight: 70
                wrapMode: TextArea.WrapAnywhere; color: Theme.textPrimary
                placeholderText: "JSON para importar/exportar (queda local)"
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                LcButton {
                    text: "Completar ficha desde muestra"; secondary: true
                    enabled: styleExamplesField.text.trim().length > 0 && !!section.styleEdit.id
                    onClicked: styleCardField.text = App.profileManager.heuristicStyleCard(styleExamplesField.text)
                }
                LcButton {
                    text: "Analizar con modelo"; secondary: true
                    enabled: styleExamplesField.text.trim().length > 0 && !!section.styleEdit.id && App.personaStyleAnalysisStatus !== "running"
                    onClicked: App.analyzePersonaStyleProfile(section.styleEdit.id, styleExamplesField.text)
                }
                Text {
                    Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.textMuted; font.pixelSize: 11
                    text: App.personaStyleAnalysisStatus === "running" ? "Analizando…" : (App.personaStyleAnalysisError || "Revisá la ficha antes de guardarla.")
                }
            }
            Text {
                Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.textMuted; font.pixelSize: 11
                text: "La ficha se inyecta como preferencia de expresión. No modifica permisos, herramientas ni guardrails. Podés generarla localmente o analizar la muestra con el modelo activo; revisala antes de guardarla."
            }

            // Guardrail global (no per-perfil): acciones destructivas
            // requieren aprobación humana aun en modo auto. En "Super
            // Agente" no aplica (autonomía total).
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: "Guardrail de acciones destructivas"; color: Theme.textPrimary; font.pixelSize: 13 }
                    Text {
                        text: "Fuerza aprobación humana antes de acciones irreversibles (borrado recursivo, format, git push --force, DROP de DB, borrar memoria, clicks de escritorio delete/eliminar), incluso en modo automático y en sub-agentes. No aplica en Super Agente."
                        color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true
                    }
                }
                LcSwitch {
                    checked: App.hitlDestructive
                    onToggled: App.hitlDestructive = checked
                }
            }

            // ── Harness modular ──
            // La lógica vive en LcHarnessEditor (componente
            // testeable): acá sólo se cablea con App. Ver
            // docs/harness.md y tests/qml/tst_harness_editor.qml.
            LcHarnessEditor {
                id: harnessEditor
                Layout.fillWidth: true
                profileId: section.edit.id
                readOnly: section.isSystem
                spec: section.specEdit
                summary: section.specSummary
                diff: section.specDiff
                packs: section.packItems
                skills: section.skillItems
                directives: section.customDirectiveItems
                parents: section.parentOptions
                engines: App.harnessEngineCatalog()
                // Los módulos del harness los aplica el agente
                // nativo; con otro backend el editor mentiría.
                // Sin agente corriendo no hay nada que advertir; con
                // uno que no sea el nativo, sí (no consume el spec).
                specApplies: App.activeAgentAdapter.length === 0
                             || App.activeAgentAdapter === "llamaagent"
                specAppliesNote: "El agente activo (" + App.activeAgentAdapter
                                 + ") no es el nativo: los módulos del harness "
                                 + "no se le aplican."
                onSpecEdited: function (s) { section.specEdit = s }
                onSaveRequested: section.saveHarnessSpec()
                onDirectiveSaveRequested: function (name, description, when, body, scope) {
                    App.saveHarnessDirective(name, description, when, body, scope)
                    section.refreshHarnessInfo()
                }
                onDirectiveRemoveRequested: function (name, scope) {
                    App.removeHarnessDirective(name, scope)
                    section.refreshHarnessInfo()
                }
                // El componente no lee del disco: le pasamos el
                // cuerpo resuelto para que abra el editor.
                onDirectiveOpenRequested: function (name) {
                    var d = App.harnessDirective(name)
                    if (d && d.ok) harnessEditor.editDirective(d)
                }
                // Los hechos de `when` los define el backend.
                directiveFacts: App.harnessDirectiveFacts()
            }

            // ── Directivas ──
            Text {
                text: "DIRECTIVAS (system prompt)"
                color: Theme.accent
                font.pixelSize: 11
                font.bold: true
            }
            Repeater {
                model: section.directiveItems
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    radius: 8
                    color: Theme.inputBg
                    border.color: Theme.borderColor
                    implicitHeight: dRow.implicitHeight + 16
                    opacity: section.isSystem ? 0.6 : 1.0

                    RowLayout {
                        id: dRow
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 10 }
                        spacing: 8
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: modelData.name
                                color: Theme.textPrimary
                                font.pixelSize: 13
                                font.bold: true
                            }
                            Text {
                                text: modelData.description
                                color: Theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                        LcSwitch {
                            enabled: !section.isSystem
                            checked: section.isDirOn(modelData.key)
                            onToggled: section.setDirOn(modelData.key, checked)
                        }
                    }
                }
            }

            // ── Capacidades (tools) ──
            Text {
                text: "CAPACIDADES (tools)"
                color: Theme.accent
                font.pixelSize: 11
                font.bold: true
            }
            Text {
                text: "Apagar las que no usás ahorra contexto (clave en modelos locales chicos)."
                color: Theme.textSecondary
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: section.toolGroups
                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        text: modelData.name
                        color: Theme.textPrimary
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Repeater {
                        model: modelData.tools
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            radius: 8
                            color: Theme.inputBg
                            border.color: Theme.borderColor
                            implicitHeight: tRow.implicitHeight + 16
                            opacity: section.isSystem ? 0.6 : 1.0

                            RowLayout {
                                id: tRow
                                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 10 }
                                spacing: 8
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    RowLayout {
                                        spacing: 8
                                        Text {
                                            text: modelData.name
                                            color: Theme.textPrimary
                                            font.pixelSize: 13
                                            font.bold: true
                                            font.family: Theme.codeFont
                                        }
                                        Text {
                                            text: "~" + modelData.approxTokens
                                            color: Theme.textMuted
                                            font.pixelSize: 10
                                        }
                                    }
                                    Text {
                                        text: modelData.description
                                        color: Theme.textMuted
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                                LcSwitch {
                                    enabled: !section.isSystem
                                    checked: section.isToolOn(modelData.name)
                                    onToggled: section.setToolOn(modelData.name, checked)
                                }
                            }
                        }
                    }
                }
            }

            LcButton {
                text: "Guardar perfil"
                Layout.alignment: Qt.AlignRight
                enabled: !section.isSystem && section.edit.id.length > 0
                onClicked: section.save()
            }
        }
    }
}
