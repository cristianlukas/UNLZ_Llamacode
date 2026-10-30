import QtQuick
import QtQuick.Controls
import LlamaCode 1.0

// LcButton / LcComboBox / LcSlider REALES (staged en el módulo del harness como
// RealLcButton / RealLcComboBox / LcSlider: los nombres originales los ocupan
// stubs que usan otras páginas). Fija lo que se vio al revisar la app maximizada:
//  - un botón deshabilitado se veía igual que uno activo (Guardar/Eliminar de
//    un perfil de sistema parecían usables);
//  - el combo reservaba dos veces el indicador: "IMAP" quedaba en "I…";
//  - el slider nativo era blanco y pintaba el tramo lleno a la derecha.
ApplicationWindow {
    id: win
    width: 400; height: 900   // alto de sobra: el diálogo se limita a la ventana
    visible: true

    property int fails: 0
    function check(cond, msg) {
        console.log((cond ? "  PASS " : "  FAIL ") + msg)
        if (!cond) win.fails++
    }

    Column {
        RealLcButton { id: onBtn; text: "Guardar" }
        RealLcButton { id: offBtn; text: "Guardar"; enabled: false }
        RealLcComboBox {
            id: combo
            width: 110
            textRole: "label"
            model: [ { label: "IMAP" }, { label: "POP3" } ]
        }
        LcSlider { id: slider; width: 300; from: 100; to: 375; value: 250 }
    }

    // Formulario de cinco filas como "Agregar directorio": tiene que entrar
    // entero (antes el diálogo medía ~0 de contenido y cortaba el modo de escaneo).
    RealLcDialog {
        id: dlg
        title: "Agregar directorio"
        width: 360
        contentItem: Column {
            spacing: 12
            Repeater { model: 5; Rectangle { width: 300; height: 34 } }
        }
    }

    Timer {
        interval: 200; running: true
        onTriggered: {
            check(onBtn.opacity === 1, "botón habilitado opaco")
            check(offBtn.opacity < 0.6, "botón deshabilitado atenuado (es " + offBtn.opacity + ")")

            const t = combo.contentItem
            check(t.rightPadding <= 4, "el texto del combo no vuelve a reservar el indicador")
            check(!t.truncated, "\"IMAP\" entra entero en un combo de 110 px")

            const fill = slider.background.children[0]
            check(Qt.colorEqual(fill.color, Theme.accent), "el tramo lleno usa el acento del tema")
            check(Math.abs(fill.width - slider.visualPosition * slider.background.width) < 1,
                  "el tramo lleno va de la izquierda hasta la perilla")
            check(Qt.colorEqual(slider.handle.color, Theme.accent), "perilla con el acento (no blanca)")

            dlg.open()
            const needed = dlg.contentItem.implicitHeight + dlg.header.height + dlg.footer.height
                           + dlg.topPadding + dlg.bottomPadding
            check(dlg.contentItem.implicitHeight >= 5 * 34, "el contenido del diálogo informa su alto")
            check(dlg.height >= needed - 1, "el diálogo no corta su formulario (" + dlg.height + " >= " + needed + ")")

            console.log(win.fails === 0 ? "ALL PASS" : ("FAIL count=" + win.fails))
            Qt.exit(win.fails === 0 ? 0 : 1)
        }
    }
}
