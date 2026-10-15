import QtQuick

// Contratos de UI de AgentPage.qml y ChatPage.qml REALES (staged como texto: las
// páginas necesitan todo el AppController para instanciarse). Fija lo que antes
// sólo se veía a ojo:
//  - los headers son Flow (los controles bajan de fila en vez de quedar bajo
//    los botones de minimizar/maximizar/cerrar) y reservan su ancho;
//  - con el agente detenido hay un botón "Iniciar agente" centrado;
//  - la tarjeta de computer use ofrece segundo plano / controlar la PC / cancelar.
QtObject {
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    function read(name) {
        var xhr = new XMLHttpRequest()
        xhr.open("GET", Qt.resolvedUrl(name), false)
        xhr.send()
        return xhr.responseText || ""
    }

    // Texto desde `marker` hasta el cierre de su bloque { ... } (cuenta llaves).
    function block(text, marker) {
        const start = text.indexOf(marker)
        if (start < 0) return ""
        const open = text.indexOf("{", start)
        var depth = 0
        for (var i = open; i < text.length; ++i) {
            if (text[i] === "{") depth++
            else if (text[i] === "}") { depth--; if (depth === 0) return text.substring(start, i + 1) }
        }
        return ""
    }

    function checkHeader(page, label, headerMarker, flowId) {
        const header = block(page, headerMarker)
        check(header.length > 200, label + ": se encuentra el header")
        const flowAt = header.indexOf("id: " + flowId)
        check(flowAt > 0 && header.lastIndexOf("Flow {", flowAt) > 0, label + ": el header es un Flow")
        check(header.indexOf("RowLayout {") < 0 || header.indexOf("RowLayout {") > flowAt,
              label + ": no vuelve a RowLayout (se salía de pantalla con la ventana angosta)")
        check(header.indexOf("rightMargin: 12 + root.windowControlsReserve") > 0,
              label + ": reserva el ancho de los botones de ventana")
        check(header.indexOf("Layout.preferredHeight: " + flowId + ".implicitHeight") > 0,
              label + ": la altura sigue a las filas del Flow")
    }

    Component.onCompleted: {
        const agent = read("AgentPage.qml.txt")
        const chat = read("ChatPage.qml.txt")
        check(agent.length > 5000 && chat.length > 5000, "se leyeron AgentPage y ChatPage")

        checkHeader(agent, "Agente", "// Flow, no RowLayout", "headerFlow")
        checkHeader(chat, "Chat", "objectName: \"chatHeader\"", "chatHeaderFlow")

        const idle = block(agent, "// Idle / not running")
        check(idle.indexOf("App.l(\"agent.start\")") > 0, "agente detenido: botón Iniciar agente")
        check(idle.indexOf("Layout.alignment: Qt.AlignHCenter") > 0, "agente detenido: el botón está centrado")
        check(idle.indexOf("root.startSelectedAgent()") > 0, "el botón usa el mismo arranque que el header")

        const cu = block(agent, "// ── Computer use: ¿en segundo plano")
        check(cu.length > 200, "existe la tarjeta de computer use")
        check(cu.indexOf("App.answerComputerUseChoice(\"background\")") > 0, "opción En segundo plano")
        check(cu.indexOf("App.answerComputerUseChoice(\"foreground\")") > 0, "opción Controlando mi PC")
        check(cu.indexOf("App.answerComputerUseChoice(\"cancel\")") > 0, "opción Cancelar")

        console.log(fails === 0 ? "ALL PASS" : ("FAIL count=" + fails))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
