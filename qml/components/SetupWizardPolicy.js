.pragma library

// Reglas del asistente de configuracion inicial (setupPopup en Main.qml).
// Viven aca, puras, para testearlas sin levantar la app (tst_setup_wizard_policy).

// La card "Perfil recomendado" (perfil de sistema: binario + modelo con un clic)
// se ofrece mientras el usuario no la descarte y haya algo que recomendar.
function quickStartVisible(dismissed, showcaseCount, systemLaunchId) {
    return !dismissed && (showcaseCount > 0 || (systemLaunchId || "").length > 0)
}

// El pick suelto de HuggingFace es el camino MANUAL. Si se muestra a la vez que
// la card de inicio rapido, el usuario ve dos recomendaciones distintas (ej.
// "Qwen3.5-4B MTP" arriba y "Qwen2.5-7B" abajo) sin saber cual conviene: solo
// aparece cuando no hay inicio rapido (o el usuario dijo "No, gracias").
function showManualModelPick(hasAnyModel, recommendationCount, quickStartShown) {
    return !hasAnyModel && recommendationCount > 0 && !quickStartShown
}

// hasAnyLaunch cuenta los perfiles de sistema que trae la app: es true desde el
// primer arranque, sin binario ni modelo. El paso 3 solo esta hecho cuando
// existen los tres.
function launchStepDone(hasAnyBinary, hasAnyModel, hasAnyLaunch) {
    return hasAnyBinary && hasAnyModel && hasAnyLaunch
}

function launchStepText(hasAnyBinary, hasAnyModel, hasAnyLaunch) {
    if (launchStepDone(hasAnyBinary, hasAnyModel, hasAnyLaunch))
        return "Listo para lanzar."
    if (hasAnyBinary && hasAnyModel)
        return "Creando automáticamente Backend, Model, Runtime y perfil de lanzamiento."
    return "Primero completá binario y modelo."
}
