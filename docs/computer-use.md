# Computer Use nativo

LlamaCode controla el escritorio mediante un pipeline local y genérico:

```text
snapshot → resolver → stale guard → política → acción → assert → receipt
```

## Snapshot y referencias

`desktop_snapshot`, `desktop_controls` y `desktop_observe` comparten un
`snapshotId` determinista. El snapshot de una ventana incluye la ventana elegida,
su PID, geometría y árbol UI Automation (`automationId`, rol, patrones,
habilitación y foco). No depende del orden Z de ventanas ajenas, que puede cambiar
entre observación y acción. Un snapshot de pantalla conserva el inventario visible
porque su alcance incluye otras ventanas.

`desktop_click_element` y `desktop_control_action` requieren el `snapshot_id`
reciente de `desktop_controls`. Si la ventana o el árbol cambiaron, el backend
rechaza la acción y obliga a observar y resolver de nuevo. No se elige
silenciosamente entre candidatos ambiguos.

En una búsqueda por nombre exacto, si un `window`, `pane` o `group` y un control
interactivo hijo comparten el nombre, `desktop_controls` prioriza el hijo
accionable. Los roles contenedores no se pueden pulsar ni invocar: volvé a buscar
el botón, campo u otro descendiente que represente la acción.

Los `controlId` son referencias opacas y deben copiarse exactamente como
strings JSON entre comillas, aunque contengan puntos o parezcan números. El
backend conserva también el texto decimal si un modelo los serializa como JSON
number, pero los prompts y schemas deben preferir la forma string para no perder
precisión ni confundir un ID con un valor numérico.

La recuperación es acotada: después de `stale` o de un target ambiguo se exige una
observación fresca y se permite como máximo una acción re-resuelta. Si vuelve a
fallar, las mutaciones siguientes se bloquean y la tarea termina como no verificada.
Si `desktop_assert` devuelve `FAIL`, eso no prueba que la acción previa no haya
ocurrido. El agente puede hacer lecturas y una nueva aserción; no repite la acción
con efectos. Una lectura OCR que contiene el texto esperado o una aserción positiva
puede resolver el estado; sin esa evidencia, debe informar `BLOCKED`.

Una mutación que falla tampoco se reenvía con los mismos argumentos en un bucle.
La firma de repetición ignora `snapshot_id`: actualizar sólo el snapshot no convierte
en nueva una acción que falló, por ejemplo `set_value` con `control_id` vacío. Una
observación UIA que muestre un cambio real del árbol libera ese bloqueo; corregir los
argumentos (como usar el `control_id` vigente) permite un nuevo intento.

## Acciones UIA

`desktop_control_action` soporta:

- `click` (alias de `invoke`)
- `invoke`
- `toggle`
- `set_value`
- `select`
- `expand`
- `collapse`
- `range_set`
- `scroll_into_view`
- `read`

Cuando existe un patrón UIA, la operación no roba foco. El fallback de pointer
se reserva para `invoke` cuando el control no expone una operación semántica.
Al usar `desktop_click_element` en un control `Edit` o `Document`, LlamaCode coloca
el foco de teclado y el punto de inserción. En Windows activa la ventana elegida,
enfoca con UI Automation y hace un clic dentro del rectángulo observado del control;
en Linux usa AT-SPI `GrabFocus`. El resultado incluye `keyboardFocusConfirmed`.
En Windows, `desktop_controls` expone `keyboardFocusable` y `hasKeyboardFocus`,
incluidos los `Edit`/`Document` enfocables que no tienen etiqueta; usa el readback
del clic antes de escribir y no repitas la acción si ya confirmó el foco.

En Windows, `desktop_type` inyecta pares Unicode de tecla abajo/arriba con una
pausa de 12 ms entre caracteres para dejar que el control procese cada evento.
`desktop_read_text` puede leer UIA TextPattern en controles Document; para una
ventana foreground cuyo render offscreen omite el editor, OCR usa los píxeles
visibles de esa ventana. Lee
el control después de escribir y compara el texto con el pedido; `ok` sólo
confirma que los eventos se enviaron.

