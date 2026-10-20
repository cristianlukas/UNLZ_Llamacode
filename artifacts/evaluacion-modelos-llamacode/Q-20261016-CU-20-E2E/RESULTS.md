# Resultados intermedios — Q-20261016-CU-20-E2E

Estado certificable vigente al 2026-10-20: **20/20 en el SHA** `AE85A27680AD2A8B3945F19BD4741177D699046676BE500D580D1E6949449F28`. CU01–CU05, CU07–CU17 y CU19–CU20 aprobaron con sus recibos; CU06 `ae85-cu06e` y CU18 `ae85-cu18g` cuentan por sus respectivos `REVALIDATION.json`, porque los recibos originales conservaron falsos negativos de validación. CU05–CU08 se repitieron en Edge con el perfil normal existente, en ventanas `--new-window`; no se usó Guest/InPrivate ni se navegó una pestaña previa. Los estados 19/20 y CAPTCHA que siguen abajo son auditorías históricas del 2026-10-19, superadas por las revalidaciones posteriores.

Auditoría independiente 2026-10-19 00:11 ART: SHA actual confirmado por hash del ejecutable y receipts: **19/20**; CU18 cuenta sólo con la revalidación conservada. `py_compile` y harness **71 + 9 subtests** pasan. CU06 continúa pendiente por `google.com/sorry/index`; el run Edge Guest y el puerto 8898 quedaron limpios. No reintentar durante el enfriamiento inmediato.


Auditoría CU06 2026-10-19 00:13 ART: ambos intentos (`ae85-cu06`, `ae85-cu06b`) en el SHA actual están bloqueados por el mismo challenge de Google. No hay un CU06 aprobado escondido en otro receipt del mismo SHA. Siguiente backoff: 6 horas desde el último intento; no antes de 09:04 UTC.


## Corridas vigentes agregadas

| Caso | Corrida | Resultado | Evidencia |
|---|---|---|---|
| CU14 | `ae85-cu14b` | Aprobado | 32,25 s; 6 llamadas de Computer Usage; `CU14-EXACT-9F2B` leído en Notepad y validado byte por byte en el archivo guardado. El retry de lectura del título no se penaliza si es exitoso, ocurre antes de escribir y usa la misma ventana. Receipt `receipts/runs/ae85-cu14b/RESULT.json`. |
| CU15 | `ae85-cu15` | Aprobado | 73,70 s; 15 llamadas; reemplazo visible y guardado de `sleepy` por `curious`. El archivo contiene exactamente `The quick brown fox jumps over the curious dog.\n`. Receipt `receipts/runs/ae85-cu15/RESULT.json`. |
| CU16 | `ae85-cu16b` | Aprobado | 24,22 s; 8 llamadas, `turn_error=null`; PNG 400×300 con cuatro lados rectos, 4.310 píxeles no blancos y cobertura completa de los cuatro lados. Receipt `receipts/runs/ae85-cu16b/RESULT.json`. El primer intento `ae85-cu16` dibujó bien, pero incluyó una llamada rechazada con puntos como pares; no cuenta. |
| CU17 | `ae85-cu17` | Aprobado | Selección UIA exacta del archivo de prueba y lectura posterior; receipt `receipts/runs/ae85-cu17/RESULT.json`. |
| CU18 | `ae85-cu18g` | Aprobado por revalidación | 82,8 s; 19 tool calls exitosas; marcador A1 guardado en disco. Receipt original conserva el falso negativo y `receipts/runs/ae85-cu18g/REVALIDATION.json` registra la revalidación con trazas runtime completas. |
| CU19 | `ae85-cu19a` | Aprobado | 66,7 s; Alfa vacío, Beta con `contenido beta solicitado`, guardado y releído; `receipts/runs/ae85-cu19a/RESULT.json`. |
| CU20 | `ae85-cu20a` | Aprobado | 58,5 s; frase `CU20-FRASE-UNICA-9F2B` escrita/guardada y exactamente una vez; `receipts/runs/ae85-cu20a/RESULT.json`. |
| CU06 | `ae85-cu06`, `ae85-cu06b` | Pendiente por CAPTCHA | Ambos receipts del SHA actual confirman que Google devolvió `google.com/sorry/index`: se ingresó/verificó la búsqueda, sin resultados, clic ni artículo. Último intento 00:04 ART; backoff siguiente no antes de 06:04 ART. `receipts/runs/ae85-cu06b/RESULT.json`; perfil Edge Guest cerrado. |

CU14 `ae85-cu14` fue un falso negativo del evaluador: la interfaz se leyó dos veces para confirmar el título durante la carga. Se actualizó el prompt para esperar la ventana y el evaluador ahora acepta una o más confirmaciones exitosas del nombre antes de la única escritura. Los casos de cleanup de Notepad también exigen detenerse inmediatamente cuando el título cambia de la pestaña objetivo. Harness validado con 70 pruebas y 9 subtests; el SHA del ejecutable no cambió.

CU16 se reintentó tras fortalecer el prompt con la sintaxis literal `points=[{"x":0.44,"y":0.47},{"x":0.56,"y":0.66}]` y prohibir pares internos. El retry quedó sin llamadas fallidas. Harness: 70 pruebas y 9 subtests aprobados; sin rebuild ni cambio de SHA.

La tabla de corridas que sigue conserva el historial observado, incluido el SHA anterior; sólo los recibos con SHA actual pueden elevar la certificación vigente.

## Configuración efectiva

- Binario: `build/Debug/LlamaCode.exe`; las corridas usan `--agent-daemon` y perfiles/rutas de datos aislados.
- Modelo: Gemma 4 12B UD-Q3_K_XL, launch `sys-vram-8-gemma`; agente base: `agent-intermedio`, el perfil local usado más recientemente en el preflight.
- Runtime fijado: `b9763`. Sin cambios a perfiles productivos.
- Cada caso se ejecuta como daemon independiente. Los `.xlsx` y `.txt` son sintéticos y permanecen en `workspace/`.

## Corridas observadas

| Caso | Corrida | Resultado | Evidencia |
|---|---|---|---|
| CU01 | `suite-v2-CU01` | Aprobado | `desktop_read_text` mostró 42; receipt con validador independiente. |
| CU02 | `suite-v2-CU02` | Aprobado | `desktop_read_text` mostró 144; receipt con validador independiente. |
| CU03 | `suite-v2-CU03` | Aprobado | `desktop_read_text` mostró 36; receipt con validador independiente. |
| CU04 | `suite-v2-CU04` | Fallido | `%` se interpretó como `Mod`; la lectura no mostró resultado. Gemma afirmó 30 sin evidencia. |
| CU04 | `suite-v3-CU04` | Aprobado | Con `200*15/100=`, el texto de escritorio y el validador confirmaron 30. |
| CU05 | `suite-v2-CU05` | Fallido | Edge InPrivate abrió; no se observó la fecha esperada. El receipt confirma búsqueda sin resultado verificable. |
| CU05 | `diag-CU05-live` | Fallido / bloqueado | Se vio el aviso del Firewall para `test_system_profiles.exe` en otro worktree. No se aceptó manualmente. La regla actual para esa ruta es Block Public; no aparece Allow. |
| CU05 | Resolución posterior a la autorización | Parcial | La ruta exacta del worktree `bold-jennings-b69d43` ya tiene reglas Inbound Allow en Public. El intento de ampliar esas dos reglas a Private devolvió “Acceso denegado”; el caso de búsqueda todavía debe repetirse y verificarse en el navegador. |
| CU05 | `suite-v33-CU05` | Aprobado | Edge Guest con perfil temporal aislado mostró Apollo 11 y la fecha; el validador de fecha reconoce formatos US, UK y español. |
| CU06 | `suite-v40-CU06` | Aprobado | La búsqueda de Apollo 11 y la lectura posterior visible confirmaron “Apollo 11” y “1969”; no abrió resultados. |
| CU06 | `sha9a-final-CU06` | Fallido | El prompt impedía hacer clic pese al criterio del plan; el validador sólo comprobaba texto tras Enter. Se detectó contradicción de harness, no fallo del producto. |
| CU06 | `sha9a-r2-CU06` | Abortado antes de interactuar | Gemma copió mal la ruta del acceso directo (`sha9a-r-CU06`); la guarda rechazó el lanzamiento. |
| CU06 | `browserb` | Fallido | El resultado NASA era un `listitem` UIA no invocable; un cambio dinámico del título dejó obsoleto el snapshot de click y la siguiente generación superó el contexto (8702/8192). El harness ahora pide usar la coordenada OCR fresca del resultado. |
| CU06 | `browserc` | E2E funcional, runner fallido | Gemma abrió el resultado NASA por la coordenada OCR `(0.168, 0.735)`; la lectura de la página y la respuesta confirmaron 1969, y `artifact_validation.passed=true`. El runner no cerró con código 0 porque la consola CP1252 no pudo imprimir U+200B del título de Edge; se corrigió el JSON de salida y debe repetirse para contar. |
| CU06 | `browserd` | Aprobado | Exit code 0, `turn_error=null`, 11/11 herramientas correctas; clic OCR en el resultado “Apollo 11 Mission Overview - NASA” y lectura posterior de la página NASA con el dato de lanzamiento el 16 de julio de 1969. `artifact_validation.passed=true`; procesos del perfil Guest y puerto limpiados. |
| CU07 | `suite-v41-CU07` | Antecedente (SHA previo; no cuenta) | La fecha británica se buscó en una versión anterior; la recertificación actual usa el formato del artículo inglés. |
| CU07 | `browser07a` | Fallido | `20 July 1969` no apareció en OCR del artículo inglés; el agente terminó sin verificación. |
| CU07 | `browser07b` | Fallido | Contexto excedido (8259/8192) tras confirmar Ctrl+F y el panel, antes de escribir la consulta. |
| CU07 | `browser07c` | E2E funcional; validador rechazó | OCR encontró `July 20, 1969,` y las 15 herramientas pasaron; la respuesta estaba en español y el validador sólo aceptaba fecha inglesa. |
| CU07 | `browser07d`, SHA 9A8963… | Aprobado | 137,297 s; 15/15 tools, Ctrl+F, campo observado, OCR de coincidencia tras Enter, respuesta con fecha localizada; Edge Guest cerrado. |
| CU08 | `suite-v44-CU08` | Antecedente (SHA previo; no cuenta) | El flujo de dos pestañas se vuelve a certificar en SHA 9A. |
| CU08 | `browser08a` | Fallido | Abrió la segunda pestaña y mostró Apollo 12, pero agotó contexto (8360/8192) antes de volver a Apollo 11. |
| CU08 | `browser08b`, SHA 9A8963… | Aprobado | 86,797 s, 16/16 tools; evidencias de Apollo 11, Ctrl+T, Apollo 12, Ctrl+Shift+Tab y regreso a Apollo 11. Edge Guest cerrado. |
| CU09 | `pilot-35-corrected-terminal-cu09` | Fallido | Datos en UI, pero el libro no se guardó; el validador no encontró el archivo. |
| CU09 | `pilot-36-uia-save-field-cu09` | Fallido | El panel Guardar como mantuvo el botón Guardar deshabilitado y el agente repitió el flujo hasta timeout. |
| CU09 | `pilot-37-preseeded-workbook-cu09` | Aprobado | Libro vacío del harness quedó con exactamente 12 celdas A1:C4; dimensiones 4×3; valores y archivo verificados. |
| CU09 | `suite-v45-CU09` | Antecedente (SHA previo; no cuenta) | El bloque A1:C4 pasó allí; la certificación actual está abajo. |
| CU09 | `excel09a`, SHA 9A8963… | Aprobado | 43,547 s, 7/7 tools; XLSX guardado A1:C4 exacto, 4×3, 12 celdas. Excel cerrado sin remanentes. |
| CU10 | `pilot-34-uia-save` | Piloto exitoso, no cuenta | Fórmula y valor 6 persistieron, pero se pidió manualmente al agente cerrar el turno tras una lectura tardía. |
| CU10 | `suite-v3-CU10` | Fallido | Excel abrió una ventana previa; D1/D2 quedaron vacías y el libro permaneció sin cambios. |
| CU10 | `suite-v4-CU10` | Fallido / bloqueado | La recuperación de Excel impidió el foco y el acceso UIA a D1; el validador confirmó D1/D2 nulas. Se identificó como consecuencia del cierre forzado del intento anterior y se eliminó ese comportamiento del harness. |
| CU10 | `suite-v46-CU10` | Fallido | El prompt abrió un workbook que el harness no había creado; Excel mostró que el archivo sintético no existía. La corrida se detuvo sin confirmar el diálogo y la ventana de prueba se cerró con WM_CLOSE dirigido. |
| CU10 | `suite-v47-CU10` | Antecedente (SHA previo; no cuenta) | Fórmula validada en la versión anterior; el pase certificable es `excel10a`. |
| CU10 | `excel10a`, SHA 9A8963… | Aprobado | 64,688 s, 14/14 tools; D1 total, D2 fórmula exacta y caché 6 en XLSX guardado; Excel cerrado. |
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |
| CU14 | `suite-v5-CU14` | Fallido | El archivo sintético quedó con `LlamaCode ` más caracteres U+2026; no coincide con la línea solicitada. La UIA del Bloc de notas reusado también incluyó títulos de otras pestañas, por lo que hay que aislar esa app antes de repetir el caso. |
| CU14 | `suite-v28-CU14` | Aprobado | Línea exacta guardada y re-leída; el archivo contiene sólo el texto esperado. |
| CU16 | `suite-v6-CU16` | Fallido / interrumpido | Cinco clics repetidos en “Formas” no cambiaron los controles UIA; no se creó PNG. Se agregó un guard en producto que bloquea el mismo clic tras una observación idéntica; la regresión y gates pasan antes del nuevo intento. |
| CU16 | `suite-v7-CU16` | Fallido | `desktop_stroke` recibió pares `[x,y]`; el backend los convertía silenciosamente en `(0,0)` y aceptaba el gesto. Ahora rechaza ese formato antes de mover el mouse. |
| CU16 | `suite-v8-CU16` | Fallido | La traza `{x,y}` fue aceptada pero no quedó dentro del lienzo; `Ctrl+S` inicial también falló por falta de foco. Se ajustó la instrucción para observar antes del gesto y enfocar antes de guardar. |
| CU16 | `suite-v9-CU16` | Fallido | Gemma emitió `scope_kind":"window` sin la comilla inicial. La solicitud quedó como texto y no ejecutó `desktop_stroke`. Se agregó recuperación acotada de esa clave JSON y regresión con el payload observado. |
| CU16 | `suite-v10-CU16` | Fallido | El parser ya despachó `desktop_stroke`; el trace confirmó puntos físicos (844,485)–(1076,684) dentro del lienzo, pero las tres capturas y el PNG persistieron en blanco. La selección UIA de “Rectángulo” no produjo evidencia visual de cambio. Se cambió el siguiente intento a un clic físico sobre el icono visible. |
| CU16 | `suite-v11-CU16` | Bloqueado antes de dibujar | `desktop_read_text` activó la guarda por diálogo de permiso de Windows; el runner paró el agente, no tomó capturas ni ejecutó clics/trazos. |
| CU16 | `suite-v12-CU16` | Fallido; falso positivo del validador | El PNG persistió una línea diagonal. La inspección visual contradijo el antiguo umbral de píxeles no blancos; el runner queda ahora con validación geométrica de cuatro lados. La selección del icono se ajustó al centro visual y el prompt exige evidencia de selección y prohíbe repetir el gesto. |
| CU16 | `suite-v13-CU16` | Aprobado | Gemma dibujó y guardó un rectángulo real de 400×300. El validador midió 4.310 píxeles oscuros y cobertura 1,0 en cada lado; la inspección del PNG confirma los cuatro bordes. El perfil fue `agent-intermedio` con `sys-vram-8-gemma`. |
| CU17 | `suite-v14-CU17` | Antecedente, SHA anterior | Explorer mostró el nombre, pero el validador entonces aceptaba cualquier clic y no demuestra selección correcta. No cuenta para SHA actual. |
| CU17 | `explorer17a`, SHA 9A8963… | Rechazado; falso positivo del validador | Gemma repitió clics en breadcrumb y coordenadas genéricas; no hubo selección semántica inequívoca. Se corrigieron prompt y validador antes de repetir. |
| CU17 | `explorer17b`, SHA 9A8963… | Aprobado | 26,593 s, `turn_error=null`; abrió el workspace exacto, consultó el control UIA único por nombre, ejecutó una selección semántica y leyó el archivo después. Cinco herramientas exitosas, cero acciones extra; fixture intacto. |
| CU18 | `suite-v15-CU18` | Fallido | El turno agotó 360 s con A1 vacío durante la validación y el portapapeles se restauró. La secuencia usó `desktop_clipboard op=copy` (inválido), luego `op=set` y `desktop_type` directo; no hubo Ctrl+C/Ctrl+V. Al cerrar el workbook sintético después del receipt, Guardar preservó el marcador que estaba en memoria; el intento sigue fallido porque no cumplió el flujo de clipboard y terminó en timeout. |
| CU18 | `suite-v16-CU18` | Fallido | Ctrl+A/Ctrl+C y `desktop_clipboard op=get` sí funcionaron. Gemma intentó cuatro lanzamientos de Excel con rutas malformadas antes de abrirlo; usó primero `key='Ctrl+V'` (inválido), luego repitió Ctrl+V/Ctrl+S. A1 quedó correcto en memoria, pero el archivo seguía vacío al validar. Durante limpieza se guardó el libro sintético para preservar ese estado; no cuenta como pase. |
| CU18 | `suite-v17-CU18` | Fallido | Excel se abrió con una sola ruta correcta y A1 terminó con el marcador. Gemma repitió Ctrl+V tras la primera lectura positiva y añadió la misma cadena en O18; el libro se guardó con dos celdas. El caso no pasa por duplicación aunque el marcador esté en A1. |

