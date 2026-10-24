# Q100 · screen E2E de subagentes LlamaCode sobre ASTRA/Strata

**Task:** Q-20261024-VF-ITERATION-100  
**Lock:** `fa90d45b-84a6-4679-9771-bad06cdb16a5`  
**Estado:** preregistrado; no producción modificada.

## Pregunta

¿El `LlamaAgentBackend` real puede ejecutar dos subtareas independientes mediante `task` en worktrees Git y completar la misma carga sintética más rápido con límite de dos workers que con uno, usando el endpoint ASTRA/Strata con dos slots?

## Alcance del contexto

La primera corrida live usó 8K, pero fue inválida: `SubAgentRunner` pidió `max_tokens=32768`, por encima del contexto del servidor, y Strata rechazó las llamadas de subagente con HTTP 400 antes de ejecutar herramientas. Se conserva como `runs/attempt-01-invalid-context/` y no cuenta como resultado funcional. El segundo intento no cargó el modelo: el config apuntaba el log a una ruta relativa incompatible con el `cwd` de Strata; se conserva como `runs/attempt-02-relative-log-path/`. El tercero cargó ASTRA y ejecutó subagentes en ambas GPUs, pero el agente principal insistió en llamar `read_file`; el proxy lo bloqueó antes del despacho. Se conservó como `runs/attempt-03-parent-readfile-blocked/` y no cuenta como medición de throughput.

La enmienda 002 alinea el screen live a **64K** para que el presupuesto de salida heredado de 32K que usa el backend quepa en el contexto del servidor y en el presupuesto por subagente. La enmienda 004 aclara que `read_file` sólo se usa desde subagentes, que cada uno debe leer una vez y que el agente principal sólo puede emitir `task`. El supervisor limpia el log por intento y aborta ante el primer tool call fuera de política para no repetir requests rechazados. Esto sigue siendo una prueba de fan-out a 64K, no del perfil productivo ASTRA DEFAULT a 1M ni de la huella KV en 1M. El test matemático de `adaptiveSubagentLimit` cubre el caso de padre 1M; no cambia el perfil ASTRA/SOL ni habilita adopción.

## Diseño preregistrado

- Modelo/productivo protegido: ASTRA Qwen3.8 Flash-Next IQ2_XS, Strata 0.1.41, MTP4, KV int8; se usa una copia de configuración aislada `parallel:2`, contexto 65536 y sampling conservador. Ambas RTX 3090 y 128 GiB RAM en todos los brazos. No se modifica el perfil ASTRA ni SOL. El test matemático de límite incluye el caso de padre 1M, pero la comparación live no es 1M.
- Ejecutor: `LlamaAgentBackend` en un test opt-in de este checkout; no abre GUI ni usa la sesión de LlamaCode. El proceso vive fuera de Codex en una unidad systemd transient.
- Por semilla (5051–5053), comparar límite del backend 1 worker vs 2 workers, con el mismo servidor ASTRA `parallel:2`. Alternar orden de brazos por semilla para reducir sesgo de caché/orden. Las mismas dos tareas, el mismo contexto y el mismo presupuesto se repiten en cada brazo.
- Dataset artificial: dos archivos de texto temporales con marcadores únicos, no publicados en el prompt principal. El agente principal sólo puede invocar `task`; se le exige emitir ambas subtareas en un mismo turno. Los subagentes reciben instrucciones de leer únicamente el archivo asignado con `read_file`, no modificarlo y devolver el marcador. La carpeta Git y worktrees son descartables.
- Filtro de herramientas antes del modelo: un proxy HTTP loopback elimina toda herramienta salvo `task` para el agente principal y `read_file` para cada subagente. También inspecciona la respuesta SSE completa y la rechaza antes de entregarla a LlamaCode si ASTRA devuelve una herramienta fuera de esa lista. El proxy y todas las worktrees quedan bajo el directorio temporal exclusivo de Q100.
- Métricas: exactitud por subtarea (marcadores exactos en ambas tarjetas y respuesta final), número de `task` en el primer batch, errores, llamadas/herramientas usadas, máximo de tarjetas de subagente en `typing` simultáneo, tiempo E2E y tareas correctas/segundo. Una fase paralela sólo cuenta si se observan dos tarjetas activas al mismo tiempo.

## Gates de decisión

- Cada brazo: 6/6 subtareas correctas en tres semillas, transporte y final completos, cero tools inesperadas/desviaciones, dos `task` en el primer batch.
- Serie: máximo 1 subagente activo por seed. Paralelo: exactamente 2 observados por seed.
- Para abrir una recomendación de experimento de adopción: concurrente no pierde ninguna subtarea en agregado ni por seed y mejora ponderada ≥10% tareas correctas/segundo. Aun pasando, no se cambia producción automáticamente: se deja como accionable para aprobación/validación operacional.
- Si el modelo no emite el batch de dos tareas o la suite es inválida, reportar screen inconcluso; no inventar una ventaja.

## Guardas de memoria y seguridad

- Se conserva la calibración respaldada por ASTRA DEFAULT 1M y SOL dual exitosos, Q97, Q98 y Q99: PSI global moderado sólo avisa (full avg10 ≥20% o some ≥70% durante 30 muestras); parada severa sólo con global full ≥60% o some ≥80% durante 15 muestras consecutivas; hard stop MemAvailable <32 GiB o aumento de OOM/oom_kill. PSI cgroup sigue diagnóstico. Memoria/swap sin topes artificiales.
- Preflight obligatorio: verificar lock propio, ningún servidor externo de inferencia, puertos 8363/8364 libres, ambas GPUs, MemAvailable y PSI. Si hay otro inference server, abortar sin tocarlo. Mantener GUI/ArtCraft y otros procesos ajenos intactos. Cleanup sólo detiene el servidor y el proxy propios.
- Se rehashean fixture/config/código de prueba/runtime y los assets del modelo antes de inferencia; se guarda evidencia de `slots` y asignación dual.

