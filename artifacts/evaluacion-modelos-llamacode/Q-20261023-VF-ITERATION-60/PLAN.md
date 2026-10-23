# Q60 — Contención de workers de evaluación sin bajar memoria de modelos

Inicio: 2026-10-23T14:53:22Z
Lock: `f26d05c9-7c30-4588-b24a-973afc127388`

## Objetivo

Auditar la ruta Linux `tools/meter_system_profiles.py`, indicada como pendiente en el accionable P0 de estabilidad. Confirmar si sus procesos hijos quedan dentro del scope de fondo con systemd-oomd y si el cierre del launcher termina el árbol. Corregir la integración si falta, manteniendo los presupuestos solicitados por los modelos.

## Límites y validación

No bajar límites de memoria, VRAM, contexto ni sampling. No compilar, iniciar modelos, servidores reales, benchmark ni usar GPU. Usar pruebas con procesos falsos que no allocan memoria sustancial; preservar GUI, perfiles y pesos. Antes de editar, inspeccionar helper existente, el launcher, documentación y tests relevantes. Si una regresión automatizada puede validarse con la toolchain disponible, correrla; si depende de systemd/oomd o una plataforma ausente, dejar el gate explícito.

## Prerregistro de canario de árbol de procesos — P60-A1

- Sólo después del unit suite CPU existente: iniciar mediante `popen_in_background_scope` un padre Python que cree un único hijo `sleep 60` y deje ambos activos.
- Antes de detener, verificar `/proc/<pid>/oom_score_adj=900` para padre e hijo y propiedades efectivas de la unidad: `Slice=background.slice`, `OOMPolicy=kill`, `KillMode=control-group`, `ManagedOOMMemoryPressure=kill`, `ManagedOOMSwap=kill`, `MemoryHigh=infinity`, `MemoryMax=infinity` y `MemorySwapMax=infinity`.
- Llamar `ScopedProcess.stop()` una sola vez y verificar que padre e hijo ya no estén ejecutándose dentro de 10 segundos; comprobar puerto/GPU sin tocar.
- Gate: todas las propiedades coinciden y no quedan procesos del canario. Si falla, no reintentar; registrar la propiedad o proceso que falló.
- Impacto de recursos: dos procesos pequeños de control, 60 s máximo; cero modelos, servidores, requests, memoria artificial o GPU. Esta prueba evalúa contención del árbol; no estima límites de memoria del modelo.