Los casos sin fila siguen pendientes. Los receipts completos están en `receipts/runs/` y conservan el resultado del validador, la secuencia de herramientas saneada, el hash del log del agente y el log de servidor/modelo.

## Correcciones del runner

- La detección del mensaje terminal usa `completedAt`/`createdAt`, tolerando que lecturas completadas antes del final se agreguen después al arreglo de mensajes.
- CU09 y CU18 preparan `.xlsx` vacíos, guardan el hash previo y rechazan workspaces con datos previos; esto separa la escritura de celdas y el flujo de clipboard de la frágil interfaz Guardar como.
- CU11/CU13 preservan las fórmulas matemáticamente equivalentes que puede guardar CU10.
- CU01–04 y CU05–08 requieren evidencia observada en `desktop_read_text` y acciones pertinentes; CU17 además requiere una única selección UIA del control exacto y lectura posterior en la misma carpeta, sin clics adicionales. La respuesta del modelo por sí sola no aprueba un caso.
- El runner detiene el agente si detecta diálogos de Firewall o permisos de Windows en cualquier salida de herramientas `desktop_*`. Las pruebas unitarias actuales del runner pasan 25/25.
- La salida textual `TOOL_CALL` puede traer una clave de objeto sin su comilla inicial. El parser ahora sólo corrige identificadores en posición de clave JSON y vuelve a exigir JSON válido; `parsesTextToolCallWithMissingOpeningQuote` cubre el payload de CU16 v9.
- El esquema y `docs/harness.md` explican que las coordenadas normalizadas de `desktop_click`/`desktop_stroke` con `scope_kind='window'` abarcan la ventana exterior completa. CU16 llama `desktop_observe` antes de dibujar; v10 confirmó que la ejecución física llegó al lienzo aunque Paint no persistió figura.
- CU10 `suite-v4-CU10` falló con una confirmación de recuperación de Excel causada por el cierre abrupto del intento previo; no escribió D1/D2. El harness ya no termina procesos: solicita `WM_CLOSE` a la ventana principal del Excel de prueba y detiene la corrida si el proceso o un diálogo siguen abiertos. La resolución manual del cuadro de recuperación está pendiente.
- CU16 mostró que el anti-loop por llamadas consecutivas no frenaba el mismo clic cuando Gemma intercalaba `desktop_controls`. `DesktopActionRepeatGuard` compara el control-tree del target antes y después del clic, conserva el bloqueo si no cambió y emite una instrucción de replanteo. Una regresión cubre el ciclo; build Debug y `tests.bat Debug` pasan.
- CU14 reveló que Notepad puede reusar una ventana con pestañas previas y que el recibo actual de `desktop_type` no prueba que el texto persistido coincida con el argumento. El archivo sintético rechazado conserva evidencia; la selección/aislamiento del editor y la ruta exacta de escritura quedan bajo investigación antes de reintentar.
- CU16 v12 expuso que contar sólo píxeles oscuros aprobaba una diagonal como “figura”. El validador ahora comprueba cobertura de los cuatro bordes del contorno y una regresión compara un rectángulo con una diagonal; la captura humana sigue siendo parte de la revisión semántica.
- Tras la respuesta explícita del usuario, se confirmó que CU05 corresponde a `C:\Users\Cristian\Documents\GitHub\LlamaCode\.claude\worktrees\bold-jennings-b69d43\build_tests\release\test_system_profiles.exe`; dos reglas inbound existentes permiten Public. Ampliarlas a Private no fue posible por falta de privilegios en esta sesión. No hay ahora proceso ni ventana de Excel; si el aviso de recuperación del libro sintético vuelve a aparecer, está autorizado responder “No”.
- El runner aplica esa autorización sólo a los casos Excel CU09–CU13 y CU18: responder “No” únicamente a un diálogo que identifique el libro sintético `cu20-computer-usage.xlsx`; otros avisos siguen sin tocarse. Regresión automatizada incluida; runner 27/27.
- CU18 v15–v17 expusieron ambigüedades de clipboard, rutas Windows y repetición tras una lectura positiva. El prompt ahora muestra los campos literales de `desktop_key`, la ruta única de Excel con barras simples y el botón UIA Guardar; tras ver el marcador, sólo permite guardar y terminar. El validador exige un solo lanzamiento correcto, fuente sintética intacta, copia seguida de un único pegado, ausencia de tipeo/set, clic de guardado y un workbook con únicamente A1 exacta. Regresiones de repetición y persistencia; runner 29/29.
- CU10 v46 encontró otro fixture ausente: el runner ya prepara workbooks sembrados para CU10–CU13 con el estado inicial de cada tarea. La regresión verifica valores, fórmula y estilos de los cuatro fixtures; suite Python actual 36/36. CU10 v47 confirmó el camino completo y el valor almacenado 6.
- CU11 v48 mostró que una instrucción breve de modificar B2 no bastaba: Gemma alternó clics por píxel, tipeo y lecturas sin progreso. El prompt ahora exige seleccionar el control UIA exacto B2, confirmar su valor antes de escribir, y parar en la primera lectura inesperada. Se agregó una regresión del prompt; el caso debe repetirse en un workspace nuevo.
- La guía global de Computer Usage ahora dirige las tareas en tablas/grillas a `desktop_controls` + `desktop_click_element`, con verificación previa y posterior del valor y detención si el target es ambiguo. `AutomationTests::desktopPromptPrefersNativeTools` cubre esa instrucción.
- CU11 v48 mostró que el guard anterior cubría clics repetidos, pero no la misma escritura seguida de lecturas iguales. `DesktopActionRepeatGuard` ahora también relaciona `desktop_type` con la consulta/target observado, ignora `receipt_id` variable y mantiene el bloqueo hasta una lectura distinta. `desktopRepeatedTypingAfterUnchangedReadIsBlocked` cubre ese ciclo.

## Gates

- Tras la guía de grillas y la guarda anti-loop de escritura, `build.bat Debug NOPAUSE` compiló y actualizó `build/Debug/LlamaCode.exe`; `tests.bat Debug`: 89/89 CTest, 6/6 auxiliares y 9/9 helpers.
- Último chequeo del runner: `python -m pytest -q artifacts/evaluacion-modelos-llamacode/Q-20261016-CU-20-E2E/tests/test_run_cu20_windows.py` — 36/36 (4 subtests adicionales); `py_compile` — OK. `git diff --check` — OK con el aviso de conversión LF→CRLF preexistente en `DesktopComputerUse.cpp`.
- La campaña final completa todavía no se ha corrido.
- Auditoría de CU11 v48: el recibo registra SHA-256 del ejecutable `1f576926d87667bda6c6bbf3543b93f889f9d1bf843eb04c12878ad5fcf3f9c2`, anterior al build actual `40DABAF32B78F443D8B90C39D7F69122CF5C68AC97086D79B3318A2D6E3EBA5E`. Gemma realizó 41 tool calls y repitió `desktop_type` sin cambiar B2; el harness canceló la tarea a los 240,922 s. El log del modelo muestra la cancelación solicitada por el harness, no demuestra una caída espontánea del servidor. CU11 debe repetirse sobre el build actual; la campaña final tendrá que recertificar los 20 casos con un mismo binario.
| CU15 | `verify-v1-CU15` | Fallido | El agente hizo 7 tool calls (2 lecturas y 2 clics UIA), pero no usó `desktop_key` ni `desktop_type`; el archivo conservó `sleepy`. La ventana de Notepad reutilizada tenía pestañas anteriores y valores recordados en Buscar/Reemplazar. |
| CU15 | `verify-v2-CU15` | Fallido | El prompt ya abrió el panel y cambió el campo Buscar, pero omitió `target_id` en una tecla; `desktop_type` fue rechazado por foco con texto. Reemplazar todo insertó el valor antiguo `-- Ausente Ausente Sin acta -- Ausente`; el validador rechazó el archivo. |
| CU15 | `verify-v3-CU15` | Aprobado | 126,5 s, `turn_error=null`; el archivo sintético contiene exactamente `The quick brown fox jumps over the curious dog.`. Receipt con Gemma 12B (`sys-vram-8-gemma`), `agent-intermedio` y SHA del binario `abb23d0c…`. |

## Corridas posteriores (continuación del 2026-10-17)

| Caso | Corrida | Resultado | Evidencia |
|---|---|---|---|
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |

