import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0

// LcSpinBox / LcRadioButton son los archivos REALES (staged en el módulo del
// harness). Con el estilo Basic el SpinBox es claro y las páginas le ponían
// texto Theme.textPrimary (claro): el valor quedaba invisible (Benchmark →
// Concurrencia). Corre con el runtime `qml` en offscreen; sale 0 si todo pasa.
ApplicationWindow {
    id: win
    width: 400; height: 300
    visible: true

    property int fails: 0
    function check(cond, msg) {
        console.log((cond ? "  PASS " : "  FAIL ") + msg)
        if (!cond) win.fails++
    }
    function lum(c) {
        function ch(v) { return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4) }
        return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b)
    }
    function contrast(a, b) {
        const la = lum(a), lb = lum(b)
        return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
    }

    ColumnLayout {
        anchors.fill: parent
        LcSpinBox { id: spin; from: 1; to: 3; value: 1; editable: true }
        // Override per-uso como en BenchmarkPage: tiene que seguir ganando.
        LcSpinBox {
            id: overridden
            from: 0; to: 10; value: 5
            contentItem: TextInput { text: overridden.displayText; color: Theme.textPrimary }
        }
        ButtonGroup { id: group }
        LcRadioButton { id: radioA; text: "A"; checked: true; ButtonGroup.group: group }
        LcRadioButton { id: radioB; text: ""; ButtonGroup.group: group }
    }

    Component.onCompleted: {
        check(Qt.colorEqual(spin.background.color, Theme.inputBg), "fondo del SpinBox = Theme.inputBg")
        const c = contrast(spin.contentItem.color, spin.background.color)
        check(c >= 4.5, "texto legible sobre el fondo (contraste " + c.toFixed(2) + ")")
        check(contrast(overridden.contentItem.color, overridden.background.color) >= 4.5,
              "un contentItem propio con textPrimary también se lee")
        check(overridden.contentItem.text === "5", "el override per-uso gana")

        spin.increase()
        check(spin.value === 2 && spin.contentItem.text === "2", "+ incrementa y se muestra: " + spin.contentItem.text)
        spin.increase(); spin.increase()
        check(spin.value === 3, "respeta el máximo")
        check(spin.up.indicator.opacity < 1 && spin.down.indicator.opacity === 1,
              "en el máximo el + se ve deshabilitado y el − no")

        check(Qt.colorEqual(radioA.indicator.color, Theme.inputBg), "radio con fondo del tema (no blanco)")
        check(radioA.indicator.children[0].visible && !radioB.indicator.children[0].visible,
              "sólo el radio marcado muestra el punto")
        radioB.checked = true
        check(!radioA.checked && radioB.indicator.children[0].visible, "ButtonGroup sigue siendo exclusivo")
        check(radioB.contentItem.leftPadding === 0, "sin texto no reserva espacio a la derecha del círculo")

        console.log(win.fails === 0 ? "TODO OK" : (win.fails + " FALLAS"))
        Qt.exit(win.fails === 0 ? 0 : 1)
    }
}
