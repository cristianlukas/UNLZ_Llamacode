import QtQuick
import "SettingsTabsPolicy.js" as SettingsTabs

// Pestañas de Configuración (SettingsTabsPolicy.js). Lee el SettingsPage.qml
// REAL (staged como texto) para exigir que cada sección esté en una pestaña:
// una sección sin pestaña no se vería nunca sin buscar.
QtObject {
    property int fails: 0

    function check(condition, message) {
        console.log((condition ? "  PASS " : "  FAIL ") + message)
        if (!condition) fails++
    }

    function readPage() {
        var xhr = new XMLHttpRequest()
        xhr.open("GET", Qt.resolvedUrl("SettingsPage.qml.txt"), false)
        xhr.send()
        return xhr.responseText || ""
    }

    Component.onCompleted: {
        const page = readPage()
        check(page.length > 1000, "se pudo leer SettingsPage.qml")
        const ids = []
        const re = /^\s*id:\s*(\w+Section)\s*$/gm
        var m
        while ((m = re.exec(page)) !== null) ids.push(m[1])
        check(ids.length >= 10, "la página tiene secciones (" + ids.length + ")")

        for (var i = 0; i < ids.length; ++i)
            check(SettingsTabs.tabForSection(ids[i]) !== "", ids[i] + " pertenece a una pestaña")

        var seen = {}
        var dup = false
        for (var t = 0; t < SettingsTabs.tabs.length; ++t)
            for (var s = 0; s < SettingsTabs.tabs[t].sections.length; ++s) {
                const sid = SettingsTabs.tabs[t].sections[s]
                if (seen[sid]) dup = true
                seen[sid] = true
                check(ids.indexOf(sid) >= 0, "la pestaña " + SettingsTabs.tabs[t].key + " no apunta a una sección inexistente: " + sid)
            }
        check(!dup, "ninguna sección está en dos pestañas")
        for (var k = 0; k < SettingsTabs.tabs.length; ++k)
            check(SettingsTabs.tabs[k].sections.length > 0, "la pestaña " + SettingsTabs.tabs[k].key + " no está vacía")

        // Visibilidad.
        check(SettingsTabs.isSectionVisible("gatewaySection", "network", "", false),
              "sin búsqueda se ve la sección de la pestaña actual")
        check(!SettingsTabs.isSectionVisible("gatewaySection", "general", "", true),
              "sin búsqueda no se ven secciones de otras pestañas")
        check(SettingsTabs.isSectionVisible("mailSection", "general", "correo", true),
              "con búsqueda se ve lo que coincide aunque sea de otra pestaña")
        check(!SettingsTabs.isSectionVisible("appearanceSection", "general", "correo", false),
              "con búsqueda se oculta lo que no coincide aunque sea de la pestaña actual")
        check(SettingsTabs.isSectionVisible("appearanceSection", "general", "   ", false),
              "espacios no cuentan como búsqueda")

        check(SettingsTabs.matchCountForTab("integrations",
              function(id) { return id === "mailSection" }) === 1, "cuenta coincidencias por pestaña")
        check(SettingsTabs.isValidTab("general") && !SettingsTabs.isValidTab("nope"),
              "valida claves guardadas")

        // Búsqueda por inicio de palabra.
        check(SettingsTabs.textMatches("compartir server en la red local (lan)", "lan"), "lan encuentra LAN")
        check(!SettingsTabs.textMatches("primer plano y contraste", "lan"), "lan NO encuentra plano")
        check(SettingsTabs.textMatches("gpu de procesamiento", "gpu proc"), "varios términos por prefijo")
        check(!SettingsTabs.textMatches("gpu de procesamiento", "gpu correo"), "todos los términos tienen que estar")
        check(SettingsTabs.textMatches("api key (opcional)", "key"), "ignora puntuación alrededor")
        check(SettingsTabs.textMatches("x", "  "), "consulta vacía coincide")

        console.log(fails === 0 ? "TODO OK" : (fails + " FALLAS"))
        Qt.exit(fails === 0 ? 0 : 1)
    }
}