La corrección siguiente debe llamar `desktop_focus` sobre el target Excel más reciente antes del atajo, inspeccionar `desktop_windows` para comprobar si apareció el modal y detenerse antes de teclear si no aparece. El contrato de `desktop_key` no acepta `target_id`; usa la última ventana enfocada. No inferir que `desktop_key: ok` significa que Excel abrió el diálogo.
- CU15 v1/v2 confirmaron que el panel Buscar/Reemplazar de Notepad conserva valores entre pestañas y que `desktop_type` rechaza controles ocupados salvo append explícito. El prompt ahora exige `target_id` en cada llamada, localiza los campos `edit` por UIA y usa `desktop_control_action set_value` con lectura de retorno para establecer `sleepy`/`curious`; sólo después pulsa el botón exacto Reemplazar todo. El esquema general de `desktop_type` ahora recomienda `set_value` al reemplazar un campo lleno y reserva `append=true` para agregar. Regresión agregada.
- CU11 v1 expuso que `desktop_controls` consultaba patrones, valores y geometría de cada nodo antes de filtrar por nombre, y recorría hasta 3000 nodos incluso si no había coincidencia. Ahora las consultas nominales leen el nombre primero, priorizan la coincidencia exacta, acotan UIA a 5 s con timeouts por transacción y devuelven una alternativa de lectura/navegación si la grilla no expone la celda. La guía general de Computer Usage y Automation/Teach ya permite navegación semántica o por teclado para celdas no expuestas; CU11 cambió a Ctrl+G, B2, escritura única y verificación. Regresiones añadidas para prioridad exacta, fallback de grilla y autorización de recuperación limitada.
- Build Debug posterior a CU11: `build/Debug/LlamaCode.exe` actualizado, SHA-256 `0F63BB1ECACDE2DDF3D5A4803F49435C86F444D62B71067A5D22C35A48391E64`; `tests.bat Debug`: 89/89 CTest, 6/6 auxiliares y 9/9 helpers. Runner Python: 37/37, 4 subtests; `py_compile` y `git diff --check` correctos (queda el aviso LF→CRLF preexistente).
- El runner ya ignora un mensaje assistant `TOOL_CALL` como terminal y eleva el timeout predeterminado a 900 s; regresiones `pending_text_tool_call_is_not_terminal` y `completed_assistant_after_tool_call_is_terminal`. `pytest`: 39/39 y 4 subtests; `py_compile` OK.
- El parser textual ahora entrecomilla sólo valores hexadecimales sin comillas del campo `target_id`; los HWND decimales JSON siguen numéricos. `parsesTextToolCallWithUnquotedHexTargetId` cubre ambos casos. Build Debug SHA `A75ECC0298271EF163971C2076E8E7DD9033BA6EA55CDE3D9D07B93979CB899F`; `tests.bat Debug`: 89/89 CTest, 6/6 auxiliares, 9/9 helpers; `git diff --check` OK con avisos LF→CRLF existentes.
- La prueba CU11 del SHA actual todavía no cuenta: `verify-v5-CU11` expiró a los 360 s antes de completar la primera acción (el runner anterior fijaba ese límite). La inspección posterior confirmó el diálogo exacto “¿Guardar los cambios en este archivo?” y B2=2. El daemon está detenido, pero el Excel sintético v49 permanece abierto. No cerrar ni elegir Guardar/No guardar hasta recibir la decisión del usuario para ese workbook; luego repetir CU11 con timeout de 900 s y seguir hasta completar la matriz.

## Corrida CU11 v14 (2026-10-17)

| Caso | Corrida | Resultado | Evidencia |
|---|---|---|---|
| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |

| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |

Nota de cierre pendiente para `verify-v15-namebox-CU11`: inspecciones posteriores read-only (`inspect-v15-readonly-v59-CU11`, `inspect-v15-buttons-v59-CU11`) confirmaron el cuadro `Guardar como` del workbook suite-v59. Sólo se encontró botón `Cerrar`; no hay `Guardar`, `No guardar` ni `Cancelar` exactos. No se accionó. El permiso anterior de descartar era exclusivo de `suite-v48-CU11`; esperar instrucción del usuario para el cuadro v59 antes de iniciar otra prueba.

## Corridas de resolución del diálogo suite-v59 (2026-10-17)

| Run | Resultado | Evidencia |
|---|---|---|
| `resolve-close-v59-CU11` | Sólo lectura fallida; sin acción | Gemma no tuvo un `target_id` real porque el perfil no incluía `desktop_windows`; `desktop_read_text` y `desktop_controls` fallaron. |
| `resolve-close-v59-CU11-v2` | Diálogo cerrado, libro sin guardar | SHA `a971f42ad0cb0c0983f68a61351ad532be66955ff66e0be3956c6d00a2d205c6`, Gemma 12B (`sys-vram-8-gemma`), perfil duplicado `agent-intermedio`; en 29,3 s encontró Excel, consultó UIA `Cerrar` (1 control), hizo exactamente una llamada `desktop_click_element` (receipt status `failed`, detalle vacío) y leyó la grilla sin diálogo. Excel PID 17764 continúa abierto. El archivo en disco conserva B2=2 y D2 `=B2+B3+B4` (caché vacía), con LastWriteTime 14:14; no hubo guardado ni descarte. Receipt `receipts/runs/resolve-close-v59-CU11-v2/RESULT.json`. |

| CU11 | excel11a, SHA 9A8963… | Aprobado | 166,657 s, 16/16 tools; B2=4, fórmula D2 exacta y caché 8 en XLSX guardado. Excel cerrado. |

## Build/gates tras mejora de foco y snapshots (2026-10-17)

- `build.bat Debug NOPAUSE` completó y actualizó `build/Debug/LlamaCode.exe`, SHA-256 `CA30546C519273A8C55EE4C52C36F2B32D8C556BBDE4D2449FB26DCCF1F5B222` (15:11:55 ART).
- `tests.bat Debug`: 89/89 CTest, 6/6 auxiliares, 9/9 helpers. La corrida previa falló sólo por exceder el límite de prompt de AutomationRunner; se acortó la instrucción y el test focalizado y el gate completo posterior pasaron.
- Runner Python: pytest 39/39 + 4 subtests; py_compile OK; `git diff --check` OK con avisos de conversión LF→CRLF existentes.
- El binario nuevo aún no tiene corridas Computer Usage. CU11 v16 fue sobre el SHA anterior y falló sin cambiar B2. Suite v60 tiene un aviso de Guardar cambios con botones Guardar/No guardar/Cerrar/Cancelar; no se accionó y se espera decisión del usuario.
- Auditoría de prompts CU01–CU20 confirma que cada caso con desktop_click_element o desktop_control_action incluye snapshot_id; regresión agregada. Pytest final 40/40 + 4 subtests, py_compile y diff-check OK; no cambia el binario.


## Estado operativo (2026-10-17, 15:22 ART)

- No se ejecutó todavía ningún caso de certificación sobre SHA `CA30546C519273A8C55EE4C52C36F2B32D8C556BBDE4D2449FB26DCCF1F5B222`; por tanto, la certificación de este binario sigue en 0/20.
- `inspect-v17-readonly-v60-CU11` se detuvo ante dos títulos Excel iguales (PID 16516 y 17764), sin consultar ni accionar.
- Para continuar el diagnóstico sin ambigüedad agregué selección por PID exacto al inspector de sólo lectura. `inspect-v18-readonly-v60-CU11` consultó sólo PID 16516; UIA vio el diálogo exacto de guardar, No guardar habilitado y Cerrar deshabilitado. No se accionó. La autorización de descarte para suite-v60 sigue pendiente.
- El runner bloquea el inicio sólo si continúa abierto el mismo fixture Excel que requiere el caso. Se comienza la recertificación por casos que no usan Excel y se retoma CU11 cuando el usuario resuelva el diálogo; ningún receipt histórico de otro SHA contará para el 20/20 final.


## Recertificación sobre SHA común `CA30546C519273A8C55EE4C52C36F2B32D8C556BBDE4D2449FB26DCCF1F5B222`

| Caso | Run / workspace | Resultado | Evidencia |
|---|---|---|---|
| CU01 | `cert-v1-CU01` / `suite-final01-CU01` | Aprobado | 11,14 s; Gemma 12B (`sys-vram-8-gemma`) con agente base `agent-intermedio`; el recibo identifica SHA `ca30546c...`, ejecutó Computer Usage y el validador observó `42`. Receipt: `receipts/runs/cert-v1-CU01/RESULT.json`. |
| CU02 | `cert-v1-CU02` / `suite-final02-CU02` | Aprobado | 11.14 s; validador independiente confirma display `144`; SHA exacto registrado en receipt. `receipts/runs/cert-v1-CU02/RESULT.json`. |
| CU03 | `cert-v1-CU03` / `suite-final03-CU03` | Aprobado | 11.11 s; validador independiente confirma display `36`; SHA exacto en receipt. `receipts/runs/cert-v1-CU03/RESULT.json`. |
| CU04 | `cert-v1-CU04` / `suite-final04-CU04` | Aprobado | 11.11 s; visor muestra `30`, confirmado por el validador independiente. `receipts/runs/cert-v1-CU04/RESULT.json`. |
| CU05 | `cert-v1-CU05` / `suite-final05-CU05` | Aprobado | 67.8 s; una lectura coincide con Apollo 11 y `20 July 1969`. `receipts/runs/cert-v1-CU05/RESULT.json`. |
| CU06 | `cert-v1-CU06` / `suite-final06-CU06` | Fallido (no cuenta) | 18,17 s; la búsqueda tiene evidencia visible positiva, pero Gemma hizo una llamada fallida `desktop_key` con `key="\n"`; una llamada posterior `Enter` funcionó. El validador de artefacto pasa, la corrida estricta no. SHA `CA30546C...`; receipt `receipts/runs/cert-v1-CU06/RESULT.json`.


## Nuevo build tras error `desktop_key` con salto de línea

- CU06 `cert-v1-CU06` confirmó un error tolerante de corregir: el artefacto web fue correcto, pero un `key="\n"` falló antes de un segundo `Enter` exitoso. Se normalizan CR/LF exactos a `ENTER` en el contrato compartido de teclas y se añadió `keyNameNormalizesLineBreakAsEnter` para LF/CR/CRLF y claves que no deben alterarse.
- `build.bat Debug NOPAUSE` y `tests.bat Debug` pasan (89/89 CTest, 6/6 auxiliares, 9/9 helpers); Python del runner 40/40 + 4 subtests; `py_compile` y `git diff --check` OK con avisos LF→CRLF ya conocidos.
- Build Debug actual: SHA-256 `F7207FBF427587EC92F2474B5B654D00E4038DD142AD9D1AD1C6EDD64B0DEC72`, actualizado 2026-10-17 15:29:49 ART. La recertificación de los 20 casos sobre este SHA todavía es 0/20; los casos CU01–CU05 del SHA `CA30546C...` no cuentan.


## Diagnóstico del fix de Enter y nueva certificación F7207FBF

| Caso | Run / workspace | Resultado | Evidencia |
|---|---|---|---|
| CU06 | `verify-v2-CU06` / `suite-fix-v2-CU06` | Diagnóstico aprobado; no cuenta | 18,19 s, SHA `F7207FBF...`; `turn_error=null`, una lectura visible con Apollo 11/1969. Gemma usó `Enter` directamente, por lo que no reprodujo `key=LF`; la normalización queda cubierta por `keyNameNormalizesLineBreakAsEnter`. Receipt `receipts/runs/verify-v2-CU06/RESULT.json`. |

La certificación final del nuevo SHA `F7207FBF427587EC92F2474B5B654D00E4038DD142AD9D1AD1C6EDD64B0DEC72` arranca en 0/20 y debe usar CU01–CU20 en workspaces nuevos, secuenciales.

| Caso | Run / workspace | Resultado | Evidencia |
|---|---|---|---|
| CU01 | `final-v2-CU01` / `final-suite-v2-CU01` | Aprobado | 11,14 s; validador independiente confirma display `42`; SHA exacto en receipt. `receipts/runs/final-v2-CU01/RESULT.json`. |
| CU02 | `final-v2-CU02` / `final-suite-v2-CU02` | Aprobado | 12.11 s; visor y validador confirman `144`. `receipts/runs/final-v2-CU02/RESULT.json`. |
| CU03 | `final-v2-CU03` / `final-suite-v2-CU03` | Aprobado | 11.09 s; visor/validador confirma `36`. `receipts/runs/final-v2-CU03/RESULT.json`. |
| CU04 | `final-v2-CU04` / `final-suite-v2-CU04` | Aprobado | 12.11 s; visor/validador confirma `30`. `receipts/runs/final-v2-CU04/RESULT.json`. |
| CU05 | `final-v2-CU05` / `final-suite-v2-CU05` | Aprobado | 65.6 s; lectura única contiene Apollo 11 y `20 July 1969`. `receipts/runs/final-v2-CU05/RESULT.json`. |
| CU06 | `final-v2-CU06` / `final-suite-v2-CU06` | Aprobado | 17.1 s; `turn_error=null`, Enter sin llamadas fallidas, lectura única Apollo 11/1969. `receipts/runs/final-v2-CU06/RESULT.json`. |


| CU07 | `final-v2-CU07` / `final-suite-v2-CU07` | Fallido (no cuenta) | 157,7 s, SHA `F7207FBF...`. Edge Guest recibió URL, pero Gemma no pulsó Enter: readback mostró la bienvenida de Guest con URL en la barra. Después Ctrl+F, no tipeó la frase y repitió lecturas sin progreso; validador `ctrl_f_observed=true`, `find_result_read_count=0`. Receipt `receipts/runs/final-v2-CU07/RESULT.json`; traza del agente `runtime/agent-data/final-v2-CU07/agent_llamaagent/d1b70e97-0e52-4e72-819a-5ac31ec07922.json`. No editó contenido ni envió formularios.


