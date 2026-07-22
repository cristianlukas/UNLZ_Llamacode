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
