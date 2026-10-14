.pragma library

// Pestañas de Configuración. Antes eran 16 secciones en un solo scroll y en un
// orden sin lógica (GPU en tres lugares, lo del agente en cuatro). Cada sección
// de SettingsPage.qml pertenece a exactamente UNA pestaña: tst_settings_tabs lo
// verifica leyendo el .qml real, así una sección nueva no queda invisible.
// Pura, para testearla sin levantar la app.

var tabs = [
    { key: "general",      title: "General", titleKey: "settings.tab.general",
      sections: ["appearanceSection", "customSection", "languageSection", "systemSection"] },
    { key: "hardware",     title: "GPU y motores", titleKey: "settings.tab.hardware",
      sections: ["gpuInferenceSection", "gpuSection", "astraSection"] },
    { key: "network",      title: "Red y API", titleKey: "settings.tab.network",
      sections: ["gatewaySection"] },
    { key: "agent",        title: "Agente y chat", titleKey: "settings.tab.agent",
      sections: ["chatSection", "teacherSection", "auxiliarySection"] },
    // Editor grande (capacidades, directivas, personalidad): pestaña propia.
    { key: "agentProfiles", title: "Perfiles de agente", titleKey: "settings.tab.agentProfiles",
      sections: ["agentProfilesSection"] },
    { key: "integrations", title: "Integraciones", titleKey: "settings.tab.integrations",
      sections: ["intgSection", "mailSection"] },
    { key: "data",         title: "Datos y diagnóstico", titleKey: "settings.tab.data",
      sections: ["performanceSection", "dataSection"] }
]

function tabForSection(sectionId) {
    for (var i = 0; i < tabs.length; ++i)
        if (tabs[i].sections.indexOf(sectionId) >= 0)
            return tabs[i].key
    return ""
}

function isValidTab(key) {
    for (var i = 0; i < tabs.length; ++i)
        if (tabs[i].key === key) return true
    return false
}

// Con búsqueda activa se ignoran las pestañas: el usuario busca en TODO.
function isSectionVisible(sectionId, currentTab, searchText, matchesSearch) {
    if (String(searchText || "").trim().length > 0)
        return matchesSearch
    return tabForSection(sectionId) === currentTab
}

// Cuántas secciones de cada pestaña coinciden con la búsqueda (para marcar las
// pestañas con resultados). matchFn(sectionId) -> bool.
function matchCountForTab(tabKey, matchFn) {
    for (var i = 0; i < tabs.length; ++i) {
        if (tabs[i].key !== tabKey) continue
        var n = 0
        for (var j = 0; j < tabs[i].sections.length; ++j)
            if (matchFn(tabs[i].sections[j])) ++n
        return n
    }
    return 0
}

// Búsqueda por INICIO de palabra: "lan" encuentra "LAN" pero no "plano" (antes,
// por substring, "lan" mostraba Temas custom). Cada término tiene que aparecer.
// haystack y query ya vienen normalizados (minúsculas, sin tildes).
function textMatches(haystack, query) {
    var terms = String(query || "").trim().split(/\s+/)
    var text = " " + String(haystack || "").replace(/[^0-9a-z\u00f1]+/g, " ") + " "
    for (var i = 0; i < terms.length; ++i) {
        var term = terms[i].replace(/[^0-9a-z\u00f1]+/g, "")
        if (term.length === 0) continue
        if (text.indexOf(" " + term) < 0) return false
    }
    return true
}