## Gate fallido tras la guía general de navegador

- `build.bat Debug NOPAUSE` compiló la guía general de navegador en LlamaAgentBackend y AutomationRunner.
- `tests.bat Debug` alcanzó 89 CTest y falló sólo `test_automation::desktopPromptKeepsVerboseRecipesCompact`: el prompt midió 7.566 caracteres, por encima del límite estricto de 7.400. Los otros 88 CTest pasaron; el wrapper no ejecutó las etapas auxiliares/helpers al fallar CTest. `pytest` Python 41/41 + 4 subtests, `py_compile` y `git diff --check` sí pasaron antes del build.
- Próxima corrección: quitar la frase duplicada de AutomationRunner; la instrucción global de navegador en LlamaAgentBackend permanece y tiene regresión en `test_agent_wire`. Después rebuild y gate completo.

## Gate y resolución del diálogo Excel — binario SHA `6635230C…` (2026-10-17)

- `tests.bat Debug` completo aprobado: 89/89 CTest, 6/6 auxiliares y 9/9 helpers. SHA-256 de `build/Debug/LlamaCode.exe`: `6635230C2CCC8C4EB1DE2A0B8A065D85D289859492573C22806DDE85E33CA33D`.
- Suite v60: con autorización explícita para descartar sólo el libro sintético `suite-v60-CU11`, la inspección UIA de sólo lectura confirmó PID 16516, el texto exacto `¿Guardar los cambios en este archivo?` y el botón habilitado `No guardar`. `resolve-nosave-v60-CU11` hizo un único clic exitoso. La ventana desapareció; PID ya no activo. El archivo se abrió y conserva la fila base, B2=2 y D2 `=B2+B3+B4`. Receipts: `inspect-v19-readonly-v60-CU11`, `inspect-v20-dialogtext-v60-CU11`, `resolve-nosave-v60-CU11`.
- Certificación E2E de este SHA: **0/20**. Los resultados de builds anteriores no cuentan. Pendientes: CU01–CU20 secuenciales con workspace separado por caso; ejecutar al final `pytest`/`py_compile`/`git diff --check`, registrar SHA y evidencia por caso. Primer caso: `final-v3-CU01`.
- Corrección horaria tomada de `createdAt` de los receipts: inspección v19 15:53:07 ART / 18:53:07 UTC; v20 15:54:17 ART / 18:54:17 UTC; clic de descarte 15:56:18 ART / 18:56:18 UTC. Las horas redondeadas del párrafo anterior quedan supersedidas por estos tiempos exactos.
- CU01 `final-v3-CU01` / `final-v3-suite-CU01` — **Aprobado**. 11,125 s; SHA exacto `6635230C2CCC8C4EB1DE2A0B8A065D85D289859492573C22806DDE85E33CA33D`; Gemma 12B `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, 0 errores, 0 llamadas desktop fallidas y validador independiente confirma `42`. Receipt: `receipts/runs/final-v3-CU01/RESULT.json`. Certificación: **1/20**.
- CU02 `final-v3-CU02` / `final-v3-suite-CU02` — **Aprobado**. 10,156 s; mismo SHA; Gemma 12B `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, 0 errores, 0 llamadas desktop fallidas y validador independiente confirma `144`. Receipt: `receipts/runs/final-v3-CU02/RESULT.json`. Certificación: **2/20**.
- CU03 `final-v3-CU03` / `final-v3-suite-CU03` — **Aprobado**. 12,109 s; mismo SHA; Gemma 12B `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, 0 errores, 0 llamadas desktop fallidas y validador independiente confirma `36`. Receipt: `receipts/runs/final-v3-CU03/RESULT.json`. Certificación: **3/20**.
- CU04 `final-v3-CU04` / `final-v3-suite-CU04` — **Aprobado**. 11,094 s; mismo SHA; Gemma 12B `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, 0 errores, 0 llamadas desktop fallidas y validador independiente confirma `30`. Receipt: `receipts/runs/final-v3-CU04/RESULT.json`. Certificación: **4/20**.
- CU05 `final-v3-CU05` / `final-v3-suite-CU05` — **Fallido (no cuenta)**. 160,578 s en SHA `6635230C…`; lectura inicial confirmó Edge Guest, pero tras Ctrl+L y escribir la consulta no hubo Enter ni lectura de resultados (`matching_read_count=0`). El verificador de efectos terminó bloqueando la respuesta incompleta. Receipt: `receipts/runs/final-v3-CU05/RESULT.json`; traza `runtime/agent-data/final-v3-CU05/agent_llamaagent/agent_runs/runs/9538b4ba-1c85-4e09-82d8-e2a44064d19a.json`. Causa a corregir en guía general del nudge y el contrato de `desktop_type`. La certificación final se reinicia en SHA nuevo desde CU01.

## Fix del nudge y recertificación reiniciada — SHA `D4385B0A…` (2026-10-17)

- La solicitud de observación del gate ahora ordena una lectura de escritorio como siguiente llamada: `desktop_read_text` sobre el `target_id` exacto; si ya no existe, una enumeración de ventanas seguida de una lectura. Para MCP conserva la lectura del mismo servidor. La guía y el resultado de `desktop_type` indican que tras URL/consulta en navegador corresponde Enter una vez y lectura de página.
- Build Debug `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`. `tests.bat Debug`: 89/89 CTest, 6/6 auxiliares, 9/9 helpers; pytest de runner 41/41 + 4 subtests; `py_compile` y `git diff --check` OK (sólo avisos LF→CRLF existentes).
- Recertificación E2E en este SHA: **0/20**. CU01–CU04 de `6635230C…` no cuentan. Repetir los 20 escenarios en workspaces nuevos; empezar `final-v4-CU01`.
- CU01 `final-v4-CU01` / `final-v4-suite-CU01` — **Aprobado**. 11,109 s; SHA `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma 12B `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, 0 errores, 0 tools fallidas y validador independiente confirma `42`. Receipt `receipts/runs/final-v4-CU01/RESULT.json`. Certificación: **1/20**.
- CU05 `final-v4-CU05` / `final-v4-suite-CU05` — **No aprobado por validador, no cuenta aún** (SHA `D4385B0A…`, 66,703 s). La traza ya completa Enter y lee el resultado: `Apollo 11`, `July 20 at 20:17 UTC` y `1969` en el resumen de la misma página. La respuesta incluyó día/hora pero omitió el año. El validador sólo reconocía el día/mes/año como frase contigua y rechazó el formato visible de Bing. Receipt `receipts/runs/final-v4-CU05/RESULT.json`. Ajustar caso/validador para formatos visibles equivalentes y exigir año en la respuesta; volver a ejecutar.

## Continuación de certificación — SHA `D4385B0A…`

- CU05 `final-v4-CU05-r2` / `final-v4-suite-CU05-r2` — **Aprobado**. 23,282 s; SHA completo `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, todas las llamadas desktop exitosas. La lectura de resultados y la respuesta contienen Apollo 11, fecha de aterrizaje y 1969; validador: `matching_read_count=1`, `matching_answer_count=1`. Receipt `receipts/runs/final-v4-CU05-r2/RESULT.json`, detalle por caso `receipts/runs/final-v4-CU05-r2/CU05.json`. El prompt/validador del harness se ajustó sin modificar el binario. Conteo vigente: **2/20**, junto con CU01. Próximo: CU02.

- Corrección de evidencia CU05 `final-v4-CU05-r2`: el delta registra seis llamadas desktop y las seis tienen `ok=true`; la mención previa de cuatro/cinco fue un error de conteo.
- CU02 `final-v4-CU02` / `final-v4-suite-CU02` — **Aprobado**. 11,125 s; SHA completo `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, cuatro llamadas desktop exitosas; validador confirma `144`. Receipt `receipts/runs/final-v4-CU02/RESULT.json` y detalle `receipts/runs/final-v4-CU02/CU02.json`. Conteo vigente: **3/20** (CU01, CU02, CU05). Próximo: CU03.

- CU03 `final-v4-CU03` / `final-v4-suite-CU03` — **Aprobado**. 11,094 s; SHA completo `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, cuatro llamadas desktop exitosas; validación confirma `36`. Receipt `receipts/runs/final-v4-CU03/RESULT.json` y detalle `receipts/runs/final-v4-CU03/CU03.json`. Conteo vigente: **4/20** (CU01–CU03, CU05). Próximo: CU04.

- CU04 `final-v4-CU04` / `final-v4-suite-CU04` — **Aprobado**. 12,109 s; SHA completo `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, cuatro llamadas desktop exitosas; la calculadora mostró `30`. Receipt `receipts/runs/final-v4-CU04/RESULT.json` y detalle `receipts/runs/final-v4-CU04/CU04.json`. Conteo vigente: **5/20** (CU01–CU05). Próximo: CU06.

- CU06 `final-v4-CU06` / `final-v4-suite-CU06` — **Aprobado**. 64,578 s; SHA completo `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, cinco llamadas desktop exitosas. El agente buscó y envió Enter; la lectura posterior contiene Apollo 11 y 1969. Receipt `receipts/runs/final-v4-CU06/RESULT.json`, detalle `receipts/runs/final-v4-CU06/CU06.json`. Conteo vigente: **6/20**. Próximo: CU07.

- CU07 `final-v4-CU07` / `final-v4-suite-CU07` — **Aprobado**. 147,594 s; SHA completo `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, 12 llamadas desktop exitosas. Ctrl+F observado y el verificador confirma una lectura de coincidencia (`find_result_read_count=1`). Latencia alta, resultado aprobado. Receipt `receipts/runs/final-v4-CU07/RESULT.json`, detalle `receipts/runs/final-v4-CU07/CU07.json`. Conteo vigente: **7/20**. Próximo: CU08.

- CU08 `final-v4-CU08` / `final-v4-suite-CU08` — **Aprobado**. 28,375 s; SHA completo `D4385B0A9EA13B3354DCF931B7F848ECF5C8BCA1113EE836ABD18A741ABE7F1B`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, diez llamadas desktop exitosas. Validador confirma Apollo 11, Ctrl+T, Apollo 12 en segunda pestaña, Ctrl+Shift+Tab y regreso a Apollo 11. Receipt `receipts/runs/final-v4-CU08/RESULT.json` y detalle `receipts/runs/final-v4-CU08/CU08.json`. Conteo vigente: **8/20**. Próximo: CU09.

## Reparo de CU09 y reinicio de certificación — SHA `807BB55F…`

- `final-v4-CU09` en SHA `D4385B0A…` falló con la hoja vacía. La solicitud indicaba el workspace correcto, pero Gemma pasó a `desktop_launch` el path antiguo `C:\Users\Cristian\Documents\LlamaCode\...`, que no existe, omitiendo `GitHub`. La ventana era Excel genérico; no confirmó el título y aun así escribió/guardó y declaró éxito.
- La primera guarda de archivo confirmado sólo detectaba archivos existentes; `final-v5-CU09` (SHA `7FC73E31…`) mostró el mismo path incorrecto y la guarda no se activó. No cuentan ambos intentos.
- La guarda final detecta rutas de archivo incluso si el path no existe; bloquea escritura/click/teclas hasta que una observación del target confirme el nombre esperado. Sigue el target tras el reemplazo de HWND. `desktop_read_text` expone el título actual. Prompt Excel de CU09–CU13/CU18 ahora da el `args` exacto entre comillas para copiar. Regresiones cubren parsing, path ausente, lectura/error y acciones bloqueadas.
- Build Debug SHA completo `807BB55F6C2D1E568537F7DD01CA961EF1FF23B79A886CD01F444FFACEC3EBC5`. `tests.bat Debug`: 89/89 CTest, 6/6 auxiliares, 9/9 helpers. Pytest del runner: 43 tests + 9 subtests; `py_compile`/`git diff --check` OK.
- CU09 `final-v6-CU09` / `final-v6-suite-CU09` — **Aprobado**. 42,391 s; mismo SHA `807BB55F…`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; cero errores y siete llamadas desktop exitosas. El archivo muestra los valores exactos en A1:C4, con 12 celdas no vacías. Receipt `receipts/runs/final-v6-CU09/RESULT.json`; detalle `receipts/runs/final-v6-CU09/CU09.json`. Nueva certificación: **1/20** (CU09). Repetir CU01–CU08 y seguir CU10.

- CU10 `final-v6-CU10` / `final-v6-suite-CU10` — **Aprobado**. 65,578 s; SHA `807BB55F6C2D1E568537F7DD01CA961EF1FF23B79A886CD01F444FFACEC3EBC5`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, 14 llamadas desktop exitosas. Validador confirma D1 `Total cantidades`, fórmula D2 `=B2+B3+B4` y valor 6. Receipt `receipts/runs/final-v6-CU10/RESULT.json`, detalle `receipts/runs/final-v6-CU10/CU10.json`. Conteo: **2/20** (CU09–CU10). Próximo: CU11.

## CU11 `final-v6-CU11` — Fallido (2026-10-17)

