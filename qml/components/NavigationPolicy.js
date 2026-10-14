.pragma library

function backendRequirementSatisfied(page, backendAvailable, agentStarting) {
    return Boolean(!page.serverOnly || backendAvailable
            || (Boolean(page.keepDuringAgentTransition) && Boolean(agentStarting)))
}

function pageEnabled(page, backendAvailable, agentRunning, agentStarting) {
    return Boolean(backendRequirementSatisfied(page, backendAvailable, agentStarting)
            && (!page.agentOnly || agentRunning || agentStarting))
}

function shouldNavigateToLaunch(page, backendAvailable, agentRunning,
                                agentStarting, thinkingRestarting) {
    const preserveThinkingRestart = page.keepDuringThinkingRestart && thinkingRestarting
    const backendMissing = !backendRequirementSatisfied(page, backendAvailable, agentStarting)
    const agentMissing = page.agentOnly && !agentRunning && !agentStarting
    return (backendMissing && !preserveThinkingRestart) || agentMissing
}

// Línea de estado bajo el nombre de la app. Antes mostraba el texto fijo del
// arranque ("Aplicación lista · servidor detenido") aunque después se cargara un
// modelo: con ASTRA listo seguía diciendo "servidor detenido".
function statusLine(startupBusy, startupStatus, serverState, serverReady,
                    serverStopping, agentRunning) {
    if (startupBusy) return startupStatus || ""
    if (serverStopping) return "Deteniendo servidor…"
    if (serverState === "failed") return "El servidor falló · ver Lanzar"
    if (serverState === "restarting") return "Reiniciando servidor…"
    if (serverState === "running") {
        if (!serverReady) return "Cargando modelo…"
        return agentRunning ? "Servidor y agente activos" : "Servidor activo · agente detenido"
    }
    return "Aplicación lista · servidor detenido"
}
