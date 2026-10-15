import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import LlamaCode 1.0
import "NavigationPolicy.js" as NavigationPolicy

Rectangle {
    id: root
    width: 200
    // Translúcida (tema custom): baja el alpha del fondo para dejar ver la ventana.
    readonly property color navBase: Theme.navBg
    color: Theme.sidebarTranslucent
        ? Qt.rgba(navBase.r, navBase.g, navBase.b, 0.8)
        : navBase

    property int currentIndex: 0
    signal pageSelected(int index)
    signal updateRequested()

    readonly property var pages: [
        { key: "nav.launch",   icon: "🚀",  serverOnly: false },
        { key: "nav.profiles", icon: "📋",  serverOnly: false },
        { key: "nav.models",   icon: "📦",  serverOnly: false },
        { key: "nav.binaries", icon: "⚙",   serverOnly: false },
        { key: "nav.chat",      icon: "💬",  serverOnly: true  },
        { key: "agent.title",   icon: "🤖",  serverOnly: true,
          keepDuringAgentTransition: true, keepDuringThinkingRestart: true },
        { key: "nav.research",  icon: "🔎",  serverOnly: true  },
        { key: "nav.datalab",   label: "Data Lab", icon: "🧾", serverOnly: false },
        { key: "nav.tasks",     icon: "🗒",  serverOnly: true, agentOnly: true,
          keepDuringAgentTransition: true },
        { key: "nav.charla",    icon: "🎙",  serverOnly: true  },
        { key: "nav.benchmark", icon: "📊",  serverOnly: false },
        { key: "nav.ranking",   icon: "🏆",  serverOnly: false },
        { key: "tuner", label: "Tuner", icon: "🎛", serverOnly: false },
        { key: "nav.downloads", icon: "⬇",   serverOnly: false },
        { key: "agents", label: "Agentes", icon: "🧠", serverOnly: false },
    ]

    // Ajustes va al pie, fuera del Repeater: su índice es el que sigue a la
    // última página. Derivarlo evita que agregar una sección lo desincronice
    // del StackLayout (era un 12 hardcodeado en tres lugares).
    readonly property int settingsIndex: pages.length

    // Índice de una página por su key, para navegar sin números mágicos.
    // -1 si no existe.
    function indexOfKey(key) {
        for (var i = 0; i < pages.length; ++i)
            if (pages[i].key === key) return i
        return -1
    }

    ColumnLayout {
        anchors { fill: parent; margins: 0 }
        spacing: 0

        // Hace de barra de título (la ventana no tiene una aparte): arrastrar
        // mueve la ventana y doble clic maximiza/restaura.
        Rectangle {
            Layout.fillWidth: true
            height: 56
            color: Theme.titleBg
            Column {
                anchors.centerIn: parent
                width: parent.width - 16
                spacing: 2
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: "UNLZ_Llamacode"
                    font { pixelSize: 16; bold: true }
                    color: Theme.textPrimary
                }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    visible: text.length > 0
                    text: NavigationPolicy.statusLine(App.startupBusy, App.startupStatus,
                                                      App.serverState, App.serverReady,
                                                      App.serverStopping, App.agentRunning)
                    font.pixelSize: 10
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                }
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
        }

        Repeater {
            model: root.pages
            delegate: ItemDelegate {
                Layout.fillWidth: true
                height: 48
                highlighted: root.currentIndex === index
                // agentOnly: permite entrar también mientras el agente ARRANCA
                // (App.agentStarting) → la página muestra su popup "Iniciando agente"
                // con los botones deshabilitados, igual que Agente. Solo queda
                // grisada si el agente no fue iniciado en absoluto.
                enabled: modelData ? NavigationPolicy.pageEnabled(modelData, App.backendAvailable,
                                                                   App.agentRunning, App.agentStarting)
                                   : true
                opacity: enabled ? 1.0 : 0.35
                background: Rectangle {
                    color: parent.highlighted ? Theme.highlight : (parent.hovered && parent.enabled ? Theme.hoverBg : "transparent")
                    Rectangle {
                        visible: parent.parent.highlighted
                        width: 3; height: parent.height
                        anchors.left: parent.left
                        color: Theme.accent
                    }
                }
                contentItem: Row {
                    spacing: 12
                    anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter }
                    Text {
                        text: modelData.label || (App.langV, App.l(modelData.key))
                        font.pixelSize: 14
                        color: root.currentIndex === index ? Theme.textPrimary : Theme.textSecondary
                    }
                }
                onClicked: { root.currentIndex = index; root.pageSelected(index) }
            }
        }

        Item { Layout.fillHeight: true }

        // Dentro del ColumnLayout `height` no cuenta (manda Layout.*), y un
        // contentItem con anchors.fill pelea con el padding del ItemDelegate:
        // el texto quedaba pegado arriba de la franja resaltada.
        ItemDelegate {
            objectName: "navSettings"
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            leftPadding: 16; rightPadding: 8; topPadding: 0; bottomPadding: 0
            highlighted: root.currentIndex === root.settingsIndex
            background: Rectangle {
                color: parent.highlighted ? Theme.highlight : (parent.hovered ? Theme.hoverBg : "transparent")
                Rectangle {
                    visible: parent.parent.highlighted
                    width: 3; height: parent.height
                    anchors.left: parent.left
                    color: Theme.accent
                }
            }
            contentItem: RowLayout {
                spacing: 8
                Text {
                    objectName: "navSettingsText"
                    text: (App.langV, App.l("nav.settings"))
                    font.pixelSize: 14
                    color: root.currentIndex === root.settingsIndex ? Theme.textPrimary : Theme.textSecondary
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
                ToolButton {
                    id: updateButton
                    visible: Qt.platform.os === "windows" && App.updateAvailable
                    enabled: visible
                    onClicked: root.updateRequested()
                    padding: 0
                    // Flecha dibujada: el glifo de Segoe MDL2 quedaba corrido hacia
                    // abajo dentro del c\u00EDrculo (sus m\u00E9tricas no centran).
                    contentItem: Item {
                        Canvas {
                            anchors.centerIn: parent
                            width: 14; height: 14
                            onPaint: {
                                const ctx = getContext("2d")
                                ctx.reset()
                                ctx.strokeStyle = "white"
                                ctx.lineWidth = 1.8
                                ctx.lineCap = "round"
                                ctx.lineJoin = "round"
                                ctx.beginPath()
                                ctx.moveTo(7, 1); ctx.lineTo(7, 9.5)      // asta
                                ctx.moveTo(3, 5.8); ctx.lineTo(7, 9.8); ctx.lineTo(11, 5.8) // punta
                                ctx.moveTo(2, 13); ctx.lineTo(12, 13)     // base
                                ctx.stroke()
                            }
                        }
                    }
                    background: Rectangle {
                        radius: width / 2
                        color: updateButton.pressed ? "#15803D"
                             : updateButton.hovered ? "#22A447" : "#16A34A"
                    }
                    Accessible.name: "Descargar e instalar la versión " + (App.updateInfo.version ?? "")
                    ToolTip.visible: hovered
                    ToolTip.delay: 350
                    ToolTip.text: "Descargar e instalar la versión " + (App.updateInfo.version ?? "")
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 28
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                }
            }
            onClicked: { root.currentIndex = root.settingsIndex; root.pageSelected(root.settingsIndex) }
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            bottomPadding: 12
            text: "v" + App.version()
            font.pixelSize: 11
            color: Theme.textDim
        }
    }
}