SHA `807BB55F6C2D1E568537F7DD01CA961EF1FF23B79A886CD01F444FFACEC3EBC5`; Gemma `sys-vram-8-gemma`; agente `agent-intermedio`; workspace `final-v6-suite-CU11`; 139,64 s. Excel se abrió en el archivo exacto. La UI mostró B2=4 y D2=8, pero no se guardó: el XLSX independiente conserva B2=2 y D2 no tiene valor cacheado. La UIA devuelve el cuadro de nombres como `combobox`, contrario al prompt previo (`Edit`); Gemma repitió clics y omitió Ctrl+S. Un segundo launch con path mal escrito quedó bloqueado por la guarda de documentos. `WM_CLOSE` dejó modal de cambios sin guardar. No cuenta. Receipts `receipts/runs/final-v6-CU11/RESULT.json` y `receipts/runs/inspect-final-v6-dialog-CU11-1/RESULT.json`.

Corrección de harness registrada en el plan: aceptar `combobox`/`edit`, un solo `set_value` sin clic repetido y Ctrl+S explícito, seguido de lectura final. Tests: 43 + 9 subtests aprobados; mismo SHA de producto. Reintento pendiente de liberar el libro fallido con la autorización exacta.

- 2026-10-17 20:09 UTC — Afiné CU11 para conservar la autorización previa estricta: sólo pulsa `No` ante el aviso exacto de recuperación del libro sintético; ante otro diálogo se detiene. La regresión verifica ambas reglas. Pytest runner 43 passed + 9 subtests; `py_compile` y `git diff --check` OK; ningún cambio de producto/SHA. Sigue pendiente la autorización para descartar el diálogo distinto de `final-v6-suite-CU11`.

## Iteraciones CU11 — SHA `807BB55F…`

- `final-v6-CU11`: **fallido**. UI mostró B2=4/D2=8, pero el archivo no quedó guardado; un segundo launch con path `Office16` mal escrito fue bloqueado por el guard. Guardado post-hoc headless en el diálogo exacto para preservar el resultado; el XLSX ahora valida B2=4, fórmula `=B2+B3+B4`, caché 8. No cuenta.
- `final-v7-CU11`: **fallido**. La primera escritura se bloqueó porque faltó Enter tras `set_value` en el Name Box. El agente después produjo B2=4/D2=8 en pantalla, pero no persistió el archivo. Guardado post-hoc sólo para preservar evidencia; no cuenta.
- `final-v8-CU11`: **fallido**. El agente repitió consultas/teclas del cuadro de nombres y no guardó. Inspección headless confirmó el estado en memoria; Guardar post-hoc y XLSX validado, no cuenta.
- `final-v9-CU11`: **fallido**. Tras validar valores en pantalla el agente volvió a consultar el cuadro de nombres, repitió Enter/lecturas y terminó por anti-loop sin llamar Guardar. Guardado post-hoc y XLSX validado, no cuenta.
- Prompt más corto y test de orden actualizado; pytest 43 + 9 subtests pasa. El validador del archivo comprueba fórmula/caché, mientras el agente observa B2/D2 y luego guarda con botón UIA.
- `final-v10-CU11` / `final-v10-suite-CU11`: **aprobado**, 63,828 s, SHA completo `807BB55F6C2D1E568537F7DD01CA961EF1FF23B79A886CD01F444FFACEC3EBC5`; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores, 11 llamadas desktop exitosas. UIA confirma B2=4/D2=8; el botón Guardar se pulsó una vez; openpyxl confirma en disco B2=4, D2=`=B2+B3+B4`, caché 8. Receipt `receipts/runs/final-v10-CU11/RESULT.json`; detalle `receipts/runs/final-v10-CU11/CU11.json`. Certificación vigente: **3/20** (CU09–CU11); siguiente CU12.


## Reparación de IDs UIA y recertificación — 2026-10-17

- Diagnóstico `final-v25-CU13` no aprobó: Gemma serializó `control_id=42.72462` como JSON number; el dispatcher y la compuerta de seguridad lo leyeron con `toString()` y recibieron cadena vacía. Se registraron ocho errores de herramienta. El turno no se verificó y no cuenta.
- Corrección general: `DesktopComputerUse::controlIdText` conserva IDs string y números JSON con forma compacta; dispatcher, clasificador de acciones destructivas, schema y descripción de UIA usan la conversión/guía consistente. CU13 evita Guardar como y pulsa una sola vez el botón UIA Guardar del libro.
- Regresiones y docs: helper para ID decimal; wire test prueba que un ID decimal numérico sigue resolviendo `Eliminar` como destructivo; integración Windows `desktopControlAction_acceptsNumericOpaqueControlId` aprobada; `docs/computer-use.md` actualizado.
- `py_compile` OK; pytest del runner `50 passed, 9 subtests`; `git diff --check` OK. `build.bat Debug NOPAUSE` pasó. SHA nuevo: `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`.
- `tests.bat Debug`: 89/89 CTest, 6/6 auxiliares y 9/9 helpers. Suite focalizada de `test_agent_tools`: 57 passed, 0 failed, 0 skipped.
- Se reinicia la certificación: **0/20** en SHA 5E195D…; repetir CU01–CU20 en orden. Los pases anteriores quedan sólo como histórico.