Un aviso de cambio de foco dentro del mismo proceso sólo indica que el control
activo cambió; no prueba que se abrió un diálogo. Observa el estado actual antes
de seguir y no pulses Enter para comprobar si existe un modal.

Para reemplazar el valor de un control exacto con contenido, preferí
`set_value` con el valor completo cuando UI Automation exponga ese patrón y
verificá el readback. Un clic sobre una celda poblada seguido de una tecla puede
entrar en modo edición y anexar el carácter al valor anterior. Si `set_value` no
está disponible, usa navegación semántica o por teclado para seleccionar el valor
completo antes de reemplazarlo; no adivines coordenadas.
`desktop_control_action action='set_value'` requiere que `value` esté presente;
puede ser una cadena vacía intencional para limpiar un control. Si falta la clave,
la tool falla en vez de confirmar una acción que no cambió el control.
En una celda de grilla, si el readback ya muestra el valor nuevo pero el
resultado dependiente sigue igual, confirma la edición con Enter una vez y
vuelve a leer; no repitas `set_value`.

`desktop_key` acepta nombres de tecla como `Enter` y `Return`. Si el modelo envía
exactamente un salto de línea (`LF`, `CR` o `CRLF`) como tecla, LlamaCode lo
normaliza a `ENTER`; el resto de los valores no se recorta ni se altera.

## Postcondiciones y finalización

Para pedidos con varios cambios, el agente debe comprobar cada efecto solicitado.
Enfocar una ventana o un control, seleccionar un rango, leer el contenido o recibir
`ok` de una tool no demuestra que el cambio ocurrió. Después de actuar, observa el
estado afectado y compáralo con la postcondición concreta; la evidencia debe cubrir
el formato o estado pedido, no sólo datos que permanecen iguales. Si la salida de
texto no expone ese estado, usa otra evidencia disponible de la aplicación o informa
que quedó sin verificar. No repitas ciegamente la misma mutación ni afirmes que un
archivo se guardó sin evidencia del guardado.

## Navegación en navegador

Después de escribir una URL o consulta en la barra de direcciones, pulsa `Enter`
una vez (`desktop_key key='ENTER'` si se usó `desktop_type`) y verifica por título
o contenido que la página cargó antes de usar otro atajo. La respuesta de
`desktop_type` recuerda este paso cuando la entrada es una URL o consulta de
navegador. Para buscar dentro de una página, abre el campo con `Ctrl+F`, escribe la
frase exacta en ese campo y lee el contador o la coincidencia visible. Si la página
no cargó o la búsqueda no aparece, observa una vez el estado actual y no repitas
atajos o escrituras sin evidencia de un cambio.

Después de un efecto de escritorio sin verificar, la compuerta de finalización
indica como siguiente llamada una lectura `desktop_read_text` sobre el target exacto
que se acaba de usar; si ese target desapareció, resuelve la ventana con una sola
lectura `desktop_windows`. La compuerta pide sólo observación antes de permitir más
teclas, escritura o clics. Esta lectura es un checkpoint intermedio: después de
observar, el agente continúa los pasos pendientes de la solicitud original. Leer un
resultado no termina una tarea que todavía pide guardar, cerrar o verificar otro
cambio.

Si el modelo intenta finalizar antes de observar, el siguiente request del backend
requiere una tool y sólo ofrece herramientas de observación desktop. Esto mantiene
la lectura posterior al efecto aunque el modelo genere texto final o no siga el
recordatorio del checkpoint. Al recibir una lectura, el backend vuelve a habilitar
las tools normales para que el agente continúe el objetivo original. Si el target ya
no existe, el agente conserva la opción de enumerar ventanas y resolver una lectura
del destino vigente.

Cuando `desktop_launch` recibe argumentos que incluyen una ruta de archivo, LlamaCode
retiene las acciones de escritorio hasta que una lectura de sólo lectura confirme el
nombre de ese archivo en el título de una ventana. El texto del cuerpo no confirma qué
archivo está abierto: puede contener el nombre de otro documento. Si la app restauró una
sesión anterior, `desktop_windows` permite ubicar el target correcto y `desktop_focus` puede
seleccionarlo mientras la guarda sigue activa; después `desktop_read_text` confirma su título.
Teclas, escritura y clics siguen bloqueados hasta esa confirmación. La guarda también aplica
si la ruta indicada no existe y sigue el target si el HWND cambia durante la carga.

