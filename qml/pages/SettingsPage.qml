import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import LlamaCode 1.0
import "../components/SettingsTabsPolicy.js" as SettingsTabs

Item {
    id: root

    LcColorPicker {
        id: colorPicker
        property var target: null
        onPicked: function (hex) { if (target) target.value = hex }
    }

    // Tarjeta plegable (cerrada por defecto) para bloques largos de una sección.
    component Collapsible: ColumnLayout {
        id: collapsible
        property string title: ""
        property string subtitle: ""
        property bool expanded: false
        default property alias content: collapsibleBody.data
        Layout.fillWidth: true
        spacing: 6
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: collapsibleHeader.implicitHeight + 16
            radius: 6
            color: collapsibleMouse.containsMouse ? Theme.hoverBg : "transparent"
            border.color: Theme.borderColor
            RowLayout {
                id: collapsibleHeader
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 10 }
                spacing: 8
                Text { text: collapsible.expanded ? "▾" : "▸"; color: Theme.textSecondary; font.pixelSize: 12 }
                Text { text: collapsible.title; color: Theme.textPrimary; font.pixelSize: 13; font.bold: true }
                Text {
                    Layout.fillWidth: true
                    text: collapsible.subtitle
                    color: Theme.textMuted; font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
            MouseArea {
                id: collapsibleMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: collapsible.expanded = !collapsible.expanded
            }
        }
        ColumnLayout {
            id: collapsibleBody
            Layout.fillWidth: true
            Layout.leftMargin: 22
            visible: collapsible.expanded
            spacing: 8
        }
    }

    property var gpuRows: []
    property var selectedVramGpus: []
    property string settingsSearchText: ""
    // Pestaña activa (se recuerda entre aperturas). Con búsqueda se ignora y se
    // muestran las coincidencias de todas las pestañas.
    property string currentTab: {
        const saved = String(App.readSetting("settings/tab", "general"))
        return SettingsTabs.isValidTab(saved) ? saved : "general"
    }
    onCurrentTabChanged: {
        App.writeSetting("settings/tab", currentTab)
        scroll.contentItem.contentY = 0
    }

    function sectionVisible(section, sectionId) {
        return SettingsTabs.isSectionVisible(sectionId, currentTab, settingsSearchText,
                                             matchesSettingsSearch(section))
    }
    function sectionById(sectionId) {
        const map = {
            appearanceSection: appearanceSection, customSection: customSection,
            languageSection: languageSection, gpuInferenceSection: gpuInferenceSection,
            astraSection: astraSection, systemSection: systemSection,
            performanceSection: performanceSection, gatewaySection: gatewaySection,
            chatSection: chatSection, gpuSection: gpuSection, intgSection: intgSection,
            agentProfilesSection: agentProfilesSection, teacherSection: teacherSection,
            auxiliarySection: auxiliarySection, mailSection: mailSection, dataSection: dataSection
        }
        return map[sectionId]
    }

    function normalizedSearchText(value) {
        return String(value ?? "").toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    }

    function collectSettingsText(item) {
        if (!item) return ""
        var result = ""
        if (item.text !== undefined) result += " " + String(item.text)
        if (item.placeholderText !== undefined) result += " " + String(item.placeholderText)
        if (item.title !== undefined) result += " " + String(item.title)
        if (item.children) {
            for (var i = 0; i < item.children.length; ++i)
                result += " " + collectSettingsText(item.children[i])
        }
        return result
    }

    function matchesSettingsSearch(item) {
        var query = normalizedSearchText(settingsSearchText).trim()
        if (!query) return true
        return SettingsTabs.textMatches(normalizedSearchText(collectSettingsText(item)), query)
    }

    function matchingSectionCount() {
        var sections = [appearanceSection, customSection, languageSection, gpuInferenceSection,
                        astraSection,
                        systemSection, performanceSection, gatewaySection, chatSection,
                        gpuSection, intgSection, agentProfilesSection, teacherSection,
                        auxiliarySection, mailSection, dataSection]
        var count = 0
        for (var i = 0; i < sections.length; ++i)
            if (matchesSettingsSearch(sections[i])) ++count
        return count
    }

    // nvidia-smi corre en un worker (en frío tarda segundos): el resultado
    // llega por gpuInventoryReady y recién ahí se pinta la lista.
    function refreshGpuInventory() {
        App.requestGpuInventory()
    }
    Connections {
        target: App
        function onGpuInventoryReady(info) {
            root.gpuRows = info.gpus ?? []
            const raw = String(App.readSetting("gpu/vramIndices", ""))
            root.selectedVramGpus = raw.length === 0 ? [] : raw.split(",").map(function(v) { return Number(v) })
        }
    }

    function isVramGpuSelected(index) { return selectedVramGpus.indexOf(index) >= 0 }
    function setVramGpuSelected(index, selected) {
        let values = selectedVramGpus.slice()
        const pos = values.indexOf(index)
        if (selected && pos < 0) values.push(index)
        if (!selected && pos >= 0) values.splice(pos, 1)
        values.sort(function(a, b) { return a - b })
        selectedVramGpus = values
        App.writeSetting("gpu/vramIndices", values.join(","))
    }

    Component.onCompleted: refreshGpuInventory()

    FolderDialog {
        id: openCodeProjectDialog
        title: "Elegí el proyecto para OpenCode"
        onAccepted: {
            var path = selectedFolder.toString().replace("file:///", "")
            var err = App.launchOpenCode(path, openCodeProfile.currentValue ?? "")
            gwMsg.text = err.length === 0
                ? "OpenCode Desktop lanzado contra " + App.gatewayBaseUrl()
                : err
            gwMsg.ok = err.length === 0
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PageHeader {
            Layout.fillWidth: true
            title: (App.langV, App.l("settings.title"))
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 10
            Layout.bottomMargin: 10
            spacing: 8

            LcTextField {
                id: settingsSearch
                Layout.fillWidth: true
                placeholderText: "Buscar configuraciones… (p. ej., GPU, privacidad, correo)"
                horizontalAlignment: TextInput.AlignLeft
                onTextChanged: {
                    root.settingsSearchText = text
                    scroll.contentItem.contentY = 0   // resultados desde arriba
                }
            }

            LcButton {
                text: "Limpiar"
                secondary: true
                visible: settingsSearch.text.length > 0
                onClicked: settingsSearch.clear()
            }
        }

        // Pestañas: agrupan las 16 secciones (antes un solo scroll larguísimo).
        Flow {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.bottomMargin: 6
            spacing: 6
            Repeater {
                model: SettingsTabs.tabs
                delegate: LcButton {
                    required property var modelData
                    readonly property bool searching: root.settingsSearchText.trim().length > 0
                    readonly property int hits: searching
                        ? SettingsTabs.matchCountForTab(modelData.key, function(id) {
                              return root.matchesSettingsSearch(root.sectionById(id)) })
                        : 0
                    text: (App.langV, App.l(modelData.titleKey)) + (searching ? "  " + hits : "")
                    secondary: searching || root.currentTab !== modelData.key
                    opacity: searching && hits === 0 ? 0.45 : 1.0
                    onClicked: {
                        root.currentTab = modelData.key
                        settingsSearch.clear()
                    }
                }
            }
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

                    Text {
                        Layout.fillWidth: true
                        visible: root.settingsSearchText.trim().length > 0 && root.matchingSectionCount() === 0
                        text: "No se encontraron configuraciones coincidentes."
                        color: Theme.textMuted
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                    }

                    // ── Appearance ───────────────────────────────────────────
                    ColumnLayout {
                        id: appearanceSection
                        visible: root.sectionVisible(appearanceSection, "appearanceSection")
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
                                            id: themeSwatch
                                            // Color de los 3 puntos de muestra; el Repeater interno
                                            // (model: 3) sombrea modelData con el índice, así que se
                                            // captura acá el dotColor del tema.
                                            property color dotColor: modelData.dotColor
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
                                                            color: themeSwatch.dotColor
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

                    // ── Temas custom ─────────────────────────────────────────
                    ColumnLayout {
                        id: customSection
                        visible: root.sectionVisible(customSection, "customSection")
                        Layout.fillWidth: true
                        spacing: 10

                        property var list: Theme.customThemes
                        Connections {
                            target: Theme
                            function onCustomThemesChanged() { customSection.list = Theme.customThemes }
                        }

                        Text {
                            text: (App.langV, App.l("settings.sec.customThemes")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: customInner.implicitHeight + 32

                            ColumnLayout {
                                id: customInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 12

                                Text {
                                    text: "Creá tus propios temas: elegí acento, fondo, primer plano, contraste y fuentes. Se guardan y los podés retomar cuando quieras."
                                    color: Theme.textSecondary
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }

                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 3
                                    rowSpacing: 8
                                    columnSpacing: 8

                                    Repeater {
                                        model: customSection.list
                                        delegate: Rectangle {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            height: 74
                                            radius: 8
                                            color: modelData.background || Theme.inputBg
                                            border.width: Theme.currentCustomId === modelData.id ? 2 : 1
                                            border.color: Theme.currentCustomId === modelData.id
                                                ? Theme.accent : Theme.divider

                                            ColumnLayout {
                                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
                                                spacing: 6
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 6
                                                    Rectangle {
                                                        width: 14; height: 14; radius: 7
                                                        color: modelData.accent || "#888"
                                                        border.color: "#80000000"
                                                    }
                                                    Text {
                                                        text: modelData.name || "(sin nombre)"
                                                        color: modelData.foreground || Theme.textPrimary
                                                        font.pixelSize: 12
                                                        font.bold: true
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }
                                                }
                                                RowLayout {
                                                    spacing: 6
                                                    Layout.fillWidth: true
                                                    LcButton {
                                                        text: "Editar"
                                                        secondary: true
                                                        implicitHeight: 26
                                                        onClicked: themeEditor.openEdit(modelData)
                                                    }
                                                    LcButton {
                                                        text: "✕"
                                                        danger: true
                                                        implicitHeight: 26
                                                        onClicked: Theme.deleteCustomTheme(modelData.id)
                                                    }
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                z: -1
                                                onClicked: Theme.applyCustomTheme(modelData.id)
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        height: 74
                                        radius: 8
                                        color: Theme.inputBg
                                        border.color: Theme.divider
                                        border.width: 1
                                        Text {
                                            anchors.centerIn: parent
                                            text: "＋ Nuevo tema"
                                            color: Theme.textSecondary
                                            font.pixelSize: 13
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: themeEditor.openNew()
                                        }
                                    }
                                }

                                Text {
                                    visible: customSection.list.length === 0
                                    text: "Sin temas custom todavía."
                                    color: Theme.textMuted
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }

                    // ── Language ─────────────────────────────────────────────
                    ColumnLayout {
                        id: languageSection
                        visible: root.sectionVisible(languageSection, "languageSection")
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

                    // ── GPU · inferencia ────────────────────────────────────
                    ColumnLayout {
                        id: gpuInferenceSection
                        visible: root.sectionVisible(gpuInferenceSection, "gpuInferenceSection")
                        Layout.fillWidth: true
                        spacing: 10

                        Text { text: (App.langV, App.l("settings.sec.gpuInference")).toUpperCase(); color: Theme.accent; font.pixelSize: 11; font.bold: true }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg; border.color: Theme.borderColor; radius: 10
                            implicitHeight: gpuInner.implicitHeight + 32

                            ColumnLayout {
                                id: gpuInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "GPU de procesamiento"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }
                                    LcComboBox {
                                        id: processingGpu
                                        Layout.preferredWidth: 250
                                        model: ["Automática"].concat(root.gpuRows.map(function(g) { return "GPU " + g.index + " · " + g.name }))
                                        Component.onCompleted: {
                                            const configured = Number(App.readSetting("gpu/processingIndex", -1))
                                            currentIndex = configured >= 0 ? configured + 1 : 0
                                        }
                                        onActivated: App.writeSetting("gpu/processingIndex", currentIndex - 1)
                                    }
                                }
                                Text {
                                    text: "Se usa para operaciones principales y muestreo de llama.cpp ( --main-gpu )."
                                    color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }
                                Text { text: "GPUs de VRAM"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true }
                                Text {
                                    text: "Elegí qué GPUs reciben el modelo. Si no marcás ninguna, llama.cpp decide automáticamente."
                                    color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true
                                }
                                Repeater {
                                    model: root.gpuRows
                                    delegate: LcCheckBox {
                                        text: "GPU " + modelData.index + " · " + modelData.name + " · " + Math.round(modelData.totalMb / 1024) + " GB"
                                        checked: root.isVramGpuSelected(modelData.index)
                                        onToggled: root.setVramGpuSelected(modelData.index, checked)
                                        Layout.fillWidth: true
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        Layout.fillWidth: true
                                        text: root.gpuRows.length === 0 ? "No se detectaron GPUs NVIDIA o nvidia-smi no está disponible." : "Cambios aplicados al próximo inicio del servidor."
                                        color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap
                                    }
                                    LcButton { text: "Actualizar"; secondary: true; onClicked: root.refreshGpuInventory() }
                                }
                            }
                        }
                    }

                    // ── Sistema / bandeja ────────────────────────────────────
                    SettingsSystemSection {
                        id: systemSection
                        visible: root.sectionVisible(systemSection, "systemSection")
                        Layout.fillWidth: true
                    }

                    // ── Rendimiento / diagnóstico ─────────────────────────
                    ColumnLayout {
                        id: performanceSection
                        visible: root.sectionVisible(performanceSection, "performanceSection")
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: (App.langV, App.l("settings.sec.performance")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: performanceInner.implicitHeight + 32

                            ColumnLayout {
                                id: performanceInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Text {
                                            text: "Modo de la aplicación"
                                            color: Theme.textPrimary
                                            font.pixelSize: 14
                                            font.bold: true
                                        }
                                        Text {
                                            text: App.devMode
                                                ? "Dev: registra memoria, CPU, pausas del event loop y fases de arranque."
                                                : "Normal: rendimiento máximo, sin muestreo periódico ni telemetría de diagnóstico."
                                            color: Theme.textMuted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }

                                    LcSwitch {
                                        checked: App.devMode
                                        onToggled: App.devMode = checked
                                    }
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Text {
                                            text: "Log ampliado"
                                            color: Theme.textPrimary
                                            font.pixelSize: 14
                                            font.bold: true
                                        }
                                        Text {
                                            text: "Registra desde el arranque los tiempos de carga, mensajes de Qt, uso de CPU y memoria, y pausas de la interfaz. Al activarlo también empieza a registrar esta sesión."
                                            color: Theme.textMuted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }

                                    LcSwitch {
                                        checked: App.expandedLogging
                                        onToggled: App.expandedLogging = checked
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: "JSONL: " + App.expandedLogPath() + " · local; puede incluir rutas y detalles de errores. Se conserva el archivo actual y una rotación anterior."
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                    wrapMode: Text.WrapAnywhere
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    LcButton {
                                        text: "Abrir carpeta de logs"
                                        secondary: true
                                        onClicked: App.openRuntimeLogDir()
                                    }
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

                                Text {
                                    visible: App.devMode
                                    Layout.fillWidth: true
                                    text: {
                                        const p = App.performanceSnapshot || {}
                                        const n = function(v, suffix) {
                                            return v === undefined || v === null ? "—" : Number(v).toFixed(1) + suffix
                                        }
                                        return "Última muestra · RSS " + n(p.rssMb, " MB")
                                            + " · privada " + n(p.privateMb, " MB")
                                            + " · CPU " + n(p.cpuPercent, "%")
                                            + " · pausa " + n(p.eventLoopLagMs, " ms")
                                            + " · fase " + (p.label || "—")
                                    }
                                    color: Theme.textSecondary
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    visible: App.devMode
                                    Layout.fillWidth: true
                                    text: "Log JSONL: " + App.performanceLogPath()
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                    wrapMode: Text.WrapAnywhere
                                }

                                RowLayout {
                                    visible: App.devMode
                                    Layout.fillWidth: true
                                    LcButton {
                                        text: "Borrar log de rendimiento"
                                        secondary: true
                                        onClicked: App.clearPerformanceLog()
                                    }
                                }
                            }
                        }
                    }

                    // ── Gateway / API (OpenAI + Anthropic + auto-load) ───────
                    ColumnLayout {
                        id: gatewaySection
                        visible: root.sectionVisible(gatewaySection, "gatewaySection")
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: (App.langV, App.l("settings.sec.gateway")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: gwInner.implicitHeight + 32

                            ColumnLayout {
                                id: gwInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Text {
                                            text: "Gateway de modelos"
                                            color: Theme.textPrimary
                                            font.pixelSize: 14
                                            font.bold: true
                                        }
                                        Text {
                                            text: "API local para OpenCode y Claude Code con auto-load: cada request puede cargar el perfil pedido. " + (App.gatewayRunning ? ("Activo en " + App.gatewayBaseUrl()) : "Apagado.")
                                            color: App.gatewayRunning ? Theme.accent : Theme.textMuted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                    LcSwitch {
                                        checked: App.gatewayEnabled
                                        onToggled: App.gatewayEnabled = checked
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled
                                    spacing: 8
                                    Text { text: "Puerto"; color: Theme.textSecondary; font.pixelSize: 12; Layout.preferredWidth: 90 }
                                    LcSpinBox {
                                        from: 1024; to: 65535
                                        value: App.gatewayPort
                                        editable: true
                                        onValueModified: App.gatewayPort = value
                                    }
                                    Text { text: "keep hot"; color: Theme.textSecondary; font.pixelSize: 12 }
                                    LcSpinBox {
                                        from: 1; to: 8
                                        value: App.gatewayKeepN
                                        onValueModified: App.gatewayKeepN = value
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled
                                    spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text { text: "Auto-load del modelo pedido"; color: Theme.textPrimary; font.pixelSize: 13 }
                                        Text {
                                            text: "Si el request nombra otro modelo, lo carga (swap del activo)."
                                            color: Theme.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true
                                        }
                                    }
                                    LcSwitch {
                                        checked: App.gatewayAutoSwap
                                        onToggled: App.gatewayAutoSwap = checked
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled
                                    spacing: 6
                                    LcTextField {
                                        id: gatewayKeyField
                                        property bool revealed: false
                                        Layout.fillWidth: true
                                        placeholderText: "API key (opcional, para exponer en LAN)"
                                        text: App.gatewayApiKey
                                        echoMode: revealed ? TextInput.Normal : TextInput.Password
                                        onEditingFinished: App.gatewayApiKey = text
                                    }
                                    LcButton {
                                        id: gatewayKeyEye
                                        text: gatewayKeyField.revealed ? "🙈" : "👁"
                                        secondary: true
                                        Layout.preferredWidth: 40
                                        // LcButton fija su texto en 13 px: el ojo quedaba diminuto.
                                        contentItem: Text {
                                            text: gatewayKeyEye.text
                                            font.pixelSize: 18
                                            color: Theme.btnSecondaryText
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                        Accessible.name: gatewayKeyField.revealed ? "Ocultar API key" : "Mostrar API key"
                                        ToolTip.visible: hovered
                                        ToolTip.text: Accessible.name
                                        onClicked: gatewayKeyField.revealed = !gatewayKeyField.revealed
                                    }
                                    // Para pasarle la key a un alumno/otro equipo sin revelarla en pantalla.
                                    LcButton {
                                        id: gatewayKeyCopy
                                        property bool copied: false
                                        text: copied ? "✓ Copiada" : "Copiar"
                                        secondary: true
                                        enabled: App.gatewayApiKey.length > 0
                                        onClicked: {
                                            App.copyToClipboard(App.gatewayApiKey)
                                            copied = true
                                            gatewayKeyCopiedTimer.restart()
                                        }
                                        Timer {
                                            id: gatewayKeyCopiedTimer
                                            interval: 1800
                                            onTriggered: gatewayKeyCopy.copied = false
                                        }
                                    }
                                    // Regenerar invalida la key repartida: con una key ya puesta
                                    // pide un segundo clic de confirmación.
                                    LcButton {
                                        id: gatewayKeyRegen
                                        property bool armed: false
                                        text: armed ? "¿Seguro? Los clientes deberán cargar la nueva"
                                                    : (App.gatewayApiKey.length > 0 ? "Generar nueva" : "Generar")
                                        secondary: !armed
                                        danger: armed
                                        onClicked: {
                                            if (App.gatewayApiKey.length > 0 && !armed) {
                                                armed = true
                                                gatewayKeyRegenTimer.restart()
                                                return
                                            }
                                            armed = false
                                            const key = App.generateGatewayApiKey()
                                            gatewayKeyField.text = key
                                        }
                                        Timer {
                                            id: gatewayKeyRegenTimer
                                            interval: 4000
                                            onTriggered: gatewayKeyRegen.armed = false
                                        }
                                    }
                                }

                                // Sin key y con contraseña en LAN, el gateway responde 401 a
                                // todos los clientes (pasó: la key desapareció del llavero).
                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled && App.gatewayLanEnabled
                                             && App.gatewayLanAuthEnabled && App.gatewayApiKey.length === 0
                                    spacing: 8
                                    Text {
                                        Layout.fillWidth: true
                                        text: "⚠ La LAN pide contraseña pero no hay API key: todos los clientes reciben \"API key inválida\". Generá una (y cargala en los clientes) o activá \"Acceso sin contraseña\"."
                                        color: Theme.warnText; font.pixelSize: 11; wrapMode: Text.WordWrap
                                    }
                                    LcButton {
                                        text: "Generar API key"
                                        onClicked: {
                                            App.generateGatewayApiKey()
                                            gatewayKeyField.text = App.gatewayApiKey
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled
                                    spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text {
                                            text: "Compartir server en la red local (LAN)"
                                            color: Theme.textPrimary
                                            font.pixelSize: 13
                                        }
                                        Text {
                                            text: App.gatewayLanEnabled
                                                ? (App.gatewayLanBaseUrl().length > 0
                                                   ? "Escuchando para otros dispositivos en " + App.gatewayLanBaseUrl()
                                                   : "No se encontró una dirección IPv4 de red local.")
                                                : "Sólo esta PC puede conectarse. Al activar LAN se genera una API key si está vacía."
                                            color: App.gatewayLanEnabled ? Theme.accent : Theme.textMuted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                    LcSwitch {
                                        checked: App.gatewayLanEnabled
                                        onToggled: App.gatewayLanEnabled = checked
                                    }
                                }

                                // Mismo ajuste que "Iniciar sin contraseña" en Lanzar; se aplica
                                // en caliente (no hace falta reiniciar el Gateway).
                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled
                                    spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text { text: "Acceso sin contraseña"; color: Theme.textPrimary; font.pixelSize: 13 }
                                        Text {
                                            text: App.gatewayLanAuthEnabled
                                                ? "Los equipos de la red tienen que mandar la API key."
                                                : "Cualquier equipo con acceso a esta red puede usar el Gateway sin API key."
                                            color: App.gatewayLanAuthEnabled ? Theme.textMuted : Theme.warnText
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                    LcSwitch {
                                        checked: !App.gatewayLanAuthEnabled
                                        onToggled: App.gatewayLanAuthEnabled = !checked
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled
                                    spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text { text: "Clientes LAN pueden cambiar el modelo cargado"; color: Theme.textPrimary; font.pixelSize: 13 }
                                        Text {
                                            text: App.gatewayLanMayLoad
                                                ? "Si un cliente pide otro perfil, esta PC descarga el actual y carga ese."
                                                : "Un cliente sólo puede usar el modelo ya cargado (o cargar uno si no hay ninguno); si pide otro recibe un error."
                                            color: Theme.textMuted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                    LcSwitch {
                                        checked: App.gatewayLanMayLoad
                                        onToggled: App.gatewayLanMayLoad = checked
                                    }
                                }

                                // Conectar otras apps. Antes eran "Opción 1/2/3" siempre abiertas y el
                                // selector de perfil (que usan todas) quedaba suelto entre la 2 y la 3.
                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor; visible: App.gatewayEnabled }
                                Text {
                                    visible: App.gatewayEnabled
                                    text: "CONECTAR OTRAS APPS"
                                    color: Theme.accent; font.pixelSize: 11; font.bold: true
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: App.gatewayEnabled
                                    spacing: 8
                                    Text { text: "Perfil a exponer"; color: Theme.textSecondary; font.pixelSize: 12 }
                                    LcComboBox {
                                        id: openCodeProfile
                                        Layout.fillWidth: true
                                        property var launchMenu: App.profileManager.launchProfilesForMenu()
                                        model: launchMenu
                                        textRole: "displayName"
                                        valueRole: "id"
                                        Component.onCompleted: {
                                            var idx = indexOfValue(App.activeLaunchId)
                                            currentIndex = idx >= 0 ? idx : 0
                                        }
                                        Connections {
                                            target: App.profileManager
                                            function onLaunchesChanged() {
                                                openCodeProfile.launchMenu =
                                                    App.profileManager.launchProfilesForMenu()
                                            }
                                        }
                                    }
                                }

                                Collapsible {
                                    visible: App.gatewayEnabled
                                    title: "Claude Code / OpenCode en esta PC"
                                    RowLayout {
                                        spacing: 8
                                        LcButton {
                                            text: "Lanzar Claude Code en mi GPU"
                                            onClicked: {
                                                var err = App.launchClaudeCode()
                                                gwMsg.text = err.length === 0
                                                    ? "Claude Code lanzado contra " + App.gatewayBaseUrl()
                                                    : err
                                                gwMsg.ok = err.length === 0
                                            }
                                        }
                                        LcButton {
                                            text: "Abrir OpenCode GUI en mi GPU"
                                            enabled: openCodeProfile.currentValue !== undefined
                                            onClicked: openCodeProjectDialog.open()
                                        }
                                    }
                                }

                                Collapsible {
                                    visible: App.gatewayEnabled
                                    title: "Otro LlamaCode en la LAN"
                                    subtitle: App.gatewayLanEnabled ? "" : "Activá \"Compartir server en la red local\" primero."
                                    Text {
                                        visible: App.gatewayLanEnabled
                                        text: "En el otro LlamaCode creá un Backend tipo Cloud/OpenAI-compatible. Base URL: "
                                              + App.gatewayLanBaseUrl()
                                              + " · Modelo: el ID del perfil elegido arriba · Var de key: LLAMACODE_GATEWAY_API_KEY."
                                        color: Theme.textSecondary; font.pixelSize: 11
                                        wrapMode: Text.WordWrap; Layout.fillWidth: true
                                    }
                                    RowLayout {
                                        visible: App.gatewayLanEnabled
                                        spacing: 8
                                        LcButton {
                                            text: "Copiar URL para LlamaCode"
                                            onClicked: {
                                                App.copyToClipboard(App.gatewayLanBaseUrl())
                                                gwMsg.text = "URL LAN copiada."
                                                gwMsg.ok = true
                                            }
                                        }
                                        LcButton {
                                            text: "Copiar API key"
                                            secondary: true
                                            onClicked: {
                                                App.copyToClipboard(App.gatewayApiKey)
                                                gwMsg.text = "API key copiada. Compartila sólo con dispositivos confiables."
                                                gwMsg.ok = true
                                            }
                                        }
                                    }
                                }

                                Collapsible {
                                    visible: App.gatewayEnabled
                                    title: "OpenCode en la LAN"
                                    subtitle: App.gatewayLanEnabled ? "" : "Activá \"Compartir server en la red local\" primero."
                                    Text {
                                        visible: App.gatewayLanEnabled
                                        text: "Copiá la configuración en opencode.json del otro dispositivo. Incluye la URL LAN, los perfiles disponibles y la API key."
                                        color: Theme.textSecondary; font.pixelSize: 11
                                        wrapMode: Text.WordWrap; Layout.fillWidth: true
                                    }
                                    LcButton {
                                        visible: App.gatewayLanEnabled
                                        text: "Copiar configuración de OpenCode"
                                        enabled: openCodeProfile.currentValue !== undefined
                                        onClicked: {
                                            App.copyToClipboard(App.gatewayLanOpenCodeConfig(openCodeProfile.currentValue ?? ""))
                                            gwMsg.text = "Configuración LAN de OpenCode copiada."
                                            gwMsg.ok = true
                                        }
                                    }
                                    Text {
                                        visible: App.gatewayLanEnabled && Qt.platform.os === "windows"
                                        text: "Windows puede pedir permiso de firewall la primera vez. Permití acceso sólo en redes privadas."
                                        color: Theme.textMuted; font.pixelSize: 10
                                        wrapMode: Text.WordWrap; Layout.fillWidth: true
                                    }
                                }

                                Collapsible {
                                    visible: App.gatewayEnabled
                                    title: "Claude Desktop"
                                    Text {
                                        text: "Configura Claude Desktop para usar este gateway en modo Third-Party Inference. "
                                              + "El perfil elegido queda disponible junto con los demás perfiles locales."
                                        color: Theme.textSecondary; font.pixelSize: 11
                                        wrapMode: Text.WordWrap; Layout.fillWidth: true
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        LcButton {
                                            text: "Configurar Claude Desktop"
                                            enabled: openCodeProfile.currentValue !== undefined
                                            onClicked: {
                                                var result = App.configureClaudeDesktop(
                                                    openCodeProfile.currentValue ?? "")
                                                gwMsg.text = result
                                                gwMsg.ok = result.indexOf("No ") !== 0
                                                    && result.indexOf("no ") !== 0
                                            }
                                        }
                                        Text {
                                            text: "Requiere cerrar y volver a abrir Claude Desktop."
                                            color: Theme.textMuted; font.pixelSize: 10
                                            wrapMode: Text.WordWrap; Layout.fillWidth: true
                                        }
                                    }
                                }
                                Text {
                                    id: gwMsg
                                    property bool ok: false
                                    visible: text.length > 0
                                    text: ""
                                    color: ok ? Theme.accent : Theme.btnDangerBg
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                                Text {
                                    visible: App.gatewayEnabled
                                    text: "Manual: OpenAI base URL " + App.gatewayBaseUrl() + "/v1  ·  endpoints /v1/models, /v1/chat/completions y /v1/messages."
                                    color: Theme.textMuted
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }

                    // ── Chat / Mermaid ───────────────────────────────────────
                    SettingsChatSection {
                        id: chatSection
                        visible: root.sectionVisible(chatSection, "chatSection")
                        Layout.fillWidth: true
                    }

                    // ── GPU power limit (nvidia-smi) ─────────────────────────
                    ColumnLayout {
                        id: gpuSection
                        visible: root.sectionVisible(gpuSection, "gpuSection")
                        Layout.fillWidth: true
                        spacing: 10

                        property var info: ({ available: false, gpus: [] })
                        property string msg: ""
                        property bool msgOk: false
                        function reload() { App.requestGpuPowerInfo() }
                        Component.onCompleted: reload()
                        Connections {
                            target: App
                            function onGpuPowerInfoReady(result) { gpuSection.info = result }
                        }

                        Text {
                            text: (App.langV, App.l("settings.sec.gpuPower")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: gpuInner.implicitHeight + 32

                            ColumnLayout {
                                id: gpuPowerInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 12

                                Text {
                                    text: "Límite de potencia de la GPU (W) vía nvidia-smi. Bajarlo reduce consumo, temperatura y ruido con poca pérdida en inferencia. Se aplica al iniciar el server. "
                                          + (Qt.platform.os === "windows"
                                             ? "Requiere admin: Windows pide confirmación (UAC)."
                                             : "Requiere root: nvidia-smi -pl falla sin sudo (o una regla de sudoers para nvidia-smi).")
                                    color: Theme.textSecondary
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    visible: !gpuSection.info.available
                                    text: "No se detectó nvidia-smi (¿GPU NVIDIA / drivers instalados?)."
                                    color: Theme.textMuted
                                    font.pixelSize: 12
                                }

                                Repeater {
                                    model: gpuSection.info.available ? gpuSection.info.gpus : []
                                    delegate: ColumnLayout {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 8

                                        Text {
                                            text: "GPU " + modelData.index + " · " + modelData.name
                                            color: Theme.textPrimary
                                            font.pixelSize: 13
                                            font.bold: true
                                        }
                                        Text {
                                            text: "actual " + Math.round(modelData.currentW) + " W · default " + Math.round(modelData.defaultW)
                                                  + " W · rango " + Math.round(modelData.minW) + "–" + Math.round(modelData.maxW) + " W"
                                            color: Theme.textMuted
                                            font.pixelSize: 11
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10
                                            Slider {
                                                id: plSlider
                                                Layout.fillWidth: true
                                                from: modelData.minW
                                                to: modelData.maxW
                                                stepSize: 5
                                                value: modelData.currentW
                                            }
                                            Text {
                                                text: Math.round(plSlider.value) + " W"
                                                color: Theme.textPrimary
                                                font.pixelSize: 13
                                                font.bold: true
                                                Layout.preferredWidth: 60
                                            }
                                            LcButton {
                                                text: "Aplicar"
                                                onClicked: {
                                                    var err = App.setGpuPowerLimit(Math.round(plSlider.value), modelData.index)
                                                    gpuSection.msgOk = (err === "")
                                                    gpuSection.msg = (err === "")
                                                        ? ("Power limit fijado en " + Math.round(plSlider.value) + " W.")
                                                        : err
                                                    gpuSection.reload()
                                                }
                                            }
                                            LcButton {
                                                text: "Default"
                                                secondary: true
                                                onClicked: {
                                                    var err = App.setGpuPowerLimit(Math.round(modelData.defaultW), modelData.index)
                                                    gpuSection.msgOk = (err === "")
                                                    gpuSection.msg = (err === "") ? "Restaurado al default." : err
                                                    gpuSection.reload()
                                                }
                                            }
                                        }
                                    }
                                }

                                Text {
                                    visible: gpuSection.msg.length > 0
                                    text: gpuSection.msg
                                    color: gpuSection.msgOk ? Theme.accent : Theme.btnDangerBg
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }

                    // ── ASTRA / Strata ──────────────────────────────────────
                    ColumnLayout {
                        id: astraSection
                        visible: root.sectionVisible(astraSection, "astraSection")
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: (App.langV, App.l("settings.sec.strata")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: astraInner.implicitHeight + 32

                            ColumnLayout {
                                id: astraInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 10

                                Text {
                                    Layout.fillWidth: true
                                    text: "Motor Strata · perfiles ASTRA"
                                    color: Theme.textPrimary
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "LlamaCode inicia, supervisa y detiene Strata. La carpeta del motor es común a todos; cada perfil usa su propio JSON de configuración para no mezclar modelos."
                                    color: Theme.textMuted
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                }

                                Text { text: "Carpeta de Strata"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    id: astraStrataRoot
                                    Layout.fillWidth: true
                                    enabled: !App.serverRunning
                                    placeholderText: "/ruta/a/Strata-0.1.35"
                                    Component.onCompleted: text = App.readSetting("astra/strataRoot", "")
                                    onEditingFinished: App.writeSetting("astra/strataRoot", text.trim())
                                }

                                // Un campo por perfil Strata existente (antes eran tres rutas fijas
                                // de IQ3_S/Q4 y el ASTRA DEFAULT IQ2_XS no tenía dónde configurarse).
                                Repeater {
                                    id: astraProfilesRepeater
                                    model: App.astraStrataProfiles()
                                    delegate: ColumnLayout {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Text {
                                            Layout.fillWidth: true
                                            text: "JSON · " + modelData.title
                                            color: Theme.textSecondary; font.pixelSize: 12
                                            elide: Text.ElideRight
                                        }
                                        LcTextField {
                                            Layout.fillWidth: true
                                            enabled: !App.serverRunning
                                            placeholderText: modelData.requiresOwnConfig
                                                ? "Obligatorio: ruta al JSON de este perfil"
                                                : "Vacío: usa ASTRA_STRATA_CONFIG o el JSON que encuentre en la carpeta"
                                            text: modelData.value
                                            onEditingFinished: App.writeSetting(modelData.setting, text.trim())
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            visible: modelData.expectedModelName.length > 0
                                            text: "Se verifica que el JSON declare model_name = " + modelData.expectedModelName
                                                  + (modelData.requiresOwnConfig ? "; sin este JSON el perfil no arranca." : ".")
                                            color: modelData.requiresOwnConfig && modelData.value.length === 0
                                                   ? Theme.warnText : Theme.textMuted
                                            font.pixelSize: 10
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    visible: astraProfilesRepeater.count === 0
                                    text: "No hay perfiles que usen Strata."
                                    color: Theme.textMuted; font.pixelSize: 11
                                }
                                Text { text: "Puerto local"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    id: astraPort
                                    Layout.fillWidth: true
                                    enabled: !App.serverRunning
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    placeholderText: "8350"
                                    Component.onCompleted: text = String(App.readSetting("astra/port", 8350))
                                    onEditingFinished: {
                                        const value = parseInt(text)
                                        if (value >= 1024 && value <= 65535) {
                                            App.writeSetting("astra/port", value)
                                            text = String(value)
                                        } else {
                                            text = String(App.readSetting("astra/port", 8350))
                                        }
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "Strata escucha sólo en 127.0.0.1. Para compartir el perfil, elegilo en Lanzar y usá Iniciar servidor LAN; LlamaCode lo publica por el Gateway autenticado. ASTRA_STRATA_ROOT configura el motor; ASTRA_STRATA_CONFIG es el JSON de respaldo de los perfiles que lo admiten."
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }

                    // ── Integrations ─────────────────────────────────────────
                    SettingsIntegrationsSection {
                        id: intgSection
                        visible: root.sectionVisible(intgSection, "intgSection")
                        Layout.fillWidth: true
                    }

                    // ── Perfiles de agente (capacidades + directivas) ────────
                    SettingsAgentProfilesSection {
                        id: agentProfilesSection
                        visible: root.sectionVisible(agentProfilesSection, "agentProfilesSection")
                        Layout.fillWidth: true
                    }

                    // ── Modelo maestro (ask_teacher) ─────────────────────────
                    ColumnLayout {
                        id: teacherSection
                        visible: root.sectionVisible(teacherSection, "teacherSection")
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: (App.langV, App.l("settings.sec.teacher")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: teacherInner.implicitHeight + 32

                            ColumnLayout {
                                id: teacherInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 12

                                Text {
                                    text: "Endpoint OpenAI-compatible de un modelo más capaz. La tool ask_teacher lo consulta para sub-problemas difíciles. Vacío = se usan las env vars LLAMACODE_TEACHER_*."
                                    color: Theme.textSecondary
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }

                                Text { text: "Base URL"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: App.agentTeacherUrl
                                    placeholderText: "https://api.openai.com  ·  http://localhost:8081"
                                    onEditingFinished: App.agentTeacherUrl = text
                                }

                                Text { text: "Modelo"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: App.agentTeacherModel
                                    placeholderText: "gpt-4o  ·  qwen2.5-coder-32b  ·  default"
                                    onEditingFinished: App.agentTeacherModel = text
                                }

                                Text { text: "API key (opcional)"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: App.agentTeacherKey
                                    placeholderText: "sk-…  (vacío para servers locales)"
                                    echoMode: TextInput.Password
                                    onEditingFinished: App.agentTeacherKey = text
                                }
                            }
                        }
                    }

                    // ── Sidecar auxiliar (embeddings/rerank) ──────────────
                    ColumnLayout {
                        id: auxiliarySection
                        visible: root.sectionVisible(auxiliarySection, "auxiliarySection")
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: (App.langV, App.l("settings.sec.auxiliary")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: auxiliaryInner.implicitHeight + 32

                            ColumnLayout {
                                id: auxiliaryInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 12

                                Text {
                                    text: "Endpoint OpenAI-compatible opcional para embeddings y rerank (Base URL sin /v1). Dejalo vacío para usar el server principal. Ideal para un llama-server CPU con un modelo chico: no consume slots del modelo del agente."
                                    color: Theme.textSecondary
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }

                                Text { text: "Base URL"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: App.agentAuxiliaryUrl
                                    placeholderText: "http://127.0.0.1:8090"
                                    onEditingFinished: App.agentAuxiliaryUrl = text
                                }

                                Text { text: "Modelo de embeddings"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: App.agentAuxiliaryEmbeddingModel
                                    placeholderText: "llamacode-embed"
                                    onEditingFinished: App.agentAuxiliaryEmbeddingModel = text
                                }

                                Text { text: "Modelo de rerank"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: App.agentAuxiliaryRerankModel
                                    placeholderText: "llamacode-rerank"
                                    onEditingFinished: App.agentAuxiliaryRerankModel = text
                                }

                                Text { text: "API key (opcional)"; color: Theme.textSecondary; font.pixelSize: 12 }
                                LcTextField {
                                    Layout.fillWidth: true
                                    text: App.agentAuxiliaryKey
                                    placeholderText: "vacío para servers locales"
                                    echoMode: TextInput.Password
                                    onEditingFinished: App.agentAuxiliaryKey = text
                                }

                                Text {
                                    text: "También se puede configurar sin guardar credenciales con LLAMACODE_AUXILIARY_URL, LLAMACODE_AUXILIARY_EMBED_MODEL, LLAMACODE_AUXILIARY_RERANK_MODEL y LLAMACODE_AUXILIARY_KEY."
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }

                    // ── Correo (email_send / email_list / email_read) ───────
                    SettingsMailSection {
                        id: mailSection
                        visible: root.sectionVisible(mailSection, "mailSection")
                        Layout.fillWidth: true
                    }

                    // ── Data maintenance ───────────────────────────────────
                    ColumnLayout {
                        id: dataSection
                        visible: root.sectionVisible(dataSection, "dataSection")
                        Layout.fillWidth: true
                        spacing: 10

                        property var wipeItems: App.wipeCategories()

                        Text {
                            text: (App.langV, App.l("settings.sec.data")).toUpperCase()
                            color: Theme.accent
                            font.pixelSize: 11
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            color: Theme.surfaceBg
                            border.color: Theme.borderColor
                            radius: 10
                            implicitHeight: dataInner.implicitHeight + 32

                            ColumnLayout {
                                id: dataInner
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                                spacing: 14

                                Text {
                                    text: "Copia de seguridad"
                                    color: Theme.textPrimary
                                    font.pixelSize: 14
                                    font.bold: true
                                }

                                Text {
                                    text: "Exportá o importá tus chats, perfiles, settings, integraciones, skills y resultados guardados como JSON."
                                    color: Theme.textSecondary
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    LcButton {
                                        text: "Exportar datos"
                                        onClicked: App.exportUserData()
                                    }
                                    LcButton {
                                        text: "Importar datos"
                                        secondary: true
                                        onClicked: App.importUserData()
                                    }
                                    Item { Layout.fillWidth: true }
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

                                Text {
                                    text: "Zona de peligro"
                                    color: Theme.btnDangerBg
                                    font.pixelSize: 14
                                    font.bold: true
                                }

                                Text {
                                    text: "Irreversible. Cada wipe apunta a una categoría; elegí exactamente qué querés borrar."
                                    color: Theme.textSecondary
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }

                                Repeater {
                                    model: dataSection.wipeItems
                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        radius: 8
                                        color: Theme.inputBg
                                        border.color: Theme.borderColor
                                        implicitHeight: wipeRow.implicitHeight + 18

                                        RowLayout {
                                            id: wipeRow
                                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                                            spacing: 12

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 3
                                                Text {
                                                    text: modelData.title
                                                    color: Theme.textPrimary
                                                    font.pixelSize: 13
                                                    font.bold: true
                                                }
                                                Text {
                                                    text: modelData.description
                                                    color: Theme.textMuted
                                                    font.pixelSize: 11
                                                    Layout.fillWidth: true
                                                    wrapMode: Text.WordWrap
                                                }
                                            }

                                            LcButton {
                                                text: "Borrar"
                                                danger: true
                                                implicitHeight: 30
                                                onClicked: {
                                                    wipeDialog.kind = modelData.kind
                                                    wipeDialog.label = modelData.title
                                                    wipeDialog.description = modelData.description
                                                    wipeConfirm.text = ""
                                                    wipeDialog.open()
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

    // ── Editor de tema custom ───────────────────────────────────────────────
    LcDialog {
        id: themeEditor
        title: "Editor de tema"
        standardButtons: Dialog.NoButton
        width: Math.min(520, root.width - 48)

        property string editId: ""
        property string baseTheme: "dark"
        property bool translucent: false

        function loadDef(def) {
            editId = def.id || ""
            nameField.text = def.name || ""
            baseTheme = def.base || "dark"
            baseCombo.currentIndex = baseCombo.indexOfValue(baseTheme)
            accentRow.value = def.accent || ""
            bgRow.value = def.background || ""
            fgRow.value = def.foreground || ""
            uiFontField.text = def.uiFont || ""
            codeFontField.text = def.codeFont || ""
            contrastSlider.value = def.contrast !== undefined ? def.contrast : 30
            translucent = def.translucent === true
        }
        function openNew() { loadDef(Theme.defaultCustomDef("dark")); open() }
        function openEdit(def) { loadDef(def); open() }
        function collect() {
            return {
                "id": editId,
                "name": nameField.text.trim(),
                "base": baseCombo.currentValue,
                "accent": accentRow.value.trim(),
                "background": bgRow.value.trim(),
                "foreground": fgRow.value.trim(),
                "uiFont": uiFontField.text.trim(),
                "codeFont": codeFontField.text.trim(),
                "contrast": Math.round(contrastSlider.value),
                "translucent": themeEditor.translucent
            }
        }

        contentItem: ColumnLayout {
            spacing: 12

            LcTextField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: "Nombre del tema"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: "Base"; color: Theme.textSecondary; font.pixelSize: 12 }
                LcComboBox {
                    id: baseCombo
                    Layout.preferredWidth: 160
                    model: [
                        { label: "Oscuro", value: "dark" },
                        { label: "Claro",  value: "light" },
                        { label: "OLED",   value: "oled" },
                    ]
                    textRole: "label"
                    valueRole: "value"
                }
                Text {
                    Layout.fillWidth: true
                    text: "Define estados (error/ok) y overlay."
                    color: Theme.textMuted; font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }

            // Anclas de color: swatch clickeable (abre el selector) + hex.
            LcColorRow { id: accentRow; label: "Acento";       picker: colorPicker }
            LcColorRow { id: bgRow;     label: "Fondo";        picker: colorPicker }
            LcColorRow { id: fgRow;     label: "Primer plano"; picker: colorPicker }

            LcTextField {
                id: uiFontField
                Layout.fillWidth: true
                placeholderText: "Fuente de la interfaz (ej. Inter)"
            }
            LcTextField {
                id: codeFontField
                Layout.fillWidth: true
                placeholderText: "Fuente de código (ej. JetBrains Mono)"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: "Barra lateral translúcida"; color: Theme.textPrimary; font.pixelSize: 13; Layout.fillWidth: true }
                LcSwitch {
                    checked: themeEditor.translucent
                    onToggled: themeEditor.translucent = checked
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: "Contraste"; color: Theme.textPrimary; font.pixelSize: 13 }
                Slider {
                    id: contrastSlider
                    Layout.fillWidth: true
                    from: 0; to: 100; stepSize: 1
                    value: 30
                }
                Text {
                    text: Math.round(contrastSlider.value)
                    color: Theme.textSecondary; font.pixelSize: 13
                    Layout.preferredWidth: 30
                }
            }
        }

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
                    text: (App.langV, App.l("common.cancel"))
                    secondary: true
                    onClicked: themeEditor.close()
                }
                LcButton {
                    text: "Guardar y aplicar"
                    onClicked: {
                        var id = Theme.saveCustomTheme(themeEditor.collect())
                        Theme.applyCustomTheme(id)
                        themeEditor.close()
                    }
                }
            }
        }
    }

    LcDialog {
        id: wipeDialog
        title: "Confirmar borrado"
        property string kind: ""
        property string label: ""
        property string description: ""
        standardButtons: Dialog.NoButton
        width: Math.min(520, root.width - 48)

        contentItem: ColumnLayout {
            spacing: 12
            Text {
                text: wipeDialog.label
                color: Theme.textPrimary
                font.pixelSize: 14
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Text {
                text: wipeDialog.description
                color: Theme.textSecondary
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Text {
                text: "Escribí WIPE para confirmar."
                color: Theme.textSecondary
                font.pixelSize: 12
            }
            LcTextField {
                id: wipeConfirm
                Layout.fillWidth: true
                placeholderText: "WIPE"
                onAccepted: {
                    if (text.trim() === "WIPE") {
                        App.wipeUserData(wipeDialog.kind, text.trim())
                        wipeDialog.close()
                    }
                }
            }
        }

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
                    text: (App.langV, App.l("common.cancel"))
                    secondary: true
                    onClicked: wipeDialog.close()
                }
                LcButton {
                    text: "Borrar"
                    danger: true
                    enabled: wipeConfirm.text.trim() === "WIPE"
                    onClicked: {
                        App.wipeUserData(wipeDialog.kind, wipeConfirm.text.trim())
                        wipeDialog.close()
                    }
                }
            }
        }
    }
}