- `final-v26-CU01` / `final-v26-suite-CU01` — **Aprobado** en SHA `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`. 11,125 s; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`; `turn_error=null`, cero errores y cuatro tools desktop exitosas. Una escritura `19+23=` y lectura independiente confirma 42. Receipt `receipts/runs/final-v26-CU01/RESULT.json`. Certificación: **1/20**; siguiente CU02.
- 2026-10-17T22:55:07Z — CU02 `final-v26-CU02` / `final-v26-suite-CU02`, SHA `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`: **aprobado** en 11.125 s con `sys-vram-8-gemma` y `agent-intermedio`; `turn_error=null`, cero errores, 4/4 tools desktop exitosas. Expresión 200−56 y lectura UIA/OCR confirman 144. Receipt `receipts/runs/final-v26-CU02/RESULT.json`; validador `{"passed": true, "expected_display": "144", "observed_display_matches": ["144"]}`. Conteo: **2/20**; próximo CU03.
- 2026-10-17T22:55:55Z — CU03 `final-v26-CU03` / `final-v26-suite-CU03`, SHA `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`: **aprobado** en 32.313 s con `sys-vram-8-gemma` y `agent-intermedio`; `turn_error=null`, cero errores, 4/4 tools desktop exitosas. Expresión (8+4)*3 y lectura UIA/OCR confirman 36. Receipt `receipts/runs/final-v26-CU03/RESULT.json`; validador `{"passed": true, "expected_display": "36", "observed_display_matches": ["36"]}`. Conteo: **3/20**; próximo CU04.
- 2026-10-17T22:56:55Z — CU04 `final-v26-CU04` / `final-v26-suite-CU04`, SHA `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`: **aprobado** en 12.125 s con `sys-vram-8-gemma` y `agent-intermedio`; `turn_error=null`, cero errores, 4/4 tools desktop exitosas. Expresión 200*15/100 y lectura UIA/OCR confirman 30. Receipt `receipts/runs/final-v26-CU04/RESULT.json`; validador `{"passed": true, "expected_display": "30", "observed_display_matches": ["30"]}`. Conteo: **4/20**; próximo CU05.

## Continuación recertificación SHA 5E195D50… — 2026-10-17

- CU05 `final-v26-CU05`: **falló** y no cuenta. La búsqueda no llegó a Enter porque el modelo omitió la lectura que la compuerta de verificación requería tras Ctrl+L y tras escribir. Evidencia: `receipts/runs/final-v26-CU05/RESULT.json`. Se corrigió el prompt del runner para leer tras cada mutación y confirmar que la consulta quedó escrita antes de Enter.
- Cleanup del Edge Guest de CU05 v26: el primer diagnóstico omitió `target_id` y falló; se reintentó con argumentos explícitos. `diag-close-final-v26-edge-r2` cerró sólo el PID 20884 / target `db0f28`; el inventario posterior no encontró procesos con el perfil de esa suite. La respuesta autorizada para `final-v6-suite-CU11` quedó sin usar porque Excel ya no estaba abierto.
- CU05 `final-v27-CU05`: **aprobado**, 40,422 s; Gemma `sys-vram-8-gemma`, agente `agent-intermedio`, 9/9 tools correctas, 2 lecturas verificadas y respuesta con Apollo 11, 20 de julio y 1969. Receipt `receipts/runs/final-v27-CU05/RESULT.json`.
- CU06 `final-v27-CU06`: **aprobado**, 19,297 s; mismo SHA y perfiles, `turn_error=null`, 7/7 tools correctas, lectura posterior a Enter con Apollo 11 y 1969. Receipt `receipts/runs/final-v27-CU06/RESULT.json`.
- Prompts de CU06–CU08 ahora explicitan observación posterior a cada tecla/escritura y `target_id`. Runner: `py_compile` OK, pytest 54 tests + 9 subtests. El binario no cambió. Estado certificable: **6/20**; próximo CU07.
- CU07 `final-v27-CU07`: **aprobado**, 86,985 s; SHA `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`, Gemma `sys-vram-8-gemma`, agente `agent-intermedio`, `turn_error=null`, 14/14 tools correctas. Ctrl+F y el panel de búsqueda se verificaron antes de escribir; validador `ctrl_f_observed=true`, `find_result_read_count=2`. Receipt `receipts/runs/final-v27-CU07/RESULT.json`. Certificación: **7/20**; sigue CU08.
- CU08 `final-v27-CU08`: **aprobado**, 55,672 s; mismo SHA/Gemma/perfil agente, `turn_error=null`, 16/16 tools correctas. Verificación completa de Apollo 11 antes del tab nuevo, Apollo 12 en la segunda pestaña, Ctrl+Shift+Tab y retorno visible a Apollo 11. Receipt `receipts/runs/final-v27-CU08/RESULT.json`. Certificación: **8/20**; sigue CU09.
- CU09 `final-v27-CU09`: **aprobado**, 91,0 s; mismo SHA/Gemma/perfil agente, 7/7 tools correctas y `turn_error=null`. El verificador independiente lee el XLSX guardado y confirma A1:C4 exacto (4×3, 12 valores). Cleanup cerró PID 5404 del libro sintético; cero Excel remanente de esa suite. Receipt `receipts/runs/final-v27-CU09/RESULT.json`. Certificación: **9/20**; sigue CU10.
- CU10 `final-v27-CU10`: **aprobado**, 66,734 s; SHA `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`, Gemma `sys-vram-8-gemma`, agente `agent-intermedio`, 14/14 tools y `turn_error=null`. El XLSX persistido conserva A1:C4, D1=`Total cantidades`, D2=`=B2+B3+B4`, caché 6. Cleanup cerró PID 31564, cero remanentes. Receipt `receipts/runs/final-v27-CU10/RESULT.json`. Certificación: **10/20**; sigue CU11.
- CU11 `final-v27-CU11`: **aprobado**, 90,234 s; mismo SHA/Gemma/perfil agente, `turn_error=null`, 17/17 tools correctas. El agente confirmó B2=4 y D2=8 en lecturas separadas tras Guardar; el archivo confirma B2=4, D2 fórmula exacta y caché 8. PID 18276 cerrado sin residuos. Prompt actualizado para observar cada transición de UI; runner pytest 54 + 9 subtests. Receipt `receipts/runs/final-v27-CU11/RESULT.json`. Certificación: **11/20**; sigue CU12.


## CU12 y limpieza de ventanas — SHA 5E195D50…

- `final-v27-CU12`: falló en 239,562 s. Name Box confirmó `C2:C4` aunque `desktop_read_text` de la grilla devolvió 0 renglones; Gemma repitió selección/inspección hasta anti-loop. No se persistieron negrita ni moneda; D2 quedó sin caché. Receipt `receipts/runs/final-v27-CU12/RESULT.json`.
- `diag-discard-final-v27-CU12`: el usuario autorizó descartar los cambios del workbook de prueba exacto. Un click UIA `No guardar` cerró PID 24004; las lecturas stale posteriores figuran en receipt, pero el proceso desapareció. `receipts/runs/diag-discard-final-v27-CU12/RESULT.json`.
- `final-v28-CU12`: aprobado en 77,859 s con `turn_error=null`. El XLSX tiene encabezados bold `[true,true,true,true]`, C2:C4 en moneda, fórmula D2 `=B2+B3+B4` y caché 8. El cleanup cerró PID 32064 y confirmó cero remanentes. `receipts/runs/final-v28-CU12/RESULT.json`.
- Limpieza de Edge Guest de CU05–CU08: PIDs raíz 5844/17420/31608/12508 validados por sus command lines de perfil aislado; todos cerrados, y el inventario final no encontró descendientes con esos perfiles. CU07 tuvo una tecla rechazada por falta de foco antes de cerrar; se corrigió el diagnóstico y CU08 cerró sin error. Receipts `diag-close-final-v27-CU05` a `diag-close-final-v27-CU08`.
- Handoff actualizado: CU13 es el siguiente caso; runner Python `55 passed, 9 subtests passed`, `py_compile` OK, puerto 8898 libre.


## CU13 — persistencia de sólo lectura entre turnos

El fixture sintético tiene D2 `=B2+B3+B4` con caché OOXML 8, cuatro encabezados en negrita y precios C2:C4 en moneda. Gemma abre/lee en el primer turno; el runner cierra por `WM_CLOSE` sólo el PID vinculado al path del fixture y verifica que no queden procesos; Gemma recibe un segundo prompt, reabre la misma ruta y vuelve a leer. La validación requiere dos `desktop_launch` exitosos con igual app/args, dos lecturas de título y de hoja, cleanup entre turnos y hash XLSX idéntico al inicial.

- `final-v29-CU13`: falló por overflow de contexto (10.114 tokens solicitados, n_ctx=8.192). Cleanup posterior, PID 15928.
- `final-v30-CU13`: falló; repitió guardar/cerrar y no reabrió. Cleanup posterior, PID 33960.
- `final-v31-CU13`: falló; cerró, consultó target viejo, no reabrió. XLSX correcto, evidencia UI incompleta.
- `final-v32-CU13`: falló; repitió `desktop_windows`/lecturas con contexto compactado, sin segunda apertura.
- `final-v33-CU13`: **aprobado** en 42,375 s. Dos turnos, dos lanzamientos/lecturas, `turn_error=null`. Se cerró PID 39452 entre turnos; no quedaron procesos. El XLSX quedó inalterado con B2=4, fórmula D2, caché 8, negrita y formatos moneda. SHA producto `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`. Receipt `receipts/runs/final-v33-CU13/RESULT.json`.

El harness tras CU13 pasó `py_compile` y pytest **58 tests + 9 subtests**.

## CU14 — escritura exacta en Bloc de notas

- `final-v34-CU14` falló: Gemma quitó el sufijo del workspace al copiar la ruta larga y el backend bloqueó el tipeo porque el archivo exacto no estaba confirmado. Las lecturas repetidas causaron overflow 8.210/8.192. Se cerró el Notepad del run por el HWND hijo exacto y el PID launcher que contenía el path errado; el fixture esperado quedó vacío.
- El prompt ahora pide verificar `notepad-exact-line.txt` antes de `desktop_type`; el validador exige esa observación en el mismo target, una escritura, Ctrl+S y lectura del marcador después de guardar. Se acortó el workspace de prueba a `cu14-v35`.
- `final-v35-CU14`: **aprobado** en 18,172 s. Gemma abrió Notepad, confirmó el nombre del archivo, escribió `CU14-EXACT-9F2B` una vez, guardó y leyó la línea exacta. El archivo contiene una sola línea. `turn_error=null`, hash producto `5E195D5046BDAA322B7F41EC8F8377CB1101294E0845CAD8A15E25D132430132`. Se cerraron PID hijo 32168 y launcher 34116 del Notepad de prueba; sin remanentes. Receipt `receipts/runs/final-v35-CU14/RESULT.json`.

Harness tras el ajuste: `py_compile` OK y pytest **58 passed + 9 subtests**. Próximo: CU15 en workspace nuevo.

## Continuación recertificación — SHA `9A8963B6…`

- La modificación C++ del backend reabrió la certificación: CU01–CU14 deben aprobar de nuevo en este binario antes de contar 20/20.
- CU15 `final-v36-CU15` falló porque el modelo emitió una llamada UIA `desktop_click_element` dividida por `finish_reason=length`. El prefijo contenía la llamada hasta mitad del `snapshot_id`; la continuación contenía sólo el sufijo. LlamaCode interpretó el sufijo aislado y no ejecutó el clic. El archivo conservó `sleepy`; Notepad de prueba fue cerrado por los PIDs exactos 17004/28252. Receipt `receipts/runs/final-v36-CU15/RESULT.json`.
- Fix en `LlamaAgentBackend`: conservar sólo un `TOOL_CALL` inicial que quedó incompleto por `length`, concatenarlo a las siguientes continuaciones antes del parse y limpiar al terminar la secuencia. `tests/test_agent_wire.cpp` reproduce los dos fragmentos reales; `docs/harness.md` documenta la regla.
- El primer `tests.bat Debug` detectó una aserción demasiado amplia en el nuevo detector (88/89); se restringió la condición y el test focal pasó. Build Debug final y gate completo: **89/89 CTest, 6/6 auxiliares, 9/9 helpers**. SHA `9A8963B6B4490A92FE98BF3A09B812C1526EAEF73DF91506B040F734DA47B33C`.
- CU01 `sha9a-final-CU01` / `sha9a-cu01`: **aprobado** en 61,594 s, `turn_error=null`, 4/4 tools `ok`, visor y validador muestran 42. El modelo agotó el presupuesto de una generación antes de terminar y el daemon realizó continuaciones automáticas. CalculatorApp PID 24900 se cerró tras verificar ruta y hora de inicio del proceso; puerto 8898 libre. Receipt `receipts/runs/sha9a-final-CU01/RESULT.json`.
- CU02 `sha9a-final-CU02` / `sha9a-cu02`: **aprobado** en 11,1 s, `turn_error=null`; las lecturas del visor y el validador independiente muestran `144`. Se cerró CalculatorApp PID 40072 tras verificar ruta/tiempo; puerto 8898 libre. Receipt `receipts/runs/sha9a-final-CU02/RESULT.json`.
- CU03 `sha9a-final-CU03` / `sha9a-cu03`: **aprobado** en 11,1 s, `turn_error=null`; visor y validador muestran `36`. Se cerró CalculatorApp PID 8464 tras verificar ruta/tiempo; puerto 8898 libre. Receipt `receipts/runs/sha9a-final-CU03/RESULT.json`.
- CU04 `sha9a-final-CU04` / `sha9a-cu04`: **aprobado** en 11,1 s, `turn_error=null`; visor y validador muestran `30`. Se cerró CalculatorApp PID 10304 tras verificar ruta/tiempo; puerto 8898 libre. Receipt `receipts/runs/sha9a-final-CU04/RESULT.json`.
- CU05 `sha9a-final-CU05` / `sha9a-cu05`: **aprobado** en 127,3 s, 10/10 tools correctas, dos lecturas coincidentes, una respuesta y fecha Apollo 11 validada. Edge Guest cerró por su perfil aislado exacto; puerto 8898 libre. Receipt `receipts/runs/sha9a-final-CU05/RESULT.json`.
- Certificación actual: **5/20**. Próximo: CU06 `sha9a-final-CU06` / `sha9a-cu06`; no reutilizar workspaces ni run IDs.


## CU07 recertificación SHA 9A8963…

Se probó búsqueda dentro de Wikipedia con el formato de fecha usado por el artículo en inglés. El caso final requiere evidencia de OCR de la fecha tras Enter; leer únicamente el valor del campo Find no es suficiente. Los fallos y correcciones iterativas están fechados en `HANDOFF_IA_Y_BITACORA.md`. Runner actualizado: `py_compile` OK; pytest 59 tests + 9 subtests. No cambió el producto ni el SHA. Siguiente: CU08 con run y workspace nuevos.


## CU08 recertificación SHA 9A8963…

La primera corrida superó el contexto por lecturas de ocho renglones; el prompt ahora filtra y limita cada observación. Se corrigió también el indicador de Apollo 12 para que no dependa de una acción de regreso posterior. Runner: `py_compile` OK; pytest 59 tests + 9 subtests. El producto no cambió. Siguiente: CU09 con run y workspace nuevos.


## CU09 recertificación SHA 9A8963…

El archivo sintético vacío se llenó mediante Excel y se guardó. La lectura independiente del XLSX confirma los valores exactos en A1:C4, sin datos fuera de la tabla. Cleanup cerró el PID de Excel 36240 y verificó cero remanentes. Receipt: `receipts/runs/excel09a/RESULT.json`. Siguiente: CU10 con run y workspace nuevos.


## CU10 recertificación SHA 9A8963…

Se escribió la suma de cantidades y se guardó desde Excel. El validador del archivo confirma fórmula `=B2+B3+B4`, caché 6 y conserva A1:C4. PID 34700 cerrado sin residuos. Receipt: `receipts/runs/excel10a/RESULT.json`. Siguiente: CU11 con IDs nuevos.


## CU11 recertificación SHA 9A8963…

La prueba cambió B2, verificó el total en la interfaz y guardó. El validador independiente confirma B2=4, D2 =B2+B3+B4, caché 8 y A1:C4 intacto. PID 20896 cerrado sin residuos. Receipt: receipts/runs/excel11a/RESULT.json. Siguiente: CU12.


## CU12 recertificación SHA 9A8963…

Se aplicó negrita al encabezado y moneda a los tres precios; el validador independiente confirma formato/persistencia, A1:C4, fórmula D2 y caché 8. PID 31656 cerrado sin residuos. Receipt: receipts/runs/excel12a/RESULT.json. Siguiente: CU13.


## CU13 - recertificacion SHA 9A8963...

- excel13a: fallo del harness; el agente abrio y leyo correctamente, pero una consulta desktop_controls y una segunda lectura read-only invalidaron el criterio exacto de tres llamadas. Archivo intacto.
- excel13b: fallo del harness; el HWND de Excel cambio durante la lectura del titulo y el agente uso el id actualizado. El verificador exigia erroneamente el id previo, por lo que no cerro entre turnos. Archivo intacto y sin procesos Excel restantes.
- Correccion: las observaciones desktop_controls y desktop_read_text redundantes no invalidan el caso; se mantiene una lista permitida de acciones read-only, se exigen dos launches y lecturas por turno, y un cambio de HWND solo vale si la salida de la lectura de titulo declara el nuevo id que se usa en la lectura de hoja. Las acciones de mutacion siguen rechazadas.
- excel13c: aprobado en 44,5 s con turn_error=null. El runner cerro PID 38776 entre turnos y no quedaron procesos. El archivo no cambio: A1:C4, B2=4, formula D2, cache 8, encabezados en negrita y precios en moneda. Receipt: receipts/runs/excel13c/RESULT.json. Estado 13/20; sigue CU14.


## CU06 - Google y Wikipedia (revalidacion de la traza)

browser06egypt navego a Google con historia de Egipto en Wikipedia, observo la fila exacta de Wikipedia, hizo click con la coordenada fresca y abrio el articulo. La UI lee el titulo Historia de Egipto - Wikipedia y el encabezado visible Prehistoria de Egipto pre-3100 a. C. El receipt original habia quedado false-negative por dos reglas del validador; la revalidacion independiente contra el trace original pasa. Detalle y hashes en receipts/runs/browser06egypt/REVALIDATION.json. browser06egyptb no cuenta: Google devolvio su pagina sorry/verificacion.

## CU14 - Bloc de notas

notepad14a aprobo en 20,2 s; nombre del archivo confirmado antes de la unica escritura, Ctrl+S y lectura exacta CU14-EXACT-9F2B. Receipt receipts/runs/notepad14a/RESULT.json. Estado 14/20; siguiente CU15.


## CU15 - buscar y reemplazar en Notepad

notepad15a aprobo en 109,25 s (turn_error=null, cero errores). Se guardo una sola sustitucion de sleepy por curious; el archivo exacto contiene The quick brown fox jumps over the curious dog. Notepad PID 33360 cerrado tras verificar su command line contra el fixture de notepad15work. Receipt receipts/runs/notepad15a/RESULT.json. Estado 15/20; sigue CU16.


## CU16 - rectangulo en Paint

paint16a fallo por overflow 8381/8192 y PNG en blanco. Se redujo a una sola observacion pre-accion; se valida el archivo guardado independientemente. paint16b aprobo en 24,3 s: PNG 400x300, 4310 pixeles no blancos, cuatro lados completos con cobertura 1.0; inspeccion visual confirma un rectangulo. Paint PID 17008 cerrado tras validar la ruta. Receipt receipts/runs/paint16b/RESULT.json. Estado 16/20; sigue CU17.

## CU18 — iteraciones en SHA 49E6207B… (pilotos, no cuentan)

| Corrida | Resultado | Evidencia y ajuste |
|---|---|---|
| `clipboard18f` | Cancelada, sin acciones GUI | Gemma produjo `"app:"notepad"`; llamada malformada no ejecutada. Impulsó la regresión del parser. |
| `clipboard18g` | No aprobado, 121,4 s | XLSX A1 exacto, pero tres lecturas pre-guardado; el validador exige una. |
| `clipboard18h` | No aprobado, 186,1 s | Primera Ctrl+A rechazada por falta de `desktop_focus`; clipboard no contenía el marcador y A1 quedó `A1`. |
| `clipboard18i` | No aprobado, 133,2 s | 16/16 tools; clipboard exacto y XLSX A1 correcto. La lectura final usó `query='A1'` y no verificó “Guardado en Este PC”. |

El parser se reconstruyó como SHA `49E6207BF6C6F582590A8CBBF5C173900E3813721F30D8B6DB227C232306935E`; gates 89/89 CTest + 6/6 auxiliares + 9/9 helpers, runner 64 + 9 subtests. La certificación de este SHA es **0/20**: CU01–CU17 deben repetirse después de estabilizar CU18–CU20. Próximo piloto CU18 con un readback completo sin filtro tras Guardar.

## SHA `71760536…` — recertificación en curso

| Caso | Corrida | Estado | Evidencia |
|---|---|---|---|
| CU19 | `final717-cu19b` | Aprobado | 12/12 tools; alfa vacío, beta con texto exacto antes y después de Ctrl+S y en disco. |
| CU20 | `readseq-cu20b` | Aprobado | 7/7 tools; frase única exacta, leída antes y después de guardar y validada en disco. |
| CU01 | `final717-cu01` | Aprobado | Calculadora mostró 42; turno sin errores. |
| CU02 | `final717-cu02` | Aprobado | Calculadora mostró 144; turno sin errores. |
| CU03 | `final717-cu03` | Aprobado | Calculadora mostró 36; turno sin errores. |
| CU04 | `final717-cu04` | Aprobado | Calculadora mostró 30; turno sin errores. |
| CU05 | `final717-cu05` | Aprobado | Edge Guest, 8/8 tools; resultado Apollo 11 y fecha 20 July 1969; perfil Guest cerrado y cero procesos remanentes. |
| CU06 | `final717-cu06` | Reintentar | Google recibió la búsqueda correcta pero respondió `/sorry` por tráfico inusual; no hubo resultados, clic ni página Wikipedia. Perfil Guest cerrado; no cuenta. |
| CU07 | `q7b` | Aprobado | 12/12 tools; Wikipedia Apollo 11, Ctrl+F y OCR detectó la coincidencia `July 20, 1969`; perfil Guest cerrado. |

