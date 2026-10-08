# Plan de portabilidad Ubuntu/Windows de LlamaCode

## Objetivo

Mantener una sola base de código y dos backends de plataforma: Windows conserva
Win32/UI Automation/Windows OCR; Ubuntu agrega CMake/Ninja, automatización X11,
accesibilidad AT-SPI2 y OCR Tesseract. Las capacidades comunes (modelos GGUF,
servidores `llama.cpp`, chat, agentes, tareas, browser, memoria, benchmarks,
voz, SDK y persistencia) no dependen de rutas Windows.

## Relevamiento

1. Compilar la aplicación y la suite QtTest con builds Linux separados en la
   caché nativa para no pisar `build/` ni `build_tests/` usados por Windows.
2. Auditar `Q_OS_WIN`, `.exe`, `cmd`, PowerShell, DPAPI, WinRT OCR, UIA, Job
   Objects, registro de inicio y rutas `%APPDATA%`.
3. Mantener esas APIs en ramas Win32 y reemplazar sólo los contratos que tenían
   stubs Linux: ventanas, foco, mouse/teclado, captura, controles, esperas,
   aserciones y OCR.
4. Agregar pruebas unitarias de los contratos portables y pruebas manuales de
   escritorio sólo cuando exista una sesión gráfica real.

## Implementación realizada

- `LinuxDesktopBackend` encapsula X11 (`xprop`, `xwininfo`, `xdotool`, `wmctrl`)
  para enumerar ventanas, enfocar/redimensionar/maximizar, mover/clickear/arrastrar,
  escribir, teclas, scroll y cursor.
- AT-SPI2 vía `gdbus` enumera controles accesibles, conserva referencias estables
  durante la vida de la ventana, permite acciones semánticas y ofrece fallback
  seguro a bounding-rect; el matching difuso no adivina coordenadas.
- `OcrEngine` conserva Windows.Media.Ocr en Windows y usa Tesseract TSV en Linux,
  preservando rects por palabra y la conversión de coordenadas existente.
- `TrayController` usa `QSystemTrayIcon` en ambas plataformas: cerrar la ventana
  con la opción activa la oculta sin destruirla, el menú permite reabrir/salir y
  Ubuntu se integra con GNOME mediante StatusNotifier/AppIndicator.
- Los controles de minimizar, maximizar/restaurar y cerrar permanecen en el
  mismo `Main.qml`: `App.buildPlatform` se fija durante la compilación mediante
  `Q_OS_WIN`/`Q_OS_LINUX`; Windows conserva los glifos `Segoe MDL2 Assets` y
  Linux usa formas QML portables, sin cargar una fuente exclusiva de Windows.
- `bootstrap.sh` instala los proveedores Linux y ya no hace reset destructivo si
  el checkout existente tiene cambios sin commitear.
- `scripts/build-linux.sh` y `scripts/tests-linux.sh` agregan el flujo Ubuntu
  reproducible con caché nativa en `~/.cache/llamacode/`; aceptan
  `LC_BUILD_DIR` y `LC_TEST_BUILD_DIR` para una ubicación explícita. Si el
  checkout está en NTFS, espejan automáticamente el código en esa caché antes
  de ejecutar CMake/Ninja, sin tocar el checkout original.
- `CLAUDE.md`, `AGENTS.md` y `README.md` separan los comandos Windows de sus
  equivalentes Ubuntu y documentan las limitaciones reales por sesión gráfica.
- Los perfiles de usuario y las raíces de modelos se comparten con Windows:
  Ubuntu usa `LLAMACODE_PROFILES_DIR` y `LLAMACODE_MODEL_ROOTS_FILE` desde el
  launcher, traduciendo `C:/` y `D:/` sólo durante la ejecución. Los JSON
  compartidos vuelven a guardarse en formato Windows para que ambos sentidos
  sean reversibles.
- Los dos volúmenes NTFS quedaron en `/etc/fstab` por UUID, con `nofail` y
  `x-systemd.automount`: el SSD `7CFE1E0FFE1DC1F6` conserva el checkout y los
  modelos de AppData, `4E503F15503F02EF` se monta como `Disco local` (D:, donde
  está Qwen3.8-Flash-Next) y `B82C7C9E2C7C58F8` como `HDD extra`.
- El registro de binarios y el catálogo SQLite siguen siendo por sistema. El
  registro necesita ELF en Linux frente a `.exe`/CUDA en Windows y el catálogo
  contiene rutas absolutas; Ubuntu recibió un catálogo local migrado con los
  `stable_id` de Windows y un fallback Linux CPU. Esto evita corrupción y no
  impide que los perfiles comunes apunten al mismo modelo.
- Ubuntu tiene instalado el toolkit CUDA 12.0 y NCCL 2.18, y registra una build
  Linux experimental de `flashnext-2x3090` compilada para `compute_86` (las dos
  RTX 3090). El perfil compartido puede declarar `platformArgs.linux`: esos
  argumentos reemplazan sólo la lista Linux y Windows sigue usando su lista
  histórica sin flags CUDA experimentales.

## Criterio de aceptación

