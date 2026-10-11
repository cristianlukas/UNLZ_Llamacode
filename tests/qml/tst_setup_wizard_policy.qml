import QtQuick
import "SetupWizardPolicy.js" as SetupWizardPolicy

QtObject {
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    Component.onCompleted: {
        // Primer arranque real: los perfiles de sistema ya cuentan como "launch".
        check(!SetupWizardPolicy.launchStepDone(false, false, true),
              "sin binario ni modelo el paso 3 NO esta hecho aunque haya perfiles de sistema")
        check(SetupWizardPolicy.launchStepText(false, false, true) === "Primero completá binario y modelo.",
              "sin binario ni modelo pide completarlos (no dice 'Listo para lanzar')")
        check(!SetupWizardPolicy.launchStepDone(true, false, true),
              "con binario pero sin modelo el paso 3 no esta hecho")
        check(SetupWizardPolicy.launchStepText(true, true, false).indexOf("Creando") === 0,
              "con binario y modelo pero sin perfil avisa que lo esta creando")
        check(SetupWizardPolicy.launchStepDone(true, true, true)
              && SetupWizardPolicy.launchStepText(true, true, true) === "Listo para lanzar.",
              "con los tres el paso 3 esta listo")

        check(SetupWizardPolicy.quickStartVisible(false, 0, "sys-4gb"),
              "ofrece el perfil de sistema recomendado")
        check(SetupWizardPolicy.quickStartVisible(false, 2, ""),
              "ofrece el showcase aunque no haya tier unico")
        check(!SetupWizardPolicy.quickStartVisible(true, 2, "sys-4gb"),
              "'No, gracias' oculta el inicio rapido")
        check(!SetupWizardPolicy.quickStartVisible(false, 0, undefined),
              "sin nada que recomendar no hay card")

        check(!SetupWizardPolicy.showManualModelPick(false, 3, true),
              "con inicio rapido visible NO muestra una segunda recomendacion de modelo")
        check(SetupWizardPolicy.showManualModelPick(false, 3, false),
              "tras 'No, gracias' muestra el pick manual")
        check(!SetupWizardPolicy.showManualModelPick(true, 3, false),
              "con un modelo ya instalado no recomienda otro")
        check(!SetupWizardPolicy.showManualModelPick(false, 0, false),
              "sin recomendaciones no muestra la card")

        console.log(fails === 0 ? "TODO OK" : (fails + " FALLAS"))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