Si `desktop_launch` reutiliza una ventana que ya estaba abierta, informa su `target_id` pero
no la selecciona para escribir automáticamente. Primero confirma el título con
`desktop_read_text`; luego usa `desktop_focus` con ese id o pásalo explícitamente a
`desktop_type`/`desktop_key`. El mensaje de lanzamiento indica este paso para evitar que una
ventana existente quede confundida con una ventana nueva ya elegida.

El guard de lanzamientos compara la app y sus argumentos. Repetir la misma solicitud en
una Task se bloquea para limitar bucles; la misma app puede abrir otro documento cuando
los argumentos cambian. Cada apertura vuelve a exigir confirmar el archivo por título
antes de permitir escritura.

## Captura

En Windows, una ventana en foreground se lee desde los píxeles visibles para
recoger contenido que el render offscreen no expone. Para otras ventanas se
intenta primero un render offscreen del HWND mediante
`PrintWindow(PW_RENDERFULLCONTENT)`; si la aplicación no lo soporta, se conserva
el fallback de captura del monitor. Una captura visible puede incluir ventanas
que la tapen; por eso la evidencia corresponde a lo que el usuario ve en pantalla.

Mouse, strokes y teclas siguen requiriendo una sesión interactiva y foco. El
modo semántico no promete mouse físico en background.

## Receipts y seguridad

Toda tool `desktop_*` produce un receipt estructurado con:

- estado `settled` o `failed`;
- tool y estrategia usada;
- hash de payload y resultado;
- snapshot asociado;
- sesión y correlación;
- target y detalle redactado.

Los tools de lectura conservan el tipo `read`. Las acciones físicas y semánticas
usan el tipo `desktop` para que los perfiles de aprobación puedan distinguirlas.
Campos de contraseña, tokens y secretos se redactan en evidencia.

Los artifacts Teach nuevos usan formato v3. Se conservan `precondition`,
`postcondition` y `repair` aunque el evento provenga de un Teach legacy. Los
artifacts v2 siguen siendo legibles.

## Presupuesto del prompt de Teach

Al inyectar una receta larga en el prompt del agente, las intenciones de cada paso
se resumen a 120 caracteres. Targets, ventanas, puntos de strokes y aserciones se
conservan como datos estructurados aparte. Así las recetas extensas no desplazan
las instrucciones operativas ni empujan el contexto fuera del límite del perfil.

## QA

Los tests unitarios cubren hashes, stale guard, receipts, redacción y clasificación
genérica. Los probes que interactúan con el escritorio siguen siendo opt-in para
no mover el mouse ni cambiar el foco durante `ctest`.

### Regresión visual de acción propuesta

La fixture
[computer_use_vision_settings_v1.json](../assets/benchmarks/custom/computer_use_vision_settings_v1.json)
usa una captura sintética de ajustes y fija una llamada semántica esperada. El
benchmark compara la comprensión de la imagen y la acción propuesta sin
ejecutarla.

Califica por separado cuatro resultados: lectura del estado visual, selección
del target exacto, llamada estructurada y resolución/ejecución por el host. La
suite visual no reemplaza las verificaciones UIA de snapshot fresco, política y
receipt, ni demuestra grounding de coordenadas o generalización a otras
aplicaciones. Añade tareas de inyección visual y layouts distintos antes de
promover un modelo como agente visual general.

El probe local reproducible y sus respuestas quedan en
[qwen38-agention-ap-local-benchmark-20260926](../artifacts/qwen38-agention-ap-local-benchmark-20260926/).

El diagnóstico y el uso de la superficie nativa se mantienen documentados en
[`docs/harness.md`](harness.md) y
[`docs/qa_foreground_automation.md`](qa_foreground_automation.md).