Receipts independientes en `receipts/runs/<run-id>/RESULT.json`. CU08 sigue; CU06 se reintenta después del enfriamiento del rate limit. El pase exige resultado visible, clic en “Historia de Egipto - Wikipedia”, lectura del artículo y dato respaldado por esa lectura.

## CU19 — iteración 1 en SHA 49E6207B…

- `final49-cu19a` / `final49-cu19awork` no aprobado (128,313 s). Gemma lanzó Notepad sin ruta, intentó escribir una ruta dentro del documento y luego envió `desktop_key key='CTRL'`; CU19 quedó sin cambios en los archivos alfa/beta. Receipt: `receipts/runs/final49-cu19a/RESULT.json`; traza: `runtime/agent-data/final49-cu19a/agent_llamaagent/`.
- Se cerró el borrador sin título PID 24620, creado por ese turno. El cleanup verificó título y hora de inicio; puerto 8898 libre.
- Prompt y validador CU19 actualizados: dos rutas de launch exactas, confirmación de título para ambos documentos, foco beta explícito, una escritura exacta, Ctrl+S y readback final. El pase combina esta secuencia con lectura independiente de ambos archivos.
- Runner: `py_compile` OK; pytest **67 passed + 9 subtests**. La primera prueba falló por una carpeta temporal ausente; corregido y repetido en verde. Sin cambio de producto/SHA. Estado certificable: **1/20**, CU18 `clipboard18j`; CU19 requiere reintento y CU20 sigue pendiente.

## CU19 — iteración 2 y reparación del guard, SHA 8996887E…

- `final49-cu19b` / `final49-cu19bwork` no aprobado (197,359 s) en SHA `49E6207BF6C6F582590A8CBBF5C173900E3813721F30D8B6DB227C232306935E`: el guard bloqueó el segundo `desktop_launch` de Notepad aunque la ruta beta era distinta. Gemma acabó escribiendo en alpha; beta quedó vacío. El validador rechazó 31 tool calls y el contenido de alpha. Receipt `receipts/runs/final49-cu19b/RESULT.json`.
- Fix general: deduplicación por app+argumentos normalizados; otro documento en la misma app ya se puede lanzar y validar por su título. Una llamada idéntica sigue bloqueada. Regresión C++ de identidad y prompt/validador CU19 reforzados.
- Rebuild Debug y `tests.bat Debug` aprobados: 89/89 CTest, 6/6 auxiliares, 9/9 helpers. `py_compile` OK; pytest **67 passed + 9 subtests**. SHA nuevo `8996887EE07D0408D52A2B032ECF66272330BEEB29FCE144D644D486B7165A5D`; certificación reiniciada a **0/20**. Próximo CU19c, luego CU20 y recertificación completa en orden.


## CU19 — iteración 3, SHA 8996887E…

`final899-cu19c` / `final899-cu19cwork`, Gemma `sys-vram-8-gemma` + `agent-intermedio`, falló en 155,609 s. Alfa abrió y se leyó vacío. La segunda apertura indicó que beta estaba en el mismo HWND (`201262`) y el título reportado pasó a `CU19-beta.txt: Bloc de notas`; foco respondió OK. En la lectura siguiente el target ya no estaba disponible y `desktop_windows` no encontró Notepad. El runner detuvo el caso: 7/8 acciones esperadas, alfa y beta vacíos, ninguna escritura. No quedan procesos de campaña ni listener 8898. Receipt: `receipts/runs/final899-cu19c/RESULT.json`; traza: `runtime/agent-data/final899-cu19c/agent_llamaagent/`. No cambia el SHA ni el estado 0/20. Próximo intento: abrir beta con Ctrl+O desde Notepad, observar el diálogo, confirmar beta y recién entonces escribir/guardar/verificar.


## CU19 — iteración 4, SHA 8996887E…

`final899-cu19d` / `final899-cu19dwork` duró 44,5 s y produjo 14/14 tools exitosas, pero el resultado falla. La traza confirma que Notepad abrió beta desde el diálogo UIA: Ctrl+O; controles `Abrir` y `Nombre de archivo`; `set_value` con el path exacto; snapshot nuevo; `invoke` Abrir; título beta y archivo vacío. El validador esperaba una ventana separada del diálogo y `target_id` en `desktop_key`; el modal owned no sale en `desktop_windows` y esa tool no emite target_id. Esos son falsos negativos del harness. La mutación real también falla: la llamada `desktop_type` lleva exactamente `contenido beta solicitado`, pero el archivo beta guardado contiene `contenido ooooooooooooooo`; la lectura final del modelo sólo consulta el título y no permite saber qué veía en pantalla. Alpha queda vacío. Receipt `receipts/runs/final899-cu19d/RESULT.json`; traza `runtime/agent-data/final899-cu19d/agent_llamaagent/`. El Notepad sintético PID 17992 se cerró ordenadamente; no quedan procesos de suite ni puerto 8898. No cambia el SHA ni el estado 0/20. Corregir el validador y el prompt para confirmar el texto después de escribir y después de guardar, y reintentar con CU19e/workspace nuevo.


## Recertificación vigente — SHA 71760536… (continuación)

| Caso | Corrida | Resultado | Evidencia |
|---|---|---|---|
| CU08 | `q8a` | Aprobado | 148,953 s, 16/16 tools; abrió Apollo 12 en una segunda pestaña y volvió a Apollo 11. |
| CU09 | `final717-cu09` | Aprobado | 97,9 s, `turn_error=null`; A1:C4 exacto, 12 celdas, dimensiones 4×3, XLSX validado. PID Excel de prueba cerrado y sin remanentes. |

Próximo caso: CU11. CU06 sigue en espera de enfriamiento porque Google devolvió su página de tráfico inusual, no resultados de búsqueda.

- CU10 `final717-cu10` falló porque Gemma incluyó los backticks Markdown del prompt en `desktop_launch`, causando una ruta inexistente; el anti-loop detuvo las repeticiones. Sin mutación del fixture.
- Se cambió CU10 al formato de argumentos que funcionó en CU09, con regresión contra backticks. El mismo patrón quedó corregido en CU11, CU13 y CU18. Harness: `py_compile` OK, pytest 69 + 9 subtests.
- CU10 `final717b-cu10`: aprobado en 164,5 s; `turn_error=null`, D1 correcto, D2 fórmula `=B2+B3+B4`, valor almacenado 6 y validación independiente aprobada. Libro cerrado; cero procesos restantes.
- CU11 `final717-cu11`: rechazado en 98 s. UI mostró B2=4 y D2=8, pero Gemma terminó antes de Guardar; XLSX persistió B2=2 y no tenía caché calculada en D2. No cuenta.
- La corrida dejó abierto sólo el Excel del workbook sintético `final717-cu11work` (PID 36012, path comprobado). El diagnóstico leyó el modal de guardado y seleccionó “No guardar” una vez; luego no quedó proceso Excel de ese path.
- Se acortó CU11 y se hizo explícito que la lectura D2 no completa el caso: Guardar debe ser la siguiente tool y el turno no puede finalizar antes del guardado y readback. Harness `py_compile` y pytest: 69 tests + 9 subtests. Próximo CU11 con workspace nuevo `final717b2-cu11work`.
- CU11 `final717b2-cu11`: aprobado en 114,9 s; B2=4, fórmula D2 persistida con caché 8, validación independiente aprobada. Excel de prueba cerrado y sin remanentes.
- CU12 `final717-cu12`: aprobado en 111,3 s; cuatro encabezados en negrita y tres precios en formato moneda guardados, contenido restante intacto. Excel cerrado y sin remanentes.

## Nuevo SHA y recertificación — C3534713…

- CU15 en el SHA anterior `71760536…` no guardó el reemplazo; la UI mostró `curious` pero el archivo en disco conservó `sleepy`. La compuerta pidió lectura post-click y Gemma respondió antes de completar el guardado.
- Se ajustó la compuerta general para identificar esa lectura como checkpoint y continuar pasos pendientes. CU15 ahora exige guardar y verificar el título/texto después de Ctrl+S. Se agregó `DIAG_CLOSE_TEST_NOTEPAD` para cerrar sólo una pestaña sintética y resolver su diálogo de cambios sin guardar.
- `build.bat Debug NOPAUSE` y `tests.bat Debug` pasaron: 89/89 CTest, 6/6 auxiliares, 9/9 helpers. Python `py_compile` y pytest: 70 tests + 9 subtests. `git diff --check` OK con avisos LF→CRLF preexistentes.
- SHA vigente: `C3534713504D2ADF5422E0E77C81315AA8AF683A4650CE0186AA6BACC024E2FF`. Certificación 0/20; la siguiente corrida debe ser CU01. Los pases del SHA 717605 quedan como antecedentes.
- CU01 `c353-cu01`: aprobado en 11,1 s; Calculadora mostró 42 y `artifact_validation.passed=true`. Certificación 1/20; próximo CU02.
- CU02 `c353-cu02`: aprobado en 12,1 s; Calculadora mostró 144 y `artifact_validation.passed=true`. Certificación 2/20; próximo CU03.
- CU03 `c353-cu03`: aprobado en 11,1 s; Calculadora mostró 36 y `artifact_validation.passed=true`. Certificación 3/20; próximo CU04.
- CU04 `c353-cu04`: aprobado en 12,2 s; Calculadora mostró 30 y `artifact_validation.passed=true`. Certificación 4/20; próximo CU05.
- CU05 `c353-cu05`: aprobado en 73,7 s; `turn_error=null`, 9/9 acciones desktop exitosas. La respuesta informó `July 20, 1969` y `20:17 UTC`; el validador encontró una lectura y respuesta coincidentes para Apollo 11, fecha y año. Receipt `receipts/runs/c353-cu05/RESULT.json`. Edge Guest del perfil aislado quedó sin procesos tras la limpieza verificada. Certificación 5/20; próximo CU06.
- CU06 `c353-cu06`: fallido en 167,9 s; se escribió y leyó la URL de búsqueda de Google y se pulsó Enter, pero no hubo lectura posterior, resultado observado, clic ni lectura de Wikipedia. Se desconoce si Google cargó o bloqueó la solicitud; el caso no cuenta. Receipt `receipts/runs/c353-cu06/RESULT.json`. El backend ahora fuerza `desktop_read_text` para los nudges de verificación de escritorio; gates/build y repetición pendientes.

## Nuevo build con observación desktop forzada — SHA `AE85A276…`

- `build.bat Debug NOPAUSE` y `tests.bat Debug` pasaron: 89/89 CTest, 6/6 auxiliares y 9/9 helpers. El request de checkpoint de escritorio exige una herramienta y limita el catálogo a lecturas/observaciones; al completar una lectura exitosa se restauran las tools normales.
- CU06 `ae85-cu06` / `ae85-cu06work`: **no aprobado por CAPTCHA de Google** en 79,8 s. La traza confirma que la lectura posterior a Enter ocurrió y mostró `google.com/sorry/index` junto al aviso de tráfico inusual. El agente no pudo obtener resultado de Wikipedia ni abrir el artículo; informó BLOCKED sin intentar resolver el CAPTCHA. Receipt `receipts/runs/ae85-cu06/RESULT.json`.
- El Edge Guest de prueba se cerró con WM_CLOSE dirigido al PID 14832 después de validar el perfil aislado; cero procesos remanentes.
- CU01 `ae85-cu01` / `ae85-cu01work`: **aprobado** en 11,1 s; calculadora y validador confirman 42, `turn_error=null`. Receipt `receipts/runs/ae85-cu01/RESULT.json`.
- CU02 `ae85-cu02` / `ae85-cu02work`: **aprobado** en 12,2 s; Calculator y validador confirman 144, `turn_error=null`. Receipt `receipts/runs/ae85-cu02/RESULT.json`.
- CU03 `ae85-cu03` / `ae85-cu03work`: **aprobado** en 11,2 s; Calculator y validador confirman 36, `turn_error=null`. Receipt `receipts/runs/ae85-cu03/RESULT.json`.
- CU04 `ae85-cu04` / `ae85-cu04work`: **aprobado** en 11,1 s; Calculator y validador confirman 30, `turn_error=null`. Receipt `receipts/runs/ae85-cu04/RESULT.json`.
- SHA actual `AE85A27680AD2A8B3945F19BD4741177D699046676BE500D580D1E6949449F28`, certificación **4/20**. CU06 fallido no cuenta; repetir CU05 y CU07–CU20, y volver a CU06 después del cooldown de Google.
- CU13 `final717-cu13`: no aprobado en 24,3 s. El launch abrió el libro correcto, pero Gemma agregó `desktop_windows` y `desktop_focus` antes de leer; la política del caso sólo permite launch + dos lecturas. XLSX sin cambios; el runner cerró Excel PID 12888 con WM_CLOSE.
- Se ajustó el prompt de ambos turnos para usar directamente el target retornado por launch y prohibir enumeración/foco extra; se quitaron backticks de la reapertura. pytest: 69 tests + 9 subtests. Repetir CU13 con workspace nuevo `final717b-cu13work`.
- CU13 `final717b-cu13`: aprobado en 42,4 s; dos turnos, reapertura confirmada tras el cierre intermedio, cero acciones extra y hash del XLSX intacto. Excel cerrado al final sin remanentes.
- CU14 `final717-cu14`: aprobado en 33,3 s; línea exacta guardada y re-leída. Se cerró únicamente la pestaña sintética exacta de CU14 con Ctrl+W; la pestaña CU19 activa debajo permaneció intacta.