- CMake configure + build Debug/Release en Ubuntu.
- `ctest --output-on-failure` verde en Ubuntu.
- La app carga todas las páginas QML en una sesión X11.
- Las herramientas desktop no devuelven un stub “sólo Windows”; devuelven datos o
  un error accionable si falta un proveedor opcional.
- `desktop_windows`, `desktop_focus`, `desktop_click`, `desktop_stroke`,
  `desktop_type`, `desktop_key`, `desktop_scroll`, `desktop_controls`,
  `desktop_click_element`, `desktop_control_action`, `desktop_observe`,
  `desktop_click_text`, `desktop_wait_for` y `desktop_assert` tienen camino Linux.
- Los cambios de Windows quedan dentro de sus ramas preexistentes y el diff se
  revisa con `git diff --check`.

## Dependencias Linux

`git rsync cmake ninja-build build-essential python3 python3-pip python3-venv`, Qt 6.8.3
`gcc_64`, las bibliotecas XCB/GL/DBus/libsecret, `x11-utils`, `xdotool`, `wmctrl`,
`at-spi2-core`, `tesseract-ocr`, `tesseract-ocr-spa` y `bubblewrap`. El backend
de escritorio requiere X11 y una sesión desbloqueada; en Wayland puro las
políticas del compositor pueden impedir inyección global, por lo que LlamaCode
lo informa en vez de simular éxito.

## Instrucciones por plataforma

### Windows — existentes

- `build.bat [Debug|Release|Both]` y `tests.bat [Debug|Release]`.
- `cmake -G "Visual Studio 17 2022" -A x64`.
- PowerShell `.ps1`, accesos `.lnk`, registro `Run`, Job Object, UI Automation y
  Windows.Media.Ocr.

### Ubuntu/Linux — equivalentes

- `./scripts/build-linux.sh Debug` o `./scripts/build-linux.sh Release`.
- `./scripts/tests-linux.sh Release` (o `Debug` para iterar).
- `cmake -G Ninja -DCMAKE_BUILD_TYPE=Release`.
- `~/.config/autostart/llamacode-scheduler.desktop`, grupos de procesos Unix o
  bubblewrap, AT-SPI2, X11 y Tesseract.
- El SDK se prueba con `python3 -m unittest discover ...` y
  `node sdk/node/test/self-test.mjs`; no requiere PowerShell.

### Configuración compartida entre arranques

- El launcher instalado en `~/.local/bin/llamacode` activa automáticamente los
  perfiles del checkout y `model_roots.json` del SSD cuando los montajes están
  disponibles.
- No ejecutar LlamaCode simultáneamente en Windows y Ubuntu sobre los mismos
  JSON: los archivos se escriben de forma atómica y con backups, pero dos
  instancias pueden sobrescribir cambios lógicamente concurrentes.
- Windows Fast Startup/hibernación debe estar desactivado si se necesita
  escritura Linux sobre NTFS; si Windows dejó el volumen hibernado, Ubuntu no
  debe forzar el montaje RW.

### Qwen3.8-Flash-Next en Ubuntu

El perfil `173_Qwen3.8-Flash-Next Q4_K_XL (ngram->SSD)` usa en Ubuntu el GGUF
UD-Q4_K_XL de 103.68 GB en `Disco local`, expertos residentes en host y caché
MoE de 188 slots. Se verificó carga completa de 49/49 capas y respuesta por las
dos GPU. En una A/B de 256 tokens a 16K de contexto, la misma configuración
pasó de 16.45 tok/s sin caché a 36.04 tok/s con caché (+119%). Es una medición
de esta máquina, no una promesa para otros PCIe/RAM.

La rama usada es experimental y conserva los límites conocidos de los PR de
expert-cache/MTP. El cabezal MTP compartido Q8_0 fue descargado y validado, pero
`draft-mtp` junto con expert-cache produjo un acceso ilegal CUDA reproducible en
la primera generación. MTP sin expert-cache fue estable, aunque sólo alcanzó
13.07 tok/s en la campaña comparable, por lo que no se activa en el perfil
usable. La medición controlada con el mismo prompt dejó `--batch-size 512`
por encima de 4096 (45.22 frente a 43.09 tok/s); el perfil Linux usa ahora
512/512. P2 funciona entre las GPU, pero `nvidia-smi` reporta NVLink inactivo
y topología PHB: NCCL está instalado, aunque no puede activar un enlace físico
que el sistema no está exponiendo.

También se descargó y escaneó Ling 3.0 Tiny APEX-I Compact; la comparación
controlada está documentada en `docs/ling-3.0-tiny.md`. En la misma receta
local alcanzó 203.75 tok/s de decode, frente a 148.37 para Qwen3.5 4B, 100.07
para Qwen3.5 9B y 69.85 para Gemma 4 12B. Qwen3.5 2B fue más rápido, con
257.42 tok/s.

Las pruebas adicionales tampoco justifican activar speculative decoding: n-gram
`M=7` fue estable, pero alcanzó 36.97 tok/s frente a 45.22 tok/s sin speculative
en el mismo prompt. `--split-mode tensor --tensor-split 1,1` no carga para esta
arquitectura: la build devuelve `LLAMA_SPLIT_MODE_TENSOR not implemented for
architecture 'qwen4exp'`.
