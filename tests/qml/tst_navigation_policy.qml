import QtQuick
import "NavigationPolicy.js" as NavigationPolicy

QtObject {
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    Component.onCompleted: {
        const agent = {
            serverOnly: true,
            keepDuringAgentTransition: true,
            keepDuringThinkingRestart: true
        }
        check(!NavigationPolicy.shouldNavigateToLaunch(agent, false, false, true, false),
              "Agente permanece visible durante el hot-swap sin backend")
        check(NavigationPolicy.pageEnabled(agent, false, false, true),
              "Agente permanece habilitado durante el hot-swap")
        check(NavigationPolicy.shouldNavigateToLaunch(agent, false, false, false, false),
              "Agente vuelve a Lanzar ante una detencion real")

        const tasks = { serverOnly: true, agentOnly: true, keepDuringAgentTransition: true }
        check(!NavigationPolicy.shouldNavigateToLaunch(tasks, false, false, true, false),
              "Tasks conserva la vista durante una transicion activa")
        check(NavigationPolicy.shouldNavigateToLaunch(tasks, true, false, false, false),
              "Tasks exige agente cuando no hay transicion")

        // Línea de estado de la barra lateral: refleja el servidor real, no el
        // texto fijo del arranque (con ASTRA listo decía "servidor detenido").
        check(NavigationPolicy.statusLine(true, "Detectando hardware…", "stopped", false, false, false)
              === "Detectando hardware…", "durante el arranque muestra la fase")
        check(NavigationPolicy.statusLine(false, "Aplicación lista · servidor detenido", "running", true, false, false)
              === "Servidor activo · agente detenido", "servidor listo sin agente")
        check(NavigationPolicy.statusLine(false, "", "running", true, false, true)
              === "Servidor y agente activos", "servidor y agente")
        check(NavigationPolicy.statusLine(false, "", "running", false, false, false)
              === "Cargando modelo…", "running sin ready = cargando")
        check(NavigationPolicy.statusLine(false, "", "running", true, true, false)
              === "Deteniendo servidor…", "deteniendo tiene prioridad")
        check(NavigationPolicy.statusLine(false, "", "failed", false, false, false).indexOf("falló") >= 0,
              "falla visible")
        check(NavigationPolicy.statusLine(false, "", "stopped", false, false, false)
              === "Aplicación lista · servidor detenido", "detenido")

        console.log(fails === 0 ? "TODO OK" : (fails + " FALLAS"))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
