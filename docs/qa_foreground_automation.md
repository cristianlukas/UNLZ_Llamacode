# QA de automatización foreground

Estos probes son opt-in porque necesitan una sesión de escritorio interactiva y no
deben mover el mouse ni cubrir pantallas durante `ctest`.

## Matriz visual

`build_tests/Release/qa_visual_automation.exe --matrix` recorre todos los monitores,
dos objetivos y temas claro/oscuro. Agregar `--execute-click` valida también el clic
real sobre las ventanas propias del probe.

## OCR autocontenido

`build_tests/Release/qa_ocr_probe.exe --self-contained` crea temporalmente controles
Qt accesibles a pantalla completa en cada monitor. Cruza cada palabra reconocida por
Windows OCR con el control reportado por UI Automation en el mismo punto físico. Sale
con código 0 si el acuerdo mínimo es al menos 70%, 1 ante discrepancias y 2 cuando no
hay motor OCR o muestra suficiente.

El modo autocontenido evita depender de aplicaciones, idioma de interfaz, ventanas
preexistentes o preparación manual. Las superficies se destruyen al terminar.

## Registro de disponibilidad y corrida compartida

### 2026-08-27 — no se inicia una segunda corrida

La comprobación de disponibilidad detectó actividad interactiva reciente y una
corrida existente de `tests.bat Debug` (PID propietario 60104, `ctest` hijo
30824). El build de Debug ya había publicado `OK` para el fingerprint
`DB20E0A28A6564A0EA43F35D1DFFD91E`; la suite de tests todavía estaba ejecutándose
al momento de la comprobación. CPU y memoria no eran un problema, pero la PC y la
lane de tests no estaban libres. Por eso no se lanzó otra compilación, no se
robaron locks y no se ejecutaron probes foreground que pudieran mover el mouse o
tomar el foco.

Observación de coordinación: `build_coord.ps1 -Lane tests -Action status` informó
`STALE` mientras el propietario seguía vivo. La causa observada es que
`ConvertFrom-Json` convierte `ownerStartedUtc` en `DateTime` y al convertirlo de
nuevo a string usa el formato local, mientras `Get-Process.StartTime` se compara
como ISO 8601. Esto queda pendiente como corrección separada del coordinador; no
se modificó durante esta verificación.

### Cierre de la verificación — 2026-08-27

La corrida compartida terminó con `tests.DB20E0A28A6564A0EA43F35D1DFFD91E.txt`
en estado `OK`. Luego se ejecutó `build.bat Debug NOPAUSE`, también con estado
`OK` (`build.DB20E0A28A6564A0EA43F35D1DFFD91E.txt`), y se confirmó la existencia
de `build/Debug/LlamaCode.exe` (26.113.024 bytes). El build fue incremental: el
ejecutable ya era posterior al archivo fuente más nuevo, por lo que su timestamp
no tuvo que avanzar; el acceso directo Debug sí fue actualizado.

No se ejecutaron `qa_visual_automation` ni `qa_ocr_probe`: ambos probes pueden
tomar foco, mostrar superficies o mover el mouse, y no había una ventana de prueba
dedicada aislada del entorno interactivo. Los locks de build y tests quedaron
libres al cierre.