## Tests/build

- El probe C++ es opt-in; la suite Linux habitual debe saltarlo cuando no está definido `LLAMACODE_Q100_SERVER_URL`.
- Validación CPU y `./scripts/tests-linux.sh Release` antes del screen. El gate terminó 93/95: `test_q100_subagent_probe` pasó; fallaron `test_harness_worker_protocol` (el namespace no permite `bwrap` configurar loopback) y `test_tray` (gap observado 34 px frente a 24 px esperado), ambos ajenos al cambio Q100. Los cuatro tests offline del proxy pasaron.
- Nada en Q100 cambia parámetros productivos, drivers, perfiles, swap, THP/NUMA o GUI.

## Intento 04 y enmienda 005

El intento 04 cargó ASTRA en ambas RTX 3090 y avanzó cuatro pares seed/política, pero los marcadores no llegaron a las worktrees. La causa fue el `TMPDIR` dentro del checkout: Git ascendió al repo padre y creó worktrees desde HEAD, omitiendo los archivos sintéticos no versionados. No es un fallo del modelo ni una falla de memoria. El supervisor propio se detuvo; se archivaron logs, cuatro resultados inválidos y postflight. Durante 241 muestras, MemAvailable mínima 69.533 GiB, PSI global full máximo 46.41%, PSI cgroup diagnóstico máximo 88.47%, OOM=0; el detector avisó ante PSI moderada y no abortó. Después del cleanup: 109.997 GiB disponibles, PSI 0%, ambas GPU al baseline.

Enmienda 005: la prueba crea un `TMPDIR` único bajo el artefacto Q100 y pasa `GIT_CEILING_DIRECTORIES` con la raíz del checkout; así el proyecto temporal inicializa su propio repo y el commit fixture se hereda a las worktrees. Se agregó regresión que reproduce `git init` → commit fixture → `git worktree add` y verifica la presencia del marcador. El supervisor corta al primer resultado de calidad fallido/error (gate de seis corridas ya inalcanzable) y limpia únicamente su directorio temporal. CPU: py_compile y 13/13 regresiones PASS. Preflight dual-GPU y nueva corrida pendientes; ASTRA DEFAULT 1M y SOL siguen intactos. Receipt `receipts/q100-amendment-005.json`.

Preflight del intento 05 PASS a 2026-10-24T21:39:56Z: lock Q100 válido; servidores externos=0; 8363/8364/18789 libres; ambas RTX 3090 visibles (1065/110 MiB), MemAvailable 110.194 GiB, PSI some/full=0%, OOM-kill=0; `memory.max/high/swap.max` siguen `max`. Se verificaron de nuevo los 11 hashes del preregistro. Se actualizó/readback el Sheet antes del lanzamiento. Ahora puede iniciarse el screen E2E con ambas GPU; UI y perfiles ASTRA/SOL sin tocar. Receipt `receipts/q100-attempt05-host-preflight.json`.

Primer checkpoint del intento 05 (2026-10-24T21:43:42Z): seed 5051 completó ambos brazos con `qualityPassed=true`: serial 2/2 aceptadas, 12.062 s, maxBusy=1; parallel2 2/2, 12.500 s, maxBusy=2. Primer batch=2 task calls, ambos marcadores exactos, sin tools inesperadas ni bloqueadas, worktrees limpiadas (conteo esperado=1). Esta seed no muestra mejora de velocidad; se esperan las seeds 5052–5053 y no hay recomendación aún. Durante la corrida: ambas RTX 3090, MemAvailable mínima observada 69.638 GiB, PSI global full peak observado ~43%, OOM=0; el aviso transitorio desapareció y el supervisor continúa.
## Enmienda 006 — scorer de mapeo exacto y gate de finalización

La revisión del intento 05 mostró que el scorer original aceptaba ambos marcadores aunque ALPHA y BETA estuvieran intercambiados. También devolvía fallo de proceso cuando las seis corridas concluían correctamente pero el gate de adopción era negativo. La corrección valida una respuesta final anclada (después del último `</think>`) y separa la finalización del screen de su decisión. Se añadieron regresiones para mapeo correcto, etiquetas intercambiadas, valor ausente y razonamiento correcto con respuesta final incorrecta. Preregistro `receipts/q100-amendment-006-preregistration.json`. Próximo paso: ejecutar `./scripts/tests-linux.sh Release` en CPU, registrar resultado y hash reconstruido. No repetir inferencia/GPU: el re-score corregido ya da serial 3/3 frente a paralelo 1/3 y el throughput paralelo es 5,11% menor.
## Cierre Q100 — 2026-10-24

Attempt05 completó seis corridas con tres seeds. El re-score exacto encontró 3/3 seeds correctas en serial y 1/3 en paralelo; parallel2 invirtió ALPHA/BETA en seeds 5051 y 5053 aunque cada subagente devolvió su archivo asignado. Throughput bruto paralelo/serial 0,9489 y correct E2E throughput 0,3163. No adopción. Enmienda 006 corrigió el scorer y el status del test; `tests-linux.sh Release` pasó 95/95, el target Q100 7/0/1 (live opt-in skip), y replays CPU del guard 10/10.

Detector en las 220 muestras del intento: MemAvailable mínima 69.386 GiB, PSI full global máximo 46.52% y 34 avisos; OOM=0. La guarda avisó y permitió concluir las seis corridas; cleanup PASS. Se conserva ASTRA DEFAULT 1M/SOL histórico sin cambios; Q100 fue contexto 65.536. Resultado completo en `RESULTS.md`.