## Continuación de recertificación — SHA `AE85A276…`

- CU05 `ae85-cu05`: aprobado en 77,7 s; `turn_error=null`, lectura visible de Edge y validador independiente confirman Apollo 11 y 1969. Receipt `receipts/runs/ae85-cu05/RESULT.json`; cero procesos Edge remanentes del perfil Guest.
- CU07 `ae85-cu07`: aprobado en 37,4 s; `turn_error=null`, todas las tools exitosas. Evidencia del validador: Ctrl+F y campo de búsqueda observados, consulta exacta leída antes de Enter, coincidencia `July 20, 1969` visible en OCR del artículo y una sola respuesta coincidente. No pulsó Enter innecesariamente ni modificó la página. Receipt `receipts/runs/ae85-cu07/RESULT.json`; cierre de Edge Guest verificado, cero procesos del perfil.
- CU08 `ae85-cu08`: falló antes de completar la secuencia; el proceso abrió el acceso directo correcto y el perfil aislado, pero el guard del harness rechazó el título de Edge por no incluir literalmente Guest/Invitado. Se corrigió esa condición frágil; receipt fallido preservado.
- CU08 `ae85-cu08b`: aprobado en 164,6 s; `turn_error=null`, todas las tools correctas. El validador confirmó Apollo 11 antes de abrir pestaña, Ctrl+T, Apollo 12 en la segunda, Ctrl+Shift+Tab y Apollo 11 tras regresar. Receipt `receipts/runs/ae85-cu08b/RESULT.json`; Edge Guest cerrado y sin procesos remanentes.
- Corrección de harness/prompt, sin cambio de producto ni SHA: el aislamiento se valida por ruta exacta del acceso directo, argumento vacío y `Local State` del perfil temporal único; el título visible de Edge varía por build/idioma. CU08 ahora instruye usar el mismo `target_id` en cada tool. `py_compile` pasa; pytest `70 passed, 9 subtests passed`.
- Certificación **7/20** en SHA AE85. CU06 sigue pendiente por `google.com/sorry`/tráfico inusual; próximo CU09.
- CU09 `ae85-cu09`: aprobado en 47,5 s; `turn_error=null`, nueve tools exitosas. El XLSX persistido contiene exactamente A1:C4, 12 valores y dimensiones 4×3; contenido validado: Producto/Cantidad/Precio, Café 2 1250, Té 3 800, Agua 1 500. Receipt `receipts/runs/ae85-cu09/RESULT.json`; SHA-256 del archivo `BEE857DBDFF964236CBDAD345D74F569893795267E20DCE06B01895F3AA34B8F`. No quedó Excel abierto con este workbook.
- Certificación **8/20** en SHA AE85. Próximo CU10; CU06 sigue pendiente por el challenge de Google.
- CU10 `ae85-cu10`: aprobado en 125,2 s; `turn_error=null`, 15/15 tools exitosas. El XLSX guardado conserva el bloque A1:C4, B2=2, D1 `Total cantidades`, D2 `=B2+B3+B4` y valor calculado persistido 6; `artifact_validation.passed=true`. Receipt `receipts/runs/ae85-cu10/RESULT.json`; no quedó Excel abierto con el workbook.
- Certificación **9/20** en SHA AE85. Próximo CU11; CU06 sigue pendiente por el challenge de Google.
- CU11 `ae85-cu11`: no aprobado en 167,9 s. Tras `desktop_control_action set_value B2`, Gemma leyó la grilla sin pulsar Enter; el foco permaneció en el cuadro de nombres y `desktop_type '4'` fue rechazado. El turno excedió el contexto (9.867/8.192 tokens); D2 no tuvo valor calculado persistido. Receipt `receipts/runs/ae85-cu11/RESULT.json`.
- Cleanup `cleanup-ae85-cu11-excel`: Gemma pulsó `No guardar` en el PID 14264, verificado por command line contra el workbook sintético exacto. El cleanup recibió errores en lecturas posteriores contra un target obsoleto; la inspección de procesos confirmó que Excel ya no tenía abierto ese workbook. Receipt `receipts/runs/cleanup-ae85-cu11-excel/RESULT.json`.
- Ajuste del prompt CU11, sin cambio de producto/SHA: después de seleccionar B2 en el cuadro de nombres, la próxima tool debe ser Enter; no se lee ni escribe antes. Se quitó una lectura intermedia para reducir contexto y se reforzó el uso de IDs de controles. `py_compile` OK; pytest `70 passed, 9 subtests passed`.
- CU11 `ae85-cu11b`: aprobado en 131,4 s; `turn_error=null`, 20/20 tools correctas. El XLSX guardado confirma B2=4, fórmula D2 `=B2+B3+B4` y valor persistido 8. Receipt `receipts/runs/ae85-cu11b/RESULT.json`; Excel no quedó abierto para ese workbook.
- CU12 `ae85-cu12`: no aprobado en 189,9 s. Tras abrir el workbook, Gemma usó `desktop_windows` y no confirmó el título exacto; `desktop_control_action set_value A1:D1` fue rechazado por la guarda de seguridad del documento. No aplicó negrita ni moneda; caché D2 nula. Receipt `receipts/runs/ae85-cu12/RESULT.json`.
- Cleanup `cleanup-ae85-cu12-excel`: UIA detectó el diálogo de guardado del PID 12224, verificado contra el workbook sintético `ae85-cu12work`, y pulsó `No guardar` una vez. Los readbacks posteriores usaron un target obsoleto; inspección Win32 confirmó cero procesos Excel de ese archivo. Receipt `receipts/runs/cleanup-ae85-cu12-excel/RESULT.json`.
- Ajuste de prompt CU12, sin cambio de producto/SHA: primero leer el título exacto `cu20-computer-usage.xlsx`; si aún no aparece, esperar con `desktop_wait_for` por ese título y releer. Prohíbe enumerar/enfocar o editar antes de esa confirmación. `py_compile` OK; pytest `70 passed, 9 subtests passed`.
- CU12 `ae85-cu12b`: aprobado en 82,0 s; `turn_error=null`, todas las tools exitosas. XLSX guardado con A1:D1 en negrita, C2:C4 en moneda, fórmula D2 y caché 8; `artifact_validation.passed=true`. Receipt `receipts/runs/ae85-cu12b/RESULT.json`; Excel no quedó abierto con ese workbook.
- CU13 `ae85-cu13`: aprobado en 41,4 s; `turn_error=null`, 6/6 tools correctas. Dos turnos y dos `desktop_launch`, título y hoja leídos en ambas aperturas, cierre real entre turnos (PID 33196), sin acciones extra. Fórmula, valor 8, estilos y hash del workbook permanecieron intactos; no quedó Excel abierto. Receipt `receipts/runs/ae85-cu13/RESULT.json`.
- Certificación **12/20** en SHA AE85. Próximo CU14; CU06 sigue pendiente por el challenge de Google.

### 2026-10-18 — CU18, persistencia del portapapeles y verificador UIA, SHA AE85A276…

- CU18 `ae85-cu18f` / `ae85-cu18fwork`: no aprobado en 130,2 s. Copia y portapapeles correctos en ambas sesiones; el agente eligió A1 por el cuadro de nombres y leyó el marcador tras Ctrl+V, pero el XLSX en disco seguía vacío después de Ctrl+S. El cierre inicial dejó Excel abierto. Tras verificar por command line el PID 26736 y el path exacto del archivo sintético, se descartaron los cambios no guardados y se cerró sólo ese PID con la autorización general del usuario; el archivo quedó vacío. Receipts `receipts/runs/ae85-cu18f/RESULT.json`, `cleanup-ae85-cu18f-discard/RESULT.json` y `cleanup-ae85-cu18f-nosave/RESULT.json`.
- Diagnóstico: el UIA de Excel publica `Cuadro de nombres` con rol `combobox`, y `Guardar` como botón `invoke` habilitado sin un atributo `enabled=1`. CU18f usó Ctrl+S; para CU18g el prompt se cambió a la selección UIA de A1, un Ctrl+V y el botón semántico Guardar, sin Ctrl+S. El diálogo de descarte del diagnóstico no tenía un botón UIA llamado No guardar; el PID se cerró por proceso sólo tras confirmar el PID y el path exactos.
- El primer resultado de `ae85-cu18g` quedó rechazado por un falso negativo del parser: la fila UIA real no incluye `enabled=1`, aunque sí expone `[button] invoke` y la traza confirma un clic semántico exacto en Guardar. Se ajustó el validador para aceptar botones invoke salvo que estén explícitamente deshabilitados y exigir el trace exacto de control/ventana. El verificador ahora acepta el rol `combobox` para el cuadro de nombres y contempla el readback opcional en la longitud esperada.
- Revalidación de `ae85-cu18g` con las dos sesiones runtime sin redacción: **aprobado** en 82,8 s; 19/19 tool calls correctas. Notepad→Ctrl+A/C→clipboard verificado antes y después de sesión nueva→Excel exacto→Name Box UIA A1→Enter→un Ctrl+V→botón UIA Guardar→readback completo. Archivo en disco A1=`CU20-CLIPBOARD-7K9-PRESERVE`, una celda no vacía; hash `30f7c87e066302f168e6e243f2eaef6df4c053eed9771195c52fb07adf0c9ef3`. Excel PID 45016 cerrado por el runner, cero remanentes. El recibo original conserva su resultado inicial; evidencia corregida en `receipts/runs/ae85-cu18g/REVALIDATION.json`.
- `py_compile` OK; pytest **71 passed, 9 subtests passed**. Sin cambios al producto ni al SHA `AE85A27680AD2A8B3945F19BD4741177D699046676BE500D580D1E6949449F28`. Certificación vigente **17/20** (CU01–CU05 y CU07–CU18). Pendientes: CU06 (Google sirvió CAPTCHA, no resolverlo ni automatizarlo), CU19 y CU20.


## Auditoría final — 2026-10-20 11:52 ART / 14:52 UTC

- Certificación: **20/20**, un único SHA de producto `AE85A27680AD2A8B3945F19BD4741177D699046676BE500D580D1E6949449F28`; Gemma 4 12B UD-Q3_K_XL, launch `sys-vram-8-gemma`, agente base `agent-intermedio`. La corrida no cambió el ejecutable.
- CU05 `ae85-cu05c` pasó en 20,2 s; búsqueda Apollo 11, fecha de 1969 observada y una respuesta. CU07 `ae85-cu07c` pasó en 120,0 s; Ctrl+F, consulta exacta y coincidencia visible. CU08 `ae85-cu08c` pasó en 119,4 s; confirmó Apollo 11, abrió Apollo 12 en pestaña nueva y volvió a la primera. Los tres recibos tienen `turn_error=null` y `artifact_validation.passed=true`.
- CU06 `ae85-cu06e` completó búsqueda Google, observación del resultado, apertura de Wikipedia y respuesta sobre Narmer/3150 a.C. El `RESULT.json` original se preserva como fallido porque el validador previo sólo aceptaba una lista literal. `REVALIDATION.json` enlaza hashes del recibo, traza raw y validador; la validación revisada exige evidencia textual compartida con el artículo y pasó (`matching_answer_count=1`). No se automatizó CAPTCHA; el usuario ya había despejado el desafío previamente.
- CU05–CU08 usaron la ventana normal de Edge del usuario mediante un acceso directo temporal con `--new-window --no-first-run`, sin Guest/InPrivate ni `--user-data-dir`. Las búsquedas fueron públicas e inocuas; no se navegó una ventana preexistente. No copiar datos personales que puedan aparecer en las trazas raw del perfil normal.
- El cleanup CU08 cerró la ventana de prueba y `desktop_windows` no mostró su HWND `8a0860`. Durante el cierre, Windows recicló el HWND y el modelo hizo una lectura de título (cero renglones de contenido) en el reemplazo antes de enumerar ventanas; no hizo clicks, navegación ni escritura allí. Se endureció el prompt para enumerar inmediatamente después de Alt+F4 y detenerse, sin relecturas.
- Verificación del harness tras ese ajuste: `py_compile` OK; `python -m pytest -q .../test_run_cu20_windows.py`: **72 passed, 9 subtests passed**. No hubo cambios a C++/QML/core en esta iteración; no corresponde rebuild ni `tests.bat Debug` nuevo. Receipts: `receipts/runs/ae85-cu05c/RESULT.json`, `ae85-cu06e/REVALIDATION.json`, `ae85-cu07c/RESULT.json`, `ae85-cu08c/RESULT.json`; cleanup en `cleanup-ae85-cu08c-edge/RESULT.json`.
