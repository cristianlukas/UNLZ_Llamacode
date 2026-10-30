import QtQuick

// Contratos de UI de AgentPage.qml y ChatPage.qml REALES (staged como texto: las
// páginas necesitan todo el AppController para instanciarse). Fija lo que antes
// sólo se veía a ojo:
//  - los headers son Flow (los controles bajan de fila en vez de quedar bajo
//    los botones de minimizar/maximizar/cerrar) y reservan su ancho;
//  - con el agente detenido hay un botón "Iniciar agente" centrado;
//  - la tarjeta de computer use ofrece segundo plano / controlar la PC / cancelar;
//  - StudIA: su barra no queda bajo los botones de ventana, levanta el servidor
//    de embeddings recién al abrirse, y Main.qml la carga en el índice que le
//    da NavBar (la 16.ª entrada; Configuración pasa a ser la 17.ª).
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

        const studia = read("StudiaPage.qml.txt")
        check(studia.length > 5000, "se leyó StudiaPage")
        const barra = block(studia, "// ── Barra superior ──")
        check(barra.indexOf("rightMargin: 16 + root.windowControlsReserve") > 0,
              "StudIA: la barra reserva el ancho de los botones de ventana")
        check(studia.indexOf("Component.onCompleted: Studia.activar()") > 0,
              "StudIA: el servidor de embeddings arranca al abrir la pestaña")

        const main = read("Main.qml.txt")
        check(main.indexOf("currentIndex === 15; asynchronous: true; source: \"pages/StudiaPage.qml\"") > 0,
              "Main.qml: StudiaPage en el índice 15")
        check(main.indexOf("currentIndex === 16; asynchronous: true; source: \"pages/MonitorPage.qml\"") > 0,
              "Main.qml: Monitor en el índice 16 (la 17.ª entrada de NavBar)")
        check(main.indexOf("currentIndex === 17; asynchronous: true; source: \"pages/SettingsPage.qml\"") > 0,
              "Main.qml: Configuración pasa al índice 17")

        // Monitor: todo sale de App.monitor y el reporte se copia desde el header.
        const monitor = read("MonitorPage.qml.txt")
        check(monitor.indexOf("import LlamaCode 1.0") > 0, "Monitor: importa el módulo (Lc* desde qml/pages)")
        check(monitor.indexOf("App.monitor") > 0, "Monitor: lee App.monitor")
        check(monitor.indexOf("App.copyMonitorReport()") > 0, "Monitor: botón Copiar reporte")
        check(monitor.indexOf("PageHeader {") > 0,
              "Monitor: usa PageHeader (reserva el ancho de los botones de ventana)")

        check(monitor.indexOf("actionEnabled: root.hasData") > 0,
              "Monitor: Copiar reporte deshabilitado sin datos")

        // Benchmark: la página carga asíncrona y los Loader de encabezado se
        // creaban de a uno (faltaban de "Fixes" en adelante). Inline component.
        const bench = read("BenchmarkPage.qml.txt")
        check(bench.indexOf("text: \"tabla_") < 0, "Benchmark: títulos sin nombres internos (tabla_best_…)")
        check(bench.indexOf("sourceComponent: sortableHeader") < 0,
              "Benchmark: encabezados sin Loader")
        check((bench.match(/SortableHeader \{ column: /g) || []).length === 25,
              "Benchmark: los 25 encabezados son SortableHeader")

        // Binarios: el build MTP sólo existe para Windows.
        const bins = read("BinariesPage.qml.txt")
        check(bins.indexOf("visible: Qt.platform.os === \"windows\"") > 0,
              "Binarios: Instalar build MTP sólo en Windows")
        check(bins.indexOf("elide: Text.ElideRight") > 0, "Binarios: nombres largos recortados")

        // Agentes: mismo encabezado que el resto (título + arrastre + botones de ventana).
        const agents = read("AgentsPage.qml.txt")
        check(agents.indexOf("PageHeader {") > 0, "Agentes: usa PageHeader")
        check(agents.indexOf("selectedId.length > 0 && App.activeAgentDefinitionId === selectedId") > 0,
              "Agentes: un agente sin guardar no figura como Activo")

        // Respuestas del modelo: razonamiento plegado y markdown seguro (App.renderMarkdown,
        // sin TextEdit.MarkdownText, que cargaría HTML/imágenes remotas).
        check(agent.indexOf("function splitThink(") > 0, "Agente: separa el <think> de la respuesta")
        check(agent.indexOf("App.renderMarkdown(") > 0, "Agente: respuesta en markdown")
        check(chat.indexOf("App.renderMarkdown(") > 0, "Chat: respuesta en markdown")
        check(agent.indexOf("MarkdownText") < 0 && chat.indexOf("MarkdownText") < 0,
              "Chat/Agente: nunca TextEdit.MarkdownText (HTML crudo / imágenes remotas)")
        check(agent.indexOf("\"Segoe UI\"") < 0 && chat.indexOf("\"Segoe UI\"") < 0,
              "Chat/Agente: sin fuentes de Windows fijas")

        // Investigación: el resultado de la última corrida (p. ej. informe rechazado por
        // la auditoría) se muestra; antes quedaba escondido en researchStatus.
        const research = read("ResearchPage.qml.txt")
        check(research.indexOf("id: lastResearchCard") > 0, "Investigación: muestra el resultado de la última corrida")
        check(research.indexOf("visible: !App.researchRunning && status.length > 0") > 0,
              "Investigación: la tarjeta aparece al terminar, no durante la corrida")

        // Lanzar: columna acotada y centrada con la ventana maximizada.
        const launch = read("LaunchPage.qml.txt")
        check(launch.indexOf("Layout.maximumWidth: 1100") > 0, "Lanzar: columna acotada")

        console.log(fails === 0 ? "ALL PASS" : ("FAIL count=" + fails))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
